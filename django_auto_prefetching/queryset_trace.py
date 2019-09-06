import copy
import logging
from typing import Iterator

import wrapt
from django.db.models import QuerySet

from django_auto_prefetching.prefetch_description import PrefetchDescription
from django_auto_prefetching.proxy import Proxy
from django_auto_prefetching.ModelProxy import ModelProxy, proxy_model_class

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