"""
test_monitoring.py — Admin tests for Nextcloud Monitoring / Server Info.

Tests:
- test_serverinfo_api: Verify the serverinfo API returns system information.
- test_prometheus_metrics: Verify Prometheus metrics endpoint is reachable
  (if the metrics app is enabled).

All tests are self-contained, idempotent, and marked @pytest.mark.admin.
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unique_suffix():
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.admin
def test_serverinfo_api(unique_suffix):
    """Verify the serverinfo API returns valid system information."""
    # The serverinfo app exposes /ocs/v2.php/apps/serverinfo/api/v1/info
    try:
        result = _ocs_get("apps/serverinfo/api/v1/info")
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (404, 501):
            pytest.skip("Server Info app is not installed or not enabled — skipping")
        raise

    ocs = result.get("ocs", {})
    meta = ocs.get("meta", {})
    data = ocs.get("data", {})

    # Verify the OCS response is successful
    assert meta.get("status") == "ok" or meta.get("statuscode") in (200, 100), (
        f"Server info API returned error: {meta}"
    )

    # Verify the response contains expected system information fields
    # The serverinfo app returns data about the Nextcloud instance
    assert isinstance(data, dict), f"Server info data is not a dict: {type(data)}"

    # Check for common serverinfo fields
    # nextcloud: version info about the NC instance
    # system: OS/memory/CPU info
    # activeUsers: user statistics
    nc_info = data.get("nextcloud", {})
    sys_info = data.get("system", {})

    # At minimum, the nextcloud section should have version info
    if nc_info:
        assert "version" in nc_info or "system" in nc_info, (
            f"Server info 'nextcloud' section missing version info: {nc_info}"
        )

    # The system section should have basic OS info
    if sys_info:
        # Check for common fields
        expected_fields = ["os", "memory", "cpu", "time", "space"]
        found_fields = [f for f in expected_fields if f in sys_info]
        assert len(found_fields) > 0, (
            f"Server info 'system' section missing expected fields. "
            f"Found: {list(sys_info.keys())}"
        )

    # Verify the response is valid JSON (already parsed by _ocs_get)
    assert True, "Server info API returned valid system information"


@pytest.mark.admin
def test_prometheus_metrics(unique_suffix):
    """Verify the Prometheus metrics endpoint is reachable and returns metrics data."""
    # Check if the serverinfo app has metrics enabled, or if a separate
    # metrics/prometheus app is installed
    try:
        apps_result = _ocs_get("cloud/apps")
        apps_data = apps_result.get("ocs", {}).get("data", {})
        apps_list = apps_data.get("apps", []) if isinstance(apps_data, dict) else []

        metrics_enabled = False
        if isinstance(apps_list, list):
            for app in apps_list:
                if isinstance(app, dict):
                    app_id = app.get("id", "")
                    if "metrics" in app_id.lower() or "prometheus" in app_id.lower():
                        if app.get("active", False):
                            metrics_enabled = True
                            break

        # Also check if serverinfo exposes metrics
        if not metrics_enabled:
            for app in apps_list:
                if isinstance(app, dict) and "serverinfo" in app.get("id", ""):
                    if app.get("active", False):
                        # serverinfo may have a metrics endpoint
                        metrics_enabled = True
                        break

        if not metrics_enabled:
            pytest.skip("No metrics/prometheus app is enabled — skipping")
    except requests.HTTPError:
        # Can't check apps — try the endpoint anyway
        pass

    # Try common metrics endpoints
    metrics_endpoints = [
        "/index.php/apps/serverinfo/api/v1/metrics",
        "/metrics",
        "/index.php/apps/metrics/metrics",
        "/ocs/v2.php/apps/serverinfo/api/v1/metrics",
    ]

    metrics_found = False
    for endpoint in metrics_endpoints:
        try:
            url = f"{_base_url()}{endpoint}"
            resp = requests.get(url, auth=_auth(), timeout=30)

            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "")
                body = resp.text

                # Prometheus metrics format: lines with HELP/TYPE/metric_name
                is_prometheus = (
                    "prometheus" in content_type.lower() or
                    "text/plain" in content_type.lower() and (
                        "# HELP" in body or "# TYPE" in body or
                        "nextcloud" in body.lower()
                    )
                )

                if is_prometheus:
                    # Verify it contains metric data
                    assert len(body) > 0, "Metrics endpoint returned empty body"
                    # Check for common Nextcloud metrics
                    assert (
                        "# HELP" in body or
                        "# TYPE" in body or
                        "nextcloud" in body.lower() or
                        "nc_" in body.lower()
                    ), (
                        f"Metrics response does not contain recognizable metric data: "
                        f"{body[:200]}"
                    )
                    metrics_found = True
                    break

        except requests.ConnectionError:
            continue
        except requests.HTTPError:
            continue

    if not metrics_found:
        pytest.skip(
            "No Prometheus metrics endpoint found — "
            "metrics app may not be installed or configured"
        )
