import logging
from json import loads, dumps
from pprint import pprint

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.utils.serializer_helpers import ReturnList

from test_project.models import (
    ChildA,
)
from test_project.views import GetPrefetchableQuerysetOverride, WrongQuerySetOverride, RightQuerySetOverride

logger = logging.getLogger("django-auto-prefetching")
logger.setLevel(level=logging.DEBUG)


class GetQuerysetOverrideTest(TestCase):
    factory = APIRequestFactory()

    def test_that_get_prefetchable_queryset_is_not_called_when_overrides(self):
        """
        GetPrefetchableQuerysetOverride overrides the get_prefetchable_queryset method, so the mixin will call overrided get_prefetchable_queryset when get_queryset is called
        """
        ChildA.objects.create(childA_text="text_1")
        ChildA.objects.create(childA_text="text_2")

        view = GetPrefetchableQuerysetOverride.as_view(
            actions={"get": "list"}
        )

        # Only 1 query because mixin get_queryset calls our overrided get_prefetchable_queryset.
        # Our get_prefetchable_queryset filter by childA_text="text_1", so only 1 result
        with self.assertNumQueries(1):
            data = view(self.factory.get("/")).data
            self.assertEqual(len(data), 1)