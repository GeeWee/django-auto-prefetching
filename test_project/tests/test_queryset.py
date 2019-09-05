import copy
from typing import Iterator

from django.db import connection
from django.db.models.query import QuerySet
from django.test import TestCase

from django_auto_prefetching.proxy import Proxy, ModelProxy
from django_auto_prefetching.queryset_trace import PrefetchDescription
from test_project.models import ChildB, TopLevel


class TestTracingQuerySet(TestCase):
    def test_tracing_queryset_will_fetch_many_to_one_fields_directly_on_the_model(self):
        parent1 = TopLevel.objects.create(
            top_level_text='1'
        )
        parent2 = TopLevel.objects.create(
            top_level_text='1'
        )
        for i in range(0, 5):
            ChildB.objects.create(
                parent=parent1,
                childB_text=i
            )
        for i in range(0, 5):
            ChildB.objects.create(
                parent=parent2,
                childB_text=i
            )

        # Here we should get only three queries.
        # 1. For the .all call
        # 2. For the .parent lazyload
        # 3. One for the internal .all() call with the prefetched parents
        with self.assertNumQueries(3):
            qs = SubclassOfQuerySet(model=ChildB)

            for i in qs:
                print('---------> printing i:')
                print('--------->', i)
                print('---------> printing i parent:')
                print('--------->', i.parent)
                print('---------> printing i parent AGAIN:')
                print('--------->', i.parent)

    def test_tracing_queryset_will_fetch_one_to_many_fields_directly_on_the_model(self):
        for i in range(0, 10):
            parent = TopLevel.objects.create(
                top_level_text=i
            )
            ChildB.objects.create(
                parent=parent,
                childB_text=i
            )

        # Here we should get only four queries.
        # 1. For the .all call
        # 2. For the .children_b lazyload
        # 3. 2 for the internal .all() call with prefetch_related of the children objects
        with self.assertNumQueries(3):
            qs = SubclassOfQuerySet(model=TopLevel)

            for i in qs:
                print('---------> printing i:')
                print('--------->', i)
                for kid in i.children_b.all():
                    print('----------------> kid', kid)

        assert False


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
        prefetch_fields: PrefetchDescription = getattr(self.originating_queryset, '_django_auto_prefetching_should_prefetch_fields', None)
        if prefetch_fields and not self.has_prefetched:
            print(f'Queryset is prefetching fields {prefetch_fields}')

            # This is a copy of the queryset without the cache
            copied_queryset: SubclassOfQuerySet = copy.deepcopy(self.originating_queryset)

            # TODO here we need to ensure that when we generate the prefetches, for nested accesses, we generate
            # them correctly
            copied_queryset = copied_queryset.select_related(*prefetch_fields.select_related)
            copied_queryset = copied_queryset.prefetch_related(*prefetch_fields.prefetch_related)

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