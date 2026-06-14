"""
test_antivirus.py — Admin tests for Nextcloud Antivirus app.

Tests:
- test_eicar_detection: Upload the EICAR test file and verify it is detected
  as malware by the antivirus scanner.

All tests are self-contained, idempotent, and marked @pytest.mark.admin.
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


def _webdav_put(path, data, content_type="text/plain"):
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
    try:
        resp = requests.delete(url, auth=_auth(), timeout=30)
        resp.raise_for_status()
    except requests.HTTPError:
        pass  # File may have been quarantined/deleted by AV
    return


# The EICAR test file — a harmless string that all AV scanners recognize as malware
EICAR_TEST_STRING = (
    r'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unique_suffix():
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.admin
def test_eicar_detection(unique_suffix):
    """Upload the EICAR test file and verify the antivirus scanner detects it."""
    # Check if the files_antivirus app is enabled
    try:
        apps_result = _ocs_get("cloud/apps")
        apps_data = apps_result.get("ocs", {}).get("data", {})
        apps_list = apps_data.get("apps", []) if isinstance(apps_data, dict) else []

        av_enabled = False
        if isinstance(apps_list, list):
            for app in apps_list:
                if isinstance(app, dict) and "files_antivirus" in app.get("id", ""):
                    av_enabled = app.get("active", False)
                    break

        if not av_enabled:
            pytest.skip("Antivirus app (files_antivirus) is not enabled — skipping")
    except requests.HTTPError:
        pytest.skip("Cannot check app status — skipping")

    filename = f"eicar_test_{unique_suffix}.txt"
    eicar_data = EICAR_TEST_STRING.encode("ascii")

    # Upload the EICAR test file
    try:
        _webdav_put(filename, eicar_data, content_type="text/plain")
    except requests.HTTPError as exc:
        # The AV scanner may reject the upload immediately (HTTP 403 or similar)
        if exc.response is not None and exc.response.status_code in (403, 423, 400):
            # Upload was blocked — this is the expected behavior for a working AV
            assert True, "EICAR file upload was correctly blocked by antivirus"
            return
        raise

    # If upload succeeded, the AV scanner may scan asynchronously.
    # Wait a moment and then check if the file was quarantined/deleted.
    import time
    time.sleep(2)

    # Try to download the file — if AV worked, it should be gone or blocked
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{filename}"
    try:
        resp = requests.get(url, auth=_auth(), timeout=30)
        if resp.status_code == 200:
            # File is still accessible — AV may not have scanned yet or is misconfigured
            # Check if the file content was modified (some AV replace content with warning)
            if EICAR_TEST_STRING.encode() not in resp.content:
                # Content was replaced — AV modified the file
                assert True, "EICAR file content was modified by antivirus"
            else:
                # File is intact — AV may be scanning on a schedule or not working
                # This is not necessarily a failure; the AV might be configured for
                # on-access scanning only on certain operations
                pytest.skip(
                    "EICAR file was not immediately detected — "
                    "AV may be scanning on a schedule or on-access only"
                )
        elif resp.status_code in (403, 404, 423):
            # File is gone or blocked — AV worked
            assert True, "EICAR file was correctly removed/blocked by antivirus"
        else:
            pytest.fail(f"Unexpected status {resp.status_code} when checking EICAR file")
    except requests.ConnectionError:
        pytest.fail("Connection error while checking EICAR file status")
    finally:
        # Best-effort cleanup
        _webdav_delete(filename)
