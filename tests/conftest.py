"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_payload() -> bytes:
    """Sample binary payload for testing."""
    return b"Hello, underwater world!"


@pytest.fixture
def sample_message_id() -> int:
    """Sample message ID for testing."""
    return 42
