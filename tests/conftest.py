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

import contextlib
import functools
import os
import socket
from collections.abc import Generator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import requests

from .utils.data_generators import (
    generate_random_file,
    generate_test_filename,
    generate_test_user_data,
)
from .utils.keycloak_api import KeycloakAPI
from .utils.lago_api import LagoAPI
from .utils.nextcloud_api import NextcloudAPI, NextcloudAPIError

# ---------------------------------------------------------------------------
# Live-service detection
#
# Almost every test in this suite exercises a *running* deployment over HTTP
# (Nextcloud on NEXTCLOUD_URL, Keycloak for test_identity, Lago for
# test_billing).  When that stack is not available -- e.g. in the CI
# "unit-tests" job -- those tests are marked ``live`` and skipped with a clear
# reason instead of erroring with KeyError / ConnectionError.  Self-contained
# tests (``tests/unit``) always run.
# ---------------------------------------------------------------------------

_TESTS_ROOT = Path(__file__).resolve().parent

# Test packages that need no running services.
_OFFLINE_PACKAGES = frozenset({"unit"})

# package -> (required env vars, env var holding the base URL, default URL)
_SERVICE_REQUIREMENTS: dict[str, tuple[tuple[str, ...], str, str]] = {
    "nextcloud": (
        ("NEXTCLOUD_URL", "NEXTCLOUD_ADMIN_USER", "NEXTCLOUD_ADMIN_PASS"),
        "NEXTCLOUD_URL",
        "http://localhost:8080",
    ),
    "keycloak": ((), "KEYCLOAK_URL", "http://localhost:8081"),
    "lago": ((), "LAGO_API_URL", "http://localhost:3000"),
}

# Which services each test package depends on (default: nextcloud only).
_PACKAGE_SERVICES: dict[str, tuple[str, ...]] = {
    "test_identity": ("nextcloud", "keycloak"),
    "test_billing": ("nextcloud", "lago"),
}


def _tcp_reachable(url: str, timeout: float = 3.0) -> bool:
    """Return True if a TCP connection to the URL's host:port succeeds."""
    parsed = urlsplit(url)
    if not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except OSError:
        return False


@functools.cache
def _service_unavailable_reason(service: str) -> str | None:
    """Return why ``service`` cannot be used, or None if it looks usable."""
    required_env, url_env, default_url = _SERVICE_REQUIREMENTS[service]
    missing = [name for name in required_env if not os.environ.get(name)]
    if missing:
        return f"{service}: environment variable(s) not set: {', '.join(missing)}"
    url = os.environ.get(url_env) or default_url
    if not _tcp_reachable(url):
        return f"{service}: server not reachable at {url}"
    return None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark tests that need a live stack and skip them if it is unavailable."""
    for item in items:
        try:
            rel = item.path.resolve().relative_to(_TESTS_ROOT)
        except ValueError:
            continue
        package = rel.parts[0] if len(rel.parts) > 1 else ""
        if not package.startswith("test_") or package in _OFFLINE_PACKAGES:
            continue
        item.add_marker(pytest.mark.live)
        for service in _PACKAGE_SERVICES.get(package, ("nextcloud",)):
            reason = _service_unavailable_reason(service)
            if reason is not None:
                item.add_marker(pytest.mark.skip(reason=f"live test skipped -- {reason}"))
                break

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
def test_user(nextcloud_api: NextcloudAPI) -> Generator[dict[str, str], None, None]:
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
    with contextlib.suppress(NextcloudAPIError, requests.RequestException):  # best-effort cleanup
        nextcloud_api.delete_user(user_data["username"])


# ---------------------------------------------------------------------------
# Disposable test file fixture (function-scoped — uploaded per test, cleaned up)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_file(nextcloud_api: NextcloudAPI) -> Generator[dict[str, Any], None, None]:
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
    with contextlib.suppress(NextcloudAPIError, requests.RequestException):  # best-effort cleanup
        nextcloud_api.delete(filename)
