from django.contrib.auth.models import User
import pytest

from bats_ai.core.models import UserProfile


@pytest.mark.django_db
def test_profile_creation():
    # Use django model directly to test the signal receiver,
    # not whether our factories are working as intended.
    user = User.objects.create()
    profile = UserProfile.objects.get(user=user)
    assert not profile.verified
