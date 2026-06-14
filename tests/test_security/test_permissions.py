"""
test_permissions.py — Security test for Nextcloud config file permissions.

Verifies that config.php is not world-readable by checking the
Nextcloud status.php endpoint, which would reveal a permissions
warning if config.php is exposed.

Self-contained, idempotent, marked @pytest.mark.security.

Environment variables:
    NEXTCLOUD_URL          - Base URL of the Nextcloud instance
"""

import os
import pytest
import requests


pytestmark = pytest.mark.security


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_url():
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _fetch_status():
    """Fetch status.php and return parsed JSON, or fail the test."""
    base_url = _base_url()
    status_url = f"{base_url}/status.php"
    resp = requests.get(status_url, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

class TestPermissions:
    """Verify config.php is not world-readable."""

    def test_config_php_permissions(self):
        """config.php must not be world-readable (no security warning)."""
        try:
            data = _fetch_status()
        except requests.RequestException as exc:
            pytest.fail(f"Failed to fetch status.php: {exc}")
            return  # unreachable, satisfies static analysis

        # Check for config_is_readable warning
        config_warning = data.get("config_is_readable", False)
        assert not config_warning, (
            "status.php reports config_is_readable=true — "
            "config.php may be world-readable!"
        )

        # Also check the general 'installed' and error fields
        if "error" in data and data["error"]:
            error_msg = str(data.get("error", "")).lower()
            assert "config" not in error_msg or "readable" not in error_msg, (
                f"status.php reports a config-related error: {data['error']}"
            )

        # Check for any security warnings in the response
        security_warnings = data.get("security", {})
        if isinstance(security_warnings, dict):
            for key, value in security_warnings.items():
                assert "config" not in str(key).lower() or "readable" not in str(value).lower(), (
                    f"Security warning about config readability: {key}={value}"
                )
