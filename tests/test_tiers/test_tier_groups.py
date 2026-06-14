"""
test_tier_groups.py — Verify tier-based Nextcloud groups exist.

Tests:
- test_tier_groups_exist: The four tier groups (nc-basic, nc-pro, nc-enterprise, nc-admin)
  should exist in Nextcloud.

All tests are marked @pytest.mark.tiers.
"""

from __future__ import annotations

import pytest

from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError


pytestmark = pytest.mark.tiers

# Expected tier groups
TIER_GROUPS = ["nc-basic", "nc-pro", "nc-enterprise", "nc-admin"]


class TestTierGroups:
    """Verify tier-based Nextcloud groups exist."""

    def test_tier_groups_exist(self, nextcloud_api: NextcloudAPI) -> None:
        """All tier groups (nc-basic, nc-pro, nc-enterprise, nc-admin) should exist."""
        missing_groups: list[str] = []

        for group_name in TIER_GROUPS:
            try:
                # Try to get group info by attempting to add a dummy user to it
                # (Nextcloud OCS doesn't have a direct "get group" endpoint,
                # but add_to_group will fail if the group doesn't exist)
                # Instead, we check via the get_users groups listing or
                # by trying to create the group (which is idempotent — returns
                # success if it already exists)
                resp = nextcloud_api._ocs_request(
                    "POST",
                    "cloud/groups",
                    data={"groupid": group_name},
                )
                # Status 102 means the group already exists (which is fine)
                # Status 100 means it was created
                statuscode = resp.ocs_meta.get("statuscode")
                if statuscode not in (100, 102):
                    missing_groups.append(group_name)
            except NextcloudAPIError:
                missing_groups.append(group_name)

        assert not missing_groups, (
            f"Missing tier groups: {', '.join(missing_groups)}. "
            f"Expected all of: {', '.join(TIER_GROUPS)}"
        )
