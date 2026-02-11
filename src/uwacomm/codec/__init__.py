"""Compact binary codec for uwacomm.

This module provides encoding and decoding functionality for compact binary
messages using DCCL-inspired bounded field optimization.
"""

from __future__ import annotations

from .decoder import decode
from .encoder import encode
from .schema import FieldSchema, MessageSchema

__all__ = [
    "encode",
    "decode",
    "MessageSchema",
    "FieldSchema",
]
