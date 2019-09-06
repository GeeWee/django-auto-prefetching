import copy
import logging

import wrapt
from django.db.models import Field

from django_auto_prefetching.QueryLogger import QueryLogger
from django_auto_prefetching.prefetch_description import PrefetchDescription
from django_auto_prefetching.proxy import Proxy

logger = logging.getLogger()


def proxy_model_class(model, prefix, originating_iterator):
    if not hasattr(originating_iterator, '_django_auto_prefetching_should_prefetch_fields'):
        originating_iterator._django_auto_prefetching_should_prefetch_fields = PrefetchDescription(set(), set())

    # Change model class here, so it won't carryover to the rest of the models
    # model.__class__ = ModelProxy

    for field in model._meta.get_fields():
        monkey_patch_field(originating_iterator, model, field)

    return model


def monkey_patch_field(originating_iterator, model, field: Field):
    if not field.is_relation:
        return

    if field.one_to_one or field.many_to_one:
        def update_iterator():
            originating_iterator._django_auto_prefetching_should_prefetch_fields.select_related.add(field.name)
    elif field.one_to_many:
        def update_iterator():
            originating_iterator._django_auto_prefetching_should_prefetch_fields.prefetch_related.add(field.name)
    else:
        # Else many to many
        def update_iterator():
            originating_iterator._django_auto_prefetching_should_prefetch_fields.prefetch_related.add(field.name)

    relational_field = field
    logger.debug(f'Patching relational field "{field.name}"')

    # Get the field without invoking __get__ to get the actual class and not the
    # data descriptor value
    corresponding_field = model.__class__.__dict__.get(field.name)

    print('field', field)

    # Subclass it and override _get_
    class FieldSubclass(corresponding_field.__class__):

        def __get__(self, instance, owner):
            if not originating_iterator.has_prefetched:
                update_iterator()
                print('get!!s', field.name)
                # print(QueryLogger.get_traceback(limit=3))
                print('attaching to queryset')

            return super().__get__(instance, owner)

    corresponding_field.__class__ = FieldSubclass

# def __getattribute__(self, name):
#     # Now we check whether or not it's been cached
#     is_cached_already = relational_field.is_cached(unproxied_model)
#     if is_cached_already:
#         logger.debug(f'Model field "{name}" was cached already.')
#         return getattr(unproxied_model, name)
#
#     logger.debug(f'Model field "{name}" was not cached already. Prefetching it on next iteration')
#     qs = self.queryset
#
#     # Put the description on the queryset
#     qs._django_auto_prefetching_should_prefetch_fields = PrefetchDescription(set(), set())
#
#     # Depending on the field type, we should add it to prefetch_related or select_related
#     if relational_field.one_to_one or relational_field.many_to_one:
#         qs._django_auto_prefetching_should_prefetch_fields.select_related.add(self.prefix + relational_field.name)
#     elif relational_field.one_to_many:
#         qs._django_auto_prefetching_should_prefetch_fields.prefetch_related.add(self.prefix + relational_field.name)
#
#     # TODO we currently don't support many to many, as the way to tell whether or not they've been prefetched
#     #  is different
#
#     # Here if we have a relational field that manifests in just a single object, we can simply wrap
#     # that model in a ModelProxy with a new prefix, to build a new path there
#     if relational_field.one_to_one or relational_field.many_to_one:
#         related_model = getattr(unproxied_model, name)
#         # The prefix here is the name of our current model
#         prefix = f"{self.prefix}{relational_field.name}__"
#         return ModelProxy(related_model, originating_queryset=self.queryset, prefix=prefix)
#
#     # If not a relational field, just return as-is as there's no point in proxying any further
#     return getattr(unproxied_model, name)
#

class ModelProxy(wrapt.ObjectProxy):
    def __init__(self, object_to_proxy, originating_queryset, prefix: str):
        super().__init__(object_to_proxy)
        self.prefix = prefix
        self.queryset = originating_queryset # TODO should probably be a weakset or something like that

    def __getattribute__(self, name):
        # Here we need to look at whether or not we've tried to prefetch with this queryset. If we have
        # skip this whole thing.
        logger.debug(f'ModelProxy getattr called with "{name}"')
        unproxied_model = object.__getattribute__(self, '__wrapped__')

        model_fields = unproxied_model._meta.get_fields()

        relational_field = None
        for field in model_fields:

            if field.name == name and field.is_relation:
                relational_field = field
                logger.debug(f'Trying to access relational field "{name}"')
                break

        if not relational_field:
            return getattr(unproxied_model, name)

        # Now we check whether or not it's been cached
        is_cached_already = relational_field.is_cached(unproxied_model)
        if is_cached_already:
            logger.debug(f'Model field "{name}" was cached already.')
            return getattr(unproxied_model, name)

        logger.debug(f'Model field "{name}" was not cached already. Prefetching it on next iteration')
        qs = self.queryset

        # Put the description on the queryset
        qs._django_auto_prefetching_should_prefetch_fields = PrefetchDescription(set(), set())

        # Depending on the field type, we should add it to prefetch_related or select_related
        if relational_field.one_to_one or relational_field.many_to_one:
            qs._django_auto_prefetching_should_prefetch_fields.select_related.add(self.prefix + relational_field.name)
        elif relational_field.one_to_many:
            qs._django_auto_prefetching_should_prefetch_fields.prefetch_related.add(self.prefix + relational_field.name)

        # TODO we currently don't support many to many, as the way to tell whether or not they've been prefetched
        #  is different

        # Here if we have a relational field that manifests in just a single object, we can simply wrap
        # that model in a ModelProxy with a new prefix, to build a new path there
        if relational_field.one_to_one or relational_field.many_to_one:
            related_model = getattr(unproxied_model, name)
            # The prefix here is the name of our current model
            prefix = f"{self.prefix}{relational_field.name}__"
            return ModelProxy(related_model, originating_queryset=self.queryset, prefix=prefix)

        # If not a relational field, just return as-is as there's no point in proxying any further
        return getattr(unproxied_model, name)