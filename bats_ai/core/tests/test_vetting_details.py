import pytest

from .factories import AccessTokenFactory, UserFactory, VettingDetailsFactory


@pytest.mark.parametrize(
    'client_fixture,status_code',
    [
        ('client', 401),
        ('authenticated_client', 200),
        ('authorized_client', 200),
    ],
)
@pytest.mark.django_db
def test_get_vetting_details(client_fixture, status_code, user, vetting_details, request):
    api_client = request.getfixturevalue(client_fixture)
    resp = api_client.get(f'/api/v1/vetting/user/{user.id}')
    assert resp.status_code == status_code
    if status_code == 200:
        assert resp.json()['reference_materials'] == vetting_details.reference_materials


@pytest.mark.django_db
def test_get_vetting_details_other_user(authenticated_client):
    other_user = UserFactory()
    VettingDetailsFactory(user=other_user)
    resp = authenticated_client.get(f'/api/v1/vetting/user/{other_user.id}')
    assert resp.status_code == 404


@pytest.mark.django_db
def test_create_vetting_details(client):
    test_text = 'foo'
    data = {'reference_materials': test_text}
    test_user = UserFactory()
    test_token = AccessTokenFactory(user=test_user)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {test_token.token}'
    resp = client.post(
        f'/api/v1/vetting/user/{test_user.id}', data=data, content_type='application/json'
    )
    assert resp.status_code == 200
    assert resp.json()['user_id'] == test_user.id


@pytest.mark.parametrize(
    'client_fixture,status_code',
    [
        ('authenticated_client', 404),
        ('authorized_client', 200),
    ],
)
@pytest.mark.django_db
def test_create_vetting_details_other_user(client_fixture, status_code, request):
    api_client = request.getfixturevalue(client_fixture)
    test_text = 'foo'
    data = {'reference_materials': test_text}
    other_user = UserFactory()
    resp = api_client.post(
        f'/api/v1/vetting/user/{other_user.id}', data=data, content_type='application/json'
    )
    assert resp.status_code == status_code
    if status_code == 200:
        assert resp.json()['reference_materials'] == test_text


@pytest.mark.django_db
def test_update_vetting_details(client):
    test_text = 'bar'
    data = {'reference_materials': 'bar'}
    test_user = UserFactory()
    test_token = AccessTokenFactory(user=test_user)
    VettingDetailsFactory(user=test_user, reference_materials='foo')
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {test_token.token}'

    initial_resp = client.get(f'/api/v1/vetting/user/{test_user.id}')
    assert initial_resp.status_code == 200

    resp = client.post(
        f'/api/v1/vetting/user/{test_user.id}', data=data, content_type='application/json'
    )
    assert resp.status_code == 200

    new_details_response = client.get(f'/api/v1/vetting/user/{test_user.id}')
    assert new_details_response.status_code == 200
    assert new_details_response.json()['reference_materials'] == test_text


@pytest.mark.parametrize(
    'client_fixture,status_code',
    [
        ('authenticated_client', 404),
        ('authorized_client', 200),
    ],
)
@pytest.mark.django_db
def test_update_vetting_details_other_user(
    client_fixture, status_code, random_user_vetting_details, request
):
    api_client = request.getfixturevalue(client_fixture)
    resp = api_client.post(
        f'/api/v1/vetting/user/{random_user_vetting_details.user.id}',
        data={'reference_materials': 'foo'},
        content_type='application/json',
    )
    assert resp.status_code == status_code


@pytest.mark.django_db
def test_update_vetting_details_length_constraint(authorized_client, random_user_vetting_details):
    data = {'reference_materials': 'a' * 2001}
    resp = authorized_client.post(
        f'/api/v1/vetting/user/{random_user_vetting_details.user.id}',
        data=data,
        content_type='application/json',
    )
    assert resp.status_code == 400
