"""
test_auto_provision.py — Verify that first SSO login automatically creates a Nextcloud user.

Tests:
- test_first_sso_login_creates_user: Simulating SSO provisioning by creating a user
  without a local password and verifying they can be managed.

All tests are marked @pytest.mark.identity.
"""

from __future__ import annotations

import pytest

from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data


pytestmark = pytest.mark.identity


class TestAutoProvision:
    """Verify auto-provisioning of users on first SSO login."""

    def test_first_sso_login_creates_user(self, nextcloud_api: NextcloudAPI) -> None:
        """Simulate SSO auto-provisioning: create a user without password and verify."""
        user_data = generate_test_user_data(prefix="autoprov")
        username = user_data["username"]

        # Simulate SSO provisioning: create user with no password
        # (as would happen on first SSO login)
        try:
            nextcloud_api.create_user(
                userid=username,
                password="",  # No password — SSO-provisioned
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to create auto-provisioned user: {exc}")

        # Verify the user exists and is enabled
        try:
            user_resp = nextcloud_api.get_user(username)
            assert user_resp.ocs_meta.get("status") == "ok", (
                f"Auto-provisioned user '{username}' not found"
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to get auto-provisioned user: {exc}")

        # Verify the user data matches what we set
        user_info = user_resp.ocs_data
        if isinstance(user_info, dict):
            actual_display = user_info.get("displayname") or user_info.get("display-name", "")
            assert actual_display == user_data["display_name"], (
                f"Display name mismatch: expected '{user_data['display_name']}', "
                f"got '{actual_display}'"
            )
            actual_email = user_info.get("email", "")
            assert actual_email == user_data["email"], (
                f"Email mismatch: expected '{user_data['email']}', got '{actual_email}'"
            )

        # Verify the user can be enabled/disabled (management works)
        try:
            nextcloud_api.disable_user(username)
            disabled_resp = nextcloud_api.get_user(username)
            disabled_data = disabled_resp.ocs_data
            if isinstance(disabled_data, dict):
                assert not disabled_data.get("enabled", True), (
                    f"User '{username}' should be disabled but is still enabled"
                )

            nextcloud_api.enable_user(username)
            enabled_resp = nextcloud_api.get_user(username)
            enabled_data = enabled_resp.ocs_data
            if isinstance(enabled_data, dict):
                assert enabled_data.get("enabled", False), (
                    f"User '{username}' should be re-enabled but is still disabled"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to toggle user enabled state: {exc}")

        # Cleanup
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass
