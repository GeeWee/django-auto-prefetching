from rest_framework.routers import DefaultRouter

from test_project.views import ChildBViewSet

router = DefaultRouter()
router.register("childb", ChildBViewSet, basename="childb")

urlpatterns = router.urls
