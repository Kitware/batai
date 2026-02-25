from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_oauth_application"),
        ("core", "0025_configuration_mark_annotations_completed_enabled_and_more"),
    ]
