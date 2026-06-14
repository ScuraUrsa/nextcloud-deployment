"""
test_bookmarks.py — Content tests for Nextcloud Bookmarks app.

Tests:
- test_create_bookmark: Create a bookmark and verify it is stored.
- test_tag_filtering: Create bookmarks with tags and verify tag filtering.

All tests are self-contained, idempotent, and marked @pytest.mark.content.
"""

from __future__ import annotations

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


def _bookmarks_api_get(endpoint, params=None):
    """Call the Bookmarks app REST API."""
    url = f"{_base_url()}/index.php/apps/bookmarks/public/rest/v2/{endpoint}"
    resp = requests.get(
        url, auth=_auth(),
        headers={"Accept": "application/json"},
        params=params or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _bookmarks_api_post(endpoint, data=None):
    """POST to the Bookmarks app REST API."""
    url = f"{_base_url()}/index.php/apps/bookmarks/public/rest/v2/{endpoint}"
    resp = requests.post(
        url, auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=data or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _bookmarks_api_delete(endpoint):
    """DELETE via the Bookmarks app REST API."""
    url = f"{_base_url()}/index.php/apps/bookmarks/public/rest/v2/{endpoint}"
    resp = requests.delete(
        url, auth=_auth(),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unique_suffix():
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.content
def test_create_bookmark(unique_suffix):
    """Create a bookmark and verify it appears in the bookmark list."""
    bookmark_data = {
        "url": f"https://example-{unique_suffix}.com/test-page",
        "title": f"Test Bookmark {unique_suffix}",
        "description": "A bookmark created by pytest",
        "tags": ["test", "pytest"],
    }

    try:
        # Create the bookmark
        result = _bookmarks_api_post("bookmark", data=bookmark_data)
        # Response should contain the bookmark data
        assert "id" in result or "item" in str(result).lower(), (
            f"Create bookmark response missing ID: {result}"
        )

        bookmark_id = result.get("id") or result.get("bookmark", {}).get("id")
        assert bookmark_id, f"Could not extract bookmark ID from: {result}"

        # Verify it appears in the list
        list_result = _bookmarks_api_get("bookmark")
        bookmarks = list_result if isinstance(list_result, list) else list_result.get("data", [])
        found = any(
            b.get("url") == bookmark_data["url"]
            for b in bookmarks
            if isinstance(b, dict)
        )
        assert found, f"Created bookmark not found in list: {list_result}"

        # Cleanup
        _bookmarks_api_delete(f"bookmark/{bookmark_id}")

    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (404, 501):
            pytest.skip("Bookmarks app is not installed or not enabled — skipping")
        raise


@pytest.mark.content
def test_tag_filtering(unique_suffix):
    """Create bookmarks with different tags and verify tag-based filtering."""
    tag_a = f"tag-a-{unique_suffix}"
    tag_b = f"tag-b-{unique_suffix}"

    bookmark_a = {
        "url": f"https://example-{unique_suffix}-a.com",
        "title": f"Bookmark A {unique_suffix}",
        "tags": [tag_a],
    }
    bookmark_b = {
        "url": f"https://example-{unique_suffix}-b.com",
        "title": f"Bookmark B {unique_suffix}",
        "tags": [tag_b],
    }

    try:
        # Create both bookmarks
        result_a = _bookmarks_api_post("bookmark", data=bookmark_a)
        result_b = _bookmarks_api_post("bookmark", data=bookmark_b)

        id_a = result_a.get("id") or result_a.get("bookmark", {}).get("id")
        id_b = result_b.get("id") or result_b.get("bookmark", {}).get("id")

        # Filter by tag_a — should return bookmark A but not B
        filter_result = _bookmarks_api_get("bookmark", params={"tags": tag_a})
        filtered = filter_result if isinstance(filter_result, list) else filter_result.get("data", [])
        urls_in_filter = [b.get("url") for b in filtered if isinstance(b, dict)]

        assert bookmark_a["url"] in urls_in_filter, (
            f"Bookmark A not found when filtering by tag '{tag_a}': {filter_result}"
        )
        assert bookmark_b["url"] not in urls_in_filter, (
            f"Bookmark B should NOT appear when filtering by tag '{tag_a}': {filter_result}"
        )

        # Cleanup
        if id_a:
            _bookmarks_api_delete(f"bookmark/{id_a}")
        if id_b:
            _bookmarks_api_delete(f"bookmark/{id_b}")

    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (404, 501):
            pytest.skip("Bookmarks app is not installed or not enabled — skipping")
        raise
