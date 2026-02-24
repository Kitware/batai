from __future__ import annotations

from ninja.testing import TestClient
import pytest

from bats_ai.core.tests.factories import SuperuserFactory, UserFactory


@pytest.mark.django_db
def test_check_is_admin_authenticated(api_client: TestClient):
    user = UserFactory.create()

    resp = api_client.get('configuration/is_admin/', user=user)

    assert resp.status_code == 200
    assert resp.data['is_admin'] is False


@pytest.mark.django_db
def test_check_is_admin_superuser(api_client: TestClient):
    user = SuperuserFactory.create()

    resp = api_client.get('configuration/is_admin/', user=user)

    assert resp.status_code == 200
    assert resp.data['is_admin'] is True
