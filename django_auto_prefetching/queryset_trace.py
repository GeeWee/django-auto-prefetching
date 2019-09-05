import copy
from typing import Iterator

from django.db.models import QuerySet

from django_auto_prefetching.prefetch_description import PrefetchDescription
from django_auto_prefetching.proxy import ModelProxy


class TracingQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)

    def __iter__(self):
        super_iter = super().__iter__()
        return ProxyingIterator(super_iter, self)

    def _original_iterator(self):
        return super().__iter__()


class ProxyingIterator:
    def __init__(self, iterator: Iterator, originating_queryset: TracingQuerySet) -> None:
        super().__init__()
        self.iterator = iterator
        self.originating_queryset = originating_queryset
        self.pk_cache = set()
        self.has_prefetched = False

    def __next__(self):
        prefetch_fields: PrefetchDescription = getattr(self.originating_queryset, '_django_auto_prefetching_should_prefetch_fields', None)
        if prefetch_fields and not self.has_prefetched:
            print(f'Queryset is prefetching fields {prefetch_fields}')

            # This is a copy of the queryset without the cache
            copied_queryset: TracingQuerySet = copy.deepcopy(self.originating_queryset)

            # TODO here we need to ensure that when we generate the prefetches, for nested accesses, we generate
            # them correctly
            copied_queryset = copied_queryset.select_related(*prefetch_fields.select_related)
            copied_queryset = copied_queryset.prefetch_related(*prefetch_fields.prefetch_related)

            self.iterator = copied_queryset._original_iterator()
            self.has_prefetched = True


        obj = next(self.iterator)
        # If we've already been over the object, don't return it
        if obj.pk in self.pk_cache:
            print(f'Skipping model with pk <{obj.pk}>')
            return next(self)

        # No need to wrap in a proxy if we've spent our prefetch
        if self.has_prefetched:
            return obj

        self.pk_cache.add(obj.pk)
        proxied_object = ModelProxy(obj, self.originating_queryset)
        return proxied_object