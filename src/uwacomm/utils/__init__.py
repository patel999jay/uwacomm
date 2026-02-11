"""Utility functions for uwacomm.

This module provides CRC checksums, size calculation, and other utilities.
"""

from __future__ import annotations

from .crc import crc16, crc16_bytes, crc32, crc32_bytes, verify_crc16, verify_crc32
from .sizing import encoded_bits, encoded_size, field_sizes

__all__ = [
    # CRC functions
    "crc16",
    "crc16_bytes",
    "crc32",
    "crc32_bytes",
    "verify_crc16",
    "verify_crc32",
    # Sizing functions
    "encoded_size",
    "encoded_bits",
    "field_sizes",
]
