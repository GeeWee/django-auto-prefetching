from django.contrib import admin

# Register your models here.
from django_auto_prefetching import AutoPrefetchModelAdmin
from test_project.models import ChildA, ChildB, ChildABro, SingleChildToy

admin.site.register(ChildA, AutoPrefetchModelAdmin)
admin.site.register(ChildB, AutoPrefetchModelAdmin)
admin.site.register(ChildABro, AutoPrefetchModelAdmin)
admin.site.register(SingleChildToy, AutoPrefetchModelAdmin)
