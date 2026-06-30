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


def VarBytes(*, max_length: int, **kwargs: Any) -> FieldInfo:
    """Create a variable-length bytes field (0 to max_length bytes).

    A compact length prefix is written before the data, consuming only
    ceil(log2(max_length + 1)) bits.

    Args:
        max_length: Maximum number of bytes
        **kwargs: Additional Field() arguments

    Example:
        >>> class Msg(BaseMessage):
        ...     payload: bytes = VarBytes(max_length=64)
    """
    return cast(FieldInfo, Field(max_length=max_length, **kwargs))


def VarStr(*, max_length: int, **kwargs: Any) -> FieldInfo:
    """Create a variable-length ASCII string field (0 to max_length characters).

    Only ASCII characters are supported (1 byte per char). Non-ASCII raises
    EncodeError. A compact length prefix precedes the encoded characters.

    Args:
        max_length: Maximum number of characters (= bytes, ASCII only)
        **kwargs: Additional Field() arguments

    Example:
        >>> class Msg(BaseMessage):
        ...     name: str = VarStr(max_length=16)
    """
    return cast(FieldInfo, Field(max_length=max_length, **kwargs))


def VarList(
    *,
    max_length: int,
    item_ge: int | float | None = None,
    item_le: int | float | None = None,
    item_precision: int | None = None,
    **kwargs: Any,
) -> FieldInfo:
    """Create a variable-length list field.

    Supports lists of booleans, bounded integers, or bounded floats.
    A compact count prefix precedes the encoded elements.

    Args:
        max_length: Maximum number of elements
        item_ge: Minimum value for each element (int/float)
        item_le: Maximum value for each element (int/float)
        item_precision: Decimal places for float elements (omit for int)
        **kwargs: Additional Field() arguments

    Examples:
        >>> class Msg(BaseMessage):
        ...     flags: List[bool] = VarList(max_length=8)
        ...     depths: List[int] = VarList(max_length=16, item_ge=0, item_le=1000)
        ...     temps: List[float] = VarList(
        ...         max_length=4, item_ge=-20.0, item_le=40.0, item_precision=1
        ...     )
    """
    extra: dict[str, Any] = {"varlist": True}
    if item_ge is not None:
        extra["item_ge"] = item_ge
    if item_le is not None:
        extra["item_le"] = item_le
    if item_precision is not None:
        extra["item_precision"] = item_precision
    return cast(FieldInfo, Field(max_length=max_length, json_schema_extra=extra, **kwargs))


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
