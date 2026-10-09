"""
Offline unit tests for the shared test helpers in ``tests/utils``.

These need no running Nextcloud/Keycloak/Lago instance and therefore always
run, including in the CI ``unit-tests`` job.
"""

from __future__ import annotations

import base64

import pytest

from ..utils.assertions import assert_webdav_response
from ..utils.data_generators import (
    generate_random_file,
    generate_test_filename,
    generate_test_user_data,
)
from ..utils.nextcloud_api import NextcloudAPI, NextcloudAPIError, WebDAVResponse

pytestmark = pytest.mark.unit


def test_generate_random_file_size() -> None:
    assert len(generate_random_file(0)) == 0
    assert len(generate_random_file(1024)) == 1024


def test_generate_test_user_data_shape() -> None:
    data = generate_test_user_data(prefix="ci")
    assert set(data) == {"username", "password", "display_name", "email"}
    assert data["username"].startswith("ci_")
    assert data["email"] == f"{data['username']}@test.example.com"
    assert generate_test_user_data()["username"] != generate_test_user_data()["username"]


@pytest.mark.parametrize("extension", ["txt", ".txt"])
def test_generate_test_filename_extension(extension: str) -> None:
    name = generate_test_filename(extension)
    assert name.startswith("testfile_")
    assert name.endswith(".txt")
    assert ".." not in name


@pytest.mark.parametrize(("status", "ok"), [(199, False), (200, True), (207, True), (299, True), (404, False)])
def test_webdav_response_ok(status: int, ok: bool) -> None:
    assert WebDAVResponse(status_code=status, headers={}, body=b"").ok is ok


def test_assert_webdav_response() -> None:
    assert_webdav_response(WebDAVResponse(status_code=201, headers={}, body=b""), 201)
    with pytest.raises(AssertionError, match="expected status 201, got 500"):
        assert_webdav_response(WebDAVResponse(status_code=500, headers={}, body=b"boom"), 201)


def test_basic_auth_header() -> None:
    header = NextcloudAPI._make_basic_auth_header("admin", "s3cr:et")
    scheme, encoded = header.split(" ", 1)
    assert scheme == "Basic"
    assert base64.b64decode(encoded).decode() == "admin:s3cr:et"


def test_nextcloud_api_error_attributes() -> None:
    err = NextcloudAPIError("failed", status_code=503, response_text="down")
    assert str(err) == "failed"
    assert err.status_code == 503
    assert err.response_text == "down"
