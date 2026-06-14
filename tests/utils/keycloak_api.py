"""
Keycloak REST Admin API wrapper for test automation.

Covers:
  - Admin token acquisition and refresh
  - User CRUD
  - Group management
  - Realm export
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class KeycloakAPIError(Exception):
    """Raised when a Keycloak API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


# ---------------------------------------------------------------------------
# Typed response dataclasses
# ---------------------------------------------------------------------------

@dataclass
class KeycloakUser:
    id: str
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: bool = True
    email_verified: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KeycloakGroup:
    id: str
    name: str
    path: str
    sub_groups: List[KeycloakGroup] = field(default_factory=list)


# ---------------------------------------------------------------------------
# KeycloakAPI
# ---------------------------------------------------------------------------

class KeycloakAPI:
    """Keycloak REST Admin API wrapper."""

    def __init__(self, base_url: str, realm: str, admin_user: str, admin_pass: str):
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.session = requests.Session()
        self._token: str = ""
        self._token_expiry: float = 0.0

    # -- token management --------------------------------------------------

    def get_admin_token(self) -> str:
        """Obtain (or refresh) an admin access token."""
        if self._token and time.time() < self._token_expiry - 10:
            return self._token

        url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
        data = {
            "client_id": "admin-cli",
            "username": self.admin_user,
            "password": self.admin_pass,
            "grant_type": "password",
        }
        resp = self.session.post(url, data=data, timeout=30)
        if not resp.ok:
            raise KeycloakAPIError(
                f"Token request failed: {resp.status_code}",
                status_code=resp.status_code,
                response_text=resp.text,
            )
        payload = resp.json()
        self._token = payload.get("access_token", "")
        expires_in = payload.get("expires_in", 60)
        self._token_expiry = time.time() + expires_in
        assert self._token is not None
        return self._token

    def _admin_headers(self) -> Dict[str, str]:
        token = self.get_admin_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _admin_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        url = f"{self.base_url}/admin/realms/{self.realm}/{path.lstrip('/')}"
        resp = self.session.request(
            method=method,
            url=url,
            headers=self._admin_headers(),
            json=json_data,
            params=params,
            timeout=30,
        )
        if not resp.ok:
            raise KeycloakAPIError(
                f"Admin {method} {path} failed: {resp.status_code}",
                status_code=resp.status_code,
                response_text=resp.text,
            )
        return resp

    # -- user management ---------------------------------------------------

    def create_user(
        self,
        username: str,
        email: str = "",
        first_name: str = "",
        last_name: str = "",
        enabled: bool = True,
        email_verified: bool = False,
        password: str = "",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> KeycloakUser:
        """Create a new user in the realm."""
        payload: Dict[str, Any] = {
            "username": username,
            "enabled": enabled,
            "emailVerified": email_verified,
        }
        if email:
            payload["email"] = email
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if attributes:
            payload["attributes"] = attributes
        if password:
            payload["credentials"] = [{"type": "password", "value": password, "temporary": False}]

        resp = self._admin_request("POST", "users", json_data=payload)
        # Keycloak returns 201 with a Location header containing the user ID
        location = resp.headers.get("Location", "")
        user_id = location.rsplit("/", 1)[-1] if location else ""
        return KeycloakUser(
            id=user_id,
            username=username,
            email=email or None,
            first_name=first_name or None,
            last_name=last_name or None,
            enabled=enabled,
            email_verified=email_verified,
            attributes=attributes or {},
        )

    def get_user(self, user_id: str) -> KeycloakUser:
        """Get user by ID."""
        resp = self._admin_request("GET", f"users/{user_id}")
        data = resp.json()
        return KeycloakUser(
            id=data.get("id", user_id),
            username=data.get("username", ""),
            email=data.get("email"),
            first_name=data.get("firstName"),
            last_name=data.get("lastName"),
            enabled=data.get("enabled", True),
            email_verified=data.get("emailVerified", False),
            attributes=data.get("attributes", {}),
        )

    def get_user_by_username(self, username: str) -> Optional[KeycloakUser]:
        """Find a user by username. Returns None if not found."""
        resp = self._admin_request("GET", "users", params={"username": username, "exact": "true"})
        users = resp.json()
        if not users:
            return None
        data = users[0]
        return KeycloakUser(
            id=data.get("id", ""),
            username=data.get("username", username),
            email=data.get("email"),
            first_name=data.get("firstName"),
            last_name=data.get("lastName"),
            enabled=data.get("enabled", True),
            email_verified=data.get("emailVerified", False),
            attributes=data.get("attributes", {}),
        )

    def delete_user(self, user_id: str) -> None:
        """Delete a user by ID."""
        self._admin_request("DELETE", f"users/{user_id}")

    def enable_user(self, user_id: str) -> None:
        """Enable a user."""
        self._admin_request("PUT", f"users/{user_id}", json_data={"enabled": True})

    def disable_user(self, user_id: str) -> None:
        """Disable a user."""
        self._admin_request("PUT", f"users/{user_id}", json_data={"enabled": False})

    # -- group management --------------------------------------------------

    def create_group(self, name: str) -> KeycloakGroup:
        """Create a new group."""
        resp = self._admin_request("POST", "groups", json_data={"name": name})
        location = resp.headers.get("Location", "")
        group_id = location.rsplit("/", 1)[-1] if location else ""
        return KeycloakGroup(id=group_id, name=name, path=f"/{name}")

    def get_groups(self) -> List[KeycloakGroup]:
        """List all groups in the realm."""
        resp = self._admin_request("GET", "groups")
        raw_groups = resp.json()

        def _parse_group(g: Dict[str, Any]) -> KeycloakGroup:
            sub = [_parse_group(s) for s in g.get("subGroups", [])]
            return KeycloakGroup(
                id=g.get("id", ""),
                name=g.get("name", ""),
                path=g.get("path", ""),
                sub_groups=sub,
            )

        return [_parse_group(g) for g in raw_groups]

    def add_user_to_group(self, user_id: str, group_id: str) -> None:
        """Add a user to a group."""
        self._admin_request("PUT", f"users/{user_id}/groups/{group_id}")

    def remove_user_from_group(self, user_id: str, group_id: str) -> None:
        """Remove a user from a group."""
        self._admin_request("DELETE", f"users/{user_id}/groups/{group_id}")

    # -- realm export ------------------------------------------------------

    def export_realm(self) -> Dict[str, Any]:
        """Export the realm configuration (partial export)."""
        resp = self._admin_request("POST", "partial-export", json_data={"exportClients": True, "exportGroupsAndRoles": True})
        return resp.json()
