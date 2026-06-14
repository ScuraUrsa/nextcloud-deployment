"""
Collaboration test: Nextcloud Talk.

Tests conversation creation, messaging, participant management.
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
    """Return headers required by the Nextcloud OCS API."""
    return {
        "OCS-APIRequest": "true",
        "Accept": "application/json",
    }


def _ocs_post(endpoint, data=None):
    """POST to an OCS endpoint, return parsed JSON."""
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.post(
        url, auth=_auth(), headers=_ocs_headers(),
        json=data or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _ocs_get(endpoint):
    """GET from an OCS endpoint, return parsed JSON."""
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.get(url, auth=_auth(), headers=_ocs_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _ocs_delete(endpoint, data=None):
    """DELETE an OCS endpoint, return parsed JSON."""
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.delete(url, auth=_auth(), headers=_ocs_headers(),
                           json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _create_conversation(room_name, room_type=2):
    """Create a Talk conversation (room). room_type: 2=group, 3=public."""
    return _ocs_post("apps/spreed/api/v4/room", data={
        "roomName": room_name,
        "roomType": room_type,
    })


def _delete_conversation(token):
    """Delete a Talk conversation by token."""
    return _ocs_delete(f"apps/spreed/api/v4/room/{token}")


def _send_message(token, message):
    """Send a text message to a conversation."""
    return _ocs_post(f"apps/spreed/api/v1/chat/{token}", data={
        "message": message,
    })


def _get_messages(token, limit=50):
    """Retrieve message history from a conversation."""
    return _ocs_get(f"apps/spreed/api/v1/chat/{token}?limit={limit}")


def _add_participant(token, user_id):
    """Add a user to a conversation."""
    return _ocs_post(f"apps/spreed/api/v4/room/{token}/participants", data={
        "newParticipant": user_id,
    })


def _remove_participant(token, user_id):
    """Remove a user from a conversation."""
    return _ocs_delete(f"apps/spreed/api/v4/room/{token}/participants", data={
        "participant": user_id,
    })


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
def conversation(admin_user, unique_suffix):
    """Create a test conversation and return its token. Clean up after."""
    room_name = f"test-talk-{unique_suffix}"
    result = _create_conversation(room_name)
    ocs = result.get("ocs", {})
    token = ocs.get("data", {}).get("token", "")
    assert token, f"Failed to create conversation: {result}"
    yield token
    try:
        _delete_conversation(token)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.collaboration
def test_create_conversation(admin_user, unique_suffix):
    """Create a group conversation and verify it exists."""
    room_name = f"test-create-{unique_suffix}"
    result = _create_conversation(room_name)
    ocs = result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") == 200, \
        f"Unexpected OCS status: {result}"
    data = ocs.get("data", {})
    assert data.get("token"), "Conversation token missing"
    assert data.get("name") == room_name, \
        f"Expected name '{room_name}', got '{data.get('name')}'"

    # Cleanup
    _delete_conversation(data["token"])


@pytest.mark.collaboration
def test_send_message(conversation):
    """Send a text message to a conversation."""
    result = _send_message(conversation, "Hello from pytest!")
    ocs = result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") == 201, \
        f"Unexpected status sending message: {result}"


@pytest.mark.collaboration
def test_get_messages(conversation):
    """Send a message then verify it appears in message history."""
    # Send a unique message
    marker = f"test-marker-{uuid.uuid4().hex[:8]}"
    _send_message(conversation, marker)

    # Retrieve messages
    result = _get_messages(conversation)
    ocs = result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") == 200, \
        f"Unexpected status getting messages: {result}"

    # Search for our marker in the message list
    messages = ocs.get("data", [])
    # Messages may be a list or a dict with 'messages' key depending on API version
    if isinstance(messages, dict):
        messages = messages.get("messages", messages.values())
    found = any(marker in str(msg) for msg in messages)
    assert found, f"Sent message '{marker}' not found in history"


@pytest.mark.collaboration
def test_add_participant(conversation, admin_user):
    """Add a participant to the conversation."""
    # The admin is already a participant; adding them again should be idempotent
    # or return success. We test the API call succeeds.
    result = _add_participant(conversation, admin_user)
    ocs = result.get("ocs", {})
    status = ocs.get("meta", {}).get("statuscode")
    # 200 = success, 409 = already participant (both acceptable)
    assert status in (200, 409), \
        f"Unexpected status adding participant: {result}"


@pytest.mark.collaboration
def test_remove_participant(conversation, admin_user):
    """Remove a participant from the conversation (idempotent test)."""
    # Attempt to remove admin — may fail if admin is the last owner,
    # but the API call itself should not crash.
    result = _remove_participant(conversation, admin_user)
    ocs = result.get("ocs", {})
    status = ocs.get("meta", {}).get("statuscode")
    # 200 = success, 403/400 = cannot remove last owner (acceptable)
    assert status in (200, 400, 403), \
        f"Unexpected status removing participant: {result}"
