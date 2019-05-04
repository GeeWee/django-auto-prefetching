from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from test_project.models import (
    ChildA,
    ChildB,
    TopLevel,
    ManyToManyModelOne,
    ManyToManyModelTwo,
)


class ManyOneSerializerOnlyPrimaryKey(ModelSerializer):
    class Meta:
        model = ManyToManyModelOne
        fields = ["one_text", "model_two_set"]


class ManyOneSerializerOnlyFullRepresentation(ModelSerializer):
    class Meta:
        model = ManyToManyModelOne
        fields = ["one_text", "model_two_set"]
        depth = 1


class ManyTwoSerializerOnlyPrimaryKey(ModelSerializer):
    class Meta:
        model = ManyToManyModelTwo
        fields = ["two_text", "model_one_set"]


class ManyTwoSerializerOnlyFullRepresentation(ModelSerializer):
    class Meta:
        model = ManyToManyModelTwo
        fields = ["two_text", "model_one_set"]
        depth = 1
