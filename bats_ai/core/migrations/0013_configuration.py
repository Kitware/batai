# Generated by Django 4.1.13 on 2025-01-03 15:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0012_recordingannotation_additional_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='Configuration',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('display_pulse_annotations', models.BooleanField(default=True)),
                ('display_sequence_annotations', models.BooleanField(default=True)),
            ],
        ),
    ]
