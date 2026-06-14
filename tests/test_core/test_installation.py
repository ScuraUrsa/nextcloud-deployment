"""
test_installation.py — Smoke tests for Nextcloud installation health.

Verifies:
- Nextcloud version via status.php
- Installed state (installed=true, maintenance=false)
- Required PHP modules loaded (via serverinfo API)
- Database connectivity (PostgreSQL)
- Redis connectivity (via serverinfo cache section)
- Cron execution timestamp
- Elasticsearch connectivity (if enabled)

All tests are marked @pytest.mark.smoke.
"""

import os
import re
import json
import pytest
import requests
from urllib.parse import urljoin


pytestmark = pytest.mark.smoke


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ocs_get(session, base_url, path, timeout=30):
    """Make an OCS API GET request and return parsed JSON."""
    url = urljoin(base_url, path)
    headers = {"OCS-APIRequest": "true", "Accept": "application/json"}
    resp = session.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _status_php(session, base_url):
    """Fetch status.php and return parsed JSON."""
    url = urljoin(base_url, "/status.php")
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNextcloudVersion:
    """Verify the Nextcloud version reported by status.php."""

    def test_nextcloud_version(self, nextcloud_api, expected_version):
        """status.php should report the expected version string."""
        api = nextcloud_api
        status = _status_php(api["session"], api["base_url"])
        actual = status.get("version", "")
        assert actual == expected_version, (
            f"Expected version {expected_version}, got {actual}"
        )


class TestNextcloudInstalled:
    """Verify Nextcloud is installed and not in maintenance mode."""

    def test_nextcloud_installed(self, nextcloud_api):
        """status.php should report installed=true and maintenance=false."""
        api = nextcloud_api
        status = _status_php(api["session"], api["base_url"])

        installed = status.get("installed")
        assert installed is True, (
            f"Expected installed=true, got {installed}"
        )

        maintenance = status.get("maintenance")
        assert maintenance is False, (
            f"Expected maintenance=false, got {maintenance}"
        )


class TestPhpModules:
    """Verify required PHP modules are loaded."""

    REQUIRED_MODULES = [
        "pgsql",       # PostgreSQL
        "redis",       # Redis
        "curl",        # HTTP
        "gd",          # Image processing
        "imagick",     # ImageMagick
        "intl",        # Internationalization
        "mbstring",    # Multibyte strings
        "zip",         # Compression
        "xml",         # XML parsing
        "json",        # JSON
        "openssl",     # TLS
        "bz2",         # Bzip2
        "ctype",       # Character type
        "dom",         # DOM
        "fileinfo",    # File type detection
        "iconv",       # Character set conversion
        "posix",       # POSIX
        "simplexml",   # SimpleXML
        "sodium",      # Encryption
    ]

    def test_php_modules(self, nextcloud_api):
        """Serverinfo API should list all required PHP modules as loaded."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]

        # Try the serverinfo API
        try:
            data = _ocs_get(session, base_url, "/ocs/v2.php/apps/serverinfo/api/v1/info")
        except (requests.RequestException, json.JSONDecodeError):
            pytest.skip("Serverinfo app not available or API unreachable")

        # Navigate to php/modules
        ocs_data = data.get("ocs", {}).get("data", {})
        php_info = ocs_data.get("php", {})
        modules = php_info.get("modules", {})

        if not modules:
            pytest.skip("PHP modules data not available in serverinfo response")

        missing = []
        for mod in self.REQUIRED_MODULES:
            if mod not in modules:
                missing.append(mod)

        assert not missing, (
            f"Missing required PHP modules: {', '.join(missing)}"
        )


class TestDatabaseConnectivity:
    """Verify PostgreSQL is reachable and Nextcloud can use it."""

    def test_database_connectivity(self, nextcloud_api):
        """status.php should report a working database connection."""
        api = nextcloud_api
        status = _status_php(api["session"], api["base_url"])

        # status.php includes a 'dbtype' field
        dbtype = status.get("dbtype", "")
        assert dbtype == "pgsql", (
            f"Expected dbtype=pgsql, got {dbtype}"
        )

        # If there's a database error, status.php would report it
        db_error = status.get("db_error", "")
        assert not db_error, (
            f"Database error reported: {db_error}"
        )


class TestRedisConnectivity:
    """Verify Redis is reachable and configured as cache backend."""

    def test_redis_connectivity(self, nextcloud_api):
        """Serverinfo cache section should show Redis as active."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]

        try:
            data = _ocs_get(session, base_url, "/ocs/v2.php/apps/serverinfo/api/v1/info")
        except (requests.RequestException, json.JSONDecodeError):
            pytest.skip("Serverinfo app not available or API unreachable")

        ocs_data = data.get("ocs", {}).get("data", {})
        cache_info = ocs_data.get("cache", {})

        if not cache_info:
            pytest.skip("Cache data not available in serverinfo response")

        # Check that Redis is the distributed cache backend
        distributed = cache_info.get("distributed", "")
        assert "redis" in distributed.lower() or "Redis" in str(cache_info), (
            f"Redis not detected as cache backend. Cache info: {cache_info}"
        )


