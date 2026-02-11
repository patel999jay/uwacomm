"""Field type helpers and utilities.

This module provides convenience functions and type aliases for defining
message fields with DCCL-style constraints.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field


def BoundedInt(min_val: int, max_val: int, **kwargs) -> int:  # type: ignore[valid-type]
    """Create a bounded integer field.

    This is a convenience wrapper around Pydantic's Field() that ensures
    both ge= and le= constraints are set for compact encoding.

    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        **kwargs: Additional Field() arguments (description, default, etc.)

    Returns:
        Annotated type suitable for use as a field annotation

    Example:
        >>> class Message(BaseMessage):
        ...     vehicle_id: Annotated[int, BoundedInt(0, 255)]
        ...     depth_cm: Annotated[int, BoundedInt(0, 10000)]
    """
    return Field(ge=min_val, le=max_val, **kwargs)  # type: ignore[return-value]


def FixedBytes(length: int, **kwargs) -> bytes:  # type: ignore[valid-type]
    """Create a fixed-length bytes field.

    Args:
        length: Exact length in bytes
        **kwargs: Additional Field() arguments

    Returns:
        Annotated type suitable for use as a field annotation

    Example:
        >>> class Message(BaseMessage):
        ...     payload: Annotated[bytes, FixedBytes(16)]
    """
    return Field(min_length=length, max_length=length, **kwargs)  # type: ignore[return-value]


def FixedStr(length: int, **kwargs) -> str:  # type: ignore[valid-type]
    """Create a fixed-length string field.

    Args:
        length: Exact length in characters
        **kwargs: Additional Field() arguments

    Returns:
        Annotated type suitable for use as a field annotation

    Example:
        >>> class Message(BaseMessage):
        ...     callsign: Annotated[str, FixedStr(8)]
    """
    return Field(min_length=length, max_length=length, **kwargs)  # type: ignore[return-value]
