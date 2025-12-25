"""Datetime utility functions."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)
