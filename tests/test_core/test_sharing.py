"""
test_sharing.py — Core tests for Nextcloud file sharing.

Verifies:
- Share file with user (read permission)
- Share file with user (read+write+delete permission)
- Share via public link (no password)
- Share via public link with password + expiry
- Share with group
- Recipient can access shared file
- Unshare revokes recipient access

All tests are marked @pytest.mark.core.
"""

import uuid
import json
import pytest
import requests
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone


pytestmark = pytest.mark.core


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ocs_api(session, base_url, method, path, data=None, timeout=30):
    """Make an OCS API request and return parsed JSON response."""
    url = urljoin(base_url, path)
    headers = {
        "OCS-APIRequest": "true",
        "Accept": "application/json",
    }
    if data and method.upper() in ("POST", "PUT"):
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    resp = session.request(method, url, headers=headers, data=data, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _dav_url(base_url, userid, path=""):
    """Build a WebDAV URL for a given user and path."""
    dav_base = f"/remote.php/dav/files/{userid}"
    if path:
        dav_base = f"{dav_base}/{path.lstrip('/')}"
    return urljoin(base_url, dav_base)


def _create_share(session, base_url, path, share_type, share_with="",
                  permissions=1, password="", expire_date=""):
    """Create a share via the OCS Share API.

    share_type: 0=user, 1=group, 3=public_link
    permissions: 1=read, 3=read+write, 15=read+write+delete, 31=all
    """
    data = {
        "path": path,
        "shareType": str(share_type),
        "permissions": str(permissions),
    }
    if share_with:
        data["shareWith"] = share_with
    if password:
        data["password"] = password
    if expire_date:
        data["expireDate"] = expire_date

    return _ocs_api(
        session, base_url, "POST",
        "/ocs/v2.php/apps/files_sharing/api/v1/shares",
        data=data,
    )


def _delete_share(session, base_url, share_id):
    """Delete a share by ID."""
    return _ocs_api(
        session, base_url, "DELETE",
        f"/ocs/v2.php/apps/files_sharing/api/v1/shares/{share_id}",
    )


def _get_shares(session, base_url, path=""):
    """Get all shares for a given path."""
    params = {"path": path} if path else {}
    return _ocs_api(
        session, base_url, "GET",
        "/ocs/v2.php/apps/files_sharing/api/v1/shares",
        data=params,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestShareWithUserRead:
    """Share a file with another user with read-only permission."""

    def test_share_with_user_read(self, nextcloud_api, test_user, test_file):
        """Share a file with read permission to another user."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]
        file_info = test_file

        # Create a recipient user
        recipient_uid = f"share-recipient-{uuid.uuid4().hex[:12]}"
        recipient_pass = "RecipientPass123!"
        _ocs_api(
            session, base_url, "POST",
            "/ocs/v2.php/cloud/users",
            data={
                "userid": recipient_uid,
                "password": recipient_pass,
            },
        )

        try:
            # Share the file with read permission (1)
            share_path = f"/{file_info['filename']}"
            resp = _create_share(
                session, base_url, share_path,
                share_type=0,          # user share
                share_with=recipient_uid,
                permissions=1,         # read only
            )

            ocs = resp.get("ocs", {})
            meta = ocs.get("meta", {})
            assert meta.get("status") == "ok", (
                f"Share creation failed: {ocs}"
            )

            share_data = ocs.get("data", {})
            share_id = share_data.get("id")
            assert share_id, f"No share ID returned: {share_data}"
            assert share_data.get("share_type") == 0, "Expected user share type"
            assert share_data.get("permissions") == 1, "Expected read-only permission"

            # Verify recipient can access the file
            recipient_session = requests.Session()
            recipient_session.auth = (recipient_uid, recipient_pass)
            shared_url = _dav_url(base_url, recipient_uid, file_info["filename"])
            get_resp = recipient_session.get(shared_url, timeout=30)
            assert get_resp.status_code == 200, (
                f"Recipient cannot access shared file: HTTP {get_resp.status_code}"
            )

            # Cleanup share
            _delete_share(session, base_url, share_id)

        finally:
            # Cleanup recipient user
            _ocs_api(
                session, base_url, "DELETE",
                f"/ocs/v2.php/cloud/users/{recipient_uid}",
            )


class TestShareWithUserReadWrite:
    """Share a file with read+write+delete permission."""

    def test_share_with_user_readwrite(self, nextcloud_api, test_user, test_file):
        """Share a file with full read+write+delete permission."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]
        file_info = test_file

        # Create a recipient user
        recipient_uid = f"share-rw-{uuid.uuid4().hex[:12]}"
        recipient_pass = "RWPass123!"
        _ocs_api(
            session, base_url, "POST",
            "/ocs/v2.php/cloud/users",
            data={
                "userid": recipient_uid,
                "password": recipient_pass,
            },
        )

        try:
            # Share with read+write+delete (permissions=15)
            share_path = f"/{file_info['filename']}"
            resp = _create_share(
                session, base_url, share_path,
                share_type=0,
                share_with=recipient_uid,
                permissions=15,        # read + write + delete
            )

            ocs = resp.get("ocs", {})
            assert ocs.get("meta", {}).get("status") == "ok", (
                f"Share creation failed: {ocs}"
            )

            share_data = ocs.get("data", {})
            share_id = share_data.get("id")
            assert share_data.get("permissions") == 15, (
                f"Expected permissions=15, got {share_data.get('permissions')}"
            )

            # Verify recipient can read
            recipient_session = requests.Session()
            recipient_session.auth = (recipient_uid, recipient_pass)
            shared_url = _dav_url(base_url, recipient_uid, file_info["filename"])
            get_resp = recipient_session.get(shared_url, timeout=30)
            assert get_resp.status_code == 200, "Recipient cannot read shared file"

            # Verify recipient can write (overwrite)
            new_content = b"Recipient wrote this!"
            put_resp = recipient_session.put(shared_url, data=new_content, timeout=30)
            assert put_resp.status_code in (201, 204), (
                f"Recipient cannot write to shared file: HTTP {put_resp.status_code}"
            )

            # Verify content changed
            get_resp2 = recipient_session.get(shared_url, timeout=30)
            assert get_resp2.content == new_content, (
                "Shared file content not updated after recipient write"
            )

            # Cleanup share
            _delete_share(session, base_url, share_id)

        finally:
            # Cleanup recipient user
            _ocs_api(
                session, base_url, "DELETE",
                f"/ocs/v2.php/cloud/users/{recipient_uid}",
            )


class TestSharePublicLink:
    """Share a file via a public link without password."""

    def test_share_public_link(self, nextcloud_api, test_user, test_file):
        """Create a public link share and verify it is accessible."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]
        file_info = test_file

        share_path = f"/{file_info['filename']}"
        resp = _create_share(
            session, base_url, share_path,
            share_type=3,          # public link
            permissions=1,         # read only
        )

        ocs = resp.get("ocs", {})
        assert ocs.get("meta", {}).get("status") == "ok", (
            f"Public link creation failed: {ocs}"
        )

        share_data = ocs.get("data", {})
        share_id = share_data.get("id")
        token = share_data.get("token")
        assert token, f"No token in public link share: {share_data}"

        # Access the public link
        public_url = urljoin(base_url, f"/s/{token}/download")
        public_resp = requests.get(public_url, timeout=30)
        assert public_resp.status_code == 200, (
            f"Public link download failed: HTTP {public_resp.status_code}"
        )

        # Cleanup
        _delete_share(session, base_url, share_id)


class TestSharePublicLinkPassword:
    """Share a file via a public link with password and expiry."""

    def test_share_public_link_password(self, nextcloud_api, test_user, test_file):
        """Create a password-protected public link with expiry date."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]
        file_info = test_file

        share_path = f"/{file_info['filename']}"
        password = "PublicLinkPass123!"
        # Expiry 7 days from now
        expire_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

        resp = _create_share(
            session, base_url, share_path,
            share_type=3,
            permissions=1,
            password=password,
            expire_date=expire_date,
        )

        ocs = resp.get("ocs", {})
        assert ocs.get("meta", {}).get("status") == "ok", (
            f"Password-protected public link creation failed: {ocs}"
        )

        share_data = ocs.get("data", {})
        share_id = share_data.get("id")
        token = share_data.get("token")
        assert token, f"No token in public link share: {share_data}"
        assert share_data.get("password_protected", False) or \
               share_data.get("share_with", "") == password, (
            "Public link should be password-protected"
        )

        # Verify expiry is set
        actual_expire = share_data.get("expiration", "")
        assert actual_expire, "No expiration date set on public link"

        # Access without password should fail or prompt for password
        public_url = urljoin(base_url, f"/s/{token}")
        no_pass_resp = requests.get(public_url, timeout=30, allow_redirects=True)
        # Should show a password prompt page
        assert "password" in no_pass_resp.text.lower(), (
            "Password-protected link did not prompt for password"
        )

        # Access with password
        pass_resp = requests.post(
            public_url,
            data={"password": password},
            timeout=30,
            allow_redirects=True,
        )
        assert pass_resp.status_code == 200, (
            f"Password-protected link access failed: HTTP {pass_resp.status_code}"
        )

        # Cleanup
        _delete_share(session, base_url, share_id)


class TestShareWithGroup:
    """Share a file with a group."""

    def test_share_with_group(self, nextcloud_api, test_user, test_file):
        """Create a group share and verify group members can access."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]
        file_info = test_file

        # Create a test group
        group_id = f"testgroup-{uuid.uuid4().hex[:12]}"
        _ocs_api(
            session, base_url, "POST",
            "/ocs/v2.php/cloud/groups",
            data={"groupid": group_id},
        )

        # Create a group member
        member_uid = f"groupmember-{uuid.uuid4().hex[:12]}"
        member_pass = "GroupMember123!"
        _ocs_api(
            session, base_url, "POST",
            "/ocs/v2.php/cloud/users",
            data={
                "userid": member_uid,
                "password": member_pass,
            },
        )

        # Add member to group
        _ocs_api(
            session, base_url, "POST",
            f"/ocs/v2.php/cloud/users/{member_uid}/groups",
            data={"groupid": group_id},
        )

        try:
            # Share file with the group
            share_path = f"/{file_info['filename']}"
            resp = _create_share(
                session, base_url, share_path,
                share_type=1,          # group share
                share_with=group_id,
                permissions=1,         # read only
            )

            ocs = resp.get("ocs", {})
            assert ocs.get("meta", {}).get("status") == "ok", (
                f"Group share creation failed: {ocs}"
            )

            share_data = ocs.get("data", {})
            share_id = share_data.get("id")
            assert share_data.get("share_type") == 1, "Expected group share type"
            assert share_data.get("share_with") == group_id, (
                f"Expected share_with={group_id}, got {share_data.get('share_with')}"
            )

            # Verify group member can access
            member_session = requests.Session()
            member_session.auth = (member_uid, member_pass)
            shared_url = _dav_url(base_url, member_uid, file_info["filename"])
            get_resp = member_session.get(shared_url, timeout=30)
            assert get_resp.status_code == 200, (
                f"Group member cannot access shared file: HTTP {get_resp.status_code}"
            )

            # Cleanup share
            _delete_share(session, base_url, share_id)

        finally:
            # Cleanup: remove member from group, delete member, delete group
            _ocs_api(
                session, base_url, "DELETE",
                f"/ocs/v2.php/cloud/users/{member_uid}/groups",
                data={"groupid": group_id},
            )
            _ocs_api(
                session, base_url, "DELETE",
                f"/ocs/v2.php/cloud/users/{member_uid}",
            )
            _ocs_api(
                session, base_url, "DELETE",
                f"/ocs/v2.php/cloud/groups/{group_id}",
            )


class TestShareRecipientAccess:
    """Verify a share recipient can access the shared file."""

    def test_share_recipient_access(self, nextcloud_api, test_user, test_file):
        """After sharing, the recipient should see the file in their DAV."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]
        file_info = test_file

        # Create recipient
        recipient_uid = f"recip-access-{uuid.uuid4().hex[:12]}"
        recipient_pass = "AccessPass123!"
        _ocs_api(
            session, base_url, "POST",
            "/ocs/v2.php/cloud/users",
            data={
                "userid": recipient_uid,
                "password": recipient_pass,
            },
        )

        try:
            # Share the file
            share_path = f"/{file_info['filename']}"
            resp = _create_share(
                session, base_url, share_path,
                share_type=0,
                share_with=recipient_uid,
                permissions=1,
            )

            ocs = resp.get("ocs", {})
            assert ocs.get("meta", {}).get("status") == "ok", (
                f"Share creation failed: {ocs}"
            )
            share_id = ocs["data"]["id"]

            # Recipient accesses the file via WebDAV
            recipient_session = requests.Session()
            recipient_session.auth = (recipient_uid, recipient_pass)

            # PROPFIND on the recipient's root to see shared files
            propfind_url = _dav_url(base_url, recipient_uid)
            propfind_resp = recipient_session.request(
                "PROPFIND", propfind_url, data="", headers={"Depth": "1"}, timeout=30
            )
            assert propfind_resp.status_code == 207, (
                f"Recipient PROPFIND failed: HTTP {propfind_resp.status_code}"
            )

            # The shared file should appear in the response
            assert file_info["filename"] in propfind_resp.text, (
                f"Shared file '{file_info['filename']}' not found in recipient's DAV listing"
            )

            # Recipient downloads the file
            get_url = _dav_url(base_url, recipient_uid, file_info["filename"])
            get_resp = recipient_session.get(get_url, timeout=30)
            assert get_resp.status_code == 200, (
                f"Recipient cannot download shared file: HTTP {get_resp.status_code}"
            )
            assert get_resp.content == file_info["content"], (
                "Shared file content mismatch for recipient"
            )

            # Cleanup
            _delete_share(session, base_url, share_id)

        finally:
            _ocs_api(
                session, base_url, "DELETE",
                f"/ocs/v2.php/cloud/users/{recipient_uid}",
            )


class TestUnshare:
    """Verify that unsharing revokes recipient access."""

    def test_unshare(self, nextcloud_api, test_user, test_file):
        """After deleting a share, the recipient should no longer have access."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]
        file_info = test_file

        # Create recipient
        recipient_uid = f"unshare-rec-{uuid.uuid4().hex[:12]}"
        recipient_pass = "UnsharePass123!"
        _ocs_api(
            session, base_url, "POST",
            "/ocs/v2.php/cloud/users",
            data={
                "userid": recipient_uid,
                "password": recipient_pass,
            },
        )

        try:
            # Share the file
            share_path = f"/{file_info['filename']}"
            resp = _create_share(
                session, base_url, share_path,
                share_type=0,
                share_with=recipient_uid,
                permissions=1,
            )

            ocs = resp.get("ocs", {})
            assert ocs.get("meta", {}).get("status") == "ok"
            share_id = ocs["data"]["id"]

            # Verify recipient can access
            recipient_session = requests.Session()
            recipient_session.auth = (recipient_uid, recipient_pass)
            get_url = _dav_url(base_url, recipient_uid, file_info["filename"])
            get_resp = recipient_session.get(get_url, timeout=30)
            assert get_resp.status_code == 200, (
                "Recipient should have access before unshare"
            )

            # Unshare (delete the share)
            del_resp = _delete_share(session, base_url, share_id)
            assert del_resp.get("ocs", {}).get("meta", {}).get("status") == "ok", (
                f"Unshare failed: {del_resp}"
            )

            # Verify recipient can NO LONGER access
            get_resp2 = recipient_session.get(get_url, timeout=30)
            assert get_resp2.status_code in (404, 403, 401), (
                f"Recipient should NOT have access after unshare, "
                f"but got HTTP {get_resp2.status_code}"
            )

        finally:
            _ocs_api(
                session, base_url, "DELETE",
                f"/ocs/v2.php/cloud/users/{recipient_uid}",
            )
