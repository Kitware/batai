from __future__ import annotations

from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver


# Define the Configuration model
class Configuration(models.Model):
    class SpectrogramViewMode(models.TextChoices):
        COMPRESSED = "compressed"
        UNCOMPRESSED = "uncompressed"

    class AvailableColorScheme(models.TextChoices):
        INFERNO = "inferno"
        CIVIDIS = "cividis"
        VIRIDIS = "viridis"
        MAGMA = "magma"
        TURBO = "turbo"
        PLASMA = "plasma"

    display_pulse_annotations = models.BooleanField(default=True)
    display_sequence_annotations = models.BooleanField(default=True)
    run_inference_on_upload = models.BooleanField(default=True)
    spectrogram_x_stretch = models.DecimalField(default=2.5, max_digits=3, decimal_places=2)
    spectrogram_view = models.CharField(
        max_length=12, choices=SpectrogramViewMode, default=SpectrogramViewMode.COMPRESSED
    )
    default_color_scheme = models.CharField(
        max_length=20,
        choices=AvailableColorScheme,
        default=AvailableColorScheme.INFERNO,
    )
    # 18 characters is just enough for "rgb(255, 255, 255)"
    default_spectrogram_background_color = models.CharField(max_length=18, default="rgb(0, 0, 0)")

    # Fields used for community vetting focused deployment of BatAI
    non_admin_upload_enabled = models.BooleanField(default=True)
    mark_annotations_completed_enabled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Ensure only one instance of Configuration exists
        if (not Configuration.objects.exists() and not self.pk) or self.pk:
            super().save(*args, **kwargs)
        else:
            raise ValueError("Only one instance of Configuration is allowed.")


# Automatically create a Configuration instance after migrations
@receiver(post_migrate)
def create_default_configuration(sender, **kwargs):
    if not Configuration.objects.exists():
        Configuration.objects.create()
