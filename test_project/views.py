
# Create your views here.
from rest_framework.viewsets import ModelViewSet

from django_auto_prefetching import AutoPrefetchViewSetMixin
from test_project.many_to_many_serializer import ManyTwoSerializerOnlyFullRepresentation
from test_project.models import ManyToManyModelTwo


class ManyTwoSerializerOnlyFullRepresentationViewSet(AutoPrefetchViewSetMixin, ModelViewSet):
    serializer_class = ManyTwoSerializerOnlyFullRepresentation
    queryset = ManyToManyModelTwo.objects.all()
