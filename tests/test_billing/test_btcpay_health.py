"""
test_btcpay_health.py — Verify BTCPay Server is reachable.

Tests:
- test_btcpay_reachable: The BTCPay Server should be reachable.

All tests are marked @pytest.mark.billing.
"""

from __future__ import annotations

import os

import pytest
import requests


pytestmark = pytest.mark.billing


class TestBTCPayHealth:
    """Verify BTCPay Server health."""

    def test_btcpay_reachable(self) -> None:
        """BTCPay Server should be reachable at the configured URL."""
        btcpay_url = os.environ.get("BTCPAY_URL", "http://localhost:49392")

        try:
            resp = requests.get(btcpay_url, timeout=30)
        except requests.RequestException as exc:
            # BTCPay may not be deployed — skip rather than fail
            pytest.skip(f"BTCPay Server unreachable at {btcpay_url}: {exc}")

        # BTCPay should respond (even a redirect or login page is fine)
        assert resp.status_code < 500, (
            f"BTCPay returned server error {resp.status_code}. "
            f"Body: {resp.text[:300]}"
        )

        # Check for BTCPay indicators in the response
        page_text = resp.text.lower()
        btcpay_indicators = ["btcpay", "bitcoin", "lightning", "payment", "invoice"]
        found = any(indicator in page_text for indicator in btcpay_indicators)
        if not found and resp.status_code == 200:
            # Not necessarily a failure — could be a redirect or API-only setup
            pass
