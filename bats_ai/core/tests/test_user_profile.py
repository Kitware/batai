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
    user = User.objects.create(
        username='foo',
        email='foo@bar.com',
    )
    m = mailoutbox[0]
    assert superuser.email in m.to
    assert reverse('admin:auth_user_change', args=[user.pk]) in m.body
