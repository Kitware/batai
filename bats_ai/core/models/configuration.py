from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver


# Define the Configuration model
class Configuration(models.Model):
    display_pulse_annotations = models.BooleanField(default=True)
    display_sequence_annotations = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Ensure only one instance of Configuration exists
        if not Configuration.objects.exists() and not self.pk:
            super().save(*args, **kwargs)
        elif self.pk:
            super().save(*args, **kwargs)
        else:
            raise ValueError('Only one instance of Configuration is allowed.')


# Automatically create a Configuration instance after migrations
@receiver(post_migrate)
def create_default_configuration(sender, **kwargs):
    if not Configuration.objects.exists():
        Configuration.objects.create()
