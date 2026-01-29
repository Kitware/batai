from django.contrib.auth.models import User
from django.test import Client
from oauth2_provider.models import AccessToken
import pytest

from bats_ai.core.models import VettingDetails

from .factories import AccessTokenFactory, SuperuserFactory, UserFactory, VettingDetailsFactory


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def user() -> User:
    return UserFactory()


@pytest.fixture
def user_token(user) -> AccessToken:
    return AccessTokenFactory(user=user)


@pytest.fixture
def authenticated_client(user: User, user_token: AccessToken) -> Client:
    client = Client()
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {user_token.token}'
    return client


@pytest.fixture
def superuser() -> User:
    return SuperuserFactory()


@pytest.fixture
def superuser_token(superuser) -> AccessToken:
    return AccessTokenFactory(user=superuser)


@pytest.fixture
def authorized_client(superuser: User, superuser_token: AccessToken) -> Client:
    client = Client()
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {superuser_token.token}'
    return client


@pytest.fixture
def vetting_details(user: User) -> VettingDetails:
    return VettingDetailsFactory(user=user)


@pytest.fixture
def random_user_vetting_details() -> VettingDetails:
    return VettingDetailsFactory(user=UserFactory())
