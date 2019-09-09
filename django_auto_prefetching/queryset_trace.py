import copy
import logging
import threading
import uuid
from contextlib import contextmanager
from pprint import pprint
from typing import Iterator

from django.db.models import QuerySet, Field

from django_auto_prefetching import dap_logger
from django_auto_prefetching.utils import PrefetchDescription


"""
Generate a threadlocal uuid here, in case multiple threads try to use the model simultaneously, we'll want the fields
to only update the queryset for the thread we care about. We'll then only do something if the uuid when the field
was created, matches the uuid when the __get__ lookup happens 
"""

threadlocal = threading.local()


@contextmanager
def trace_queryset(queryset):
    try:
        threadlocal.id = uuid.uuid4()
        dap_logger.error('Tracing a queryset')
        queryset.__class__ = TracingQuerySet
        yield queryset
    finally:
        queryset.revert_changes()
        queryset.spent = True


class TracingQuerySet(QuerySet):
    spent = False

    revert_functions = []

    def revert_changes(self):
        for function in self.revert_functions:
            function()


    def __iter__(self):
        if self.spent:
            raise NotImplementedError('Cannot use a TracingQueryset multiple times')
        dap_logger.info("Proxying Queryset iterator")
        iterator = super().__iter__()
        return ProxyingIterator(iterator, self)


class ProxyingIterator:
    def __init__(self, iterator: Iterator, originating_queryset: TracingQuerySet) -> None:
        super().__init__()
        self.iterator = iterator
        self.originating_queryset = originating_queryset
        self.pk_cache = set()
        self.has_prefetched = False

    def __next__(self):
        prefetch_fields: PrefetchDescription = getattr(self, '_django_auto_prefetching_should_prefetch_fields', None)
        if prefetch_fields and not self.has_prefetched:
            self.originating_queryset.revert_changes()
            dap_logger.info(f'!!!!!Commencing automatic pre-fetching with fields {prefetch_fields}')

            # This is a copy of the queryset without the cache, and the special methods
            copied_queryset: QuerySet = copy.deepcopy(self.originating_queryset)
            copied_queryset.__class__ = QuerySet

            copied_queryset = copied_queryset.select_related(*prefetch_fields.select_related)
            copied_queryset = copied_queryset.prefetch_related(*prefetch_fields.prefetch_related)

            # Replace the iterator we're proxying with the fresh one with the prefetches
            self.iterator = iter(copied_queryset)
            self.has_prefetched = True

        obj = next(self.iterator)
        dap_logger.info(f'Iterator supplying next model {obj.pk}')
        # If we've already been over the object, don't return it
        if obj.pk in self.pk_cache:
            dap_logger.info(f'Skipping model with pk <{obj.pk}>')
            return next(self)

        # No need to wrap in a proxy if we've spent our prefetch
        if self.has_prefetched:
            # dap_logger.info("Returning object as-is, as we've already prefetched")
            return obj

        self.pk_cache.add(obj.pk)

        monkey_patch_model(obj, self, '')

        # dap_logger.info(f'Returning proxied model {}: ')
        return obj


def monkey_patch_model(model, originating_iterator, prefix):
    dap_logger.debug(f'Monkeypatching {model.__class__} with prefix "{prefix}"')
    if not hasattr(originating_iterator, '_django_auto_prefetching_should_prefetch_fields'):
        originating_iterator._django_auto_prefetching_should_prefetch_fields = PrefetchDescription(set(), set())


    for field in model._meta.get_fields():
        monkey_patch_field(originating_iterator, model, field, prefix)


# TODO we need to special case a prefetch_related branch here
def monkey_patch_field(originating_iterator, model, field: Field, prefix: str):
    if not field.is_relation:
        return

    if field.one_to_one or field.many_to_one:
        def update_iterator():
            name = f'{prefix}{field.name}'
            logging.debug(f"Updating iterator to select_related {name}")
            originating_iterator._django_auto_prefetching_should_prefetch_fields.select_related.add(name)
    elif field.one_to_many:
        logging.debug(f'Not patching 1->many field "{field.name}"')
        return
    else:
        logging.debug(f'Not patching many->many field "{field.name}"')
        return

    # Get the field without invoking __get__ to get the actual class and not the
    # data descriptor value
    corresponding_field = model.__class__.__dict__.get(field.name)

    threadlocal_id = threadlocal.id

    # Subclass it and override _get_
    class TracingField(corresponding_field.__class__):
        exhausted = False

        def __get__(self, instance, owner):
            dap_logger.debug(f'get: "{field.name}"')

            if originating_iterator.has_prefetched or threadlocal_id != threadlocal.id or self.exhausted:
                logging.debug('TracingField should not modify anything.')
                return super().__get__(instance, owner)

            update_iterator()


            model =  super().__get__(instance, owner)
            # Monkey patch the model we get with the new prefix
            new_prefix = f'{prefix}{calculate_field_name(field)}__'

            monkey_patch_model(model, originating_iterator, new_prefix)

            self.exhausted = True

            return model


    # Build revert function
    original_class = corresponding_field.__class__

    def reverse_class_change():
        dap_logger.info(
            f'Reverting field "{field.name}" from {corresponding_field.__class__} to original class {original_class}')
        corresponding_field.__class__ = original_class

    # Change class
    corresponding_field.__class__ = TracingField

    # Append the reverse function to the queryset
    originating_iterator.originating_queryset.revert_functions.append(reverse_class_change)


def calculate_field_name(field: Field) -> str:
    """
    This is a method to calculate the field name for the prefetch_related/select_related string. We can't just use
    field.name, as that seems to return the wrong name for ForeignKeys, without a 'related' name (e.g. 'containers' (model in plural) instead
    of 'container_set' which is the correct reverse lookup.
    """
    # If it's a many to one without the related_name set, mimick djangos behaviour and create the field name with _set afterwards
    if field.many_to_many or field.one_to_many and getattr(field, "related_name", None) is None:
        # a _set field name
        return field.name + "_set"

    return field.name