import logging
from json import loads, dumps
from pprint import pprint

from django.test import TestCase
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework.test import APIRequestFactory
from rest_framework.utils.serializer_helpers import ReturnList

from django_auto_prefetching import prefetch
from test_project.child_a_serializer import (
    ChildASerializer,
    ChildABrotherSerializerWithBrother,
    ChildASerializerWithNoRelations,
)
from test_project.child_b_serializers import (
    ChildBSerializer,
    ChildBSerializerWithSlug,
    ChildBSerializerWithNestedSerializer,
    ChildBSerializerWithNestedRenamedSerializer,
    ChildBSerializerWithDottedPropertyAccess,
)
from test_project.many_to_many_serializer import (
    ManyOneSerializerOnlyPrimaryKey,
    ManyOneSerializerOnlyFullRepresentation,
    ManyTwoSerializerOnlyPrimaryKey,
    ManyTwoSerializerOnlyFullRepresentation,
)
from test_project.models import (
    ChildA,
    TopLevel,
    ChildB,
    ChildABro,
    ManyToManyModelOne,
    ManyToManyModelTwo,
    DeeplyNestedParent,
    DeeplyNestedChild,
    DeeplyNestedChildren,
    GrandKids,
    DeeplyNestedChildrenToys,
    SingleChildToy,
    ParentCar,
)
from test_project.nested_serializer import DeeplyNestedParentSerializer
from test_project.top_level_serializer import (
    TopLevelSerializerWithChildren,
    TopLevelSerializerWithNestedSerializer,
    TopLevelSerializerWithNestedSerializerWithSource,
)
from test_project.views import ManyTwoSerializerOnlyFullRepresentationViewSet


logger = logging.getLogger('django-auto-prefetching')
logger.setLevel(level=logging.DEBUG)

class NoRelationsTest(TestCase):
    def test_that_it_fetches_without_relations_properly(self):
        ChildA.objects.create(childA_text="text")

        queryset = ChildA.objects.all()

        serializer = ChildASerializerWithNoRelations(instance=queryset, many=True)
        with self.assertNumQueries(1):
            assert len(serializer.data) == 1


class TestOneToMany(TestCase):
    def setUp(self):
        top_level = TopLevel.objects.create(top_level_text="foo")
        child_b = ChildB.objects.create(parent=top_level)


    def test_it_prefetches_foreign_key_when_source_is_changed(self):
        car = ParentCar.objects.create()
        parent = DeeplyNestedParent.objects.create(car=car)

        class CarSerializer(ModelSerializer):
            car_id = PrimaryKeyRelatedField(source="car", queryset=ParentCar.objects.all())

            class Meta:
                model = DeeplyNestedParent
                fields = ['car', 'car_id']
                depth=1

        _run_test(CarSerializer, DeeplyNestedParent, 1)



    def test_it_prefetches_foreign_key_relations_when_owning(self):
        serializer_class = ChildBSerializer
        queryset = ChildB.objects.all()

        queryset = prefetch(queryset, serializer_class)

        serializer = serializer_class(instance=queryset, many=True)
        with self.assertNumQueries(1):
            print(serializer.data)

    def test_it_prefetches_slug_related_fields(self):
        serializer_class = ChildBSerializerWithSlug
        queryset = ChildB.objects.all()
        queryset = prefetch(queryset, serializer_class)

        with self.assertNumQueries(1):
            serializer = ChildBSerializerWithSlug(instance=queryset, many=True)
            assert serializer.data[0]["parent"] == "foo"
            print(serializer.data)

    def test_it_prefetches_using_nested_serializers(self):
        serializer_class = ChildBSerializerWithNestedSerializer
        queryset = ChildB.objects.all()

        queryset = prefetch(queryset, serializer_class)
        serializer = serializer_class(instance=queryset, many=True)

        with self.assertNumQueries(1):
            data = serializer.data
            print(data)

        assert len(data) == 1
        assert data[0]["parent"]["top_level_text"] == "foo"

    def test_it_prefetches_using_nested_serializers_when_source_is_changed(self):
        serializer_class = ChildBSerializerWithNestedRenamedSerializer
        queryset = ChildB.objects.all()

        queryset = prefetch(queryset, serializer_class)
        serializer = serializer_class(instance=queryset, many=True)

        with self.assertNumQueries(1):
            data = serializer.data
            print(data)

        assert len(data) == 1
        assert data[0]["dad"]["top_level_text"] == "foo"

    def test_it_prefetches_when_using_dotted_property_access(self):
        serializer_class = ChildBSerializerWithDottedPropertyAccess
        queryset = ChildB.objects.all()

        with self.assertNumQueries(1):
            queryset = prefetch(queryset, serializer_class)
            serializer = serializer_class(instance=queryset, many=True)
            data = serializer.data
            print(data)

        assert len(data) == 1
        assert data[0]["parent_text"] == "foo"

    def test_reverse_foreign_key_lookups(self):
        serializer_class = ChildBSerializerWithDottedPropertyAccess
        queryset = ChildB.objects.all()

        with self.assertNumQueries(1):
            queryset = prefetch(queryset, serializer_class)
            serializer = serializer_class(instance=queryset, many=True)
            data = serializer.data
            print(data)

        assert len(data) == 1
        assert data[0]["parent_text"] == "foo"

    # Test one to one


class TestManyToMany(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()


        # Three ModelOne exists
        # Four ModelTwo exists

        # Two relations. Here is a modelOne with two ModelTwos
        model_one = ManyToManyModelOne.objects.create(one_text="one")
        model_one.model_two_set.create(two_text="one one")
        model_one.model_two_set.create(two_text="one two")
        model_one.model_two_set.create(two_text="one three")

        # Here is a modelTwo with two modelOnes
        model_two = ManyToManyModelTwo.objects.create(two_text="two")
        model_two.model_one_set.create(one_text="two one")
        model_two.model_one_set.create(one_text="two two")

    def test_it_prefetches_many_to_many_relationships_on_owning_side_with_only_primary_keys(
        self
    ):
        data = _run_test(
            ManyOneSerializerOnlyPrimaryKey, ManyToManyModelOne, sql_queries=2
        )
        self.assertEqual(len(data), 3)

    def test_it_prefetches_many_to_many_relationships_on_owning_side_with_full_representation(
        self
    ):
        data = _run_test(
            ManyOneSerializerOnlyFullRepresentation, ManyToManyModelOne, sql_queries=2
        )
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["model_two_set"][0]["two_text"], "one one")

    def test_it_prefetches_many_to_many_relationships_on_reverse_side_with_only_primary_keys(
        self
    ):
        data = _run_test(
            ManyTwoSerializerOnlyPrimaryKey, ManyToManyModelTwo, sql_queries=2
        )
        self.assertEqual(len(data), 4)

    def test_it_prefetches_many_to_many_relationships_on_reverse_side_with_full_representation(
        self
    ):
        # One query to fetch ModelTwo
        # One Query to fetch ModelOne
        # One Query to fetch ModelTwo for the new ModelOnes
        data = _run_test(
            ManyTwoSerializerOnlyFullRepresentation, ManyToManyModelTwo, sql_queries=3
        )
        self.assertEqual(len(data), 4)

    def test_it_prefetches_many_to_many_relationships_when_attached_to_viewset(self):

        # Same test as above but just with a viewsetmixin involved
        view = ManyTwoSerializerOnlyFullRepresentationViewSet.as_view(actions={"get": "list"})
        with self.assertNumQueries(3):
            data = view(self.factory.get("/")).data
            pprint_result(data)
            self.assertEqual(len(data), 4)


class TestDeeplyNested(TestCase):
    def setUp(self):
        car = ParentCar.objects.create()
        parent = DeeplyNestedParent.objects.create(car=car)
        only_child = DeeplyNestedChild.objects.create(parent=parent)
        SingleChildToy.objects.create(owner=only_child)

        children_set = []
        for i in range(0, 3):
            children_set.append(DeeplyNestedChildren.objects.create(parent=parent))

        for child in children_set:
            for _i in range(0, 2):
                GrandKids.objects.create(parent=child)
        for i in range(0, 3):
            toys = DeeplyNestedChildrenToys.objects.create()
            toys.owners.set(children_set)

    def test_with_nested_one_to_one(self):
        class ChildSerializer(ModelSerializer):
            class Meta:
                model = DeeplyNestedChild
                fields = ["toy", "parent"]
                depth = 1

        class ParentSerializer(ModelSerializer):
            child = ChildSerializer()

            class Meta:
                model = DeeplyNestedParent
                fields = ["child", "car"]
                depth = 2

        data = _run_test(ParentSerializer, DeeplyNestedParent, sql_queries=2)

    def test_with_nested_foreign_key(self):
        class ChildSerializer(ModelSerializer):
            class Meta:
                model = DeeplyNestedChildren
                fields = ["children", "parent"]
                depth = 1

        class ParentSerializer(ModelSerializer):
            children = ChildSerializer(source="children_set", many=True)

            class Meta:
                model = DeeplyNestedParent
                fields = ["children", "car"]

        data = _run_test(ParentSerializer, DeeplyNestedParent, sql_queries=3)

    def test_we_can_serialize_deeply_nested_without_explicit_serializers(self):
        # Car is gotten via select_related
        # Query one: Fetch parent
        # Query two: Fetch DeeplyNestedChild
        # Query three: Fetch DeeplyNestedChildren
        data = _run_test(
            DeeplyNestedParentSerializer, DeeplyNestedParent, sql_queries=2
        )


class TestManyToOne(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        top_level = TopLevel.objects.create(top_level_text="top")
        child_b = ChildB.objects.create(childB_text="1", parent=top_level)
        child_b = ChildB.objects.create(childB_text="2", parent=top_level)
        child_b = ChildB.objects.create(childB_text="3", parent=top_level)

    def test_it_prefetches_many_to_one_relationships(self):
        data = _run_test(TopLevelSerializerWithChildren, TopLevel, sql_queries=2)
        pprint_result(data)
        assert len(data) == 1
        assert len(data[0]["children_b"]) == 3

    def test_it_prefetches_foreign_key_relations_from_reverse_side_with_serializer(
        self
    ):
        # Need two queries because of prefetch related
        data = _run_test(
            TopLevelSerializerWithNestedSerializer, TopLevel, sql_queries=2
        )

        assert len(data) == 1
        assert len(data[0]["children_b"]) == 3

    def test_it_prefetches_foreign_key_relations_from_reverse_side_with_serializer_that_has_source(
        self
    ):
        # Need two queries because of prefetch related
        data = _run_test(
            TopLevelSerializerWithNestedSerializerWithSource, TopLevel, sql_queries=2
        )

        assert len(data) == 1
        assert len(data[0]["kiddos"]) == 3


class TestOneToOne(TestCase):
    def setUp(self):
        child_a = ChildA.objects.create(childA_text="childA")
        child_a_bro = ChildABro.objects.create(sibling=child_a, brother_text="bro")

    def test_it_prefetches_foreign_key_relations_from_owning_side(self):
        data = _run_test(ChildASerializer, ChildA)
        assert len(data) == 1
        assert data[0]["brother"]["brother_text"] == "bro"

    def test_it_prefetches_foreign_key_relations_from_reverse_side_with_depth(self):
        # Need two queries because of prefetch related
        data = _run_test(ChildABrotherSerializerWithBrother, ChildABro, sql_queries=1)

        pprint_result(data)
        assert len(data) == 1
        assert data[0]["brother_text"] == "bro"
        assert data[0]["sibling"]["childA_text"] == "childA"



def _run_test(serializer_cls, model_cls, sql_queries=1) -> ReturnList:
    """
    Boilerplate for running the tests
    :return: the serializer data to assert one
    """

    print(
        f'Running test with serializer "{serializer_cls.__name__}" and model {model_cls.__name__}'
    )
    case = TestCase()
    with case.assertNumQueries(sql_queries):
        prefetched_queryset = prefetch(model_cls.objects.all(), serializer_cls)
        serializer_instance = serializer_cls(instance=prefetched_queryset, many=True)
        print("Data returned:")
        pprint_result(serializer_instance.data)
        return serializer_instance.data


def pprint_result(list: ReturnList):
    # Convert to regular dicts
    def to_dict(input_ordered_dict):
        return loads(dumps(input_ordered_dict))

    pprint([to_dict(res) for res in list])
