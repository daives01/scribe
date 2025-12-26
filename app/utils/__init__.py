"""Utility modules."""

import json

from app.utils.auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.utils.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServiceError,
    VoiceNotesException,
)

DEFAULT_TAGS = ["Idea", "Todo", "Work", "Personal", "Reference"]

__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_password_hash",
    "verify_password",
    "AuthenticationError",
    "NotFoundError",
    "ServiceError",
    "VoiceNotesException",
    "DEFAULT_TAGS",
    "get_custom_tags",
]


def get_custom_tags(custom_tags_json: str) -> list[str]:
    """
    Parse custom tags JSON or return defaults.

    Args:
        custom_tags_json: JSON string of tags

    Returns:
        List of tag strings
    """
    try:
        return json.loads(custom_tags_json)
    except json.JSONDecodeError:
        return DEFAULT_TAGS.copy()
