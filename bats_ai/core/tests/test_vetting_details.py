from __future__ import annotations

from ninja.testing import TestClient
import pytest

from bats_ai.core.models import VettingDetails

from .factories import SuperuserFactory, UserFactory, VettingDetailsFactory


@pytest.mark.django_db
def test_get_vetting_details(api_client: TestClient):
    vetting_details = VettingDetailsFactory.create()

    resp = api_client.get(f"vetting/user/{vetting_details.user.id}", user=vetting_details.user)

    assert resp.status_code == 200
    assert resp.data["reference_materials"] == vetting_details.reference_materials


@pytest.mark.django_db
def test_get_vetting_details_other_user(api_client: TestClient):
    vetting_details = VettingDetailsFactory.create()
    other_user = UserFactory.create()

    resp = api_client.get(f"vetting/user/{vetting_details.user.id}", user=other_user)

    assert resp.status_code == 404


@pytest.mark.django_db
def test_create_vetting_details(api_client: TestClient):
    user = UserFactory.create()

    resp = api_client.post(
        f"vetting/user/{user.id}",
        json={"reference_materials": "foo"},
        user=user,
    )

    assert resp.status_code == 200
    assert resp.data["user_id"] == user.id
    assert resp.data["reference_materials"] == "foo"
    assert VettingDetails.objects.filter(user=user, reference_materials="foo").exists()


@pytest.mark.django_db
def test_create_vetting_details_other_user(api_client: TestClient):
    user = UserFactory.create()
    other_user = UserFactory.create()

    resp = api_client.post(
        f"vetting/user/{user.id}",
        json={"reference_materials": "foo"},
        user=other_user,
    )

    assert resp.status_code == 404


@pytest.mark.django_db
def test_create_vetting_details_other_superuser(api_client: TestClient):
    user = UserFactory.create()
    other_superuser = SuperuserFactory.create()

    resp = api_client.post(
        f"vetting/user/{user.id}",
        json={"reference_materials": "foo"},
        user=other_superuser,
    )

    assert resp.status_code == 200
    assert resp.data["reference_materials"] == "foo"
    assert VettingDetails.objects.filter(user=user, reference_materials="foo").exists()


@pytest.mark.django_db
def test_update_vetting_details(api_client: TestClient):
    vetting_details = VettingDetailsFactory.create()

    resp = api_client.post(
        f"vetting/user/{vetting_details.user.id}",
        json={"reference_materials": "foo"},
        user=vetting_details.user,
    )

    assert resp.status_code == 200
    assert resp.data["reference_materials"] == "foo"
    vetting_details.refresh_from_db()
    assert vetting_details.reference_materials == "foo"


@pytest.mark.django_db
def test_update_vetting_details_other_user(api_client: TestClient):
    vetting_details = VettingDetailsFactory.create()
    other_user = UserFactory.create()

    resp = api_client.post(
        f"vetting/user/{vetting_details.user.id}",
        json={"reference_materials": "foo"},
        user=other_user,
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_update_vetting_details_other_superuser(api_client: TestClient):
    vetting_details = VettingDetailsFactory.create()
    other_superuser = SuperuserFactory.create()

    resp = api_client.post(
        f"vetting/user/{vetting_details.user.id}",
        json={"reference_materials": "foo"},
        user=other_superuser,
    )

    assert resp.status_code == 200
    assert resp.data["reference_materials"] == "foo"
    vetting_details.refresh_from_db()
    assert vetting_details.reference_materials == "foo"


@pytest.mark.django_db
def test_update_vetting_details_length_constraint(api_client: TestClient):
    vetting_details = VettingDetailsFactory.create()

    resp = api_client.post(
        f"vetting/user/{vetting_details.user.id}",
        json={"reference_materials": "a" * 2001},
        user=vetting_details.user,
    )

    assert resp.status_code == 400
