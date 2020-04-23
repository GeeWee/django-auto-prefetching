from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from test_project.models import ChildA, ChildB, TopLevel, ChildABro


class ChildABrotherSerializer(ModelSerializer):
    class Meta:
        model = ChildABro
        fields = ["brother_text"]


class ChildABrotherSerializerWithBrother(ModelSerializer):
    class Meta:
        model = ChildABro
        fields = ["brother_text", "sibling"]
        depth = 1


class ChildASerializer(ModelSerializer):

    class Meta:
        model = ChildA
        fields = ["childA_text", "brother"]
        depth = 1


class ChildASerializerWithNoRelations(ModelSerializer):

    class Meta:
        model = ChildA
        fields = ["childA_text"]
        depth = 1
