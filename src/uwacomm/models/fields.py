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


def BoundedFloat(*, min: float, max: float, precision: int = 2, **kwargs: Any) -> FieldInfo:
    """Create a bounded float field for efficient encoding.

    Floats are encoded as scaled integers using DCCL-style compression:
    - Scale to integer: int_value = round((value - min) * 10^precision)
    - Encode as bounded integer

    This dramatically reduces bandwidth compared to IEEE 754 floats/doubles.

    Args:
        min: Minimum value (inclusive)
        max: Maximum value (inclusive)
        precision: Number of decimal places (0-6), default 2
        **kwargs: Additional Field() arguments

    Returns:
        Pydantic FieldInfo suitable for use as a field default/metadata.

    Examples:
        >>> class Message(BaseMessage):
        ...     # Depth sensor: -5.00 to 100.00 m in cm resolution
        ...     depth: Annotated[float, BoundedFloat(min=-5.0, max=100.0, precision=2)]
        ...     # 10,500 distinct values = 14 bits (vs 64 bits for double)
        ...
        ...     # GPS coordinates: -90.000000 to 90.000000 degrees
        ...     latitude: Annotated[float, BoundedFloat(min=-90.0, max=90.0, precision=6)]
        ...     # 180,000,000 values = 28 bits (vs 64 bits for double)
        ...
        ...     # Temperature: -20.0 to 40.0°C in 0.1°C precision
        ...     temperature: Annotated[float, BoundedFloat(min=-20.0, max=40.0, precision=1)]

    Bandwidth comparison:
        - IEEE 754 double: 64 bits
        - IEEE 754 float: 32 bits
        - Bounded float (precision=2, range=100): ~14 bits
        - Savings: 78% vs double, 56% vs float

    Note:
        Precision must be 0-6. Higher precision requires more bits for encoding.
    """
    if not 0 <= precision <= 6:
        raise ValueError("precision must be 0-6")

    return cast(
        FieldInfo, Field(ge=min, le=max, json_schema_extra={"precision": precision}, **kwargs)
    )
