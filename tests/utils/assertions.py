"""
Custom assertion helpers for Nextcloud deployment tests.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .nextcloud_api import NextcloudAPI, WebDAVResponse


def assert_webdav_response(
    response: WebDAVResponse,
    expected_status: int,
    message: str = "",
) -> None:
    """Assert that a WebDAV response has the expected HTTP status code."""
    assert response.status_code == expected_status, (
        f"{message or 'WebDAV response'}: expected status {expected_status}, "
        f"got {response.status_code}. Body: {response.body[:500]!r}"
    )


def assert_nextcloud_installed(api: NextcloudAPI) -> None:
    """Assert that Nextcloud is installed and not in maintenance mode."""
    info = api.status()
    assert info.installed, f"Nextcloud is not installed at {api.base_url}"
    assert not info.maintenance, f"Nextcloud is in maintenance mode at {api.base_url}"
    assert info.version, "Nextcloud version string is empty"


def assert_user_exists(api: NextcloudAPI, username: str) -> None:
    """Assert that a user exists in Nextcloud."""
    resp = api.get_user(username)
    assert resp.ocs_meta.get("status") == "ok", (
        f"User '{username}' does not exist or query failed: {resp.ocs_meta}"
    )


def assert_app_enabled(api: NextcloudAPI, app_name: str) -> None:
    """Assert that a Nextcloud app is enabled."""
    resp = api.list_apps()
    apps = resp.ocs_data
    # apps is a list of app strings or a dict; handle both
    if isinstance(apps, dict):
        app_list = list(apps.keys())
    elif isinstance(apps, list):
        app_list = apps
    else:
        app_list = []

    assert app_name in app_list, (
        f"App '{app_name}' not found in app list. Available: {app_list}"
    )

    # If the data is a dict with active status, check it
    if isinstance(apps, dict) and app_name in apps:
        app_info = apps[app_name]
        if isinstance(app_info, dict):
            assert app_info.get("active", False), f"App '{app_name}' is not active"


def assert_file_uploaded(api: NextcloudAPI, path: str, expected_size: int) -> None:
    """Assert that a file exists at the given WebDAV path with the expected size."""
    resp = api.propfind(path, depth=0)
    assert resp.status_code == 207, (
        f"PROPFIND on '{path}' failed: status {resp.status_code}"
    )
    # Check that the response contains the file
    if resp.xml_tree is not None:
        ns = {"d": "DAV:"}
        # Look for getcontentlength
        for propstat in resp.xml_tree.findall(".//d:propstat", ns):
            prop = propstat.find("d:prop", ns)
            if prop is not None:
                content_length = prop.find("d:getcontentlength", ns)
                if content_length is not None and content_length.text:
                    actual_size = int(content_length.text)
                    assert actual_size == expected_size, (
                        f"File '{path}' size mismatch: expected {expected_size}, got {actual_size}"
                    )
                    return
        # If we didn't find getcontentlength, check the href
        hrefs = resp.xml_tree.findall(".//d:href", ns)
        found = any(path.rstrip("/") in (h.text or "") for h in hrefs)
        assert found, f"File '{path}' not found in PROPFIND response"
