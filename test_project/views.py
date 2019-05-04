from django.shortcuts import render

# Create your views here.
from rest_framework.viewsets import ModelViewSet

from django_auto_prefetching import AutoPrefetchViewSetMixin
from test_project.models import TopLevel
from test_project.top_level_serializer import TopLevelSerializerWithChildren


class TopLevelWithChildrenViewSet(AutoPrefetchViewSetMixin, ModelViewSet):
    serializer_class = TopLevelSerializerWithChildren
    queryset = TopLevel.objects.all()
