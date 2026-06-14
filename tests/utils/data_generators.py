"""
Test data generators for Nextcloud deployment tests.
"""

from __future__ import annotations

import os
import random
import string
import uuid
from typing import Dict


def generate_random_file(size_bytes: int) -> bytes:
    """Generate random binary content of the given size."""
    return os.urandom(size_bytes)


def generate_test_user_data(prefix: str = "testuser") -> Dict[str, str]:
    """Generate random test user credentials and profile data."""
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    return {
        "username": username,
        "password": f"TestPass_{suffix}!",
        "display_name": f"Test User {suffix}",
        "email": f"{username}@test.example.com",
    }


def generate_test_filename(extension: str = "txt") -> str:
    """Generate a random filename with the given extension."""
    suffix = uuid.uuid4().hex[:12]
    return f"testfile_{suffix}.{extension.lstrip('.')}"
