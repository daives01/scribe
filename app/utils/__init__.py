"""Utility modules."""

import json

from app.utils.exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    VoiceNotesException,
)
from app.utils.vector import serialize_vector

DEFAULT_TAGS = ["Idea", "Todo", "Work", "Personal", "Reference"]

__all__ = [
    "AuthenticationError",
    "NotFoundError",
    "PermissionDeniedError",
    "VoiceNotesException",
    "serialize_vector",
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
