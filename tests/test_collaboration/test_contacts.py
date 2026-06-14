"""
Collaboration test: Contacts (CardDAV).

Tests contact creation, update, deletion, and CardDAV PROPFIND.
All tests are self-contained, idempotent, and marked @pytest.mark.collaboration.

Environment variables:
    NEXTCLOUD_URL          - Base URL of the Nextcloud instance
    NEXTCLOUD_ADMIN_USER   - Admin username
    NEXTCLOUD_ADMIN_PASS   - Admin password
"""

import os
import uuid
import pytest
import requests
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
NS = {
    "D": "DAV:",
    "CARD": "urn:ietf:params:xml:ns:carddav",
    "CS": "http://calendarserver.org/ns/",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth():
    return (os.environ["NEXTCLOUD_ADMIN_USER"], os.environ["NEXTCLOUD_ADMIN_PASS"])


def _base_url():
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _carddav_root(user):
    """CardDAV addressbook-home-set URL for a given user."""
    return f"{_base_url()}/remote.php/dav/addressbooks/{user}"


def _propfind(url, body="", depth="0"):
    resp = requests.request(
        "PROPFIND", url, auth=_auth(),
        headers={"Depth": depth, "Content-Type": "application/xml"},
        data=body, timeout=30,
    )
    resp.raise_for_status()
    return resp


def _mkcol(url):
    """Create a WebDAV collection (address book)."""
    resp = requests.request(
        "MKCOL", url, auth=_auth(), timeout=30,
    )
    resp.raise_for_status()
    return resp


def _put_vcard(addressbook_url, vcard_data):
    """PUT a vCard to an address book collection."""
    uid = uuid.uuid4().hex
    contact_url = f"{addressbook_url}/{uid}.vcf"
    resp = requests.put(
        contact_url, auth=_auth(),
        headers={"Content-Type": "text/vcard; charset=utf-8"},
        data=vcard_data, timeout=30,
    )
    resp.raise_for_status()
    return contact_url


def _delete(url):
    resp = requests.delete(url, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp


def _vcard(fullname, email, org="", tel="", uid=None):
    """Build a minimal vCard 4.0 string."""
    uid = uid or f"{uuid.uuid4().hex}@nextcloud-deployment"
    lines = [
        "BEGIN:VCARD",
        "VERSION:4.0",
        f"UID:{uid}",
        f"FN:{fullname}",
        f"EMAIL:{email}",
    ]
    if org:
        lines.append(f"ORG:{org}")
    if tel:
        lines.append(f"TEL:{tel}")
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_user():
    return os.environ["NEXTCLOUD_ADMIN_USER"]


@pytest.fixture
def unique_suffix():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def addressbook_url(admin_user, unique_suffix):
    """Create a test address book and return its URL. Clean up after test."""
    ab_name = f"test-ab-{unique_suffix}"
    url = f"{_carddav_root(admin_user)}/{ab_name}"
    _mkcol(url)
    yield url
    try:
        _delete(url)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.collaboration
def test_carddav_propfind(admin_user):
    """Verify that CardDAV addressbook-home-set is discoverable via PROPFIND."""
    body = """<?xml version="1.0" encoding="UTF-8"?>
<D:propfind xmlns:D="DAV:" xmlns:CARD="urn:ietf:params:xml:ns:carddav">
  <D:prop>
    <CARD:addressbook-home-set/>
  </D:prop>
</D:propfind>"""
    resp = _propfind(
        f"{_base_url()}/remote.php/dav/addressbooks/{admin_user}",
        body=body, depth="0",
    )
    assert resp.status_code == 207
    root = ET.fromstring(resp.text)
    hrefs = root.findall(".//D:href", NS)
    assert len(hrefs) >= 1, "Expected at least one addressbook-home-set href"
    assert any(f"/addressbooks/{admin_user}" in (h.text or "") for h in hrefs), \
        "addressbook-home-set should reference the user's address book root"


@pytest.mark.collaboration
def test_create_contact(addressbook_url):
    """Create a contact via CardDAV and verify it exists."""
    vcard = _vcard("John Doe", "john.doe@example.com", org="Acme Corp", tel="+1-555-0100")
    contact_url = _put_vcard(addressbook_url, vcard)

    # Verify via GET
    resp = requests.get(contact_url, auth=_auth(), timeout=30)
    assert resp.status_code == 200
    assert "VCARD" in resp.text
    assert "John Doe" in resp.text
    assert "john.doe@example.com" in resp.text

    # Cleanup
    _delete(contact_url)


@pytest.mark.collaboration
def test_update_contact(addressbook_url):
    """Update a contact's fields and verify changes."""
    uid = f"{uuid.uuid4().hex}@nextcloud-deployment"

    # Create initial
    vcard_orig = _vcard("Jane Smith", "jane.smith@example.com", org="Old Corp", uid=uid)
    contact_url = _put_vcard(addressbook_url, vcard_orig)

    # Update: change org and add phone
    vcard_updated = _vcard("Jane Smith", "jane.smith@example.com", org="New Corp", tel="+1-555-0200", uid=uid)
    _put_vcard(addressbook_url, vcard_updated)  # same URL, overwrites

    # Verify
    resp = requests.get(contact_url, auth=_auth(), timeout=30)
    assert resp.status_code == 200
    assert "New Corp" in resp.text
    assert "+1-555-0200" in resp.text
    assert "Old Corp" not in resp.text

    # Cleanup
    _delete(contact_url)


@pytest.mark.collaboration
def test_delete_contact(addressbook_url):
    """Delete a contact and verify it is gone."""
    vcard = _vcard("Delete Me", "delete.me@example.com")
    contact_url = _put_vcard(addressbook_url, vcard)

    # Confirm exists
    resp = requests.get(contact_url, auth=_auth(), timeout=30)
    assert resp.status_code == 200

    # Delete
    _delete(contact_url)

    # Verify gone
    resp = requests.get(contact_url, auth=_auth(), timeout=30)
    assert resp.status_code == 404, f"Expected 404 after deletion, got {resp.status_code}"
