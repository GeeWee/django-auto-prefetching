from django.db.models import QuerySet
from django.test import TestCase

from django_auto_prefetching.queryset_trace import TracingQuerySet
from test_project.models import ChildB, TopLevel, ChildABro, ChildA, ManyToManyModelOne, ManyToManyModelTwo, ParentCar, \
    DeeplyNestedParent, DeeplyNestedChild, DeeplyNestedChildren, GrandKids


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
            qs = TracingQuerySet(model=ChildB)

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
                childA_text=i
            )
            ChildABro.objects.create(
                brother_text=i,
                sibling=child_a
            )

        # Here we should get only three queries on both sides.
        # 1. For the .all call
        # 2. For the .brother/sibling lazyload
        # 3. One for the internal .all() call with the prefetched parents
        with self.assertNumQueries(3):
            qs = TracingQuerySet(model=ChildA)
            for i in qs:
                print('---------> printing i:')
                print('--------->', i)
                print('---------> printing i parent:')
                print('--------->', i.brother)
                print('---------> printing i parent AGAIN:')
                print('--------->', i.brother)

        with self.assertNumQueries(3):
            qs = TracingQuerySet(model=ChildABro)

            for i in qs:
                print('---------> printing i:')
                print('--------->', i)
                print('---------> printing i parent:')
                print('--------->', i.sibling)
                print('---------> printing i parent AGAIN:')
                print('--------->', i.sibling)

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
        with self.assertNumQueries(4):
            qs = TracingQuerySet(model=TopLevel)

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
            qs = TracingQuerySet(model=DeeplyNestedChild)

            for i in qs:
                print('-------->')
                print(i.parent.car)
                print('-------->')
                print(i.parent.car)