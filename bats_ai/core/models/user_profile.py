from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    verified = models.BooleanField(default=False)


@receiver(post_save, sender=User, dispatch_uid='create_new_user_profile')
def create_new_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
