from __future__ import annotations

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"UserProfile {self.pk} (user={self.user_id})"


@receiver(post_save, sender=User, dispatch_uid="create_new_user_profile")
def _create_new_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def _notify_admins_new_user(sender, instance, created, **kwargs):
    if not created:
        # Only send the email on initial user creation
        return
    admins = User.objects.filter(is_superuser=True)
    current_site = Site.objects.get_current()
    recipient_list = [admin.email for admin in admins]

    if recipient_list:
        email_content = render_to_string(
            "core/new_user_signup.txt",
            {
                "user": instance,
                "site": current_site,
            },
        )
        send_mail(
            subject=f"{current_site.name}: New user signup",
            message=email_content,
            from_email=None,
            recipient_list=recipient_list,
        )
