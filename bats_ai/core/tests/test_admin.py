import pytest


@pytest.mark.parametrize(
    'client_fixture,status_code,is_admin',
    [
        ('client', 401, None),
        ('authenticated_client', 200, False),
        ('authorized_client', 200, True),
    ],
)
@pytest.mark.django_db
def test_is_admin(client_fixture, status_code, is_admin, request):
    api_client = request.getfixturevalue(client_fixture)
    resp = api_client.get('/api/v1/configuration/is_admin/')
    assert resp.status_code == status_code
    if is_admin is not None:
        assert resp.json()['is_admin'] == is_admin


@pytest.mark.parametrize(
    'client_fixture,status_code',
    [
        ('authenticated_client', 200),
        ('client', 401),
    ],
)
@pytest.mark.django_db
def test_get_current_user(client_fixture, status_code, user, request):
    api_client = request.getfixturevalue(client_fixture)
    resp = api_client.get('/api/v1/configuration/me')
    assert resp.status_code == status_code
    if status_code == 200:
        assert resp.json()['name'] == user.username
        assert resp.json()['email'] == user.email
