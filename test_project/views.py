# Create your views here.
from rest_framework.viewsets import ModelViewSet

from django_auto_prefetching import AutoPrefetchViewSetMixin
import django_auto_prefetching
from test_project.serializers.child_a_serializer import ChildASerializer
from test_project.serializers.child_b_serializers import ChildBSerializer
from test_project.serializers.many_to_many_serializer import (
    ManyTwoSerializerOnlyFullRepresentation,
)
from test_project.models import ManyToManyModelTwo, ChildB, ChildA


class ManyTwoSerializerOnlyFullRepresentationViewSet(
    AutoPrefetchViewSetMixin, ModelViewSet
):
    serializer_class = ManyTwoSerializerOnlyFullRepresentation
    queryset = ManyToManyModelTwo.objects.all()


class ChildBViewSet(ModelViewSet):
    serializer_class = ChildBSerializer
    queryset = ChildB.objects.all()


class WrongQuerySetOverride(AutoPrefetchViewSetMixin, ModelViewSet):
    serializer_class = ChildASerializer

    def get_queryset(self):
        return ChildA.objects.all()


class RightQuerySetOverride(AutoPrefetchViewSetMixin, ModelViewSet):
    serializer_class = ChildASerializer

    def get_queryset(self):
        qs = ChildA.objects.all()
        return django_auto_prefetching.prefetch(qs, self.serializer_class)
