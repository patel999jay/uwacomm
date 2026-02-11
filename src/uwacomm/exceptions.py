"""Exception hierarchy for uwacomm.

This module defines all custom exceptions used throughout the package.
All exceptions inherit from UwacommError for easy catching of any uwacomm-specific error.
"""

from __future__ import annotations


class UwacommError(Exception):
    """Base exception for all uwacomm errors."""

    pass


# Backward compatibility alias
PyDCCLError = UwacommError


class SchemaError(UwacommError):
    """Raised when a message schema is invalid or incompatible.

    Examples:
        - Field constraints are invalid (e.g., min > max)
        - Unsupported field type
        - Missing required DCCL metadata
        - Conflicting configuration
    """

    pass


class EncodeError(UwacommError):
    """Raised when encoding a message fails.

    Examples:
        - Value out of bounds for a bounded field
        - Invalid enum value
        - Field type mismatch
        - Message exceeds max_bytes constraint
    """

    pass


class DecodeError(UwacommError):
    """Raised when decoding binary data fails.

    Examples:
        - Truncated data (insufficient bytes)
        - Invalid field value (out of bounds, unknown enum)
        - Corrupted data structure
        - Schema version mismatch
    """

    pass


class FramingError(UwacommError):
    """Raised when framing operations fail.

    Examples:
        - CRC checksum mismatch
        - Invalid frame structure (missing header/footer)
        - Length field inconsistency
        - Truncated frame
    """

    pass
