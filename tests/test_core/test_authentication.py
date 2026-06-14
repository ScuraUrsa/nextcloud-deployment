"""
test_authentication.py — Smoke tests for Nextcloud authentication flows.

Verifies:
- Admin login succeeds
- Invalid login is rejected
- Session persistence across requests
- Logout invalidates session
- 2FA challenge when enforced (if 2FA enabled)

All tests are marked @pytest.mark.smoke.
"""

import re
import pytest
import requests
from urllib.parse import urljoin


pytestmark = pytest.mark.smoke


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_requesttoken(html: str) -> str | None:
    """Extract the CSRF requesttoken from an HTML page."""
    match = re.search(r'data-requesttoken="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
    if match:
        return match.group(1)
    return None


def _is_logged_in(session, base_url) -> bool:
    """Check if the session is currently authenticated by hitting a protected page."""
    try:
        resp = session.get(
            urljoin(base_url, "/settings/user"),
            timeout=30,
            allow_redirects=False,
        )
        # If we get a 200 and stay on the settings page, we're logged in
        # If we get redirected to /login, we're not
        if resp.status_code == 200 and "/login" not in resp.url:
            return True
        return False
    except requests.RequestException:
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAdminLogin:
    """Verify the admin user can log in successfully."""

    def test_admin_login(self, nextcloud_api):
        """Admin login should succeed and return a valid session."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]

        # The nextcloud_api fixture already performed login.
        # Verify the session is still authenticated.
        assert _is_logged_in(session, base_url), (
            "Admin session is not authenticated after login"
        )


class TestInvalidLogin:
    """Verify that invalid credentials are rejected."""

    def test_invalid_login(self, nextcloud_url):
        """Login with wrong password should be rejected."""
        base_url = nextcloud_url.rstrip("/")

        session = requests.Session()
        session.headers.update({"User-Agent": "Nextcloud-TestSuite/1.0"})

        # Get CSRF token
        login_page = urljoin(base_url, "/login")
        resp = session.get(login_page, timeout=30)
        resp.raise_for_status()
        token = _extract_requesttoken(resp.text)

        # Attempt login with wrong password
        login_data = {
            "user": "admin",
            "password": "DefinitelyWrongPassword123!@#",
        }
        if token:
            login_data["requesttoken"] = token

        login_action = urljoin(base_url, "/login")
        resp = session.post(login_action, data=login_data, timeout=30)

        # Nextcloud returns 200 even on failed login, but the page contains
        # an error message
        assert "Invalid password" in resp.text or "Wrong password" in resp.text or \
               "invalidpassword" in resp.text.lower() or \
               "Login failed" in resp.text, (
            "Expected login failure message, but none found in response"
        )

        # Verify we are NOT logged in
        assert not _is_logged_in(session, base_url), (
            "Session should not be authenticated after invalid login"
        )


class TestSessionPersistence:
    """Verify that a session cookie persists across multiple requests."""

    def test_session_persistence(self, nextcloud_api):
        """After login, the session should remain valid for subsequent requests."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]

        # Make multiple requests to different protected endpoints
        endpoints = [
            "/settings/user",
            "/index.php/apps/files/",
            "/ocs/v2.php/cloud/capabilities",
        ]

        for endpoint in endpoints:
            url = urljoin(base_url, endpoint)
            headers = {"OCS-APIRequest": "true"} if "ocs" in endpoint else {}
            try:
                resp = session.get(url, headers=headers, timeout=30)
                # Should not be redirected to login
                assert resp.status_code in (200, 302), (
                    f"Unexpected status {resp.status_code} for {endpoint}"
                )
                if resp.status_code == 302:
                    assert "/login" not in resp.headers.get("Location", ""), (
                        f"Session redirected to login on {endpoint}"
                    )
            except requests.RequestException as exc:
                pytest.fail(f"Request to {endpoint} failed: {exc}")


class TestLogout:
    """Verify that logout invalidates the session."""

    def test_logout(self, nextcloud_api):
        """After logout, the session should no longer be authenticated."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]

        # Verify we are logged in first
        assert _is_logged_in(session, base_url), (
            "Precondition failed: session is not authenticated before logout test"
        )

        # Perform logout
        logout_url = urljoin(base_url, "/logout")
        try:
            resp = session.get(logout_url, timeout=30, allow_redirects=True)
        except requests.RequestException as exc:
            pytest.fail(f"Logout request failed: {exc}")

        # After logout, the session should not be authenticated
        assert not _is_logged_in(session, base_url), (
            "Session is still authenticated after logout"
        )


class Test2FARequired:
    """Verify 2FA challenge is presented when enforced (if 2FA is enabled)."""

    def test_2fa_required(self, nextcloud_url, admin_user, admin_pass):
        """If 2FA is enforced, login should present a 2FA challenge."""
        base_url = nextcloud_url.rstrip("/")

        # First, check if 2FA is enabled for the admin user
        # We do this by attempting login and checking for 2FA challenge
        session = requests.Session()
        session.headers.update({"User-Agent": "Nextcloud-TestSuite/1.0"})

        login_page = urljoin(base_url, "/login")
        resp = session.get(login_page, timeout=30)
        resp.raise_for_status()
        token = _extract_requesttoken(resp.text)

        login_data = {
            "user": admin_user,
            "password": admin_pass,
        }
        if token:
            login_data["requesttoken"] = token

        login_action = urljoin(base_url, "/login")
        resp = session.post(login_action, data=login_data, timeout=30)

        # Check if we got a 2FA challenge page
        is_2fa_challenge = (
            "two-factor" in resp.text.lower() or
            "totp" in resp.text.lower() or
            "challenge" in resp.text.lower() or
            "2fa" in resp.text.lower() or
            "second factor" in resp.text.lower()
        )

        if is_2fa_challenge:
            # 2FA is enabled — verify the challenge page is presented
            # (we can't complete 2FA without the TOTP secret, but we can
            # verify the challenge is shown)
            assert "token" in resp.text.lower() or "code" in resp.text.lower(), (
                "2FA challenge page does not contain token/code input field"
            )
        else:
            # 2FA is not enabled — skip the test
            pytest.skip("2FA is not enforced for the admin user — skipping")
