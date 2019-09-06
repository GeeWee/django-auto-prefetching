import logging

from django.db.models import Field

from django_auto_prefetching import dap_logger
from django_auto_prefetching.utils import PrefetchDescription


def get_related_fields_for_model(model, depth, fields=None) -> Tuple[set, set]:
    """
    Returns a tuple of sets for use with "select_related" and "prefetch_related"
    Takes in a model, a depth to recurse to, an optionally a list of fields to recurse on. Defaults for fields
    is all fields."
    Returns select_related_fields, prefetch_related_fields
    """
    return recurse_on_model(model, depth, fields, None, None)


def recurse_on_model(model, depth, fields, previous_relation_string, previous_model):
    """
    This is the moneymaker. It runs through a models fields, and for relational fields,
    it either puts them into select_related or prefetch_related depending on the type.
    When it finds a relational field, it will call itself with the new model, and a lower
    depth, until we have traversed the entire tree.

    :param model: The model to traverse currently
    :param depth: The depth to pursue when building relations
    :param fields: The fields to use for this model. If None, all fields are taken into account
    :param previous_relation_string: A string to use when building relations, e.g. if we're already at "containers" and
    traversing further, the string is "containers", so we can build the string "containers__order".
    This should be None for the initial model.
    :param previous_model: The previous model. Should be none at first. Used for not traversing One->One relationships
    continuously.
    """

    # INITIALIZE SETS
    select_related_fields = set()
    prefetch_related_fields = set()

    dap_logger.info(
        f"Recursing on model {model.__name__}, with depth: {depth} and previous relation string {previous_relation_string}"
    )

    for field in model._meta.get_fields():
        related_model = field.related_model
        name = calculate_field_name(field)
        # ------- DO WE WANT TO BREAK OUT? ----------
        if fields is not None and name not in fields:
            continue  # If we have a fields array, and our fields not in it, we #bail
        if related_model == previous_model:
            continue  # Do not go back and forth between the same models. E.g. in a one->one relationship we could bounce back and forth

        # --- BUILD THE RELATIONSHIP STRING HERE ----
        if previous_relation_string is None:
            # If it's none, the string is simply the name of this field
            current_field_name = name
        else:
            current_field_name = previous_relation_string + "__" + name

        # ---------- PREFETCH RELATED ---------
        if field.many_to_many or field.one_to_many:
            dap_logger.info(f'Treating field "{name}" as a prefetch_related field')

            # ADD CURRENT FIELD
            prefetch_related_fields.add(current_field_name)

            # RECURSE DOWN TO ADD MORE FIELDS
            if depth > 1:
                dap_logger.info(
                    f"Following relation to prefetch_related model {related_model.__name__}"
                )
                select_related, prefetch_related = recurse_on_model(
                    related_model, depth - 1, None, current_field_name, model
                )
                prefetch_related_fields |= select_related
                prefetch_related_fields |= prefetch_related

        # --------- SELECT RELATED -----------
        elif field.one_to_one or field.many_to_one:
            dap_logger.info(f'Treating field "{name}" as a select_related field')

            # ADD CURRENT FIELD
            select_related_fields.add(current_field_name)

            # RECURSE DOWN TO ADD MORE FIELDS
            if depth > 1:
                dap_logger.info(f"Following relation to select_related model {related_model.__name__}")
                select_related, prefetch_related = recurse_on_model(
                    related_model, depth - 1, None, current_field_name, model
                )
                select_related_fields |= select_related
                prefetch_related_fields |= prefetch_related

    dap_logger.info(f'DONE WITH MODEL {model.__name__} from "{previous_relation_string}"')
    return select_related_fields, prefetch_related_fields


def calculate_field_name(field):
    """
    This is a method to calculate the field name for the prefetch_related/select_related string. We can't just use
    field.name, as that seems to return the wrong name for ForeignKeys, without a 'related' name (e.g. 'containers' (model in plural) instead
    of 'container_set' which is the correct reverse lookup.
    """
    # If it's a many to one without the related_name set, mimick djangos behaviour and create the field name with _set afterwards
    if field.many_to_many or field.one_to_many and getattr(field, "related_name", None) is None:
        # a _set field name
        return field.name + "_set"

    return field.name


""" New implementation for django-auto-prefetching """


def calculate_field_name(self, field: Field) -> str:
    """
    This is a method to calculate the field name for the prefetch_related/select_related string. We can't just use
    field.name, as that seems to return the wrong name for ForeignKeys, without a 'related' name (e.g. 'containers' (model in plural) instead
    of 'container_set' which is the correct reverse lookup.
    """
    # If it's a many to one without the related_name set, mimick djangos behaviour and create the field name with _set afterwards
    if field.many_to_many or field.one_to_many and getattr(field, "related_name", None) is None:
        # a _set field name
        return field.name + "_set"

    return field.name


def is_field_cached(self, field, model):
    # One to one fields correctly tells us whether they're cached or not, so if it says it's cached,
    # it definitely is, but if it says no it might be lying
    if field.is_cached(model):
        return True

    # TODO maybe this should be calculate_field_name
    if hasattr(model, '_prefetched_objects_cache'):
        return field.name in model._prefetched_objects_cache


