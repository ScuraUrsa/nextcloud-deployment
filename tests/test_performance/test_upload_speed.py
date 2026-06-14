"""
test_upload_speed.py — Performance test for Nextcloud chunked upload throughput.

Uploads a 10MB file via WebDAV PUT and measures bytes/sec throughput.
Asserts throughput > 1 MB/s.

Self-contained, idempotent, marked @pytest.mark.performance.

Environment variables:
    NEXTCLOUD_URL          - Base URL of the Nextcloud instance
    NEXTCLOUD_ADMIN_USER   - Admin username
    NEXTCLOUD_ADMIN_PASS   - Admin password
"""

import os
import time
import uuid
import pytest
import requests


pytestmark = pytest.mark.performance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth():
    return (os.environ["NEXTCLOUD_ADMIN_USER"], os.environ["NEXTCLOUD_ADMIN_PASS"])


def _base_url():
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _dav_url(path=""):
    """Build a WebDAV URL for the admin user."""
    user = os.environ["NEXTCLOUD_ADMIN_USER"]
    dav_base = f"{_base_url()}/remote.php/dav/files/{user}"
    if path:
        dav_base = f"{dav_base}/{path.lstrip('/')}"
    return dav_base


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

class TestUploadSpeed:
    """Measure chunked upload throughput for a 10MB file."""

    def test_chunked_upload_throughput(self):
        """Upload a 10MB file via WebDAV PUT and assert throughput > 1 MB/s."""
        # Generate 10MB of deterministic content
        size_bytes = 10 * 1024 * 1024  # 10 MiB
        content = bytes(i % 256 for i in range(size_bytes))

        filename = f"perf-upload-{uuid.uuid4().hex[:8]}.bin"
        url = _dav_url(filename)

        # Measure upload time
        start = time.monotonic()
        resp = requests.put(
            url,
            auth=_auth(),
            data=content,
            headers={"Content-Type": "application/octet-stream"},
            timeout=120,
        )
        elapsed = time.monotonic() - start

        # Cleanup: delete the uploaded file
        try:
            requests.delete(url, auth=_auth(), timeout=30)
        except Exception:
            pass

        # Assert upload succeeded
        assert resp.status_code in (201, 204), (
            f"PUT 10MB file failed: HTTP {resp.status_code}. "
            f"Response: {resp.text[:500]}"
        )

        # Calculate throughput
        throughput_bytes_per_sec = size_bytes / elapsed if elapsed > 0 else 0
        throughput_mb_per_sec = throughput_bytes_per_sec / (1024 * 1024)

        assert throughput_mb_per_sec > 1.0, (
            f"Upload throughput {throughput_mb_per_sec:.2f} MB/s "
            f"is below 1 MB/s threshold. "
            f"Uploaded {size_bytes} bytes in {elapsed:.2f} seconds."
        )
