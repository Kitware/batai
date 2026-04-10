from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0037_alter_spectrogram_recording"),
    ]

    operations = [
        migrations.AlterField(
            model_name="compressedspectrogram",
            name="recording",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="compressed_spectrograms",
                to="core.recording",
            ),
        ),
        migrations.AlterField(
            model_name="nabatcompressedspectrogram",
            name="nabat_recording",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="compressed_spectrograms",
                to="core.nabatrecording",
            ),
        ),
    ]
