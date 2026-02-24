from __future__ import annotations

from django.db import models


class Species(models.Model):
    CATEGORY_CHOICES = {
        'couplet': 'Couplet',
        'individual': 'Individual Species',
        'frequency': 'Frequency',
        'noid': 'NoID',
    }

    species_code = models.CharField(max_length=255, blank=True, null=True)
    family = models.CharField(max_length=255, blank=True, null=True)
    genus = models.CharField(max_length=255, blank=True, null=True)
    species = models.CharField(max_length=255, blank=True, null=True)
    common_name = models.CharField(max_length=255, blank=True, null=True)
    species_code_6 = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='individual',
        help_text='Category label: couplet, individual species, frequency, or NoID',
    )