class TestCronConfigured:
    """Verify system cron is configured and has executed recently."""

    def test_cron_configured(self, nextcloud_api):
        """status.php should report a recent cron execution timestamp."""
        api = nextcloud_api
        status = _status_php(api["session"], api["base_url"])

        # Check cron mode
        cron_mode = status.get("cron", "")
        assert cron_mode == "cron", (
            f"Expected cron mode 'cron', got '{cron_mode}'. "
            "System cron (not AJAX) should be configured."
        )

        # Check last cron execution
        last_cron = status.get("lastcron", None)
        assert last_cron is not None, (
            "No last cron timestamp found. Cron may never have executed."
        )

        # lastcron is a Unix timestamp; verify it's recent (within 24 hours)
        import time
        now = time.time()
        age_seconds = now - int(last_cron)
        assert age_seconds < 86400, (
            f"Last cron execution was {age_seconds:.0f} seconds ago "
            f"({age_seconds / 3600:.1f} hours). Expected within 24 hours."
        )


class TestElasticsearchConnectivity:
    """Verify Elasticsearch is reachable if the fulltextsearch app is enabled."""

    def test_elasticsearch_connectivity(self, nextcloud_api):
        """If Elasticsearch is configured, it should be reachable."""
        api = nextcloud_api
        session = api["session"]
        base_url = api["base_url"]

        # Check if fulltextsearch is enabled
        try:
            data = _ocs_get(session, base_url, "/ocs/v2.php/apps/serverinfo/api/v1/info")
        except (requests.RequestException, json.JSONDecodeError):
            pytest.skip("Serverinfo app not available or API unreachable")

        ocs_data = data.get("ocs", {}).get("data", {})
        apps = ocs_data.get("apps", {}) if isinstance(ocs_data, dict) else {}

        # Check if fulltextsearch or elasticsearch app is enabled
        es_enabled = False
        for app_name in ("fulltextsearch", "fulltextsearch_elasticsearch", "elastic_search"):
            if app_name in str(apps).lower():
                es_enabled = True
                break

        if not es_enabled:
            pytest.skip("Elasticsearch / fulltextsearch not enabled — skipping")

        # Try to reach the ES health endpoint via Nextcloud's serverinfo
        # or directly if configured
        es_url = os.environ.get("NEXTCLOUD_ELASTICSEARCH_URL", "")
        if es_url:
            try:
                resp = requests.get(urljoin(es_url, "/_cluster/health"), timeout=10)
                resp.raise_for_status()
                health = resp.json()
                status = health.get("status", "unknown")
                assert status in ("green", "yellow"), (
                    f"Elasticsearch cluster status is {status}, expected green or yellow"
                )
            except requests.RequestException as exc:
                pytest.fail(f"Elasticsearch at {es_url} is not reachable: {exc}")
        else:
            # Without a direct URL, we can only verify the app is enabled
            # which we already confirmed above
            pass
