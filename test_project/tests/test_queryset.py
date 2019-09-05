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


        with self.assertNumQueries(3):
            qs = SubclassOfQuerySet(model=ChildB)

            for i in qs:
                print('--> printing i:')
                print('-->',i)
                print('--> printing i parent:')
                print('-->', i.parent)
                print('--> printing i parent AGAIN:')
                print('-->', i.parent)


        assert False
        pass


class SubclassOfQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)

    def __iter__(self):
        super_iter = super().__iter__()
        return ProxyingIterator(super_iter, self)


class ProxyingIterator:
    def __init__(self, original, originating_queryset) -> None:
        super().__init__()
        self.original = original
        self.originating_queryset = originating_queryset

    def __next__(self):
        obj = next(self.original)
        proxied_object = ModelProxy(obj, self.originating_queryset)
        return proxied_object