import logging
from json import loads, dumps
from pprint import pprint

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.utils.serializer_helpers import ReturnList

from test_project.models import (
    ChildA,
)
from test_project.views import WrongQuerySetOverride, RightQuerySetOverride

logger = logging.getLogger("django-auto-prefetching")
logger.setLevel(level=logging.DEBUG)


class GetQuerysetOverrideTest(TestCase):
    factory = APIRequestFactory()

    def test_that_it_does_not_work_when_overriding_get_queryset_wrong(self):
        """
        This viewSet overrides the get_queryset method, so the mixin is never called
        """
        ChildA.objects.create(childA_text="text")
        ChildA.objects.create(childA_text="text")

        view = WrongQuerySetOverride.as_view(
            actions={"get": "list"}
        )

        # 1 list query and 2 for siblings
        with self.assertNumQueries(3):
            data = view(self.factory.get("/")).data
            pprint_result(data)
            self.assertEqual(len(data), 2)

    def test_that_it_does_work_when_overriding_get_queryset_right(self):
        """
        This viewSet overrides the get_queryset method but calls prefetch manually
        """
        ChildA.objects.create(childA_text="text")
        ChildA.objects.create(childA_text="text")
        ChildA.objects.create(childA_text="text")
        ChildA.objects.create(childA_text="text")

        view = RightQuerySetOverride.as_view(
            actions={"get": "list"}
        )

        # Only 1 query as prefetch is called manually
        with self.assertNumQueries(1):
            data = view(self.factory.get("/")).data
            pprint_result(data)
            self.assertEqual(len(data), 4)


def pprint_result(list: ReturnList):
    # Convert to regular dicts
    def to_dict(input_ordered_dict):
        return loads(dumps(input_ordered_dict))

    pprint([to_dict(res) for res in list])
