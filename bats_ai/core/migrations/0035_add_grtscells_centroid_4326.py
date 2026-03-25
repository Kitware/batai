from __future__ import annotations

from django.db import migrations, models


def backfill_centroids(apps, schema_editor) -> None:
    GRTSCells = apps.get_model("core", "GRTSCells")

    batch_size = 1000
    to_update = []

    qs = (
        GRTSCells.objects.filter(centroid_4326__isnull=True)
        .exclude(geom_4326__isnull=True)
        .only("id", "grts_cell_id", "sample_frame_id", "geom_4326")
    )

    for cell in qs.iterator(chunk_size=batch_size):
        # `centroid` returns a Point geometry in the same SRID.
        cell.centroid_4326 = cell.geom_4326.centroid
        to_update.append(cell)

        if len(to_update) >= batch_size:
            GRTSCells.objects.bulk_update(to_update, ["centroid_4326"], batch_size=batch_size)
            to_update.clear()

    if to_update:
        GRTSCells.objects.bulk_update(to_update, ["centroid_4326"], batch_size=batch_size)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0034_alter_spectrogramimage_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="grtscells",
            name="centroid_4326",
            field=models.PointField(srid=4326, null=True, blank=True),
        ),
        migrations.RunPython(backfill_centroids, migrations.RunPython.noop),
    ]
