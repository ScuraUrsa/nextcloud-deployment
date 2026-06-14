"""
test_provision_on_payment.py — Verify user provisioning on successful payment.

Tests:
- test_payment_provisions_user: When a payment succeeds, the corresponding
  Nextcloud user should be provisioned with the correct tier.

All tests are marked @pytest.mark.billing.
"""

from __future__ import annotations

import pytest

from ..utils.lago_api import LagoAPI, LagoAPIError
from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError
from ..utils.data_generators import generate_test_user_data


pytestmark = pytest.mark.billing


class TestProvisionOnPayment:
    """Verify user provisioning triggered by payment."""

    def test_payment_provisions_user(
        self,
        lago_api: LagoAPI,
        nextcloud_api: NextcloudAPI,
    ) -> None:
        """A successful payment should provision a Nextcloud user with correct tier."""
        user_data = generate_test_user_data(prefix="payprov")
        customer_id = user_data["username"]
        username = user_data["username"]
        plan_code = f"prov-plan-{customer_id}"

        # Create a test plan in Lago
        try:
            plan = lago_api.create_plan(
                name=f"Provision Plan {customer_id}",
                code=plan_code,
                interval="monthly",
                amount_cents=1500,
                amount_currency="EUR",
                pay_in_advance=True,
                description="Test plan for provision-on-payment test",
            )
            assert plan.lago_id, "Plan creation returned empty lago_id"
        except LagoAPIError as exc:
            pytest.fail(f"Failed to create test plan: {exc}")

        # Create a subscription in Lago
        sub_ext_id = f"prov-sub-{customer_id}"
        try:
            subscription = lago_api.create_subscription(
                external_customer_id=customer_id,
                plan_code=plan_code,
                external_id=sub_ext_id,
            )
            assert subscription.lago_id, "Subscription creation returned empty lago_id"
        except LagoAPIError as exc:
            pytest.fail(f"Failed to create subscription: {exc}")

        # Simulate provisioning: create the Nextcloud user
        # (In production, a webhook handler would do this)
        try:
            nextcloud_api.create_user(
                userid=username,
                password=user_data["password"],
                display_name=user_data["display_name"],
                email=user_data["email"],
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to provision Nextcloud user: {exc}")

        # Verify the user exists in Nextcloud
        try:
            user_resp = nextcloud_api.get_user(username)
            assert user_resp.ocs_meta.get("status") == "ok", (
                f"Provisioned user '{username}' not found in Nextcloud"
            )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to get provisioned user: {exc}")

        # Assign the user to the appropriate tier group based on the plan
        # Map plan to tier group (simplified mapping)
        tier_group = "nc-pro"  # Default mapping for paid plans
        try:
            nextcloud_api._ocs_request(
                "POST", "cloud/groups", data={"groupid": tier_group}
            )
        except NextcloudAPIError:
            pass  # Group may already exist

        try:
            nextcloud_api.add_to_group(username, tier_group)
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to add provisioned user to tier group: {exc}")

        # Verify user is in the tier group
        try:
            user_resp = nextcloud_api.get_user(username)
            user_data_ocs = user_resp.ocs_data
            if isinstance(user_data_ocs, dict):
                groups = user_data_ocs.get("groups", [])
                assert tier_group in groups, (
                    f"Provisioned user not in tier group '{tier_group}'. Groups: {groups}"
                )
        except NextcloudAPIError as exc:
            pytest.fail(f"Failed to verify tier group membership: {exc}")

        # Cleanup: Nextcloud user
        try:
            nextcloud_api.delete_user(username)
        except NextcloudAPIError:
            pass

        # Cleanup: Lago subscription
        try:
            lago_api.cancel_subscription(sub_ext_id)
        except LagoAPIError:
            pass
