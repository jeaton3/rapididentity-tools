"""
Validation utilities for RapidIdentity API interactions.
"""

import re
from typing import Optional
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_username(username: str, min_length: int = 3, max_length: int = 32) -> bool:
    """
    Validate username format.

    Args:
        username: Username to validate
        min_length: Minimum username length (default: 3)
        max_length: Maximum username length (default: 32)

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(username, str):
        return False
    if len(username) < min_length or len(username) > max_length:
        return False
    # Allow alphanumeric, dots, hyphens, underscores
    pattern = r"^[a-zA-Z0-9._-]+$"
    return bool(re.match(pattern, username))


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format (basic validation for common formats).

    Args:
        phone: Phone number to validate

    Returns:
        True if valid, False otherwise
    """
    # Remove common separators
    cleaned = re.sub(r"[\s\-\(\)\.+]", "", phone)
    # Should be 7-15 digits
    return bool(re.match(r"^\d{7,15}$", cleaned))


def validate_required_fields(
    data: dict, required_fields: list
) -> tuple[bool, Optional[list]]:
    """
    Validate that required fields are present in data.

    Args:
        data: Dictionary to check
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing = [field for field in required_fields if field not in data or data[field] is None]
    return len(missing) == 0, missing if missing else None
