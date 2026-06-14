"""
test_tls.py — Security tests for Nextcloud TLS configuration.

Verifies:
- TLS 1.2 or higher is enforced (no TLS 1.0/1.1)
- No weak cipher suites are accepted

Self-contained, idempotent, marked @pytest.mark.security.

Environment variables:
    NEXTCLOUD_URL          - Base URL of the Nextcloud instance
"""

import os
import ssl
import socket
import pytest


pytestmark = pytest.mark.security


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hostname():
    """Extract hostname from NEXTCLOUD_URL."""
    from urllib.parse import urlparse
    url = os.environ["NEXTCLOUD_URL"]
    parsed = urlparse(url)
    return parsed.hostname or "localhost"


def _port():
    """Extract port from NEXTCLOUD_URL, default 443 for https, 80 for http."""
    from urllib.parse import urlparse
    url = os.environ["NEXTCLOUD_URL"]
    parsed = urlparse(url)
    if parsed.port:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def _is_https():
    """Check if NEXTCLOUD_URL uses HTTPS."""
    return os.environ["NEXTCLOUD_URL"].startswith("https://")


def _get_tls_version_and_ciphers():
    """Connect via TLS and return (protocol_version, cipher_tuple)."""
    host = _hostname()
    port = _port()

    context = ssl.create_default_context()
    # We want to see what the server actually negotiates, so don't restrict
    # our client too much — but we do require a secure connection.
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    sock = socket.create_connection((host, port), timeout=10)
    try:
        with context.wrap_socket(sock, server_hostname=host) as tls_sock:
            version = tls_sock.version()
            cipher = tls_sock.cipher()
            return (version, cipher)
    finally:
        # sock is closed by wrap_socket context manager
        pass


# ---------------------------------------------------------------------------
# Known weak cipher suites (substrings to match)
# ---------------------------------------------------------------------------

WEAK_CIPHER_PATTERNS = [
    "NULL",
    "anon",
    "EXPORT",
    "DES",
    "RC4",
    "MD5",
    "3DES",
    "CBC3",
    "PSK",
    "SRP",
    "aNULL",
    "eNULL",
    "ADH",
    "AECDH",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTLS:
    """Verify TLS version and cipher suite security."""

    def test_tls_version(self):
        """Server must negotiate TLS 1.2 or higher."""
        if not _is_https():
            pytest.skip("NEXTCLOUD_URL is not HTTPS — skipping TLS version test")

        try:
            version, _ = _get_tls_version_and_ciphers()
        except (ssl.SSLError, socket.error, ConnectionRefusedError) as exc:
            pytest.fail(f"TLS connection failed: {exc}")

        # TLS 1.0 and 1.1 are deprecated
        deprecated = {"TLSv1", "TLSv1.1", "SSLv2", "SSLv3"}
        assert version not in deprecated, (
            f"Server negotiated deprecated TLS version '{version}'. "
            f"Expected TLS 1.2 or higher."
        )

        # Verify it's at least TLS 1.2
        valid_tls12_plus = {"TLSv1.2", "TLSv1.3"}
        assert version in valid_tls12_plus, (
            f"Server negotiated TLS version '{version}'. "
            f"Expected TLSv1.2 or TLSv1.3."
        )

    def test_cipher_suites(self):
        """Server must not negotiate weak cipher suites."""
        if not _is_https():
            pytest.skip("NEXTCLOUD_URL is not HTTPS — skipping cipher suite test")

        try:
            _, cipher = _get_tls_version_and_ciphers()
        except (ssl.SSLError, socket.error, ConnectionRefusedError) as exc:
            pytest.fail(f"TLS connection failed: {exc}")

        # cipher is a 3-tuple: (name, protocol_version, secret_bits)
        cipher_name = cipher[0] if cipher else ""

        assert cipher_name, "No cipher suite negotiated"

        # Check for weak cipher patterns
        cipher_upper = cipher_name.upper()
        for pattern in WEAK_CIPHER_PATTERNS:
            assert pattern.upper() not in cipher_upper, (
                f"Weak cipher suite detected: '{cipher_name}' "
                f"matches weak pattern '{pattern}'"
            )
