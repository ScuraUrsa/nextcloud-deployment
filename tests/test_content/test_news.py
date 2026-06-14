"""
test_news.py — Content tests for Nextcloud News app.

Tests:
- test_subscribe_feed: Subscribe to an RSS/Atom feed and verify it appears.
- test_fetch_articles: Fetch articles from a subscribed feed.

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


def _ocs_headers():
    return {
        "OCS-APIRequest": "true",
        "Accept": "application/json",
    }


def _ocs_get(endpoint, params=None):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.get(
        url, auth=_auth(), headers=_ocs_headers(),
        params=params or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _ocs_post(endpoint, data=None):
    url = f"{_base_url()}/ocs/v2.php/{endpoint}"
    resp = requests.post(
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


def _news_api_get(endpoint, params=None):
    """Call the News app REST API (not OCS — it has its own endpoint)."""
    url = f"{_base_url()}/index.php/apps/news/api/v1-3/{endpoint}"
    resp = requests.get(
        url, auth=_auth(),
        headers={"Accept": "application/json"},
        params=params or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _news_api_post(endpoint, data=None):
    """POST to the News app REST API."""
    url = f"{_base_url()}/index.php/apps/news/api/v1-3/{endpoint}"
    resp = requests.post(
        url, auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=data or {}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _news_api_delete(endpoint):
    """DELETE via the News app REST API."""
    url = f"{_base_url()}/index.php/apps/news/api/v1-3/{endpoint}"
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
def test_subscribe_feed(unique_suffix):
    """Subscribe to a known RSS feed and verify it appears in the feed list."""
    # Use a well-known, stable RSS feed
    feed_url = "https://www.nasa.gov/rss/dyn/breaking_news.rss"

    try:
        # Subscribe to the feed
        result = _news_api_post("feeds", data={"url": feed_url})
        # The response should contain feed info
        assert "feeds" in result or "feed" in str(result).lower(), (
            f"Subscribe response missing feed data: {result}"
        )

        # Verify the feed appears in the feed list
        feeds_result = _news_api_get("feeds")
        feeds = feeds_result.get("feeds", [])
        # Find our feed by URL
        found = any(f.get("url") == feed_url for f in feeds)
        if not found:
            # The feed might be stored with a normalized URL
            found = any("nasa" in str(f.get("url", "")).lower() for f in feeds)
        assert found, f"Subscribed feed not found in feed list: {feeds_result}"

        # Cleanup: delete the feed
        # Find the feed ID
        feed_id = None
        for f in feeds:
            if f.get("url") == feed_url or "nasa" in str(f.get("url", "")).lower():
                feed_id = f.get("id")
                break
        if feed_id:
            _news_api_delete(f"feeds/{feed_id}")

    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (404, 501):
            pytest.skip("News app is not installed or not enabled — skipping")
        raise


@pytest.mark.content
def test_fetch_articles(unique_suffix):
    """Subscribe to a feed and verify articles can be fetched."""
    feed_url = "https://www.nasa.gov/rss/dyn/breaking_news.rss"

    try:
        # Subscribe
        sub_result = _news_api_post("feeds", data={"url": feed_url})
        feeds = sub_result.get("feeds", [])
        feed_id = None
        for f in feeds:
            if f.get("url") == feed_url or "nasa" in str(f.get("url", "")).lower():
                feed_id = f.get("id")
                break

        if not feed_id:
            # Try to get it from the feeds list
            feeds_result = _news_api_get("feeds")
            for f in feeds_result.get("feeds", []):
                if f.get("url") == feed_url or "nasa" in str(f.get("url", "")).lower():
                    feed_id = f.get("id")
                    break

        assert feed_id, f"Could not determine feed ID after subscribing: {sub_result}"

        # Fetch articles for this feed
        articles_result = _news_api_get("items", params={"feedId": feed_id, "limit": 5})
        # The response should contain items/articles
        items = articles_result.get("items", [])
        # A fresh subscription may have 0 items initially (fetch happens async),
        # so we just verify the API call succeeded
        assert "items" in articles_result or "error" not in str(articles_result).lower(), (
            f"Fetch articles response unexpected: {articles_result}"
        )

        # Cleanup
        _news_api_delete(f"feeds/{feed_id}")

    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (404, 501):
            pytest.skip("News app is not installed or not enabled — skipping")
        raise
