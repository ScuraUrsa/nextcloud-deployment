"""
Collaboration test: Deck (Kanban Boards).

Tests board creation, stack (column) creation, card creation, card assignment,
and board deletion.
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


def _ocs_delete(endpoint):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.delete(url, auth=_auth(), headers=_ocs_headers(), timeout=30)
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


# ---------------------------------------------------------------------------
# Deck API wrappers
# ---------------------------------------------------------------------------

def _create_board(title, color="ff6600"):
    """Create a Deck board via the Deck API."""
    return _ocs_post("apps/deck/api/v1.1/boards", data={
        "title": title,
        "color": color,
    })


def _delete_board(board_id):
    """Delete a Deck board."""
    return _ocs_delete(f"apps/deck/api/v1.1/boards/{board_id}")


def _create_stack(board_id, title, order=1):
    """Create a stack (column) in a board."""
    return _ocs_post(f"apps/deck/api/v1.1/boards/{board_id}/stacks", data={
        "title": title,
        "order": order,
    })


def _create_card(board_id, stack_id, title, description="", order=1):
    """Create a card in a stack."""
    return _ocs_post(f"apps/deck/api/v1.1/boards/{board_id}/stacks/{stack_id}/cards", data={
        "title": title,
        "description": description,
        "order": order,
        "type": "plain",
    })


def _assign_card(board_id, stack_id, card_id, user_id):
    """Assign a card to a user."""
    return _ocs_put(
        f"apps/deck/api/v1.1/boards/{board_id}/stacks/{stack_id}/cards/{card_id}/assign",
        data={"userId": user_id},
    )


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
def board(admin_user, unique_suffix):
    """Create a test board and return its ID. Clean up after."""
    title = f"test-board-{unique_suffix}"
    result = _create_board(title)
    ocs = result.get("ocs", {})
    board_id = ocs.get("data", {}).get("id")
    assert board_id, f"Failed to create board: {result}"
    yield board_id
    try:
        _delete_board(board_id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.collaboration
def test_create_board(admin_user, unique_suffix):
    """Create a kanban board and verify it exists."""
    title = f"test-create-board-{unique_suffix}"
    result = _create_board(title)
    ocs = result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") == 200, \
        f"Unexpected OCS status: {result}"
    data = ocs.get("data", {})
    assert data.get("id"), "Board ID missing"
    assert data.get("title") == title, \
        f"Expected title '{title}', got '{data.get('title')}'"

    # Cleanup
    _delete_board(data["id"])


@pytest.mark.collaboration
def test_create_stack(board):
    """Create a stack (column) in a board."""
    result = _create_stack(board, "To Do", order=1)
    ocs = result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") == 200, \
        f"Unexpected OCS status: {result}"
    data = ocs.get("data", {})
    assert data.get("id"), "Stack ID missing"
    assert data.get("title") == "To Do", \
        f"Expected title 'To Do', got '{data.get('title')}'"


@pytest.mark.collaboration
def test_create_card(board):
    """Create a card with a title in a stack."""
    # First create a stack to hold the card
    stack_result = _create_stack(board, "Backlog", order=1)
    stack_id = stack_result["ocs"]["data"]["id"]

    # Create card
    card_result = _create_card(board, stack_id, "Implement login page", description="Add SSO support")
    ocs = card_result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") == 200, \
        f"Unexpected OCS status: {card_result}"
    data = ocs.get("data", {})
    assert data.get("id"), "Card ID missing"
    assert data.get("title") == "Implement login page", \
        f"Expected card title, got '{data.get('title')}'"


@pytest.mark.collaboration
def test_assign_card(board, admin_user):
    """Assign a card to a user."""
    # Create stack and card
    stack_result = _create_stack(board, "In Progress", order=1)
    stack_id = stack_result["ocs"]["data"]["id"]
    card_result = _create_card(board, stack_id, "Fix bug #42")
    card_id = card_result["ocs"]["data"]["id"]

    # Assign
    assign_result = _assign_card(board, stack_id, card_id, admin_user)
    ocs = assign_result.get("ocs", {})
    assert ocs.get("meta", {}).get("statuscode") == 200, \
        f"Unexpected OCS status assigning card: {assign_result}"


@pytest.mark.collaboration
def test_delete_board(admin_user, unique_suffix):
    """Delete a board and verify it is gone."""
    title = f"test-delete-board-{unique_suffix}"
    result = _create_board(title)
    board_id = result["ocs"]["data"]["id"]

    # Confirm exists by listing boards
    list_result = _ocs_get("apps/deck/api/v1.1/boards")
    boards = list_result.get("ocs", {}).get("data", [])
    assert any(b.get("id") == board_id for b in boards), \
        "Board should exist before deletion"

    # Delete
    _delete_board(board_id)

    # Verify gone
    list_result = _ocs_get("apps/deck/api/v1.1/boards")
    boards = list_result.get("ocs", {}).get("data", [])
    assert not any(b.get("id") == board_id for b in boards), \
        "Board should not exist after deletion"
