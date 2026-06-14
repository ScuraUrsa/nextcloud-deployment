"""
Pytest fixtures for Nextcloud deployment tests.

Provides fixtures for:
  - Nextcloud API client
  - Keycloak API client
  - Lago API client
  - Disposable test user (auto-cleanup)
  - Disposable test file (auto-cleanup)
"""

from __future__ import annotations

import os
from typing import Generator

import pytest

from .utils.nextcloud_api import NextcloudAPI
from .utils.keycloak_api import KeycloakAPI
from .utils.lago_api import LagoAPI
from .utils.data_generators import generate_random_file, generate_test_user_data, generate_test_filename


# ---------------------------------------------------------------------------
# API client fixtures (session-scoped — one instance per test run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def nextcloud_api() -> NextcloudAPI:
    """Nextcloud API client, configured from environment variables."""
    base_url = os.environ.get("NEXTCLOUD_URL", "http://localhost:8080")
    admin_user = os.environ.get("NEXTCLOUD_ADMIN_USER", "admin")
    admin_pass = os.environ.get("NEXTCLOUD_ADMIN_PASS", "admin")
    return NextcloudAPI(base_url=base_url, admin_user=admin_user, admin_pass=admin_pass)


@pytest.fixture(scope="session")
def keycloak_api() -> KeycloakAPI:
    """Keycloak API client, configured from environment variables."""
    base_url = os.environ.get("KEYCLOAK_URL", "http://localhost:8081")
    realm = os.environ.get("KEYCLOAK_REALM", "master")
    admin_user = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
    admin_pass = os.environ.get("KEYCLOAK_ADMIN_PASS", "admin")
    return KeycloakAPI(base_url=base_url, realm=realm, admin_user=admin_user, admin_pass=admin_pass)


@pytest.fixture(scope="session")
def lago_api() -> LagoAPI:
    """Lago API client, configured from environment variables."""
    base_url = os.environ.get("LAGO_API_URL", "http://localhost:3000")
    api_key = os.environ.get("LAGO_API_KEY", "")
    return LagoAPI(base_url=base_url, api_key=api_key)


# ---------------------------------------------------------------------------
# Disposable test user fixture (function-scoped — created per test, cleaned up)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_user(nextcloud_api: NextcloudAPI) -> Generator[dict, None, None]:
    """Create a disposable Nextcloud test user, then delete after the test."""
    user_data = generate_test_user_data(prefix="pytest")
    nextcloud_api.create_user(
        userid=user_data["username"],
        password=user_data["password"],
        display_name=user_data["display_name"],
        email=user_data["email"],
    )
    yield user_data
    # Cleanup
    try:
        nextcloud_api.delete_user(user_data["username"])
    except Exception:
        pass  # best-effort cleanup


# ---------------------------------------------------------------------------
# Disposable test file fixture (function-scoped — uploaded per test, cleaned up)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_file(nextcloud_api: NextcloudAPI) -> Generator[dict, None, None]:
    """Upload a disposable test file, then delete after the test."""
    filename = generate_test_filename("bin")
    content = generate_random_file(1024)  # 1 KiB
    nextcloud_api.put(filename, content)
    yield {
        "filename": filename,
        "content": content,
        "size": len(content),
    }
    # Cleanup
    try:
        nextcloud_api.delete(filename)
    except Exception:
        pass  # best-effort cleanup
