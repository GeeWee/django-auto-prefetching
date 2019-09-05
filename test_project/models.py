from django.db import models

# Create your models here.


class ChildA(models.Model):
    name = models.TextField()

    def __str__(self):
        return f'ChildA name={self.name} brother = {self.brother.name}'


class ChildABro(models.Model):
    sibling = models.OneToOneField(
        ChildA, on_delete=models.CASCADE, related_name="brother"
    )
    name = models.TextField()

    def __str__(self):
        return f'ChildABro name={self.name} brother = {self.sibling.name}'


class ChildB(models.Model):
    name = models.TextField()
    parent = models.ForeignKey(
        "test_project.Parent", on_delete=models.CASCADE, related_name="children_b"
    )

    def __str__(self):
        return f'ChildB name={self.name} parent = {self.parent.name}'


class Parent(models.Model):
    name = models.TextField()


# ------- Models for m2m ---------
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

    def __str__(self):
        return f"SingleChildToy for child {self.owner} in car {self.owner.parent.car}"


class DeeplyNestedChildren(models.Model):
    parent = models.ForeignKey(
        DeeplyNestedParent, on_delete=models.CASCADE, related_name="children_set"
    )

class GrandKidFavouriteMeal(models.Model):
    name = models.TextField()


class GrandKids(models.Model):
    parent = models.ForeignKey(
        DeeplyNestedChildren, on_delete=models.CASCADE, related_name="children"
    )
    favourite_meal = models.ForeignKey(GrandKidFavouriteMeal, on_delete=models.SET_NULL, null=True, related_name='eaters')


class GrandKidFavouriteToy(models.Model):
    owner = models.ForeignKey(
        GrandKids, on_delete=models.CASCADE, related_name="toy"
    )



class DeeplyNestedChildrenToys(models.Model):
    owners = models.ManyToManyField(DeeplyNestedChildren, related_name="toys")
