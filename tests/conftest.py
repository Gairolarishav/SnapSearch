"""
Shared pytest fixtures for SnapSearch tests.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    """Provide a synchronous TestClient for the full app."""
    with TestClient(app) as c:
        yield c
