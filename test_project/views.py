# Create your views here.
from rest_framework.viewsets import ModelViewSet

from django_auto_prefetching import AutoPrefetchViewSetMixin
from test_project.serializers.child_b_serializers import ChildBSerializer
from test_project.serializers.many_to_many_serializer import (
    ManyTwoSerializerOnlyFullRepresentation,
)
from test_project.models import ManyToManyModelTwo, ChildB


class ManyTwoSerializerOnlyFullRepresentationViewSet(
    AutoPrefetchViewSetMixin, ModelViewSet
):
    serializer_class = ManyTwoSerializerOnlyFullRepresentation
    queryset = ManyToManyModelTwo.objects.all()


class ChildBViewSet(ModelViewSet):
    serializer_class = ChildBSerializer
    queryset = ChildB.objects.all()
