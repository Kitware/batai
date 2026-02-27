# Generated manually for RecordingAnnotationSpecies through model
from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


def copy_species_to_through(apps, schema_editor):
    """Copy existing M2M relations into RecordingAnnotationSpecies with order."""
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
    """Reverse migration does not restore old M2M table data."""


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
        # Copy data before we remove the old M2M: temporarily we have both.
        # RunPython runs after CreateModel, so the through table exists but is empty.
        # The old M2M is still on RecordingAnnotation until we AlterField.
        # So we need to copy from old M2M to through *before* removing the field.
        # But CreateModel only creates the through table; the field on RecordingAnnotation
        # is still the old M2M. So we can: 1) Create through model 2) RunPython copy
        # (read from ann.species.all() - that still uses the OLD M2M table) 3) RemoveField
        # species 4) AddField species with through.
        migrations.RunPython(copy_species_to_through, noop_reverse),
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
                to="core.species",
            ),
        ),
    ]
