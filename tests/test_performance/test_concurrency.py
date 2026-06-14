"""
test_concurrency.py — Performance test for Nextcloud concurrent operations.

Performs 5 concurrent WebDAV uploads and verifies all succeed.

Self-contained, idempotent, marked @pytest.mark.performance.

Environment variables:
    NEXTCLOUD_URL          - Base URL of the Nextcloud instance
    NEXTCLOUD_ADMIN_USER   - Admin username
    NEXTCLOUD_ADMIN_PASS   - Admin password
"""

import os
import uuid
import pytest
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


pytestmark = pytest.mark.performance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth():
    return (os.environ["NEXTCLOUD_ADMIN_USER"], os.environ["NEXTCLOUD_ADMIN_PASS"])


def _base_url():
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _dav_url(path=""):
    user = os.environ["NEXTCLOUD_ADMIN_USER"]
    dav_base = f"{_base_url()}/remote.php/dav/files/{user}"
    if path:
        dav_base = f"{dav_base}/{path.lstrip('/')}"
    return dav_base


def _upload_one(filename, content):
    """Upload a single file and return (filename, status_code, error)."""
    url = _dav_url(filename)
    try:
        resp = requests.put(
            url,
            auth=_auth(),
            data=content,
            headers={"Content-Type": "application/octet-stream"},
            timeout=30,
        )
        return (filename, resp.status_code, None)
    except Exception as exc:
        return (filename, None, str(exc))


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

class TestConcurrency:
    """Verify 5 concurrent uploads all succeed."""

    def test_parallel_operations(self):
        """Upload 5 files concurrently and assert all succeed."""
        num_uploads = 5
        uploads = []

        for i in range(num_uploads):
            filename = f"concurrent-{uuid.uuid4().hex[:8]}-{i}.bin"
            content = os.urandom(1024)  # 1 KiB each
            uploads.append((filename, content))

        # Execute uploads concurrently
        results = []
        with ThreadPoolExecutor(max_workers=num_uploads) as executor:
            futures = {
                executor.submit(_upload_one, fn, ct): fn
                for fn, ct in uploads
            }
            for future in as_completed(futures):
                results.append(future.result())

        # Cleanup: delete all uploaded files
        for filename, _, _ in results:
            try:
                requests.delete(_dav_url(filename), auth=_auth(), timeout=30)
            except Exception:
                pass

        # Verify all uploads succeeded
        failures = [
            (fn, status, err)
            for fn, status, err in results
            if status not in (201, 204)
        ]

        assert len(failures) == 0, (
            f"{len(failures)} of {num_uploads} concurrent uploads failed:\n"
            + "\n".join(
                f"  {fn}: HTTP {status}, error: {err}"
                for fn, status, err in failures
            )
        )

        # All succeeded
        assert len(results) == num_uploads, (
            f"Expected {num_uploads} results, got {len(results)}"
        )
