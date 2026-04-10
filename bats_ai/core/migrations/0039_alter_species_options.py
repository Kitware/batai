from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0038_alter_compressedspectrogram_recording"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="species",
            options={"verbose_name_plural": "species"},
        ),
    ]
