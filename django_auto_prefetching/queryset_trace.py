import copy
import logging
from typing import Iterator

from django.db.models import QuerySet, Field
from django_auto_prefetching.ModelProxy import proxy_model_class

from django_auto_prefetching.utils import PrefetchDescription

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def trace_queryset(queryset):
    logger.debug('Tracing a queryset')
    queryset.__class__ = TracingQuerySet
    return queryset


class TracingQuerySet(QuerySet):
    def __iter__(self):
        logger.debug("Proxying Queryset iterator")
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
            logger.debug(f'Commencing automatic pre-fetching with fields {prefetch_fields}')

            # This is a copy of the queryset without the cache, and the special methods
            copied_queryset: QuerySet = copy.deepcopy(self.originating_queryset)
            copied_queryset.__class__ = QuerySet

            copied_queryset = copied_queryset.select_related(*prefetch_fields.select_related)
            copied_queryset = copied_queryset.prefetch_related(*prefetch_fields.prefetch_related)

            # Replace the iterator we're proxying with the fresh one with the prefetches
            self.iterator = iter(copied_queryset)
            self.has_prefetched = True

        obj = next(self.iterator)
        logging.debug(f'Iterator supplying next model {obj.pk}')
        # If we've already been over the object, don't return it
        if obj.pk in self.pk_cache:
            logging.debug(f'Skipping model with pk <{obj.pk}>')
            return next(self)

        # No need to wrap in a proxy if we've spent our prefetch
        if self.has_prefetched:
            # logging.debug("Returning object as-is, as we've already prefetched")
            return obj

        self.pk_cache.add(obj.pk)
        proxied_object = proxy_model_class(obj, '', self)
        logging.debug('Returning proxied model')
        return proxied_object


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
