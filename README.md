
# Django auto-prefetching

**NOTICE: THIS PROJECT IS A WORK IN PROGRESS, AND IS NOT PUBLISHED TO PYPI YET**

Automatic prefetching of related objects for Django Rest Framework.

Inside your ViewSets `get_queryset` add the following code:
```python3.7
    def get_queryset():
        qs = YOUR_MODEL.objects.all() # Or whatever queryset you want to use
        qs = prefetch(self.get_serializer_class(), queryset) # This line prefetches the related model depending on the serializer.
        return qs
```

# Unresolved issues

- If you forget to add `many=True` to a serializer that has the reverse side of the ForeignKey we calculate the wrong prefetch_related
fields and we get an error. We can't catch this error early because it's only thrown when the queryset is evaluated
- We can't prefetch anything that's accessed in serializer method fields.


# LICENSE:
MIT