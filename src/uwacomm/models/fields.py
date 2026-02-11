"""Field type helpers and utilities.

This module provides convenience functions and type aliases for defining
message fields with DCCL-style constraints.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field
from pydantic.fields import FieldInfo


def BoundedInt(*, ge: int | None = None, le: int | None = None, **kwargs: Any) -> FieldInfo:
    """Create a bounded integer field.

    This is a convenience wrapper around Pydantic's Field() that ensures
    both ge= and le= constraints are set for compact encoding.

    Args:
        ge: Minimum value (inclusive)
        le: Maximum value (inclusive)
        **kwargs: Additional Field() arguments (description, default, etc.)

    Returns:
        Pydantic FieldInfo suitable for use as a field default/metadata.

    Example:
        >>> class Message(BaseMessage):
        ...     vehicle_id: Annotated[int, BoundedInt(ge=0, le=255)]
        ...     depth_cm: Annotated[int, BoundedInt(ge=0, le=10000)]
    """
    return cast(FieldInfo, Field(ge=ge, le=le, **kwargs))


def FixedBytes(*, length: int, **kwargs: Any) -> FieldInfo:
    """Create a fixed-length bytes field.

    Args:
        length: Exact length in bytes
        **kwargs: Additional Field() arguments

    Returns:
        Pydantic FieldInfo suitable for use as a field default/metadata.

    Example:
        >>> class Message(BaseMessage):
        ...     payload: Annotated[bytes, FixedBytes(length=16)]
    """
    return cast(FieldInfo, Field(min_length=length, max_length=length, **kwargs))


def FixedStr(*, length: int, **kwargs: Any) -> FieldInfo:
    """Create a fixed-length string field.

    Args:
        length: Exact length in characters
        **kwargs: Additional Field() arguments

    Returns:
        Pydantic FieldInfo suitable for use as a field default/metadata.

    Example:
        >>> class Message(BaseMessage):
        ...     callsign: Annotated[str, FixedStr(length=8)]
    """
    return cast(FieldInfo, Field(min_length=length, max_length=length, **kwargs))


def FixedInt(*, bits: int, signed: bool = False, **kwargs: Any) -> FieldInfo:
    """Create a fixed-size integer field.

    This is a convenience function to specify the bit width and signedness of an
    integer field. The actual constraints (ge=, le=) are not automatically applied,
    but the metadata can be used by the encoder to determine how to pack the field.

    Args:
        bits: Number of bits (e.g. 8, 16, 32)
        signed: Whether the integer is signed (default False)
        **kwargs: Additional Field() arguments

    Returns:
        Pydantic FieldInfo suitable for use as a field default/metadata.

    Example:
        >>> class Message(BaseMessage):
        ...     temperature: Annotated[int, FixedInt(bits=16, signed=True)]

    Note:
        ``bits`` and ``signed`` are stored as extra metadata for uwacomm. They do not
        enforce constraints by themselves, but may be used by the encoder.
    """
    return cast(FieldInfo, Field(json_schema_extra={"bits": bits, "signed": signed}, **kwargs))
