import copy
from typing import Iterator

from django.db import connection
from django.db.models.query import QuerySet
from django.test import TestCase

from django_auto_prefetching.proxy import Proxy, ModelProxy
from test_project.models import ChildB, TopLevel


class TestTracingQuerySet(TestCase):
    def test_foo(self):
        parent1 = TopLevel.objects.create(
            top_level_text='1'
        )
        parent2 = TopLevel.objects.create(
            top_level_text='1'
        )
        ChildB.objects.create(
            parent=parent1,
            childB_text='1'
        )
        ChildB.objects.create(
            parent=parent1,
            childB_text='2'
        )
        ChildB.objects.create(
            parent=parent2,
            childB_text='3'
        )
        ChildB.objects.create(
            parent=parent2,
            childB_text='4'
        )
        ChildB.objects.create(
            parent=parent1,
            childB_text='2'
        )
        ChildB.objects.create(
            parent=parent2,
            childB_text='3'
        )
        ChildB.objects.create(
            parent=parent2,
            childB_text='4'
        )


        with self.assertNumQueries(3):
            qs = SubclassOfQuerySet(model=ChildB)

            for i in qs:
                print('---------> printing i:')
                print('--------->', i)
                print('---------> printing i parent:')
                print('--------->', i.parent)
                print('---------> printing i parent AGAIN:')
                print('--------->', i.parent)


        assert False
        pass


class SubclassOfQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)

    def __iter__(self):
        super_iter = super().__iter__()
        return ProxyingIterator(super_iter, self)

    def _original_iterator(self):
        return super().__iter__()




class ProxyingIterator:
    def __init__(self, iterator: Iterator, originating_queryset: SubclassOfQuerySet) -> None:
        super().__init__()
        self.iterator = iterator
        self.originating_queryset = originating_queryset
        self.pk_cache = set()
        self.has_prefetched = False

    def __next__(self):
        prefetch_fields = getattr(self.originating_queryset, '_django_auto_prefetching_should_prefetch_fields', None)
        if prefetch_fields and not self.has_prefetched:
            print(f'Queryset is prefetching fields {prefetch_fields}')

            # This is a copy of the queryset without the cache
            copied_queryset: SubclassOfQuerySet = copy.deepcopy(self.originating_queryset)

            # TODO here we need to ensure that when we generate the prefetches, for nested accesses, we generate
            # them correctly
            copied_queryset = copied_queryset.prefetch_related(*prefetch_fields)

            # TODO The iterator we get here is also a proxying iterator...
            self.iterator = copied_queryset._original_iterator()
            self.has_prefetched = True

            # How do we prefetch the queryset here? We need to keep this iterator, but we need to change what it iterates over
            # We can probably clone the queryset, and iterate over that instead, if we keep a cache of the stuff
            # we've already been through


        obj = next(self.iterator)
        # If we've already been over the object, don't return it
        if obj.pk in self.pk_cache:
            print(f'Skipping model with pk <{obj.pk}>')
            return next(self)


        self.pk_cache.add(obj.pk)
        proxied_object = ModelProxy(obj, self.originating_queryset)
        return proxied_object