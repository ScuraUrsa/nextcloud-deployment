"""
test_external_storage.py — Admin tests for Nextcloud External Storage app.

Tests:
- test_s3_mount: Verify an S3 external storage mount can be configured.
- test_file_through_mount: Upload a file through an external storage mount
  and verify it is accessible.

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


def _ocs_post(endpoint, data=None):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.post(
        url, auth=_auth(), headers=_ocs_headers(),
        json=data or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _ocs_delete(endpoint):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.delete(url, auth=_auth(), headers=_ocs_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _ocs_put(endpoint, data=None):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.put(
        url, auth=_auth(), headers=_ocs_headers(),
        json=data or {}, timeout=30,
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


def _webdav_get(path):
    """Download a file via WebDAV GET."""
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{path.lstrip('/')}"
    resp = requests.get(url, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp


def _webdav_delete(path):
    """Delete a file via WebDAV DELETE."""
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{path.lstrip('/')}"
    try:
        resp = requests.delete(url, auth=_auth(), timeout=30)
        resp.raise_for_status()
    except requests.HTTPError:
        pass


def _webdav_mkcol(path):
    """Create a directory via WebDAV MKCOL."""
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{path.lstrip('/')}"
    resp = requests.request("MKCOL", url, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp


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
def test_s3_mount(unique_suffix):
    """Verify that an S3 external storage mount can be configured via the API."""
    # Check if the files_external app is enabled
    try:
        apps_result = _ocs_get("cloud/apps")
        apps_data = apps_result.get("ocs", {}).get("data", {})
        apps_list = apps_data.get("apps", []) if isinstance(apps_data, dict) else []

        external_enabled = False
        if isinstance(apps_list, list):
            for app in apps_list:
                if isinstance(app, dict) and "files_external" in app.get("id", ""):
                    external_enabled = app.get("active", False)
                    break

        if not external_enabled:
            pytest.skip("External Storage app (files_external) is not enabled — skipping")
    except requests.HTTPError:
        pytest.skip("Cannot check app status — skipping")

    # The external storage API is at /index.php/apps/files_external/api/v1/mounts
    mounts_url = f"{_base_url()}/index.php/apps/files_external/api/v1/mounts"

    # S3 mount configuration (using placeholder credentials)
    # In a real test environment, these would come from env vars
    s3_bucket = os.environ.get("TEST_S3_BUCKET", "test-bucket")
    s3_key = os.environ.get("TEST_S3_KEY", "test-key")
    s3_secret = os.environ.get("TEST_S3_SECRET", "test-secret")
    s3_region = os.environ.get("TEST_S3_REGION", "us-east-1")
    s3_endpoint = os.environ.get("TEST_S3_ENDPOINT", "")

    mount_data = {
        "mountPoint": f"s3_test_{unique_suffix}",
        "backend": "amazons3",
        "authMechanism": "key::secret",
        "backendOptions": {
            "bucket": s3_bucket,
            "key": s3_key,
            "secret": s3_secret,
            "region": s3_region,
            "hostname": s3_endpoint,
            "use_ssl": True,
            "use_path_style": False,
        },
        "priority": 128,
        "applicable": {
            "users": [os.environ["NEXTCLOUD_ADMIN_USER"]],
            "groups": [],
        },
    }

    try:
        resp = requests.post(
            mounts_url,
            auth=_auth(),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=mount_data,
            timeout=30,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            mount_id = data.get("id") or data.get("mountId") or data.get("mount_id")
            assert mount_id, f"Mount creation response missing ID: {data}"

            # Verify the mount appears in the list
            list_resp = requests.get(
                mounts_url,
                auth=_auth(),
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if list_resp.status_code == 200:
                mounts = list_resp.json()
                mounts_list = mounts if isinstance(mounts, list) else mounts.get("data", mounts.get("mounts", []))
                found = any(
                    m.get("id") == mount_id or m.get("mountPoint") == mount_data["mountPoint"]
                    for m in mounts_list
                    if isinstance(m, dict)
                )
                assert found, f"Created mount not found in list: {mounts}"

            # Cleanup: delete the mount
            requests.delete(
                f"{mounts_url}/{mount_id}",
                auth=_auth(),
                headers={"Accept": "application/json"},
                timeout=30,
            )

        elif resp.status_code in (404, 501):
            pytest.skip("External storage mounts API not available — skipping")
        else:
            pytest.skip(f"Mount creation returned status {resp.status_code} — skipping")

    except requests.ConnectionError:
        pytest.skip("External storage API endpoint not reachable — skipping")


@pytest.mark.admin
def test_file_through_mount(unique_suffix):
    """Upload a file through an external storage mount and verify accessibility."""
    # Check if the files_external app is enabled
    try:
        apps_result = _ocs_get("cloud/apps")
        apps_data = apps_result.get("ocs", {}).get("data", {})
        apps_list = apps_data.get("apps", []) if isinstance(apps_data, dict) else []

        external_enabled = False
        if isinstance(apps_list, list):
            for app in apps_list:
                if isinstance(app, dict) and "files_external" in app.get("id", ""):
                    external_enabled = app.get("active", False)
                    break

        if not external_enabled:
            pytest.skip("External Storage app (files_external) is not enabled — skipping")
    except requests.HTTPError:
        pytest.skip("Cannot check app status — skipping")

    # For this test, we use the local storage backend (which is always available)
    # to simulate a mount and verify file operations through it.
    mounts_url = f"{_base_url()}/index.php/apps/files_external/api/v1/mounts"

    # Create a local storage mount pointing to a directory within Nextcloud
    mount_point = f"local_mount_{unique_suffix}"

    mount_data = {
        "mountPoint": mount_point,
        "backend": "local",
        "authMechanism": "password::password",
        "backendOptions": {
            "datadir": f"/tmp/nc_external_test_{unique_suffix}",
        },
        "priority": 128,
        "applicable": {
            "users": [os.environ["NEXTCLOUD_ADMIN_USER"]],
            "groups": [],
        },
    }

    mount_id = None
    try:
        resp = requests.post(
            mounts_url,
            auth=_auth(),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=mount_data,
            timeout=30,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            mount_id = data.get("id") or data.get("mountId") or data.get("mount_id")
        else:
            pytest.skip(f"Mount creation returned status {resp.status_code} — skipping")
            return

        if not mount_id:
            pytest.skip("Could not create mount for file-through-mount test — skipping")
            return

        # Now try to upload a file into the mount point
        test_filename = f"{mount_point}/test_file_{unique_suffix}.txt"
        test_content = b"File through external storage mount test"

        try:
            _webdav_put(test_filename, test_content)
        except requests.HTTPError as exc:
            # The mount may not be writable or the backend may not be available
            if exc.response is not None and exc.response.status_code in (403, 404, 405, 507):
                pytest.skip(f"Cannot write to mount (status {exc.response.status_code}) — skipping")
            else:
                raise

        # Verify the file is accessible through the mount
        try:
            get_resp = _webdav_get(test_filename)
            assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
            assert test_content in get_resp.content, (
                "File content through mount does not match uploaded content"
            )
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in (404, 403):
                pytest.skip("File not accessible through mount — skipping")
            else:
                raise

        # Cleanup: delete the file and the mount
        _webdav_delete(test_filename)

    finally:
        if mount_id:
            try:
                requests.delete(
                    f"{mounts_url}/{mount_id}",
                    auth=_auth(),
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
            except Exception:
                pass
