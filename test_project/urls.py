from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from test_project.views import ChildBViewSet

router = DefaultRouter()
router.register("childb", ChildBViewSet, basename="childb")


urlpatterns = [
    *router.urls,
    path('admin/', admin.site.urls)
    ]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),

        # For django versions before 2.0:
        # url(r'^__debug__/', include(debug_toolbar.urls)),

    ] + urlpatterns
