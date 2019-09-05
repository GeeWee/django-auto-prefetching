from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from test_project.models import ChildA, ChildB, Parent


class _ChildrenBSerializer(ModelSerializer):
    class Meta:
        model = ChildB
        fields = ["name", "parent"]


class TopLevelSerializerWithChildren(ModelSerializer):
    class Meta:
        model = Parent
        fields = ["name", "children_b"]
        depth = 1


class TopLevelSerializerWithNestedSerializer(ModelSerializer):
    children_b = _ChildrenBSerializer(many=True, read_only=True)

    class Meta:
        model = Parent
        fields = ["name", "children_b"]


class TopLevelSerializerWithNestedSerializerWithSource(ModelSerializer):
    kiddos = _ChildrenBSerializer(many=True, read_only=True, source="children_b")

    class Meta:
        model = Parent
        fields = ["name", "kiddos"]


class TopLevelSerializerWithHyperlinkedIdentityField(ModelSerializer):
    children_b = serializers.HyperlinkedIdentityField(view_name="childb-detail")

    class Meta:
        model = Parent
        fields = ["name", "children_b"]
