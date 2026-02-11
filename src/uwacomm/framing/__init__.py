"""Message framing utilities for uwacomm.

This module provides utilities for framing messages with length prefixes,
CRC checksums, and message IDs.
"""

from __future__ import annotations

from .basic import frame_message, frame_with_id, unframe_message, unframe_with_id

__all__ = [
    "frame_message",
    "unframe_message",
    "frame_with_id",
    "unframe_with_id",
]
