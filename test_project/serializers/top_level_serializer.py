from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from test_project.models import ChildA, ChildB, TopLevel


class _ChildrenBSerializer(ModelSerializer):
    class Meta:
        model = ChildB
        fields = ["childB_text", "parent"]


class TopLevelSerializerWithChildren(ModelSerializer):
    class Meta:
        model = TopLevel
        fields = ["top_level_text", "children_b"]
        depth = 1


class TopLevelSerializerWithNestedSerializer(ModelSerializer):
    children_b = _ChildrenBSerializer(many=True, read_only=True)

    class Meta:
        model = TopLevel
        fields = ["top_level_text", "children_b"]


class TopLevelSerializerWithNestedSerializerWithSource(ModelSerializer):
    kiddos = _ChildrenBSerializer(many=True, read_only=True, source="children_b")

    class Meta:
        model = TopLevel
        fields = ["top_level_text", "kiddos"]
