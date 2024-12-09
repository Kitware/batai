# Generated by Django 4.1.13 on 2024-12-09 15:26

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_extensions.db.fields


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0010_compressedspectrogram'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='annotations',
            options={'get_latest_by': 'modified'},
        ),
        migrations.AddField(
            model_name='annotations',
            name='confidence',
            field=models.FloatField(
                default=1.0,
                help_text='A confidence value between 0 and 1.0, default is 1.0.',
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AddField(
            model_name='annotations',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True, default=django.utils.timezone.now, verbose_name='created'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='annotations',
            name='model',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='annotations',
            name='modified',
            field=django_extensions.db.fields.ModificationDateTimeField(
                auto_now=True, verbose_name='modified'
            ),
        ),
        migrations.CreateModel(
            name='RecordingAnnotation',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('comments', models.TextField(blank=True, null=True)),
                ('model', models.TextField(blank=True, null=True)),
                (
                    'confidence',
                    models.FloatField(
                        default=1.0,
                        help_text='A confidence value between 0 and 1.0, default is 1.0.',
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(1.0),
                        ],
                    ),
                ),
                (
                    'owner',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    'recording',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='core.recording'
                    ),
                ),
                ('species', models.ManyToManyField(to='core.species')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]