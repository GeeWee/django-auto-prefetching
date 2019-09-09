import logging

from django.db import connection
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor, ForwardOneToOneDescriptor, \
    ForwardManyToOneDescriptor, ReverseOneToOneDescriptor

from django_auto_prefetching.utils import log_queries, QueryLogger

# logging.basicConfig(level=logging.DEBUG)

from django.db.models import QuerySet
from django.test import TestCase

import unittest

# Show full diff in unittest
unittest.util._MAX_LENGTH = 2000

logger = logging.getLogger()

"""
TODO these tests don't work, because the proxy we're currently using doesn't do proxying
properly with e.g. str() where it simply calls str() on the underlying object, and bypassing
the __str__ attribute we'd like to have happen on __getattr__, which means we can't track
the attribute access

We should look for a different Proxy implementation, perhaps wrapt
"""

from django_auto_prefetching.queryset_trace import TracingQuerySet, trace_queryset
from test_project.models import ChildB, Parent, ChildABro, ChildA, ManyToManyModelOne, ManyToManyModelTwo, ParentCar, \
    DeeplyNestedParent, DeeplyNestedChild, DeeplyNestedChildren, GrandKids


class TestTracingQuerySet(TestCase):
    def test_tracing_queryset_will_fetch_many_to_one_fields_directly_on_the_model(self):
        parent1 = Parent.objects.create(
            name='1'
        )
        parent2 = Parent.objects.create(
            name='1'
        )
        for i in range(0, 5):
            ChildB.objects.create(
                parent=parent1,
                name=i
            )
        for i in range(0, 5):
            ChildB.objects.create(
                parent=parent2,
                name=i
            )

        # Here we should get only three queries.
        # 1. For the .all call
        # 2. For the .parent lazyload
        # 3. One for the internal .all() call with the prefetched parents
        with self.assertNumQueries(3):
            with log_queries():
                with trace_queryset(ChildB.objects.all()) as qs:

                    for i in qs:
                        print('---------> printing i:')
                        print('--------->', i)
                        print('---------> printing i parent:')
                        print('--------->', i.parent)
                        print('---------> printing i parent AGAIN:')
                        print('--------->', i.parent)

    def test_tracing_queryset_will_fetch_one_to_one_fields_directly_on_the_model(self):
        for i in range(0, 10):
            child_a = ChildA.objects.create(
                name=i
            )
            ChildABro.objects.create(
                name=i,
                sibling=child_a
            )

        # Here we should get only three queries on both sides.
        # 1. For the .all call
        # 2. For the .brother/sibling lazyload
        # 3. One for the internal .all() call with the prefetched parents
        with self.assertNumQueries(3):
            with log_queries():
                with trace_queryset(ChildA.objects.all()) as qs:
                    for i in qs:
                        print('---------> printing i:')
                        print('--------->', i)
                        # print('---------> printing i parent:')
                        # print('--------->', i.brother)
                        # print('---------> printing i parent AGAIN:')
                        # print('--------->', i.brother)
        #
        with self.assertNumQueries(3):
            with trace_queryset(ChildABro.objects.all()) as qs:

                for i in qs:
                    print('---------> printing i:')
                    print('--------->', i)
                    print('---------> printing i parent:')
                    print('--------->', i.sibling)
                    print('---------> printing i parent AGAIN:')
                    print('--------->', i.sibling)

    def test_tracing_queryset_will_fetch_one_to_many_fields_directly_on_the_model(self):
        for i in range(0, 10):
            parent = Parent.objects.create(
                name=i
            )
            ChildB.objects.create(
                parent=parent,
                name=i
            )

        # Here we should get only four queries.
        # 1. For the .all call
        # 2. For the .children_b lazyload
        # 3. 2 for the internal .all() call with prefetch_related of the children objects
        with self.assertNumQueries(4):
            with trace_queryset(Parent.objects.all()) as qs:

                for i in qs:
                    print('---------> printing i:')
                    print('--------->', i)
                    for kid in i.children_b.all():
                        print('----------------> kid', kid)

    def test_tracing_queryset_will_fetch_deeply_nested_relations_one_to_one_and_many_to_one_relations(self):
        for i in range(0, 5):
            car = ParentCar.objects.create()
            parent = DeeplyNestedParent.objects.create(
                car=car,
            )
            parent2 = DeeplyNestedParent.objects.create(
                car=car,
            )
            child = DeeplyNestedChild.objects.create(
                parent=parent
            )
            child2 = DeeplyNestedChild.objects.create(
                parent=parent2
            )


        # Here we should get only four queries.
        # 1. For the .all call
        # 2. For the .parent call
        # 3. For the .parent.car call
        # 4  For the internal .all() call with select_related of the other objects
        with self.assertNumQueries(4):
            original_queryset = DeeplyNestedChild.objects.all()
            with trace_queryset(original_queryset) as qs:
                for i in qs:
                    print('-------->')
                    str(i.parent.car)
                    print('-------->')
                    str(i.parent.car)







