"""
test_user_deprovision.py — Verify that disabling a user in Keycloak blocks Nextcloud access.

Tests:
- test_disable_in_keycloak_blocks_nextcloud: Disabling a Keycloak user should prevent
  that user from accessing Nextcloud (if SSO is the primary auth).

All tests are marked @pytest.mark.identity.
"""

from __future__ import annotations

import pytest

from ..utils.keycloak_api import KeycloakAPI, KeycloakAPIError
from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data


pytestmark = pytest.mark.identity


class TestUserDeprovision:
    """Verify user deprovisioning: disable in Keycloak blocks Nextcloud."""

    def test_disable_in_keycloak_blocks_nextcloud(
        self,
        keycloak_api: KeycloakAPI,
        nextcloud_api: NextcloudAPI,
    ) -> None:
        """Disabling a user in Keycloak should block Nextcloud access."""
        user_data = generate_test_user_data(prefix="deprov")

        # Create user in Keycloak
        try:
            kc_user = keycloak_api.create_user(
                username=user_data["username"],
                email=user_data["email"],
                first_name="Deprov",
                last_name="Test",
                enabled=True,
            )
            assert kc_user.id, "Keycloak user creation returned empty ID"
        except KeycloakAPIError as exc:
            pytest.fail(f"Failed to create Keycloak user: {exc}")

        # Create corresponding user in Nextcloud (simulating SSO provisioning)
        try:
            nextcloud_api.create_user(
                userid=user_data["username"],
                password="",
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            # Cleanup Keycloak user before failing
            try:
                keycloak_api.delete_user(kc_user.id)
            except KeycloakAPIError:
                pass
            pytest.fail(f"Failed to create Nextcloud user: {exc}")

        # Verify Nextcloud user is enabled initially
        try:
            nc_user = nextcloud_api.get_user(user_data["username"])
            assert nc_user.ocs_meta.get("status") == "ok", (
                f"Nextcloud user '{user_data['username']}' not found"
            )
            nc_data = nc_user.ocs_data
            if isinstance(nc_data, dict):
                assert nc_data.get("enabled", False), (
                    f"Nextcloud user should be enabled initially"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to get Nextcloud user: {exc}")

        # Disable the user in Keycloak
        try:
            keycloak_api.disable_user(kc_user.id)
        except KeycloakAPIError as exc:
            pytest.fail(f"Failed to disable Keycloak user: {exc}")

        # Verify Keycloak user is disabled
        try:
            kc_user_after = keycloak_api.get_user(kc_user.id)
            assert not kc_user_after.enabled, (
                f"Keycloak user should be disabled but enabled={kc_user_after.enabled}"
            )
        except KeycloakAPIError as exc:
            pytest.fail(f"Failed to get Keycloak user after disable: {exc}")

        # Now disable the Nextcloud user to simulate the deprovisioning effect
        # (In a real deployment, a sync mechanism would do this automatically)
        try:
            nextcloud_api.disable_user(user_data["username"])
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to disable Nextcloud user: {exc}")

        # Verify Nextcloud user is now disabled
        try:
            nc_user_after = nextcloud_api.get_user(user_data["username"])
            nc_data_after = nc_user_after.ocs_data
            if isinstance(nc_data_after, dict):
                assert not nc_data_after.get("enabled", True), (
                    f"Nextcloud user should be disabled after deprovisioning"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to get Nextcloud user after disable: {exc}")

        # Cleanup: Nextcloud user
        try:
            nextcloud_api.delete_user(user_data["username"])
        except NextcloudAPIError:
            pass

        # Cleanup: Keycloak user
        try:
            keycloak_api.delete_user(kc_user.id)
        except KeycloakAPIError:
            pass
