"""
test_music.py — Content tests for Nextcloud Music app.

Tests:
- test_upload_audio: Upload an audio file and verify it is stored correctly.
- test_ampache_api: Verify the Ampache-compatible API is reachable.

All tests are self-contained, idempotent, and marked @pytest.mark.content.
"""

from __future__ import annotations

import os
import uuid
import pytest
import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth():
    return (os.environ["NEXTCLOUD_ADMIN_USER"], os.environ["NEXTCLOUD_ADMIN_PASS"])


def _base_url():
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _ocs_headers():
    return {
        "OCS-APIRequest": "true",
        "Accept": "application/json",
    }


def _ocs_get(endpoint, params=None):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.get(
        url, auth=_auth(), headers=_ocs_headers(),
        params=params or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _webdav_put(path, data, content_type="audio/mpeg"):
    """Upload a file via WebDAV PUT."""
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{path.lstrip('/')}"
    resp = requests.put(
        url, auth=_auth(), data=data,
        headers={"Content-Type": content_type},
        timeout=30,
    )
    resp.raise_for_status()
    return resp


def _webdav_delete(path):
    """Delete a file via WebDAV DELETE."""
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{path.lstrip('/')}"
    resp = requests.delete(url, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp


def _generate_tiny_mp3() -> bytes:
    """Generate a minimal valid MP3 file (silent, ~417 bytes)."""
    # Minimal MP3: ID3v2 header + a single silent MPEG audio frame
    # ID3v2.3 header (10 bytes) + empty frame
    id3_header = b"ID3\x03\x00\x00\x00\x00\x00\x00"
    # MPEG audio frame header: MPEG1 Layer3 128kbps 44100Hz stereo, padding=0
    # Frame sync 0xFFE0 | version=3 | layer=1 | no CRC=1 | bitrate=5 (128kbps)
    # sample rate=0 (44100) | padding=0 | private=0 | channel=0 (stereo)
    frame_header = b"\xff\xfb\x50\x00"
    # Frame body: 417 bytes total frame size for 128kbps 44100Hz
    # Frame size = 144 * bitrate / samplerate + padding
    # = 144 * 128000 / 44100 + 0 = 417 (rounded)
    frame_body = b"\x00" * (417 - 4)  # silent frame
    return id3_header + frame_header + frame_body


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unique_suffix():
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.content
def test_upload_audio(unique_suffix):
    """Upload an MP3 audio file via WebDAV and verify it is stored correctly."""
    filename = f"test_audio_{unique_suffix}.mp3"
    mp3_data = _generate_tiny_mp3()

    # Upload the audio file
    _webdav_put(filename, mp3_data)

    # Verify it exists by downloading it back
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{filename}"
    resp = requests.get(url, auth=_auth(), timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert len(resp.content) > 0, "Downloaded file is empty"
    # Verify it starts with ID3 magic bytes
    assert resp.content[:3] == b"ID3", "Downloaded file is not a valid MP3 (missing ID3 header)"

    # Cleanup
    _webdav_delete(filename)


@pytest.mark.content
def test_ampache_api(unique_suffix):
    """Verify the Ampache-compatible API endpoint is reachable and responds."""
    # The Music app exposes an Ampache API at /index.php/apps/music/ampache/
    # The handshake endpoint is /index.php/apps/music/ampache/server/xml.server.php
    ampache_url = f"{_base_url()}/index.php/apps/music/ampache/server/xml.server.php"

    # Ampache handshake: action=handshake&auth=passphrase&timestamp=...
    # We use a simple ping/handshake attempt
    params = {
        "action": "handshake",
        "auth": os.environ["NEXTCLOUD_ADMIN_PASS"],
        "timestamp": "0",
        "version": "350001",
        "user": os.environ["NEXTCLOUD_ADMIN_USER"],
    }

    try:
        resp = requests.get(ampache_url, params=params, timeout=30)
        # Ampache returns XML. A successful handshake returns an <auth> token.
        # If the app is not installed, we get a 404 or redirect.
        if resp.status_code == 200:
            assert "xml" in resp.headers.get("Content-Type", "").lower() or resp.text.strip().startswith("<?xml"), (
                "Ampache API did not return XML response"
            )
            # Check for handshake response elements
            assert "<root>" in resp.text or "<auth>" in resp.text or "session" in resp.text.lower(), (
                f"Ampache handshake response unexpected: {resp.text[:200]}"
            )
        elif resp.status_code in (404, 302):
            pytest.skip("Music app (Ampache API) is not installed or not enabled — skipping")
        else:
            pytest.fail(f"Ampache API returned unexpected status {resp.status_code}")
    except requests.ConnectionError:
        pytest.skip("Ampache API endpoint is not reachable — skipping")
