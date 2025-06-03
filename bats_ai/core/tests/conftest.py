from django.contrib.auth.models import User
from django.test import Client
import pytest

from .factories import SuperuserFactory, UserFactory


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
