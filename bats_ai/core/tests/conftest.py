from __future__ import annotations

from django.test import Client
from ninja.testing import TestClient
import pytest

from bats_ai.core.api import api


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(api)
