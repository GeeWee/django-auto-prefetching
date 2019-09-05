# From http://code.activestate.com/recipes/496741-object-proxying/
# Probably not perfect. Replace later maybe
from django_auto_prefetching.prefetch_description import PrefetchDescription


class Proxy(object):
    __slots__ = ["_obj", "__weakref__"]

    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)

    #
    # proxying (special cases)
    #
    def __getattribute__(self, name):
        unproxied_model = object.__getattribute__(self, '_obj')
        attribute = getattr(unproxied_model, name)
        return attribute

    def __delattr__(self, name):
        delattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_obj"), name, value)

    def __nonzero__(self):
        return bool(object.__getattribute__(self, "_obj"))

    def __str__(self):
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self):
        return repr(object.__getattribute__(self, "_obj"))

    #
    # factories
    #
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__',
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__',
        '__eq__', '__float__', '__floordiv__', '__ge__', '__getitem__',
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__',
        '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__',
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__',
        '__neg__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__',
        '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__',
        '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
        '__rtruediv__', '__rxor__', '__setitem__', '__setslice__', '__sub__',
        '__truediv__', '__xor__', 'next',
    ]

    @classmethod
    def _create_class_proxy(cls, theclass):
        """creates a proxy for the given class"""

        def make_method(name):
            def method(self, *args, **kw):
                return getattr(object.__getattribute__(self, "_obj"), name)(*args, **kw)

            return method

        namespace = {}
        for name in cls._special_names:
            if hasattr(theclass, name):
                namespace[name] = make_method(name)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)

    def __new__(cls, obj, *args, **kwargs):
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        try:
            cache = cls.__dict__["_class_proxy_cache"]
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls._create_class_proxy(obj.__class__)
        ins = object.__new__(theclass)
        theclass.__init__(ins, obj, *args, **kwargs)
        return ins


class ModelProxy(Proxy):
    def __init__(self, object_to_proxy, originating_queryset, prefix: str):
        super().__init__(object_to_proxy)
        self.prefix = prefix
        self.queryset = originating_queryset # TODO should probably be a weakset or something like that

    def __getattribute__(self, name):
        # Here we need to look at whether or not we've tried to prefetch with this queryset. If we have
        # skip this whole thing.

        unproxied_model = object.__getattribute__(self, '_obj')
        attribute = getattr(unproxied_model, name)

        model_fields = unproxied_model._meta.get_fields()

        relational_field = None
        for field in model_fields:
            # print(f'field "{field.name}"', field)

            if field.name == name and field.is_relation:
                relational_field = field
                # print(f'model field: "{field.name}"')

        if not relational_field:
            return attribute

        # Now we check whether or not it's been cached
        is_cached_already = relational_field.is_cached(unproxied_model)
        if not is_cached_already:
            return attribute

        print(f'Model field "{name}" was not cached already. Prefetching it on next iteration')
        qs = self.queryset

        # Put the description on the queryset if it doesn't exist
        if not hasattr(qs, '_django_auto_prefetching_should_prefetch_fields'):
            qs._django_auto_prefetching_should_prefetch_fields = PrefetchDescription(set(), set())

        # Depending on the field type, we should add it to prefetch_related or select_related
        if relational_field.one_to_one or relational_field.many_to_one:
            qs._django_auto_prefetching_should_prefetch_fields.select_related.add(self.prefix + relational_field.name)
        elif relational_field.one_to_many:
            qs._django_auto_prefetching_should_prefetch_fields.prefetch_related.add(self.prefix + relational_field.name)

        # TODO we currently don't support many to many, as the wayt to tell whether or not they've been prefetched
        #  is different

        # Here if we have a relational field that manifests in just a single object, we can simply wrap
        # that model in a ModelProxy with a new prefix, to build a new path there
        if relational_field.one_to_one or relational_field.many_to_one:
            related_model = getattr(unproxied_model, name)
            # The prefix here is the name of our current model
            prefix = f"{self.prefix}{relational_field.name}__"
            return ModelProxy(related_model, originating_queryset=self.queryset, prefix=prefix)