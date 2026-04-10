from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_rename_grts_cell_recording_sample_frame_id_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nabatspectrogram",
            name="nabat_recording",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="spectrograms",
                to="core.nabatrecording",
            ),
        ),
        migrations.AlterField(
            model_name="spectrogram",
            name="recording",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="spectrograms",
                to="core.recording",
            ),
        ),
    ]
