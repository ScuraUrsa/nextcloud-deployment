"""
test_brute_force.py — Security test for Nextcloud brute-force rate limiting.

Performs 10 rapid failed login attempts and verifies that the server
responds with HTTP 429 (Too Many Requests) to indicate rate limiting
is active.

Self-contained, idempotent, marked @pytest.mark.security.

Environment variables:
    NEXTCLOUD_URL          - Base URL of the Nextcloud instance
"""

import os
import re
import time
import pytest
import requests
from urllib.parse import urljoin


pytestmark = pytest.mark.security


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_url():
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _extract_requesttoken(html):
    """Extract the CSRF requesttoken from an HTML page."""
    match = re.search(r'data-requesttoken="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
    if match:
        return match.group(1)
    return None


def _attempt_failed_login(login_url):
    """Perform one failed login attempt. Returns HTTP status code."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Nextcloud-TestSuite/1.0"})

    # Get CSRF token
    get_resp = session.get(login_url, timeout=30)
    get_resp.raise_for_status()
    token = _extract_requesttoken(get_resp.text)

    # Attempt login with wrong password
    login_data = {
        "user": os.environ.get("NEXTCLOUD_ADMIN_USER", "admin"),
        "password": "DefinitelyWrongPassword_12345!@#$%",
    }
    if token:
        login_data["requesttoken"] = token

    post_resp = session.post(login_url, data=login_data, timeout=30)
    return post_resp.status_code


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

class TestBruteForce:
    """Verify rate limiting is enforced on repeated failed logins."""

    def test_rate_limiting(self):
        """10 rapid failed logins should trigger a 429 response."""
        base_url = _base_url()
        login_url = urljoin(base_url, "/login")

        got_429 = False
        statuses = []

        for attempt in range(1, 11):
            try:
                status = _attempt_failed_login(login_url)
            except requests.RequestException as exc:
                pytest.fail(f"Login attempt {attempt} failed: {exc}")
                return  # unreachable, but satisfies static analysis

            statuses.append(status)

            if status == 429:
                got_429 = True
                break

            # Small delay to avoid overwhelming the server but still
            # rapid enough to trigger rate limiting
            time.sleep(0.1)

        assert got_429, (
            f"Rate limiting not triggered after 10 rapid failed logins. "
            f"All response statuses: {statuses}. "
            f"Expected at least one HTTP 429 (Too Many Requests)."
        )
