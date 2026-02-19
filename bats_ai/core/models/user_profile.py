from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    verified = models.BooleanField(default=False)


@receiver(post_save, sender=User, dispatch_uid='create_new_user_profile')
def _create_new_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def _notify_admins_new_user(sender, instance, created, **kwargs):
    admins = User.objects.filter(is_superuser=True).all()
    recipient_list = [admin.email for admin in admins]

    if recipient_list:
        new_user_url = reverse('admin:auth_user_change', args=[instance.pk])
        email_content = render_to_string('core/new_user_signup.txt', {'new_user_url': new_user_url})
        send_mail(
            'New user signup',
            email_content,
            None,
            recipient_list,
        )
