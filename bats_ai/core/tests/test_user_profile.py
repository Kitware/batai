from django.contrib.auth.models import User
import pytest

from bats_ai.core.models import UserProfile


@pytest.mark.django_db
def test_profile_creation():
    user = User.objects.create()
    profile = UserProfile.objects.filter(user=user).first()
    assert profile is not None
    assert not profile.verified
