from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from test_project.models import ChildA, ChildB, Parent


class TopLevelSerializer(ModelSerializer):
    class Meta:
        model = Parent
        fields = ["name"]


class ChildBSerializerWithDottedPropertyAccess(ModelSerializer):
    parent_text = serializers.CharField(read_only=True, source="parent.name")

    class Meta:
        model = ChildB
        fields = ["parent_text"]


class ChildBSerializerWithNestedRenamedSerializer(ModelSerializer):
    dad = TopLevelSerializer(read_only=True, source="parent")

    class Meta:
        model = ChildB
        fields = ["dad"]


class ChildBSerializerWithNestedSerializer(ModelSerializer):
    parent = TopLevelSerializer(read_only=True)

    class Meta:
        model = ChildB
        fields = ["parent"]


class ChildBSerializerWithSlug(ModelSerializer):
    parent = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = ChildB
        fields = ["name", "parent"]


class ChildBSerializer(ModelSerializer):
    class Meta:
        model = ChildB
        fields = ["name", "parent"]
        depth = 1
