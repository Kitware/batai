# Generated manually for RecordingAnnotationSpecies through model
from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion

# This migration introduces a custom through model
# (RecordingAnnotationSpecies) to store ordered species per
# RecordingAnnotation, migrates existing relations into it,
# and redefines the species Many-to-Many field to use that through model


def copy_species_to_recording_annotation_species(apps, schema_editor):
    """Copy existing relations into RecordingAnnotationSpecies with order."""
    RecordingAnnotation = apps.get_model("core", "RecordingAnnotation")
    RecordingAnnotationSpecies = apps.get_model("core", "RecordingAnnotationSpecies")
    for ann in RecordingAnnotation.objects.prefetch_related("species").all():
        species_list = list(ann.species.all())
        for order, species in enumerate(species_list):
            RecordingAnnotationSpecies.objects.create(
                recording_annotation=ann,
                species=species,
                order=order,
            )


def noop_reverse(apps, schema_editor):
    """Reverse migration does not restore old Many-to-Many table data."""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0032_pulsemetadata_slopes"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecordingAnnotationSpecies",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "recording_annotation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="core.recordingannotation",
                    ),
                ),
                (
                    "species",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="core.species",
                    ),
                ),
            ],
            options={
                "ordering": ["recording_annotation", "order"],
                "unique_together": {("recording_annotation", "order")},
            },
        ),
        migrations.RunPython(copy_species_to_recording_annotation_species, noop_reverse),
        migrations.RemoveField(
            model_name="recordingannotation",
            name="species",
        ),
        migrations.AddField(
            model_name="recordingannotation",
            name="species",
            field=models.ManyToManyField(
                blank=True,
                through="core.RecordingAnnotationSpecies",
                through_fields=("recording_annotation", "species"),
                to="core.species",
            ),
        ),
    ]