def get_cached_fields_for_model(self, model, prefix='', prefetch_fields=None, previous_model_cls=None,
                                indent=0) -> PrefetchDescription:
    if not prefetch_fields:
        prefetch_fields = PrefetchDescription(set(), set())

    dap_logger.info(
        f"{' ' * indent}Recursing on model {model.__class__.__name__} and previous relation string '{prefix}', indent={indent}"
    )

    model_fields = model._meta.get_fields()

    for field in model_fields:
        if not field.is_relation:
            continue

        if not self.is_field_cached(field, model):
            # If it hasn't been cached in the first model, it means that it hasn't been accessed
            dap_logger.info(f'{" " * indent}Model field "{field.name}" was not cached during first iteration')
            continue

        dap_logger.info(f'{" " * indent}Model field "{field.name}" was cached during first visit..')

        # Calculate some things we need here
        related_model_cls = field.related_model
        field_name = self.calculate_field_name(field)
        field_prefetch_string = f'{prefix}{field_name}'

        # This is a safeguard between jumping back and forth between e.g. OneToOne relationships continuously.
        # However this might fail if there's a circle of dependencies. E.g.
        # Parent -> Child -> Toy -> Parent
        # Where we'd still end up recursing infinitely
        # TODO this should probably be more sophisticated
        if previous_model_cls and related_model_cls == previous_model_cls:
            dap_logger.info("Skipping over relation back to original model")
            continue

        if field.one_to_one or field.many_to_one:
            prefetch_fields.select_related.add(field_prefetch_string)

            cached_model = getattr(model, field.name)
            # Here we'll want to keep going, to fetch nested models
            dap_logger.info(f'{" " * indent} Found cached field "{field_prefetch_string}", following:')

            # OneToOneField if we own the field, and OneToOneRel if not
            self.get_cached_fields_for_model(cached_model, f'{field_prefetch_string}__', prefetch_fields,
                                             previous_model_cls=model.__class__, indent=indent + 1)

        # If it's a m:m or 1:m, we don't follow any nested property accesses, but simply do one prefetching
        elif field.one_to_many or field.many_to_many:
            prefetch_fields.prefetch_related.add(
                prefix + field.name)

    return prefetch_fields



# def __getattribute__(self, name):
#     # Now we check whether or not it's been cached
#     is_cached_already = relational_field.is_cached(unproxied_model)
#     if is_cached_already:
#         dap_logger.info(f'Model field "{name}" was cached already.')
#         return getattr(unproxied_model, name)
#
#     dap_logger.info(f'Model field "{name}" was not cached already. Prefetching it on next iteration')
#     qs = self.queryset
#
#     # Put the description on the queryset
#     qs._django_auto_prefetching_should_prefetch_fields = PrefetchDescription(set(), set())
#
#     # Depending on the field type, we should add it to prefetch_related or select_related
#     if relational_field.one_to_one or relational_field.many_to_one:
#         qs._django_auto_prefetching_should_prefetch_fields.select_related.add(self.prefix + relational_field.name)
#     elif relational_field.one_to_many:
#         qs._django_auto_prefetching_should_prefetch_fields.prefetch_related.add(self.prefix + relational_field.name)
#
#     # TODO we currently don't support many to many, as the way to tell whether or not they've been prefetched
#     #  is different
#
#     # Here if we have a relational field that manifests in just a single object, we can simply wrap
#     # that model in a ModelProxy with a new prefix, to build a new path there
#     if relational_field.one_to_one or relational_field.many_to_one:
#         related_model = getattr(unproxied_model, name)
#         # The prefix here is the name of our current model
#         prefix = f"{self.prefix}{relational_field.name}__"
#         return ModelProxy(related_model, originating_queryset=self.queryset, prefix=prefix)
#
#     # If not a relational field, just return as-is as there's no point in proxying any further
#     return getattr(unproxied_model, name)




class ModelProxy(wrapt.ObjectProxy):
    def __init__(self, object_to_proxy, originating_queryset, prefix: str):
        super().__init__(object_to_proxy)
        self.prefix = prefix
        self.queryset = originating_queryset # TODO should probably be a weakset or something like that

    def __getattribute__(self, name):
        # Here we need to look at whether or not we've tried to prefetch with this queryset. If we have
        # skip this whole thing.
        dap_logger.info(f'ModelProxy getattr called with "{name}"')
        unproxied_model = object.__getattribute__(self, '__wrapped__')

        model_fields = unproxied_model._meta.get_fields()

        relational_field = None
        for field in model_fields:

            if field.name == name and field.is_relation:
                relational_field = field
                dap_logger.info(f'Trying to access relational field "{name}"')
                break

        if not relational_field:
            return getattr(unproxied_model, name)

        # Now we check whether or not it's been cached
        is_cached_already = relational_field.is_cached(unproxied_model)
        if is_cached_already:
            dap_logger.info(f'Model field "{name}" was cached already.')
            return getattr(unproxied_model, name)

        dap_logger.info(f'Model field "{name}" was not cached already. Prefetching it on next iteration')
        qs = self.queryset

        # Put the description on the queryset
        qs._django_auto_prefetching_should_prefetch_fields = PrefetchDescription(set(), set())

        # Depending on the field type, we should add it to prefetch_related or select_related
        if relational_field.one_to_one or relational_field.many_to_one:
            qs._django_auto_prefetching_should_prefetch_fields.select_related.add(self.prefix + relational_field.name)
        elif relational_field.one_to_many:
            qs._django_auto_prefetching_should_prefetch_fields.prefetch_related.add(self.prefix + relational_field.name)

        # TODO we currently don't support many to many, as the way to tell whether or not they've been prefetched
        #  is different

        # Here if we have a relational field that manifests in just a single object, we can simply wrap
        # that model in a ModelProxy with a new prefix, to build a new path there
        if relational_field.one_to_one or relational_field.many_to_one:
            related_model = getattr(unproxied_model, name)
            # The prefix here is the name of our current model
            prefix = f"{self.prefix}{relational_field.name}__"
            return ModelProxy(related_model, originating_queryset=self.queryset, prefix=prefix)

        # If not a relational field, just return as-is as there's no point in proxying any further
        return getattr(unproxied_model, name)