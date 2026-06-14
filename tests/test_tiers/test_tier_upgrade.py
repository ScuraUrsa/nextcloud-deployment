"""
test_tier_upgrade.py — Verify tier upgrade: basic to pro.

Tests:
- test_basic_to_pro_upgrade: Moving a user from nc-basic to nc-pro group
  should grant pro-tier features.

All tests are marked @pytest.mark.tiers.
"""

from __future__ import annotations

import pytest

from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data


pytestmark = pytest.mark.tiers


class TestTierUpgrade:
    """Verify tier upgrade from basic to pro."""

    def test_basic_to_pro_upgrade(self, nextcloud_api: NextcloudAPI) -> None:
        """Moving a user from nc-basic to nc-pro should grant pro features."""
        user_data = generate_test_user_data(prefix="upgrade")
        username = user_data["username"]
        password = user_data["password"]

        # Create user
        try:
            nextcloud_api.create_user(
                userid=username,
                password=password,
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to create user: {exc}")

        # Ensure both groups exist
        for group in ("nc-basic", "nc-pro"):
            try:
                nextcloud_api._ocs_request(
                    "POST", "cloud/groups", data={"groupid": group}
                )
            except NextcloudAPIError:
                pass  # Group may already exist

        # Start as basic tier
        try:
            nextcloud_api.add_to_group(username, "nc-basic")
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to add user to nc-basic: {exc}")

        # Verify user is in nc-basic
        try:
            user_resp = nextcloud_api.get_user(username)
            user_data_ocs = user_resp.ocs_data
            if isinstance(user_data_ocs, dict):
                groups = user_data_ocs.get("groups", [])
                assert "nc-basic" in groups, (
                    f"User not in nc-basic group. Groups: {groups}"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to verify basic group membership: {exc}")

        # Upgrade: remove from nc-basic, add to nc-pro
        try:
            nextcloud_api.remove_from_group(username, "nc-basic")
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to remove user from nc-basic: {exc}")

        try:
            nextcloud_api.add_to_group(username, "nc-pro")
        except NextcloudAPIError as exc:
            # Re-add to nc-basic before failing
            try:
                nextcloud_api.add_to_group(username, "nc-basic")
            except NextcloudAPIError:
                pass
            pytest.fail(f"Failed to add user to nc-pro: {exc}")

        # Verify user is now in nc-pro and not in nc-basic
        try:
            user_resp = nextcloud_api.get_user(username)
            user_data_ocs = user_resp.ocs_data
            if isinstance(user_data_ocs, dict):
                groups = user_data_ocs.get("groups", [])
                assert "nc-pro" in groups, (
                    f"User not in nc-pro group after upgrade. Groups: {groups}"
                )
                assert "nc-basic" not in groups, (
                    f"User still in nc-basic after upgrade. Groups: {groups}"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to verify pro group membership: {exc}")

        # Verify pro features are accessible (Talk, if enabled)
        try:
            apps_resp = nextcloud_api.list_apps()
            apps = apps_resp.ocs_data
            app_list = (
                list(apps.keys()) if isinstance(apps, dict)
                else apps if isinstance(apps, list)
                else []
            )
            if "spreed" in app_list:
                import requests
                import base64

                user_session = requests.Session()
                auth_raw = f"{username}:{password}"
                auth_header = f"Basic {base64.b64encode(auth_raw.encode()).decode()}"

                talk_url = f"{nextcloud_api.base_url}/ocs/v2.php/apps/spreed/api/v4/room"
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
                    f"Upgraded user cannot access Talk: status {resp.status_code}"
                )
        except NextcloudAPIError:
            pass  # Can't verify apps, skip feature check

        # Cleanup
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass
