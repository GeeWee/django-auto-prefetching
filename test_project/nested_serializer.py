from rest_framework.serializers import ModelSerializer

from test_project.models import (
    DeeplyNestedParent,
    DeeplyNestedChild,
    DeeplyNestedChildren,
    GrandKids,
)


class DeeplyNestedParentSerializer(ModelSerializer):
    class Meta:
        model = DeeplyNestedParent
        fields = ["child", "children_set", "car"]
        depth = 2


class DeeplyNestedChildSerializer(ModelSerializer):
    class Meta:
        model = DeeplyNestedChild
        fields = ["toy", "parent"]
        depth = 1


class GrandKidSerializer(ModelSerializer):
    class Meta:
        fields = ["id", "parent"]
        model = GrandKids


class DeeplyNestedChildrenSerializer(ModelSerializer):
    grandkids = GrandKidSerializer(source="children")

    class Meta:
        model = DeeplyNestedChildren
        fields = ["toys", "grandkids"]


class ExplicitDeeplyNestedParentSerializer(ModelSerializer):
    children_set = DeeplyNestedChildrenSerializer(many=True)
    child = DeeplyNestedChildSerializer()

    class Meta:
        model = DeeplyNestedParent
        fields = ["child", "children_set", "car"]
        depth = 2
