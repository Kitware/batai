from django.test import Client
from ninja.testing import TestClient
import pytest

from .factories import SuperuserFactory, UserFactory


@pytest.mark.parametrize(
    'url_suffix',
    [
        'configuration/is_admin/',
    ],
)
@pytest.mark.django_db
def test_auth_anonymous_deny(url_suffix: str, client: Client):
    resp = client.get(f'/api/v1/{url_suffix}')

    assert resp.status_code == 401


@pytest.mark.django_db
def test_auth_verified(api_client: TestClient):
    user = UserFactory(profile__verified=True)
    resp = api_client.get('configuration/me', user=user)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_auth_unverified_deny(api_client: TestClient):
    user = UserFactory(profile__verified=False)
    resp = api_client.get('configuration/me', user=user)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_auth_unverified_superuser(api_client: TestClient):
    user = SuperuserFactory(profile__verified=False)
    resp = api_client.get('configuration/me', user=user)
    assert resp.status_code == 200
