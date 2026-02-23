from django.contrib.auth.models import User
from django.urls import reverse
import pytest

from bats_ai.core.models import UserProfile

from .factories import SuperuserFactory


@pytest.mark.django_db
def test_profile_creation():
    # Use django model directly to test the signal receiver,
    # not whether our factories are working as intended.
    user = User.objects.create()
    profile = UserProfile.objects.get(user=user)
    assert not profile.verified


@pytest.mark.django_db
def test_new_user_signup_email_sent(mailoutbox):
    superuser = SuperuserFactory()
    new_user = User.objects.create(
        username='foo',
        email='foo@bar.com',
    )
    message = next(filter(lambda message: 'New user signup' in message.subject, mailoutbox), None)
    assert message is not None
    assert superuser.email in message.to
    assert reverse('admin:auth_user_change', args=[new_user.pk]) in message.body


@pytest.mark.django_db
def test_user_save_no_email_sent(mailoutbox):
    SuperuserFactory()
    new_user = User.objects.create(
        username='foo',
        email='foo@bar.com',
    )
    new_user.username = 'bar'
    new_user.save()
    filter(lambda message: 'New user signup' in message.subject, mailoutbox)
    assert len(mailoutbox) == 1
