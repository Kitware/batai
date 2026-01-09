from django.contrib.auth.models import User
from django.test import Client
import pytest

from bats_ai.core.models import VettingDetails

from .factories import SuperuserFactory, UserFactory, VettingDetailsFactory


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def user() -> User:
    return UserFactory()


@pytest.fixture
def superuser() -> User:
    return SuperuserFactory()


@pytest.fixture
def authenticated_client(user: User) -> Client:
    client = Client()
    client.force_login(user=user)
    return client


@pytest.fixture
def authorized_client(superuser: User) -> Client:
    client = Client()
    client.force_login(user=superuser)
    return client


@pytest.fixture
def vetting_details(user: User) -> VettingDetails:
    return VettingDetailsFactory(user=user)


@pytest.fixture
def random_user_vetting_details() -> VettingDetails:
    return VettingDetailsFactory(user=UserFactory())
