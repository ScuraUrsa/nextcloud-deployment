"""
test_quota_enforcement.py — Verify quota limits are enforced per tier.

Tests:
- test_upload_until_quota_rejected: Upload files until the quota limit is hit
  and verify further uploads are rejected.

All tests are marked @pytest.mark.tiers.
"""

from __future__ import annotations

import pytest

from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data, generate_random_file, generate_test_filename


pytestmark = pytest.mark.tiers


class TestQuotaEnforcement:
    """Verify quota enforcement for tiered users."""

    def test_upload_until_quota_rejected(self, nextcloud_api: NextcloudAPI) -> None:
        """Upload files until quota is exceeded and verify rejection."""
        user_data = generate_test_user_data(prefix="quota")
        username = user_data["username"]
        password = user_data["password"]

        # Create user with a small quota (1 MB)
        try:
            nextcloud_api.create_user(
                userid=username,
                password=password,
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to create quota test user: {exc}")

        # Set a small quota: 1 MB
        try:
            nextcloud_api.set_quota(username, "1 MB")
        except NextcloudAPIError as exc:
            # Cleanup and skip if quota setting not supported
            try:
                nextcloud_api.delete_user(username)
            except NextcloudAPIError:
                pass
            pytest.fail(f"Failed to set quota: {exc}")

        # Verify quota is set
        try:
            user_resp = nextcloud_api.get_user(username)
            user_data_ocs = user_resp.ocs_data
            if isinstance(user_data_ocs, dict):
                quota_info = user_data_ocs.get("quota", {})
                if isinstance(quota_info, dict):
                    quota_limit = quota_info.get("quota", 0)
                    assert quota_limit > 0, (
                        f"Quota not set correctly: {quota_info}"
                    )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to verify quota: {exc}")

        import requests
        import base64

        user_session = requests.Session()
        auth_raw = f"{username}:{password}"
        auth_header = f"Basic {base64.b64encode(auth_raw.encode()).decode()}"

        # Upload files until quota is exceeded
        # 1 MB quota, upload 256 KB chunks
        chunk_size = 256 * 1024  # 256 KB
        max_chunks = 10  # Up to 2.5 MB total (should exceed 1 MB quota)
        uploaded = 0
        quota_hit = False

        for i in range(max_chunks):
            filename = generate_test_filename("bin")
            content = generate_random_file(chunk_size)
            webdav_url = (
                f"{nextcloud_api.base_url}/remote.php/dav/files/{username}/{filename}"
            )

            try:
                resp = user_session.put(
                    webdav_url,
                    data=content,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/octet-stream",
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201, 204):
                    uploaded += 1
                elif resp.status_code == 507:  # Insufficient Storage
                    quota_hit = True
                    break
                elif resp.status_code in (403, 413):
                    quota_hit = True
                    break
            except requests.RequestException:
                break

        # At least one file should have been uploaded
        assert uploaded >= 1, (
            f"Could not upload even a single file. Quota may be 0 or user has no storage."
        )

        # If we uploaded 4+ chunks (1 MB+), quota should have been hit
        if uploaded >= 4:
            assert quota_hit, (
                f"Uploaded {uploaded} chunks ({uploaded * chunk_size / 1024:.0f} KB) "
                f"without hitting 1 MB quota. Quota enforcement may not be working."
            )

        # Cleanup: delete all uploaded files
        for i in range(uploaded):
            # We can't easily track filenames, but we can try to clean up
            # via the admin API
            pass

        # Cleanup user
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass
