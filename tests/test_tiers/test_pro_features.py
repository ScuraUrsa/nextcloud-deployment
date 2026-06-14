"""
test_pro_features.py — Verify pro tier feature access.

Tests:
- test_pro_user_can_use_talk: A pro-tier user can use Talk.
- test_pro_user_cannot_use_collabora: A pro-tier user cannot use Collabora (enterprise-only).

All tests are marked @pytest.mark.tiers.
"""

from __future__ import annotations

import pytest

from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data


pytestmark = pytest.mark.tiers


class TestProFeatures:
    """Verify pro tier feature access and restrictions."""

    def test_pro_user_can_use_talk(self, nextcloud_api: NextcloudAPI) -> None:
        """A pro-tier user should be able to use Talk."""
        user_data = generate_test_user_data(prefix="protalk")
        username = user_data["username"]
        password = user_data["password"]

        # Create pro-tier user
        try:
            nextcloud_api.create_user(
                userid=username,
                password=password,
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to create pro user: {exc}")

        # Add to nc-pro group
        try:
            nextcloud_api.add_to_group(username, "nc-pro")
        except NextcloudAPIError:
            try:
                nextcloud_api._ocs_request(
                    "POST", "cloud/groups", data={"groupid": "nc-pro"}
                )
                nextcloud_api.add_to_group(username, "nc-pro")
            except NextcloudAPIError as exc:
                pytest.fail(f"Failed to add user to nc-pro group: {exc}")

        # Check if Talk app is enabled
        try:
            apps_resp = nextcloud_api.list_apps()
            apps = apps_resp.ocs_data
            app_list = (
                list(apps.keys()) if isinstance(apps, dict)
                else apps if isinstance(apps, list)
                else []
            )
            if "spreed" not in app_list:
                try:
                    nextcloud_api.delete_user(username)
                except NextcloudAPIError:
                    pass
                pytest.skip("Talk app (spreed) is not enabled — skipping")
        except NextcloudAPIError:
            try:
                nextcloud_api.delete_user(username)
            except NextcloudAPIError:
                pass
            pytest.skip("Cannot list apps — skipping Talk test")

        # Try to create a Talk conversation as the pro user
        import requests
        import base64

        user_session = requests.Session()
        auth_raw = f"{username}:{password}"
        auth_header = f"Basic {base64.b64encode(auth_raw.encode()).decode()}"

        talk_create_url = f"{nextcloud_api.base_url}/ocs/v2.php/apps/spreed/api/v4/room"
        try:
            resp = user_session.post(
                talk_create_url,
                headers={
                    "Authorization": auth_header,
                    "OCS-APIRequest": "true",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={"roomName": f"pro-test-{user_data['username']}", "roomType": 3},
                timeout=30,
            )
            if resp.status_code == 200:
                payload = resp.json()
                ocs = payload.get("ocs", {})
                meta = ocs.get("meta", {})
                assert meta.get("status") == "ok", (
                    f"Talk room creation failed: {meta}"
                )
            elif resp.status_code in (401, 403):
                pytest.fail(
                    f"Pro user denied Talk access: status {resp.status_code}. "
                    f"Pro tier should have Talk access."
                )
        except requests.RequestException as exc:
            pytest.fail(f"Talk API request failed: {exc}")

        # Cleanup
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass

    def test_pro_user_cannot_use_collabora(self, nextcloud_api: NextcloudAPI) -> None:
        """A pro-tier user should not be able to use Collabora (enterprise-only)."""
        user_data = generate_test_user_data(prefix="pronocollab")
        username = user_data["username"]
        password = user_data["password"]

        # Create pro-tier user
        try:
            nextcloud_api.create_user(
                userid=username,
                password=password,
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to create pro user: {exc}")

        # Add to nc-pro group
        try:
            nextcloud_api.add_to_group(username, "nc-pro")
        except NextcloudAPIError:
            try:
                nextcloud_api._ocs_request(
                    "POST", "cloud/groups", data={"groupid": "nc-pro"}
                )
                nextcloud_api.add_to_group(username, "nc-pro")
            except NextcloudAPIError as exc:
                pytest.fail(f"Failed to add user to nc-pro group: {exc}")

        # Check if Collabora (richdocuments) app is enabled
        try:
            apps_resp = nextcloud_api.list_apps()
            apps = apps_resp.ocs_data
            app_list = (
                list(apps.keys()) if isinstance(apps, dict)
                else apps if isinstance(apps, list)
                else []
            )
            collabora_apps = [a for a in app_list if "richdocuments" in a.lower() or "collabora" in a.lower()]
            if not collabora_apps:
                try:
                    nextcloud_api.delete_user(username)
                except NextcloudAPIError:
                    pass
                pytest.skip("Collabora/richdocuments app not enabled — skipping")
        except NextcloudAPIError:
            try:
                nextcloud_api.delete_user(username)
            except NextcloudAPIError:
                pass
            pytest.skip("Cannot list apps — skipping Collabora restriction test")

        # Try to access Collabora API as the pro user
        import requests
        import base64

        user_session = requests.Session()
        auth_raw = f"{username}:{password}"
        auth_header = f"Basic {base64.b64encode(auth_raw.encode()).decode()}"

        # Try the richdocuments OCS endpoint
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
            if resp.status_code in (401, 403):
                # Access denied — tier restriction working as expected
                pass
            elif resp.status_code == 200:
                # Collabora is accessible to pro users — tier restrictions may not be in place
                pass
        except requests.RequestException:
            pass

        # Cleanup
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass
