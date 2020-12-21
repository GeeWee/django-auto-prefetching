"""
A package for automatic prefetching of data with select_related and prefetch_related in Django and django-rest-framework
"""
import inspect
import logging
from typing import Type, Union

from django.core.exceptions import FieldError
from django.db import models
from rest_framework.relations import (
    RelatedField,
    ManyRelatedField,
    HyperlinkedIdentityField,
    HyperlinkedRelatedField,
)
from rest_framework.serializers import ModelSerializer, BaseSerializer, ListSerializer

logger = logging.getLogger("django-auto-prefetching")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARNING)

SERIALIZER_SOURCE_RELATION_SEPARATOR = '.'

class AutoPrefetchViewSetMixin:
    def get_queryset(self):
        serializer = self.get_serializer()
        qs = super().get_queryset()

        return prefetch(qs, serializer)


def prefetch(queryset, serializer: Type[ModelSerializer]):
    select_related, prefetch_related = _prefetch(serializer)
    try:
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        return queryset
    except FieldError as e:
        raise ValueError(
            f"Calculated wrong field in select_related. Do you have a nested serializer for a ForeignKey where "
            f"you've forgotten to specify many=True? Original error: {e}"
        )


def _prefetch(
    serializer: Union[Type[BaseSerializer], BaseSerializer], path=None, indentation=0
):
    """
    Returns prefetch_related, select_related
    :param serializer:
    :return:
    """
    prepend = f"{path}__" if path is not None else ""
    class_name = getattr(serializer, "__name__", serializer.__class__.__name__)
    logger.debug("\n")

    logger.debug(
        f'{" " * indentation}LOOKING AT SERIALIZER: {class_name} from path: {prepend}'
    )

    select_related = set()
    prefetch_related = set()

    if inspect.isclass(serializer):
        serializer_instance = serializer()
    else:
        serializer_instance = serializer

    try:
        fields = getattr(
            serializer_instance, "child", serializer_instance
        ).fields.fields.items()
    except AttributeError:
        # This can happen if there's no further fields, e.g. if we're passed a PrimaryKeyRelatedField
        # as the nested representation of a ManyToManyField
        return (set(), set())

    for name, field_instance in fields:
        field_type_name = field_instance.__class__.__name__
        logger.debug(
            f'{" " * indentation} Field "{name}", type: {field_type_name}, src: "{field_instance.source}"'
        )

        # We potentially need to recurse deeper
        if isinstance(
            field_instance, (BaseSerializer, RelatedField, ManyRelatedField)
        ) and not isinstance(field_instance, IGNORED_FIELD_TYPES):
            logger.debug(
                f'{" " * indentation}Found related: {field_type_name} ({type(field_instance)}) - recursing deeper'
            )
            field_path = f"{prepend}{field_instance.source}"

            # Fields where the field name *is* the model.
            if isinstance(field_instance, RelatedField):
                logger.debug(
                    f'{" " * indentation} Found related field: {field_type_name} - selecting {field_instance.source}'
                )
                select_related.add(f"{prepend}{field_instance.source}")

                """
                If we have multiple entities, we need to use prefetch_related instead of select_related
                We also need to do this for all further calls
                """
            elif isinstance(field_instance, (ListSerializer, ManyRelatedField)):
                logger.debug(
                    f'{" " * indentation} Found *:m relation: {field_type_name}'
                )
                prefetch_related.add(field_path)

                # If it's a ManyRelatedField, we can only get the actual underlying field by querying child_relation
                nested_field = getattr(field_instance, "child_relation", field_instance)

                select, prefetch = _prefetch(nested_field, field_path, indentation + 4)
                prefetch_related |= select
                prefetch_related |= prefetch
            else:
                logger.debug(
                    f'{" " * indentation} Found *:1 relation: {field_type_name}'
                )
                select_related.add(field_path)
                select, prefetch = _prefetch(
                    field_instance, field_path, indentation + 4
                )
                select_related |= select
                prefetch_related |= prefetch
        
        elif SERIALIZER_SOURCE_RELATION_SEPARATOR in field_instance.source:
            # The serializer declares a field from a related object.
            relation_name = field_instance.source.split(SERIALIZER_SOURCE_RELATION_SEPARATOR)[0]
            if is_model_relation(serializer.Meta.model, relation_name):
                logger.debug(
                    f'{" " * indentation} Found *:1 relation: {relation_name}'
                )
                select_related.add(relation_name)

    return (select_related, prefetch_related)

def is_model_relation(model, field_name):
    field = next((field for field in model._meta.fields if field.name == field_name), None)
    return isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField)



IGNORED_FIELD_TYPES = (
    # This is a subclass of RelatedField, but it always generates a URL no matter the depth, so we shouldn't prefetch
    # based on it.
    HyperlinkedRelatedField
)