class TestTracingQuerySetErrorHandling(TestCase):

    def test_tracing_queryset_will_reset_field_class_when_done(self):
        parent1 = Parent.objects.create(
            name='1'
        )

        with trace_queryset(Parent.objects.all()) as qs:
            for i in qs:
                print('looping')

            self.assertEqual(type(Parent.__dict__['children_b']), ReverseManyToOneDescriptor)

    def test_tracing_queryset_will_reset_field_class_even_if_not_looped_through(self):
        parent1 = Parent.objects.create(
            name='1'
        )

        # Trace the queryset but *do not* loop through it
        with trace_queryset(Parent.objects.all()) as qs:
            pass

        self.assertEqual(type(Parent.__dict__['children_b']), ReverseManyToOneDescriptor)

    def test_tracing_queryset_will_reset_field_class_even_if_it_throws_error_halfway_through(self):
        self.maxDiff = None
        parent1 = Parent.objects.create(
            name='1'
        )

        # Trace the queryset but *do not* loop through it
        with trace_queryset(Parent.objects.all()) as qs:
            try:
                for i in qs:
                    raise AssertionError("Test exception")
            except AssertionError:
                pass

        self.assertEqual(type(Parent.__dict__['children_b']), ReverseManyToOneDescriptor)

    def test_tracing_queryset_will_throw_an_error_if_exhausted_multiple_times(self):
        self.maxDiff = None
        parent1 = Parent.objects.create(
            name='1'
        )

        # Trace the queryset but *do not* loop through it
        with trace_queryset(Parent.objects.all()) as qs:
            for i in qs:
                print(i)

        with self.assertRaisesMessage(expected_exception=NotImplementedError, expected_message='Cannot use a TracingQueryset multiple times'):
            for i in qs:
                print(i)

        self.assertEqual(type(Parent.__dict__['children_b']), ReverseManyToOneDescriptor)


    def test_tracing_queryset_will_restore_fields_for_deeply_nested_relations(self):
        for i in range(0, 5):
            car = ParentCar.objects.create()
            parent = DeeplyNestedParent.objects.create(
                car=car,
            )
            parent2 = DeeplyNestedParent.objects.create(
                car=car,
            )
            child = DeeplyNestedChild.objects.create(
                parent=parent
            )
            child2 = DeeplyNestedChild.objects.create(
                parent=parent2
            )


        # Here we should get only four queries.
        # 1. For the .all call
        # 2. For the .parent call
        # 3. For the .parent.car call
        # 4  For the internal .all() call with select_related of the other objects
        with self.assertNumQueries(4):
            original_queryset = DeeplyNestedChild.objects.all()
            with trace_queryset(original_queryset) as qs:
                for i in qs:
                    print('-------->')
                    str(i.parent.car)
                    print('-------->')
                    str(i.parent.car)

        # Assert child is normal
        self.assertEqual(type(DeeplyNestedChild.__dict__['parent']), ForwardOneToOneDescriptor)


        # Assert parent is normal
        self.assertEqual(type(DeeplyNestedParent.__dict__['children_set']), ReverseManyToOneDescriptor)
        self.assertEqual(type(DeeplyNestedParent.__dict__['car']), ForwardManyToOneDescriptor)
        self.assertEqual(type(DeeplyNestedParent.__dict__['child']), ReverseOneToOneDescriptor)

        # Assert car is normal
        self.assertEqual(type(ParentCar.__dict__['deeplynestedparent_set']), ReverseManyToOneDescriptor)