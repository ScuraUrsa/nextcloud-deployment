"""
test_keycloak_deployment.py — Verify Keycloak is deployed and the Nextcloud realm exists.

Tests:
- test_keycloak_health: Keycloak admin API is reachable and returns a valid token.
- test_realm_exists: The configured realm exists and is accessible.

All tests are marked @pytest.mark.identity.
"""

from __future__ import annotations

import pytest

from ..utils.keycloak_api import KeycloakAPI, KeycloakAPIError


pytestmark = pytest.mark.identity


class TestKeycloakDeployment:
    """Verify Keycloak server health and realm configuration."""

    def test_keycloak_health(self, keycloak_api: KeycloakAPI) -> None:
        """Keycloak admin API should be reachable and return a valid access token."""
        try:
            token = keycloak_api.get_admin_token()
        except KeycloakAPIError as exc:
            pytest.fail(f"Keycloak admin token request failed: {exc}")

        assert token, "Keycloak admin token is empty — API may be unreachable"
        assert len(token) > 20, f"Token too short ({len(token)} chars), likely invalid"

    def test_realm_exists(self, keycloak_api: KeycloakAPI) -> None:
        """The configured realm should exist and be accessible via the admin API."""
        # Exporting the realm (partial export) confirms it exists
        try:
            realm_data = keycloak_api.export_realm()
        except KeycloakAPIError as exc:
            pytest.fail(f"Realm export failed — realm may not exist: {exc}")

        assert realm_data, "Realm export returned empty data"
        # The export should contain at least a realm identifier
        realm_id = realm_data.get("id") or realm_data.get("realm")
        assert realm_id, f"Realm export missing identifier. Keys: {list(realm_data.keys())[:10]}"
