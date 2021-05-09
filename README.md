
# Django Auto-Prefetching
[![<GeeWee>](https://circleci.com/gh/GeeWee/django-auto-prefetching.svg?style=shield)](https://app.circleci.com/pipelines/github/GeeWee/django-auto-prefetching)

*Never worry about n+1 performance problems again*

This project aims to automatically perform the correct `select_related` and `prefetch_related`
calls for your django-rest-framework code. It does this by inspecting your serializers, seeing what fields
they use, and what models they refer to, and automatically calculating what needs to be prefetched.

## Installation
`pip install django-auto-prefetching`

## AutoPrefetchViewSetMixin
This is a ViewSet mixin you can use, which will automatically prefetch the needed objects from the database.
In most circumstances this will be all the database optimizations you'll ever need to do:

### Usage
Simply add it after your ModelViewSet class.

```python
from django_auto_prefetching import AutoPrefetchViewSetMixin
from rest_framework.viewsets import ModelViewSet

class BaseModelViewSet(AutoPrefetchViewSetMixin, ModelViewSet):
    queryset = YourModel.objects.all()
    serializer_class = YourModelSerializer
```
It supports all types of relational fields, (many to many, one to many, one to one, etc.) out of the box.

### Manually calling prefetch
The `AutoPrefetchViewSetMixin` cannot see what objects are being accessed in e.g. a `SerializerMethodField`.
If you use objects in there, you might need to do some additional prefetches.
If you do this and override `get_queryset`, you will have to call `prefetch` manually as the mixin code is never reached.

```python
import django_auto_prefetching
from rest_framework.viewsets import ModelViewSet

class BaseModelViewSet(django_auto_prefetching.AutoPrefetchViewSetMixin, ModelViewSet):
    serializer_class = YourModelSerializer
    
    def get_queryset(self):
            # Simply do the extra select_related / prefetch_related here
            # and leave the mixin to do the rest of the work
            queryset = YourModel.objects.all()
            queryset = queryset.select_related('my_extra_field')
            return django_auto_prefetching.prefetch(queryset, self.serializer_class)
```

## Supported Versions
Currently the project is currently being tested against Python 3.7 and 3.8 and Django 3.2
Pull Requests to support other versions are welcome.

## Maturity
The project is currently being used without issues in a medium-sized Django project(20.000 lines of code)

## Contributing
Contributions are welcome! To get the tests running, do the following:
- Clone the repository.
- If you don't have it, install [pipenv](https://docs.pipenv.org/en/latest/install/#installing-pipenv)
- Install the dependencies with `pipenv sync --dev`
- Activate the virtualenv created by pipenv by writing `pipenv shell`
- Run the tests with `./manage.py test`   

# LICENSE:
MIT