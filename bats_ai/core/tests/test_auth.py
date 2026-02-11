from django.test import Client
import pytest


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
