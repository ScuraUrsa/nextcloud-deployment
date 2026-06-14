"""
test_subscription_create.py — Verify subscription creation in Lago.

Tests:
- test_create_subscription: A subscription can be created for a customer.

All tests are marked @pytest.mark.billing.
"""

from __future__ import annotations

import pytest

from ..utils.lago_api import LagoAPI, LagoAPIError, LagoPlan, LagoSubscription
from ..utils.data_generators import generate_test_user_data


pytestmark = pytest.mark.billing


class TestSubscriptionCreate:
    """Verify subscription creation in Lago."""

    def test_create_subscription(self, lago_api: LagoAPI) -> None:
        """A subscription can be created for a test customer."""
        user_data = generate_test_user_data(prefix="lago")
        customer_id = user_data["username"]
        plan_code = f"test-plan-{customer_id}"

        # Create a test plan first
        try:
            plan = lago_api.create_plan(
                name=f"Test Plan {customer_id}",
                code=plan_code,
                interval="monthly",
                amount_cents=1000,  # $10.00
                amount_currency="EUR",
                pay_in_advance=True,
                description="Test plan for subscription creation test",
            )
            assert plan.lago_id, "Plan creation returned empty lago_id"
        except LagoAPIError as exc:
            pytest.fail(f"Failed to create test plan: {exc}")

        # Create a subscription for the customer
        try:
            subscription = lago_api.create_subscription(
                external_customer_id=customer_id,
                plan_code=plan_code,
                external_id=f"sub-{customer_id}",
            )
            assert subscription.lago_id, "Subscription creation returned empty lago_id"
            assert subscription.external_id == f"sub-{customer_id}", (
                f"Subscription external_id mismatch: "
                f"expected 'sub-{customer_id}', got '{subscription.external_id}'"
            )
            assert subscription.plan_code == plan_code, (
                f"Subscription plan_code mismatch: "
                f"expected '{plan_code}', got '{subscription.plan_code}'"
            )
        except LagoAPIError as exc:
            pytest.fail(f"Failed to create subscription: {exc}")

        # Verify the subscription exists by fetching it
        try:
            fetched = lago_api.get_subscription(f"sub-{customer_id}")
            assert fetched.lago_id == subscription.lago_id, (
                f"Fetched subscription lago_id mismatch"
            )
            assert fetched.status in ("active", "pending"), (
                f"Subscription status is '{fetched.status}', expected 'active' or 'pending'"
            )
        except LagoAPIError as exc:
            pytest.fail(f"Failed to fetch subscription: {exc}")

        # Cleanup: cancel the subscription
        try:
            lago_api.cancel_subscription(f"sub-{customer_id}")
        except LagoAPIError:
            pass  # Best-effort cleanup
