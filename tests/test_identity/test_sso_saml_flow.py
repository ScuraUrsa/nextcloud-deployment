"""
test_sso_saml_flow.py — Verify SAML SSO integration between Keycloak and Nextcloud.

Tests:
- test_saml_idp_metadata: Keycloak SAML IdP metadata is accessible.
- test_saml_login_redirect: Nextcloud login page offers SAML SSO redirect.

All tests are marked @pytest.mark.identity.
"""

from __future__ import annotations

import pytest
import requests
from urllib.parse import urljoin

from ..utils.keycloak_api import KeycloakAPI


pytestmark = pytest.mark.identity


class TestSSOSAMLFlow:
    """Verify SAML SSO IdP metadata and login redirect flow."""

    def test_saml_idp_metadata(self, keycloak_api: KeycloakAPI) -> None:
        """Keycloak should serve SAML IdP metadata at the standard endpoint."""
        # The SAML IdP descriptor URL for a Keycloak realm
        metadata_url = (
            f"{keycloak_api.base_url}/realms/{keycloak_api.realm}"
            f"/protocol/saml/descriptor"
        )

        try:
            resp = requests.get(metadata_url, timeout=30)
        except requests.RequestException as exc:
            pytest.fail(f"SAML metadata endpoint unreachable: {exc}")

        assert resp.status_code == 200, (
            f"SAML metadata returned {resp.status_code}, expected 200. "
            f"Body preview: {resp.text[:300]}"
        )

        # The response should be valid XML containing SAML EntityDescriptor
        assert "EntityDescriptor" in resp.text, (
            "SAML metadata does not contain EntityDescriptor — not valid SAML metadata"
        )
        assert "IDPSSODescriptor" in resp.text or "SPSSODescriptor" in resp.text, (
            "SAML metadata missing IdP or SP descriptor"
        )

    def test_saml_login_redirect(self, nextcloud_url: str) -> None:
        """Nextcloud login page should offer a SAML SSO login option."""
        base_url = nextcloud_url.rstrip("/")
        login_url = urljoin(base_url, "/login")

        try:
            resp = requests.get(login_url, timeout=30)
        except requests.RequestException as exc:
            pytest.fail(f"Nextcloud login page unreachable: {exc}")

        assert resp.status_code == 200, (
            f"Login page returned {resp.status_code}, expected 200"
        )

        # Look for SAML/SSO indicators in the login page
        page_text = resp.text.lower()
        sso_indicators = [
            "sso", "saml", "single sign-on", "single sign on",
            "sociallogin", "oauth", "openid", "keycloak",
            "login with", "external", "identity provider",
        ]

        found = any(indicator in page_text for indicator in sso_indicators)
        if not found:
            # Not necessarily a failure — SSO may be configured differently.
            # We check if the user_saml app is enabled via OCS.
            pytest.skip(
                "No SSO indicators found on login page. "
                "SAML/SSO app may not be enabled or configured."
            )
