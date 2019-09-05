from django.contrib import admin

# Register your models here.
from test_project.models import ChildA, ChildB, ChildABro, SingleChildToy

admin.site.register(ChildA)
admin.site.register(ChildB)
admin.site.register(ChildABro)
admin.site.register(SingleChildToy)
