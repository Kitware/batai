from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length

models.TextField.register_lookup(Length, 'length')


class VettingDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    reference_materials = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(reference_materials__length__lte=2000),
                name='reference_materials_max_2000',
            )
        ]
