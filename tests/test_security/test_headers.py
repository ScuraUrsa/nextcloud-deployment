"""
test_headers.py — Security tests for Nextcloud HTTP security headers.

Verifies:
- Strict-Transport-Security (HSTS) header is present
- X-Content-Type-Options header is set to nosniff
- X-Frame-Options header is set to prevent clickjacking

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


def _get_headers(path="/"):
    """Fetch response headers for a given path."""
    url = f"{_base_url()}{path}"
    resp = requests.get(url, timeout=30, allow_redirects=True)
    return dict(resp.headers)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Verify critical HTTP security headers are present."""

    def test_hsts_header(self):
        """Strict-Transport-Security header should be present."""
        headers = _get_headers("/")

        hsts = headers.get("Strict-Transport-Security", "")
        assert hsts, (
            "Strict-Transport-Security (HSTS) header is missing. "
            f"Response headers: {dict(headers)}"
        )

        # HSTS should include max-age
        assert "max-age" in hsts.lower(), (
            f"HSTS header present but missing 'max-age' directive: '{hsts}'"
        )

    def test_x_content_type_options(self):
        """X-Content-Type-Options should be set to nosniff."""
        headers = _get_headers("/")

        xcto = headers.get("X-Content-Type-Options", "")
        assert xcto.lower() == "nosniff", (
            f"X-Content-Type-Options expected 'nosniff', got '{xcto}'. "
            f"Response headers: {dict(headers)}"
        )

    def test_x_frame_options(self):
        """X-Frame-Options should be set to prevent clickjacking."""
        headers = _get_headers("/")

        xfo = headers.get("X-Frame-Options", "")
        assert xfo, (
            "X-Frame-Options header is missing. "
            f"Response headers: {dict(headers)}"
        )

        # Valid values: DENY, SAMEORIGIN, or ALLOW-FROM uri
        valid = {"deny", "sameorigin"}
        xfo_lower = xfo.lower()
        assert xfo_lower in valid or xfo_lower.startswith("allow-from"), (
            f"X-Frame-Options has unexpected value '{xfo}'. "
            f"Expected DENY, SAMEORIGIN, or ALLOW-FROM."
        )
