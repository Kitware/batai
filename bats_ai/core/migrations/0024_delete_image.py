from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0023_recordingtag_recording_tags_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Image',
        ),
    ]
