"""Shared fixtures for DriftBalloon SDK tests."""

import os
from uuid import uuid4

import httpx
import pytest


def _backend_is_running(url: str) -> bool:
    """Check if the local backend is reachable."""
    try:
        r = httpx.get(f"{url}/health", timeout=3.0)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.fixture(scope="session")
def backend_url() -> str:
    """Base URL for the local backend."""
    return os.environ.get("DRIFTBALLOON_TEST_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def test_credentials(backend_url: str) -> tuple[str, str]:
    """Create a one-time test user and return (api_key, jwt_token).

    Supports three modes:
    1. DRIFTBALLOON_API_KEY env var set — use that directly (jwt_token will be empty).
    2. Signup succeeds — use the returned api_key and token.
    3. Signup fails with "already registered" — login and regenerate an API key.

    Skips the entire session if the backend is not running.
    """
    if not _backend_is_running(backend_url):
        pytest.skip("Backend is not running – skipping integration tests")

    # Allow override via env var for manual testing
    env_key = os.environ.get("DRIFTBALLOON_API_KEY")
    if env_key:
        return (env_key, "")

    uid = uuid4().hex[:12]
    email = f"sdk-test-{uid}@sdktest.io"
    password = "testpass123456"

    # Try signup first
    r = httpx.post(
        f"{backend_url}/api/auth/signup",
        json={"email": email, "password": password},
        timeout=10.0,
    )

    if r.status_code == 200:
        data = r.json()
        return (data["api_key"], data["token"])

    # If signup failed with "already registered", login + regenerate key
    if r.status_code == 400 and "already registered" in r.text:
        lr = httpx.post(
            f"{backend_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=10.0,
        )
        if lr.status_code == 200:
            token = lr.json()["token"]
            kr = httpx.post(
                f"{backend_url}/api/key/regenerate",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            if kr.status_code == 200:
                return (kr.json()["api_key"], token)

    pytest.skip(f"Could not create test user: {r.status_code} {r.text}")


@pytest.fixture(scope="session")
def test_api_key(test_credentials: tuple[str, str]) -> str:
    """Convenience fixture – just the API key."""
    return test_credentials[0]


@pytest.fixture(scope="session")
def test_jwt_token(test_credentials: tuple[str, str]) -> str:
    """Convenience fixture – just the JWT token."""
    return test_credentials[1]
