from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from test_project.models import ChildA, ChildB, Parent, ChildABro


class ChildABrotherSerializer(ModelSerializer):
    class Meta:
        model = ChildABro
        fields = ["name"]


class ChildABrotherSerializerWithBrother(ModelSerializer):
    class Meta:
        model = ChildABro
        fields = ["name", "sibling"]
        depth = 1


class ChildASerializer(ModelSerializer):
    # brother = ChildABrotherSerializer(read_only=True)

    class Meta:
        model = ChildA
        fields = ["name", "brother"]
        depth = 1


class ChildASerializerWithNoRelations(ModelSerializer):
    # brother = ChildABrotherSerializer(read_only=True)

    class Meta:
        model = ChildA
        fields = ["name"]
        depth = 1
