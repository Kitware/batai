from django.contrib.auth.models import User
from django.test import Client
import pytest
from pytest_factoryboy import register

from .factories import SuperuserFactory, UserFactory


@pytest.fixture
def client() -> Client:
    return Client()


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


register(UserFactory, 'user')
register(SuperuserFactory, 'superuser')
