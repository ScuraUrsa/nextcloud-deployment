"""
Collaboration test: Calendar (CalDAV).

Tests calendar creation, event CRUD, recurring events, and CalDAV PROPFIND.
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
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Namespaces used in CalDAV / WebDAV XML
# ---------------------------------------------------------------------------
NS = {
    "D": "DAV:",
    "C": "urn:ietf:params:xml:ns:caldav",
    "CS": "http://calendarserver.org/ns/",
    "ICAL": "http://apple.com/ns/ical/",
    "NC": "http://nextcloud.com/ns",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth():
    """Return (user, pass) tuple for HTTP Basic Auth."""
    return (os.environ["NEXTCLOUD_ADMIN_USER"], os.environ["NEXTCLOUD_ADMIN_PASS"])


def _base_url():
    """Return the base URL, stripping trailing slash."""
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _caldav_root(user):
    """CalDAV calendar-home-set URL for a given user."""
    return f"{_base_url()}/remote.php/dav/calendars/{user}"


def _propfind(url, body="", depth="0"):
    """Send a WebDAV PROPFIND request."""
    resp = requests.request(
        "PROPFIND", url, auth=_auth(),
        headers={"Depth": depth, "Content-Type": "application/xml"},
        data=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp


def _mkcalendar(url, displayname="{http://apple.com/ns/ical/}calendar-color"):
    """Create a calendar collection via MKCALENDAR."""
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<C:mkcalendar xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"
              xmlns:ICAL="http://apple.com/ns/ical/" xmlns:CS="http://calendarserver.org/ns/">
  <D:set>
    <D:prop>
      <D:displayname>{displayname}</D:displayname>
      <ICAL:calendar-color>#ff6600</ICAL:calendar-color>
      <C:supported-calendar-component-set>
        <C:comp name="VEVENT"/>
      </C:supported-calendar-component-set>
    </D:prop>
  </D:set>
</C:mkcalendar>"""
    resp = requests.request(
        "MKCALENDAR", url, auth=_auth(),
        headers={"Content-Type": "application/xml"},
        data=body, timeout=30,
    )
    resp.raise_for_status()
    return resp


def _put_event(calendar_url, ics_data):
    """PUT an iCalendar object to a calendar collection."""
    uid = uuid.uuid4().hex
    event_url = f"{calendar_url}/{uid}.ics"
    resp = requests.put(
        event_url, auth=_auth(),
        headers={"Content-Type": "text/calendar; charset=utf-8"},
        data=ics_data, timeout=30,
    )
    resp.raise_for_status()
    return event_url


def _delete(url):
    """DELETE a WebDAV resource."""
    resp = requests.delete(url, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp


def _ics_event(summary, dtstart, dtend, uid=None, description=""):
    """Build a minimal VEVENT iCalendar string."""
    uid = uid or f"{uuid.uuid4().hex}@nextcloud-deployment"
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Nextcloud Deployment Test//\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{now}\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"SUMMARY:{summary}\r\n"
        f"DESCRIPTION:{description}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


def _ics_recurring(summary, dtstart, dtend, rrule, uid=None):
    """Build a recurring VEVENT iCalendar string."""
    uid = uid or f"{uuid.uuid4().hex}@nextcloud-deployment"
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Nextcloud Deployment Test//\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{now}\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"SUMMARY:{summary}\r\n"
        f"RRULE:{rrule}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_user():
    """Return the admin username from environment."""
    return os.environ["NEXTCLOUD_ADMIN_USER"]


@pytest.fixture
def unique_suffix():
    """Return a unique string for resource names to ensure idempotency."""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def calendar_url(admin_user, unique_suffix):
    """Create a test calendar and return its URL. Clean up after test."""
    cal_name = f"test-cal-{unique_suffix}"
    url = f"{_caldav_root(admin_user)}/{cal_name}"
    _mkcalendar(url, displayname=cal_name)
    yield url
    # Cleanup: delete the calendar
    try:
        _delete(url)
    except Exception:
        pass  # best-effort cleanup


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.collaboration
def test_caldav_propfind(admin_user):
    """Verify that CalDAV calendar-home-set is discoverable via PROPFIND."""
    body = """<?xml version="1.0" encoding="UTF-8"?>
<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:prop>
    <C:calendar-home-set/>
  </D:prop>
</D:propfind>"""
    resp = _propfind(f"{_base_url()}/remote.php/dav/calendars/{admin_user}", body=body, depth="0")
    assert resp.status_code == 207
    root = ET.fromstring(resp.text)
    # Find calendar-home-set href
    hrefs = root.findall(".//D:href", NS)
    assert len(hrefs) >= 1, "Expected at least one calendar-home-set href"
    # The href should point to the user's calendar root
    assert any(f"/calendars/{admin_user}" in (h.text or "") for h in hrefs), \
        "calendar-home-set should reference the user's calendar root"


@pytest.mark.collaboration
def test_create_calendar(admin_user, unique_suffix):
    """Create a calendar via MKCALENDAR and verify it appears in PROPFIND."""
    cal_name = f"test-create-{unique_suffix}"
    url = f"{_caldav_root(admin_user)}/{cal_name}"

    # Create
    _mkcalendar(url, displayname=cal_name)

    # Verify via PROPFIND listing
    resp = _propfind(_caldav_root(admin_user), depth="1")
    assert resp.status_code == 207
    root = ET.fromstring(resp.text)
    hrefs = [h.text for h in root.findall(".//D:href", NS) if h.text]
    assert any(cal_name in h for h in hrefs), f"Calendar '{cal_name}' not found in PROPFIND listing"

    # Cleanup
    _delete(url)


@pytest.mark.collaboration
def test_create_event(calendar_url):
    """Create a single event in a calendar."""
    start = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%dT%H%M%SZ")
    end = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).strftime("%Y%m%dT%H%M%SZ")
    ics = _ics_event("Test Single Event", start, end, description="Created by pytest")
    event_url = _put_event(calendar_url, ics)

    # Verify the event exists via GET
    resp = requests.get(event_url, auth=_auth(), timeout=30)
    assert resp.status_code == 200
    assert "VEVENT" in resp.text
    assert "Test Single Event" in resp.text

    # Cleanup
    _delete(event_url)


