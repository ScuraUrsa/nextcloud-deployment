"""
test_enterprise_features.py — Verify enterprise tier has access to all features.

Tests:
- test_enterprise_user_all_features: An enterprise-tier user should have access to
  files, Talk, and Collabora.

All tests are marked @pytest.mark.tiers.
"""

from __future__ import annotations

import pytest

from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data, generate_random_file, generate_test_filename


pytestmark = pytest.mark.tiers


class TestEnterpriseFeatures:
    """Verify enterprise tier has full feature access."""

    def test_enterprise_user_all_features(self, nextcloud_api: NextcloudAPI) -> None:
        """An enterprise-tier user should have access to files, Talk, and Collabora."""
        user_data = generate_test_user_data(prefix="ent")
        username = user_data["username"]
        password = user_data["password"]

        # Create enterprise-tier user
        try:
            nextcloud_api.create_user(
                userid=username,
                password=password,
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to create enterprise user: {exc}")

        # Add to nc-enterprise group
        try:
            nextcloud_api.add_to_group(username, "nc-enterprise")
        except NextcloudAPIError:
            try:
                nextcloud_api._ocs_request(
                    "POST", "cloud/groups", data={"groupid": "nc-enterprise"}
                )
                nextcloud_api.add_to_group(username, "nc-enterprise")
            except NextcloudAPIError as exc:
                pytest.fail(f"Failed to add user to nc-enterprise group: {exc}")

        import requests
        import base64

        user_session = requests.Session()
        auth_raw = f"{username}:{password}"
        auth_header = f"Basic {base64.b64encode(auth_raw.encode()).decode()}"

        # Test 1: Files access (WebDAV upload)
        filename = generate_test_filename("txt")
        content = generate_random_file(256)
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
            assert resp.status_code in (200, 201, 204), (
                f"Enterprise user file upload failed: status {resp.status_code}"
            )
        except requests.RequestException as exc:
            pytest.fail(f"Enterprise user WebDAV upload failed: {exc}")

        # Cleanup file
        try:
            user_session.delete(webdav_url, headers={"Authorization": auth_header}, timeout=30)
        except requests.RequestException:
            pass

        # Test 2: Talk access (if enabled)
        try:
            apps_resp = nextcloud_api.list_apps()
            apps = apps_resp.ocs_data
            app_list = (
                list(apps.keys()) if isinstance(apps, dict)
                else apps if isinstance(apps, list)
                else []
            )
            talk_enabled = "spreed" in app_list
        except NextcloudAPIError:
            talk_enabled = False

        if talk_enabled:
            talk_url = f"{nextcloud_api.base_url}/ocs/v2.php/apps/spreed/api/v4/room"
            try:
                resp = user_session.get(
                    talk_url,
                    headers={
                        "Authorization": auth_header,
                        "OCS-APIRequest": "true",
                        "Accept": "application/json",
                    },
                    timeout=30,
                )
                assert resp.status_code == 200, (
                    f"Enterprise user Talk access failed: status {resp.status_code}"
                )
            except requests.RequestException as exc:
                pytest.fail(f"Enterprise user Talk request failed: {exc}")

        # Test 3: Collabora access (if enabled)
        try:
            apps_resp = nextcloud_api.list_apps()
            apps = apps_resp.ocs_data
            app_list = (
                list(apps.keys()) if isinstance(apps, dict)
                else apps if isinstance(apps, list)
                else []
            )
            collab_enabled = any("richdocuments" in a.lower() for a in app_list)
        except NextcloudAPIError:
            collab_enabled = False

        if collab_enabled:
            collab_url = f"{nextcloud_api.base_url}/ocs/v2.php/apps/richdocuments/api/v1/document"
            try:
                resp = user_session.post(
                    collab_url,
                    headers={
                        "Authorization": auth_header,
                        "OCS-APIRequest": "true",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json={"path": "/test.docx", "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                    timeout=30,
                )
                # Enterprise should have access; 200 or 4xx with a meaningful error
                # (not 401/403) is acceptable
                if resp.status_code in (401, 403):
                    pytest.fail(
                        f"Enterprise user denied Collabora access: status {resp.status_code}"
                    )
            except requests.RequestException as exc:
                pytest.fail(f"Enterprise user Collabora request failed: {exc}")

        # Cleanup user
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass
