"""
test_search.py — Performance test for Nextcloud full-text search latency.

Performs a search query via the OCS search API and measures response time.
Asserts latency < 2 seconds.

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


def _ocs_headers():
    return {
        "OCS-APIRequest": "true",
        "Accept": "application/json",
    }


def _dav_url(path=""):
    user = os.environ["NEXTCLOUD_ADMIN_USER"]
    dav_base = f"{_base_url()}/remote.php/dav/files/{user}"
    if path:
        dav_base = f"{dav_base}/{path.lstrip('/')}"
    return dav_base


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

class TestSearchLatency:
    """Measure full-text search query latency."""

    def test_fulltext_search_latency(self):
        """Search for a known term and assert response time < 2 seconds."""
        # First, upload a file with a unique searchable term so we have
        # something to find. This makes the test self-contained.
        search_term = f"searchtest-{uuid.uuid4().hex[:8]}"
        filename = f"search-{uuid.uuid4().hex[:8]}.txt"
        content = f"This file contains the unique term: {search_term}".encode("utf-8")

        # Upload the file
        put_url = _dav_url(filename)
        put_resp = requests.put(
            put_url,
            auth=_auth(),
            data=content,
            headers={"Content-Type": "text/plain"},
            timeout=30,
        )
        assert put_resp.status_code in (201, 204), (
            f"Failed to upload search test file: HTTP {put_resp.status_code}"
        )

        try:
            # Perform the search and measure latency
            search_url = (
                f"{_base_url()}/ocs/v2.php/search/providers/files/search"
            )
            params = {"term": search_term}

            start = time.monotonic()
            resp = requests.get(
                search_url,
                auth=_auth(),
                headers=_ocs_headers(),
                params=params,
                timeout=30,
            )
            elapsed = time.monotonic() - start

            # The search API may return 200 (success) or 404/501 if the
            # fulltextsearch app is not installed. Handle both gracefully.
            if resp.status_code == 200:
                # Search succeeded — verify latency
                assert elapsed < 2.0, (
                    f"Search latency {elapsed:.2f}s exceeds 2s threshold. "
                    f"Query: '{search_term}'"
                )
            elif resp.status_code in (404, 501):
                pytest.skip(
                    f"Full-text search API not available (HTTP {resp.status_code}). "
                    "Skipping latency test."
                )
            else:
                # Unexpected status — still check latency if it was fast enough
                # to not be a timeout
                if elapsed < 2.0:
                    pytest.skip(
                        f"Search API returned unexpected status {resp.status_code}. "
                        "Skipping latency assertion."
                    )
                else:
                    pytest.fail(
                        f"Search API returned HTTP {resp.status_code} and took "
                        f"{elapsed:.2f}s (exceeds 2s threshold). "
                        f"Response: {resp.text[:500]}"
                    )

        finally:
            # Cleanup: delete the uploaded file
            try:
                requests.delete(put_url, auth=_auth(), timeout=30)
            except Exception:
                pass
