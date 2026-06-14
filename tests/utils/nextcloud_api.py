"""
Nextcloud REST API wrapper for test automation.

Covers:
  - WebDAV (PROPFIND, MKCOL, PUT, GET, DELETE, MOVE, COPY)
  - OCS Share API
  - User provisioning
  - App management
  - System info (status.php, serverinfo)
  - Talk API
  - CalDAV/CardDAV basics
"""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class NextcloudAPIError(Exception):
    """Raised when a Nextcloud API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


# ---------------------------------------------------------------------------
# Typed response dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WebDAVResponse:
    status_code: int
    headers: Dict[str, str]
    body: bytes
    xml_tree: Optional[ET.Element] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass
class OCSResponse:
    status_code: int
    ocs_meta: Dict[str, Any]
    ocs_data: Any
    raw: Dict[str, Any]


@dataclass
class UserInfo:
    id: str
    display_name: str
    email: Optional[str] = None
    quota: Optional[Dict[str, Any]] = None
    enabled: bool = True
    groups: List[str] = field(default_factory=list)


@dataclass
class ShareInfo:
    id: str
    share_type: int
    share_with: str
    path: str
    permissions: int
    uid_owner: str
    uid_file_owner: str
    token: Optional[str] = None


@dataclass
class AppInfo:
    id: str
    name: str
    version: str
    active: bool
    description: str = ""


@dataclass
class SystemInfo:
    installed: bool
    version: str
    versionstring: str
    edition: str
    maintenance: bool


@dataclass
class TalkConversation:
    token: str
    name: str
    display_name: str
    type: int
    participant_type: int


@dataclass
class TalkMessage:
    id: int
    token: str
    actor_type: str
    actor_id: str
    actor_display_name: str
    message: str
    timestamp: int


# ---------------------------------------------------------------------------
# NextcloudAPI
# ---------------------------------------------------------------------------

class NextcloudAPI:
    """Comprehensive Nextcloud REST API wrapper."""

    def __init__(self, base_url: str, admin_user: str, admin_pass: str):
        self.base_url = base_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.session = requests.Session()
        self._auth_header = self._make_basic_auth_header(admin_user, admin_pass)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _make_basic_auth_header(user: str, password: str) -> str:
        raw = f"{user}:{password}"
        encoded = base64.b64encode(raw.encode()).decode()
        return f"Basic {encoded}"

    def _ocs_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> OCSResponse:
        url = f"{self.base_url}/ocs/v2.php/{endpoint}"
        headers = {
            "OCS-APIRequest": "true",
            "Accept": "application/json",
            "Authorization": self._auth_header,
        }
        resp = self.session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            timeout=30,
        )
        if not resp.ok:
            raise NextcloudAPIError(
                f"OCS {method} {endpoint} failed: {resp.status_code}",
                status_code=resp.status_code,
                response_text=resp.text,
            )
        payload = resp.json()
        ocs = payload.get("ocs", {})
        meta = ocs.get("meta", {})
        ocs_data = ocs.get("data", {})
        if meta.get("status") != "ok" and meta.get("statuscode") not in (100, 200):
            raise NextcloudAPIError(
                f"OCS error: {meta.get('message', 'unknown')}",
                status_code=meta.get("statuscode"),
                response_text=resp.text,
            )
        return OCSResponse(
            status_code=resp.status_code,
            ocs_meta=meta,
            ocs_data=ocs_data,
            raw=payload,
        )

    def _webdav_request(
        self,
        method: str,
        path: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        depth: Optional[int] = None,
    ) -> WebDAVResponse:
        url = f"{self.base_url}/remote.php/dav/files/{self.admin_user}/{path.lstrip('/')}"
        req_headers = {"Authorization": self._auth_header}
        if headers:
            req_headers.update(headers)
        if depth is not None:
            req_headers["Depth"] = str(depth)

        resp = self.session.request(
            method=method,
            url=url,
            headers=req_headers,
            data=data,
            timeout=30,
        )
        xml_tree = None
        if resp.text and resp.text.strip().startswith("<?xml"):
            try:
                xml_tree = ET.fromstring(resp.text)
            except ET.ParseError:
                pass

        return WebDAVResponse(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp.content,
            xml_tree=xml_tree,
        )

    # -- WebDAV methods ----------------------------------------------------

    def propfind(self, path: str = "", depth: int = 1) -> WebDAVResponse:
        """PROPFIND on a path. depth=0 for the resource itself, 1 for children."""
        return self._webdav_request("PROPFIND", path, depth=depth)

    def mkcol(self, path: str) -> WebDAVResponse:
        """Create a collection (directory)."""
        return self._webdav_request("MKCOL", path)

    def put(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> WebDAVResponse:
        """Upload a file via PUT."""
        headers = {"Content-Type": content_type}
        return self._webdav_request("PUT", path, data=data, headers=headers)

    def get(self, path: str) -> WebDAVResponse:
        """Download a file via GET."""
        return self._webdav_request("GET", path)

    def delete(self, path: str) -> WebDAVResponse:
        """Delete a file or directory."""
        return self._webdav_request("DELETE", path)

    def move(self, source_path: str, dest_path: str) -> WebDAVResponse:
        """Move a file or directory."""
        dest_url = f"{self.base_url}/remote.php/dav/files/{self.admin_user}/{dest_path.lstrip('/')}"
        headers = {
            "Authorization": self._auth_header,
            "Destination": dest_url,
        }
        return self._webdav_request("MOVE", source_path, headers=headers)

    def copy(self, source_path: str, dest_path: str) -> WebDAVResponse:
        """Copy a file or directory."""
        dest_url = f"{self.base_url}/remote.php/dav/files/{self.admin_user}/{dest_path.lstrip('/')}"
        headers = {
            "Authorization": self._auth_header,
            "Destination": dest_url,
        }
        return self._webdav_request("COPY", source_path, headers=headers)

    # -- OCS Share API -----------------------------------------------------

    def create_share(
        self,
        path: str,
        share_type: int = 0,
        share_with: str = "",
        permissions: int = 31,
        password: str = "",
        public_upload: bool = False,
    ) -> OCSResponse:
        """Create a share. share_type: 0=user, 1=group, 3=public link, 4=email."""
        data = {
            "path": path,
            "shareType": share_type,
            "shareWith": share_with,
            "permissions": permissions,
        }
        if password:
            data["password"] = password
        if public_upload:
            data["publicUpload"] = "true"
        return self._ocs_request("POST", "apps/files_sharing/api/v1/shares", data=data)

    def get_shares(
        self,
        path: Optional[str] = None,
        reshares: bool = False,
        subfiles: bool = False,
    ) -> OCSResponse:
        """List shares, optionally filtered by path."""
        params: Dict[str, Any] = {"reshares": str(reshares).lower(), "subfiles": str(subfiles).lower()}
        if path:
            params["path"] = path
        return self._ocs_request("GET", "apps/files_sharing/api/v1/shares", params=params)

    def delete_share(self, share_id: str) -> OCSResponse:
        """Delete a share by ID."""
        return self._ocs_request("DELETE", f"apps/files_sharing/api/v1/shares/{share_id}")

    # -- User provisioning -------------------------------------------------

    def create_user(
        self,
        userid: str,
        password: str = "",
        display_name: str = "",
        email: str = "",
        groups: Optional[List[str]] = None,
    ) -> OCSResponse:
        """Create a new user."""
        data: Dict[str, Any] = {"userid": userid}
        if password:
            data["password"] = password
        if display_name:
            data["displayName"] = display_name
        if email:
            data["email"] = email
        if groups:
            data["groups"] = groups
        return self._ocs_request("POST", "cloud/users", data=data)

    def get_user(self, userid: str) -> OCSResponse:
        """Get user details."""
        return self._ocs_request("GET", f"cloud/users/{userid}")

    def delete_user(self, userid: str) -> OCSResponse:
        """Delete a user."""
        return self._ocs_request("DELETE", f"cloud/users/{userid}")

    def enable_user(self, userid: str) -> OCSResponse:
        """Enable a user."""
        return self._ocs_request("PUT", f"cloud/users/{userid}/enable")

    def disable_user(self, userid: str) -> OCSResponse:
        """Disable a user."""
        return self._ocs_request("PUT", f"cloud/users/{userid}/disable")

    def set_quota(self, userid: str, quota: str) -> OCSResponse:
        """Set user quota (e.g. '1 GB', 'none', 'default')."""
        return self._ocs_request("PUT", f"cloud/users/{userid}", data={"key": "quota", "value": quota})

    def add_to_group(self, userid: str, group: str) -> OCSResponse:
        """Add user to a group."""
        return self._ocs_request("POST", f"cloud/users/{userid}/groups", data={"groupid": group})

    def remove_from_group(self, userid: str, group: str) -> OCSResponse:
        """Remove user from a group."""
        return self._ocs_request("DELETE", f"cloud/users/{userid}/groups", data={"groupid": group})

    def get_users(self, search: str = "", limit: int = 100, offset: int = 0) -> OCSResponse:
        """List users."""
        params = {"search": search, "limit": limit, "offset": offset}
        return self._ocs_request("GET", "cloud/users", params=params)

    # -- App management ----------------------------------------------------

    def enable_app(self, app_name: str) -> OCSResponse:
        """Enable an app."""
        return self._ocs_request("POST", f"cloud/apps/{app_name}")

    def disable_app(self, app_name: str) -> OCSResponse:
        """Disable an app."""
        return self._ocs_request("DELETE", f"cloud/apps/{app_name}")

    def list_apps(self) -> OCSResponse:
        """List all apps."""
        return self._ocs_request("GET", "cloud/apps")

    # -- System info -------------------------------------------------------

    def status(self) -> SystemInfo:
        """Get system status from status.php."""
        url = f"{self.base_url}/status.php"
        resp = self.session.get(url, timeout=30)
        if not resp.ok:
            raise NextcloudAPIError(
                f"status.php failed: {resp.status_code}",
                status_code=resp.status_code,
                response_text=resp.text,
            )
        data = resp.json()
        return SystemInfo(
            installed=data.get("installed", False),
            version=data.get("version", ""),
            versionstring=data.get("versionstring", ""),
            edition=data.get("edition", ""),
            maintenance=data.get("maintenance", False),
        )

    def serverinfo(self) -> OCSResponse:
        """Get server info via OCS."""
        return self._ocs_request("GET", "apps/serverinfo/api/v1/info")

    # -- Talk API ----------------------------------------------------------

    def create_conversation(self, room_name: str, room_type: int = 3) -> OCSResponse:
        """Create a Talk conversation. room_type: 1=one2one, 2=group, 3=public."""
        return self._ocs_request(
            "POST",
            "apps/spreed/api/v4/room",
            data={"roomName": room_name, "roomType": room_type},
        )

    def send_message(self, token: str, message: str) -> OCSResponse:
        """Send a message to a Talk conversation."""
        return self._ocs_request(
            "POST",
            f"apps/spreed/api/v1/chat/{token}",
            data={"message": message},
        )

    def get_messages(self, token: str, look_into_future: int = 0, limit: int = 100) -> OCSResponse:
        """Get messages from a Talk conversation."""
        params = {"lookIntoFuture": look_into_future, "limit": limit}
        return self._ocs_request("GET", f"apps/spreed/api/v1/chat/{token}", params=params)

    # -- CalDAV / CardDAV basics -------------------------------------------

    def caldav_propfind(self, path: str = "", depth: int = 1) -> WebDAVResponse:
        """PROPFIND on the CalDAV endpoint."""
        url = f"{self.base_url}/remote.php/dav/calendars/{self.admin_user}/{path.lstrip('/')}"
        headers = {"Authorization": self._auth_header}
        if depth is not None:
            headers["Depth"] = str(depth)
        resp = self.session.request("PROPFIND", url, headers=headers, timeout=30)
        xml_tree = None
        if resp.text and resp.text.strip().startswith("<?xml"):
            try:
                xml_tree = ET.fromstring(resp.text)
            except ET.ParseError:
                pass
        return WebDAVResponse(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp.content,
            xml_tree=xml_tree,
        )

    def carddav_propfind(self, path: str = "", depth: int = 1) -> WebDAVResponse:
        """PROPFIND on the CardDAV endpoint."""
        url = f"{self.base_url}/remote.php/dav/addressbooks/users/{self.admin_user}/{path.lstrip('/')}"
        headers = {"Authorization": self._auth_header}
        if depth is not None:
            headers["Depth"] = str(depth)
        resp = self.session.request("PROPFIND", url, headers=headers, timeout=30)
        xml_tree = None
        if resp.text and resp.text.strip().startswith("<?xml"):
            try:
                xml_tree = ET.fromstring(resp.text)
            except ET.ParseError:
                pass
        return WebDAVResponse(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp.content,
            xml_tree=xml_tree,
        )
