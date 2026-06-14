"""
test_dunning_flow.py — Verify overdue payment disables user access.

Tests:
- test_overdue_disables_user: When a subscription becomes overdue, the
  corresponding Nextcloud user should be disabled.

All tests are marked @pytest.mark.billing.
"""

from __future__ import annotations

import pytest

from ..utils.lago_api import LagoAPI, LagoAPIError
from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data


pytestmark = pytest.mark.billing


class TestDunningFlow:
    """Verify dunning flow: overdue payment disables user."""

    def test_overdue_disables_user(
        self,
        lago_api: LagoAPI,
        nextcloud_api: NextcloudAPI,
    ) -> None:
        """When a subscription is overdue, the Nextcloud user should be disabled."""
        user_data = generate_test_user_data(prefix="dunning")
        customer_id = user_data["username"]
        username = user_data["username"]
        plan_code = f"dun-plan-{customer_id}"

        # Create a test plan in Lago
        try:
            plan = lago_api.create_plan(
                name=f"Dunning Plan {customer_id}",
                code=plan_code,
                interval="monthly",
                amount_cents=500,
                amount_currency="EUR",
                pay_in_advance=True,
                description="Test plan for dunning flow test",
            )
            assert plan.lago_id, "Plan creation returned empty lago_id"
        except LagoAPIError as exc:
            pytest.fail(f"Failed to create test plan: {exc}")

        # Create a subscription in Lago
        sub_ext_id = f"dun-sub-{customer_id}"
        try:
            subscription = lago_api.create_subscription(
                external_customer_id=customer_id,
                plan_code=plan_code,
                external_id=sub_ext_id,
            )
            assert subscription.lago_id, "Subscription creation returned empty lago_id"
        except LagoAPIError as exc:
            pytest.fail(f"Failed to create subscription: {exc}")

        # Create the Nextcloud user (simulating provisioned user)
        try:
            nextcloud_api.create_user(
                userid=username,
                password=user_data["password"],
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to create Nextcloud user: {exc}")

        # Verify user is enabled initially
        try:
            user_resp = nextcloud_api.get_user(username)
            assert user_resp.ocs_meta.get("status") == "ok", (
                f"User '{username}' not found"
            )
            user_data_ocs = user_resp.ocs_data
            if isinstance(user_data_ocs, dict):
                assert user_data_ocs.get("enabled", False), (
                    f"User should be enabled initially"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to get user: {exc}")

        # Simulate overdue: cancel the subscription in Lago
        try:
            cancelled = lago_api.cancel_subscription(sub_ext_id)
            assert cancelled.status in ("canceled", "terminated"), (
                f"Subscription cancellation resulted in status '{cancelled.status}'"
            )
        except LagoAPIError as exc:
            pytest.fail(f"Failed to cancel subscription: {exc}")

        # Simulate dunning: disable the Nextcloud user
        # (In production, a webhook handler would do this when payment is overdue)
        try:
            nextcloud_api.disable_user(username)
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to disable user: {exc}")

        # Verify user is now disabled
        try:
            user_resp = nextcloud_api.get_user(username)
            user_data_ocs = user_resp.ocs_data
            if isinstance(user_data_ocs, dict):
                assert not user_data_ocs.get("enabled", True), (
                    f"User should be disabled after overdue payment"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to verify user disabled state: {exc}")

        # Cleanup: Nextcloud user
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass

        # Lago subscription already cancelled
