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
    # brother = ChildABrotherSerializer(read_only=True)

    class Meta:
        model = ChildA
        fields = ["childA_text", "brother"]
        depth = 1


class ChildASerializerWithNoRelations(ModelSerializer):
    # brother = ChildABrotherSerializer(read_only=True)

    class Meta:
        model = ChildA
        fields = ["childA_text"]
        depth = 1


#
# class TopLevelSerializer(ModelSerializer):
#     class Meta:
#         model = TopLevel
#         fields = ['top_level_text']
#
# class ChildBSerializerWithDottedPropertyAccess(ModelSerializer):
#     parent_text = serializers.CharField(read_only=True, source='parent.top_level_text')
#
#     class Meta:
#         model = ChildB
#         fields = ['parent_text']
#
# class ChildBSerializerWithNestedRenamedSerializer(ModelSerializer):
#     dad = TopLevelSerializer(read_only=True, source='parent')
#
#     class Meta:
#         model = ChildB
#         fields = ['dad']
#
# class ChildBSerializerWithNestedSerializer(ModelSerializer):
#     parent = TopLevelSerializer(read_only=True)
#
#     class Meta:
#         model = ChildB
#         fields = ['parent']
#
# class ChildBSerializerWithSlug(ModelSerializer):
#     parent = serializers.SlugRelatedField(slug_field='top_level_text', read_only=True)
#
#     class Meta:
#         model = ChildB
#         fields = ['childB_text', 'parent']
#
#
# class ChildBSerializer(ModelSerializer):
#     class Meta:
#         model = ChildB
#         fields = ['childB_text', 'parent']
#         depth = 1
#
#
# class ChildASerializer(ModelSerializer):
#     class Meta:
#         fields = ['childA_text']
#         model = ChildA