@pytest.mark.collaboration
def test_create_recurring_event(calendar_url):
    """Create a recurring event with an RRULE."""
    start = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y%m%dT%H%M%SZ")
    end = (datetime.now(timezone.utc) + timedelta(days=2, hours=1)).strftime("%Y%m%dT%H%M%SZ")
    ics = _ics_recurring(
        "Weekly Standup", start, end,
        rrule="FREQ=WEEKLY;COUNT=10;BYDAY=MO",
    )
    event_url = _put_event(calendar_url, ics)

    # Verify
    resp = requests.get(event_url, auth=_auth(), timeout=30)
    assert resp.status_code == 200
    assert "VEVENT" in resp.text
    assert "RRULE" in resp.text
    assert "Weekly Standup" in resp.text

    # Cleanup
    _delete(event_url)


@pytest.mark.collaboration
def test_update_event(calendar_url):
    """Update an event's time and description."""
    start = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y%m%dT%H%M%SZ")
    end = (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).strftime("%Y%m%dT%H%M%SZ")
    uid = f"{uuid.uuid4().hex}@nextcloud-deployment"

    # Create initial event
    ics_original = _ics_event("Original Title", start, end, uid=uid, description="Before update")
    event_url = _put_event(calendar_url, ics_original)

    # Update: new time and description
    new_start = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y%m%dT%H%M%SZ")
    new_end = (datetime.now(timezone.utc) + timedelta(days=4, hours=2)).strftime("%Y%m%dT%H%M%SZ")
    ics_updated = _ics_event("Updated Title", new_start, new_end, uid=uid, description="After update")
    _put_event(calendar_url, ics_updated)  # same URL, overwrites

    # Verify update
    resp = requests.get(event_url, auth=_auth(), timeout=30)
    assert resp.status_code == 200
    assert "Updated Title" in resp.text
    assert "After update" in resp.text
    assert "Original Title" not in resp.text

    # Cleanup
    _delete(event_url)


@pytest.mark.collaboration
def test_delete_event(calendar_url):
    """Delete an event and verify it is gone."""
    start = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y%m%dT%H%M%SZ")
    end = (datetime.now(timezone.utc) + timedelta(days=5, hours=1)).strftime("%Y%m%dT%H%M%SZ")
    ics = _ics_event("Event To Delete", start, end)
    event_url = _put_event(calendar_url, ics)

    # Confirm it exists
    resp = requests.get(event_url, auth=_auth(), timeout=30)
    assert resp.status_code == 200

    # Delete
    _delete(event_url)

    # Verify deletion
    resp = requests.get(event_url, auth=_auth(), timeout=30)
    assert resp.status_code == 404, f"Expected 404 after deletion, got {resp.status_code}"
