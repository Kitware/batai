from django.db import models


class Species(models.Model):
    species_code = models.CharField(max_length=10, blank=True, null=True)
    family = models.CharField(max_length=50, blank=True, null=True)
    genus = models.CharField(max_length=50, blank=True, null=True)
    species = models.CharField(max_length=100, blank=True, null=True)
    common_name = models.CharField(max_length=100, blank=True, null=True)
    species_code_6 = models.CharField(max_length=10, blank=True, null=True)

