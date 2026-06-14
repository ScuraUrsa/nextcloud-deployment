"""
test_lago_health.py — Verify Lago billing API is reachable.

Tests:
- test_lago_api_reachable: The Lago API should respond to health/version checks.

All tests are marked @pytest.mark.billing.
"""

from __future__ import annotations

import pytest
import requests

from ..utils.lago_api import LagoAPI, LagoAPIError


pytestmark = pytest.mark.billing


class TestLagoHealth:
    """Verify Lago billing API health."""

    def test_lago_api_reachable(self, lago_api: LagoAPI) -> None:
        """Lago API should be reachable and respond to requests."""
        # Try to hit the Lago API base endpoint
        try:
            resp = requests.get(
                f"{lago_api.base_url}/api/v1/plans",
                headers={"Authorization": f"Bearer {lago_api.api_key}"},
                timeout=30,
            )
        except requests.RequestException as exc:
            pytest.fail(f"Lago API unreachable at {lago_api.base_url}: {exc}")

        # Any response (even 401 if API key is wrong) means the service is up
        assert resp.status_code < 500, (
            f"Lago API returned server error {resp.status_code}. "
            f"Body: {resp.text[:300]}"
        )

        # If we got a 200, verify the response is valid JSON
        if resp.status_code == 200:
            try:
                data = resp.json()
                assert data is not None, "Lago API returned null response"
            except ValueError:
                pytest.fail("Lago API returned non-JSON response")
