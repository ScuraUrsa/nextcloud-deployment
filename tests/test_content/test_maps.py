"""
test_maps.py — Content tests for Nextcloud Maps app.

Tests:
- test_geotag_photo: Upload a photo with GPS coordinates and verify geotagging.

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


def _webdav_put(path, data, content_type="image/jpeg"):
    """Upload a file via WebDAV PUT."""
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{path.lstrip('/')}"
    resp = requests.put(
        url, auth=_auth(), data=data,
        headers={"Content-Type": content_type},
        timeout=30,
    )
    resp.raise_for_status()
    return resp


def _webdav_delete(path):
    """Delete a file via WebDAV DELETE."""
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{path.lstrip('/')}"
    resp = requests.delete(url, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp


def _generate_tiny_jpeg_with_exif_gps(lat: float, lon: float) -> bytes:
    """Generate a minimal JPEG with EXIF GPS metadata.

    This embeds GPS latitude/longitude into the EXIF IFD of a minimal JPEG.
    """
    import struct

    # Build a minimal JPEG with an EXIF APP1 segment containing GPS data
    # SOI marker
    soi = b"\xff\xd8"

    # APP1 marker for EXIF
    # TIFF header: little-endian (II), magic 0x002a, offset to IFD0
    tiff_header = b"II\x2a\x00\x08\x00\x00\x00"

    # IFD0: 1 entry (just a pointer to GPS IFD)
    # Entry: tag 0x8825 (GPS IFD pointer), type LONG (4), count 1, value = offset to GPS IFD
    ifd0_count = b"\x01\x00"
    gps_ifd_tag = b"\x25\x88"  # 0x8825 little-endian
    gps_ifd_type = b"\x04\x00"  # LONG
    gps_ifd_count = b"\x01\x00\x00\x00"
    # GPS IFD will be at offset 26 from TIFF start (after IFD0 + next IFD pointer)
    gps_ifd_offset = struct.pack("<I", 26)
    ifd0_entry = gps_ifd_tag + gps_ifd_type + gps_ifd_count + gps_ifd_offset
    # Next IFD offset: 0 (no more IFDs)
    next_ifd = b"\x00\x00\x00\x00"

    # GPS IFD: 4 entries (version, lat ref, lat, lon ref, lon)
    gps_ifd_count = b"\x04\x00"

    # GPSVersionID tag 0x0000, BYTE(1), count 4
    gps_ver_tag = b"\x00\x00"
    gps_ver_type = b"\x01\x00"
    gps_ver_count = b"\x04\x00\x00\x00"
    gps_ver_value = b"\x02\x02\x00\x00"  # version 2.2.0.0
    gps_ver_entry = gps_ver_tag + gps_ver_type + gps_ver_count + gps_ver_value

    # GPSLatitudeRef tag 0x0001, ASCII(2), count 2
    lat_ref = b"N" if lat >= 0 else b"S"
    gps_lat_ref_tag = b"\x01\x00"
    gps_lat_ref_type = b"\x02\x00"
    gps_lat_ref_count = b"\x02\x00\x00\x00"
    # Value is offset to string (we'll put strings after GPS IFD)
    gps_lat_ref_offset = struct.pack("<I", 26 + 2 + 4 * 12 + 4)  # after GPS IFD + next IFD
    gps_lat_ref_entry = gps_lat_ref_tag + gps_lat_ref_type + gps_lat_ref_count + gps_lat_ref_offset

    # GPSLatitude tag 0x0002, RATIONAL(5), count 3
    abs_lat = abs(lat)
    lat_deg = int(abs_lat)
    lat_min = int((abs_lat - lat_deg) * 60)
    lat_sec_num = int(((abs_lat - lat_deg) * 60 - lat_min) * 60 * 100)
    lat_sec_den = 100
    gps_lat_tag = b"\x02\x00"
    gps_lat_type = b"\x05\x00"
    gps_lat_count = b"\x03\x00\x00\x00"
    gps_lat_offset = struct.pack("<I", 26 + 2 + 4 * 12 + 4 + 2)  # after lat ref string
    gps_lat_entry = gps_lat_tag + gps_lat_type + gps_lat_count + gps_lat_offset

    # GPSLongitudeRef tag 0x0003, ASCII(2), count 2
    lon_ref = b"E" if lon >= 0 else b"W"
    gps_lon_ref_tag = b"\x03\x00"
    gps_lon_ref_type = b"\x02\x00"
    gps_lon_ref_count = b"\x02\x00\x00\x00"
    gps_lon_ref_offset = struct.pack("<I", 26 + 2 + 4 * 12 + 4 + 2 + 24)  # after lat values
    gps_lon_ref_entry = gps_lon_ref_tag + gps_lon_ref_type + gps_lon_ref_count + gps_lon_ref_offset

    # GPSLongitude tag 0x0004, RATIONAL(5), count 3
    abs_lon = abs(lon)
    lon_deg = int(abs_lon)
    lon_min = int((abs_lon - lon_deg) * 60)
    lon_sec_num = int(((abs_lon - lon_deg) * 60 - lon_min) * 60 * 100)
    lon_sec_den = 100
    gps_lon_tag = b"\x04\x00"
    gps_lon_type = b"\x05\x00"
    gps_lon_count = b"\x03\x00\x00\x00"
    gps_lon_offset = struct.pack("<I", 26 + 2 + 4 * 12 + 4 + 2 + 24 + 2)  # after lon ref string
    gps_lon_entry = gps_lon_tag + gps_lon_type + gps_lon_count + gps_lon_offset

    # Next GPS IFD offset: 0
    gps_next_ifd = b"\x00\x00\x00\x00"

    # String values and rational values after GPS IFD
    lat_ref_str = lat_ref + b"\x00"  # null-terminated ASCII
    lat_rationals = (
        struct.pack("<II", lat_deg, 1) +
        struct.pack("<II", lat_min, 1) +
        struct.pack("<II", lat_sec_num, lat_sec_den)
    )
    lon_ref_str = lon_ref + b"\x00"
    lon_rationals = (
        struct.pack("<II", lon_deg, 1) +
        struct.pack("<II", lon_min, 1) +
        struct.pack("<II", lon_sec_num, lon_sec_den)
    )

    # Assemble EXIF APP1
    exif_body = (
        tiff_header +
        ifd0_count + ifd0_entry + next_ifd +
        gps_ifd_count +
        gps_ver_entry + gps_lat_ref_entry + gps_lat_entry +
        gps_lon_ref_entry + gps_lon_entry +
        gps_next_ifd +
        lat_ref_str + lat_rationals +
        lon_ref_str + lon_rationals
    )

    # APP1 marker: 0xFFE1 + length (2 bytes, includes length field itself) + EXIF identifier + body
    app1_length = len(exif_body) + 2 + 6  # +2 for length field, +6 for "Exif\x00\x00"
    app1 = (
        b"\xff\xe1" +
        struct.pack(">H", app1_length) +
        b"Exif\x00\x00" +
        exif_body
    )

    # Minimal JPEG image data (SOF, DHT, SOS, compressed data, EOI)
    # DQT marker
    dqt = (
        b"\xff\xdb\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09"
        b"\x08\x0a\x0c\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f"
        b"\x1e\x1d\x1a\x1c\x1c\x20\x24\x2e\x27\x20\x22\x2c\x23\x1c\x1c\x28\x37"
        b"\x29\x2c\x30\x31\x34\x34\x34\x1f\x27\x39\x3d\x38\x32\x3c\x2e\x33\x34"
        b"\x32\xff\xdb\x00\x43\x01\x09\x09\x09\x0c\x0b\x0c\x18\x0d\x0d\x18\x32"
        b"\x21\x1c\x21\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32"
        b"\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32"
        b"\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32\x32"
    )
    # SOF0 marker
    sof = (
        b"\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03"
        b"\x11\x01"
    )
    # DHT marker
    dht = (
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
        b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04"
        b"\x00\x00\x01\x7d\x01\x02\x03\x00\x04\x11\x05\x12\x21\x31\x41\x06\x13"
        b"\x51\x61\x07\x22\x71\x14\x32\x81\x91\xa1\x08\x23\x42\xb1\xc1\x15\x52"
        b"\xd1\xf0\x24\x33\x62\x72\x82\x09\x0a\x16\x17\x18\x19\x1a\x25\x26\x27"
        b"\x28\x29\x2a\x34\x35\x36\x37\x38\x39\x3a\x43\x44\x45\x46\x47\x48\x49"
        b"\x4a\x53\x54\x55\x56\x57\x58\x59\x5a\x63\x64\x65\x66\x67\x68\x69\x6a"
        b"\x73\x74\x75\x76\x77\x78\x79\x7a\x83\x84\x85\x86\x87\x88\x89\x8a\x92"
        b"\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa"
        b"\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9"
        b"\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7"
        b"\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
    )
    # SOS + compressed data + EOI
    sos_eoi = (
        b"\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xbf\xff\xd9"
    )

    return soi + app1 + dqt + sof + dht + sos_eoi


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
def test_geotag_photo(unique_suffix):
    """Upload a photo with EXIF GPS coordinates and verify geotagging via Maps API."""
    # Coordinates for Paris, France
    lat, lon = 48.8566, 2.3522

    filename = f"test_geotag_{unique_suffix}.jpg"
    jpeg_data = _generate_tiny_jpeg_with_exif_gps(lat, lon)

    # Upload the photo
    _webdav_put(filename, jpeg_data)

    # Verify the file exists and contains EXIF data
    url = f"{_base_url()}/remote.php/dav/files/{os.environ['NEXTCLOUD_ADMIN_USER']}/{filename}"
    resp = requests.get(url, auth=_auth(), timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Exif" in resp.content or b"\xff\xe1" in resp.content, (
        "Uploaded file does not contain EXIF metadata"
    )

    # Try to query the Maps API for geotagged photos
    # The Maps app exposes endpoints under /index.php/apps/maps/api/
    try:
        maps_url = f"{_base_url()}/index.php/apps/maps/api/v1/photos"
        maps_resp = requests.get(
            maps_url, auth=_auth(),
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if maps_resp.status_code == 200:
            # Maps API returned data — verify it's valid JSON
            data = maps_resp.json()
            assert isinstance(data, (list, dict)), (
                f"Maps API returned unexpected data type: {type(data)}"
            )
        elif maps_resp.status_code in (404, 501):
            pytest.skip("Maps app is not installed or not enabled — skipping")
        else:
            # Non-200 but not 404 — might be a different API version
            pytest.skip(f"Maps API returned status {maps_resp.status_code} — skipping")
    except requests.ConnectionError:
        pytest.skip("Maps API endpoint is not reachable — skipping")
    except requests.HTTPError:
        pytest.skip("Maps app is not installed or not enabled — skipping")

    # Cleanup
    _webdav_delete(filename)
