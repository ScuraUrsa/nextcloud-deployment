"""
Collaboration test: Notes (Markdown Notes).

Tests note creation, update, and deletion via the Notes API.
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth():
    return (os.environ["NEXTCLOUD_ADMIN_USER"], os.environ["NEXTCLOUD_ADMIN_PASS"])


def _base_url():
    return os.environ["NEXTCLOUD_URL"].rstrip("/")


def _ocs_headers():
    return {
        "OCS-APIRequest": "true",
        "Accept": "application/json",
    }


def _ocs_post(endpoint, data=None):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.post(
        url, auth=_auth(), headers=_ocs_headers(),
        json=data or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _ocs_get(endpoint):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.get(url, auth=_auth(), headers=_ocs_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _ocs_put(endpoint, data=None):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.put(
        url, auth=_auth(), headers=_ocs_headers(),
        json=data or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _ocs_delete(endpoint):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.delete(url, auth=_auth(), headers=_ocs_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Notes API wrappers
# ---------------------------------------------------------------------------

def _create_note(title, content="", category=""):
    """Create a note via the Notes API."""
    return _ocs_post("apps/notes/api/v1/notes", data={
        "title": title,
        "content": content,
        "category": category,
    })


def _update_note(note_id, title=None, content=None, category=None):
    """Update a note's fields."""
    data = {}
    if title is not None:
        data["title"] = title
    if content is not None:
        data["content"] = content
    if category is not None:
        data["category"] = category
    return _ocs_put(f"apps/notes/api/v1/notes/{note_id}", data=data)


def _get_note(note_id):
    """Retrieve a single note."""
    return _ocs_get(f"apps/notes/api/v1/notes/{note_id}")


def _delete_note(note_id):
    """Delete a note."""
    return _ocs_delete(f"apps/notes/api/v1/notes/{note_id}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_user():
    return os.environ["NEXTCLOUD_ADMIN_USER"]


@pytest.fixture
def unique_suffix():
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.collaboration
def test_create_note(unique_suffix):
    """Create a markdown note and verify it exists."""
    title = f"Test Note {unique_suffix}"
    content = "# Hello\n\nThis is a test note created by pytest."
    result = _create_note(title, content=content)
    ocs = result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") in (200, 201), \
        f"Unexpected OCS status: {result}"
    data = ocs.get("data", {})
    note_id = data.get("id")
    assert note_id, f"Note ID missing: {result}"
    assert data.get("title") == title, \
        f"Expected title '{title}', got '{data.get('title')}'"

    # Cleanup
    _delete_note(note_id)


@pytest.mark.collaboration
def test_update_note(unique_suffix):
    """Edit a note's content and verify the update."""
    title = f"Update Note {unique_suffix}"
    original_content = "# Original\n\nOriginal content."
    result = _create_note(title, content=original_content)
    note_id = result["ocs"]["data"]["id"]

    # Update content
    new_content = "# Updated\n\nUpdated content with more details."
    update_result = _update_note(note_id, content=new_content)
    ocs = update_result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") in (200, 201), \
        f"Unexpected OCS status on update: {update_result}"

    # Verify update
    get_result = _get_note(note_id)
    note_data = get_result.get("ocs", {}).get("data", {})
    assert "Updated" in note_data.get("content", ""), \
        "Note content should reflect the update"
    assert "Original" not in note_data.get("content", ""), \
        "Original content should be replaced"

    # Cleanup
    _delete_note(note_id)


@pytest.mark.collaboration
def test_delete_note(unique_suffix):
    """Delete a note and verify it is gone."""
    title = f"Delete Note {unique_suffix}"
    result = _create_note(title, content="To be deleted.")
    note_id = result["ocs"]["data"]["id"]

    # Confirm exists
    get_result = _get_note(note_id)
    assert get_result.get("ocs", {}).get("meta", {}).get("statuscode") == 200, \
        "Note should exist before deletion"

    # Delete
    _delete_note(note_id)

    # Verify gone
    get_result = _get_note(note_id)
    status = get_result.get("ocs", {}).get("meta", {}).get("statuscode")
    assert status != 200, \
        f"Note should not be retrievable after deletion, got status {status}"
