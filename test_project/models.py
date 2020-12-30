from django.db import models

# Create your models here.


class ChildA(models.Model):
    childA_text = models.TextField()


class ChildABro(models.Model):
    sibling = models.OneToOneField(
        ChildA, on_delete=models.CASCADE, related_name="brother"
    )
    brother_text = models.TextField()


class ChildB(models.Model):
    childB_text = models.TextField()
    parent = models.ForeignKey(
        "test_project.TopLevel", on_delete=models.CASCADE, related_name="children_b", null=True
    )


class TopLevel(models.Model):
    top_level_text = models.TextField()


class ManyToManyModelOne(models.Model):
    one_text = models.TextField()
    model_two_set = models.ManyToManyField(
        to="test_project.ManyToManyModelTwo", related_name="model_one_set"
    )


class ManyToManyModelTwo(models.Model):
    two_text = models.TextField()
    pass


# -------- MODELS FOR DEEP NESTING -------------
class ParentCar(models.Model):
    pass


class DeeplyNestedParent(models.Model):
    car = models.ForeignKey(ParentCar, on_delete=models.SET_NULL, null=True)


class DeeplyNestedChild(models.Model):
    parent = models.OneToOneField(
        DeeplyNestedParent, on_delete=models.CASCADE, related_name="child"
    )


class SingleChildToy(models.Model):
    owner = models.ForeignKey(
        DeeplyNestedChild, on_delete=models.CASCADE, related_name="toy"
    )


class DeeplyNestedChildren(models.Model):
    parent = models.ForeignKey(
        DeeplyNestedParent, on_delete=models.CASCADE, related_name="children_set"
    )


class GrandKids(models.Model):
    parent = models.ForeignKey(
        DeeplyNestedChildren, on_delete=models.CASCADE, related_name="children"
    )


class DeeplyNestedChildrenToys(models.Model):
    owners = models.ManyToManyField(DeeplyNestedChildren, related_name="toys")
