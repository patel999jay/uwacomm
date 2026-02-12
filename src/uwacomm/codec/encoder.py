"""Compact binary encoder for Pydantic messages.

This module provides the encode() function that converts a Pydantic message
instance to compact binary format using DCCL-inspired bounded field optimization.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..exceptions import EncodeError
from .bitpack import BitPacker
from .schema import FieldSchema, MessageSchema


def encode(message: BaseModel, include_id: bool = False, routing: Any = None) -> bytes:
    """Encode a Pydantic message to compact binary format.

    This function uses schema introspection to determine the optimal bit packing
    for each field based on its constraints. Fields are encoded in declaration order
    with deterministic big-endian byte order.

    Args:
        message: Pydantic message instance to encode
        include_id: If True, prepend message ID for self-describing messages (Mode 2)
        routing: Optional RoutingHeader for multi-vehicle routing (Mode 3)

    Returns:
        Compact binary representation

    Raises:
        SchemaError: If message schema is invalid
        EncodeError: If a field value is invalid or out of bounds

    Examples:
        ```python
        from uwacomm import BaseMessage, BoundedInt, encode
        from uwacomm import RoutingHeader

        class Status(BaseMessage):
            vehicle_id: int = BoundedInt(ge=0, le=255)
            active: bool
            uwacomm_id: int = 10

        msg = Status(vehicle_id=42, active=True)

        # Mode 1: Point-to-point (maximum compression)
        data = encode(msg)

        # Mode 2: Self-describing (includes message ID)
        data = encode(msg, include_id=True)

        # Mode 3: Multi-vehicle routing
        data = encode(msg, routing=RoutingHeader(3, 0, 2))
        ```
    """
    # Introspect the schema
    schema = MessageSchema.from_model(type(message))

    # Create bit packer
    packer = BitPacker()

    # Mode 3: Routing header (includes source/dest/priority/ack)
    if routing is not None:
        # Encode routing header
        packer.write_uint(routing.source_id, 8)
        packer.write_uint(routing.dest_id, 8)
        packer.write_uint(routing.priority, 2)
        packer.write_bool(routing.ack_requested)
        # Routing always includes message ID
        include_id = True

    # Mode 2: Include message ID for self-describing messages
    if include_id:
        msg_id = getattr(type(message), 'uwacomm_id', None)
        if msg_id is None:
            raise EncodeError(
                f"{type(message).__name__} has no uwacomm_id attribute. "
                f"Self-describing messages require uwacomm_id."
            )
        if not isinstance(msg_id, int) or msg_id < 0 or msg_id > 32767:
            raise EncodeError(
                f"uwacomm_id must be an integer 0-32767, got {msg_id}"
            )

        # Variable-length ID encoding (varint-style):
        # - IDs 0-127: 1 byte with high bit = 0 (0xxxxxxx)
        # - IDs 128-32767: 2 bytes with high bit = 1 (1xxxxxxx xxxxxxxx)
        if msg_id < 128:
            # 1 byte: 0xxxxxxx (high bit = 0)
            packer.write_bool(False)  # High bit = 0
            packer.write_uint(msg_id, 7)  # 7 bits for ID
        elif msg_id < 32768:
            # 2 bytes: 1xxxxxxx xxxxxxxx (high bit = 1)
            packer.write_bool(True)  # High bit = 1
            packer.write_uint(msg_id, 15)  # 15 bits for ID
        else:
            raise EncodeError(
                f"uwacomm_id must be 0-32767, got {msg_id}"
            )

    # Encode each field
    for field_schema in schema.fields:
        field_value = getattr(message, field_schema.name)
        _encode_field(packer, field_schema, field_value)

    # Convert to bytes
    encoded = packer.to_bytes()

    # Check max_bytes constraint if present
    max_bytes = getattr(type(message), "uwacomm_max_bytes", None)
    if max_bytes is not None and len(encoded) > max_bytes:
        raise EncodeError(
            f"Encoded message size ({len(encoded)} bytes) exceeds " f"uwacomm_max_bytes={max_bytes}"
        )

    return encoded


def _encode_field(packer: BitPacker, field_schema: FieldSchema, value: Any) -> None:
    """Encode a single field value.

    Args:
        packer: BitPacker to write to
        field_schema: Schema information for the field
        value: Field value to encode

    Raises:
        EncodeError: If value is invalid
    """
    # Handle None (optional fields)
    if value is None:
        if field_schema.required:
            raise EncodeError(f"Field {field_schema.name} is required but got None")
        # For optional fields in v0.1.0, we don't support them yet
        raise EncodeError(f"Optional fields not supported in v0.1.0: {field_schema.name}")

    # Boolean
    if field_schema.python_type is bool:
        if not isinstance(value, bool):
            raise EncodeError(
                f"Field {field_schema.name}: expected bool, got {type(value).__name__}"
            )
        packer.write_bool(value)
        return

    # Enum
    if field_schema.enum_type is not None:
        if not isinstance(value, field_schema.enum_type):
            raise EncodeError(
                f"Field {field_schema.name}: expected {field_schema.enum_type.__name__}, "
                f"got {type(value).__name__}"
            )
        # Encode enum as its ordinal (0-indexed position in enum)
        enum_values = list(field_schema.enum_type)
        try:
            ordinal = enum_values.index(value)
        except ValueError as err:
            raise EncodeError(
                f"Field {field_schema.name}: {value} not in {field_schema.enum_type.__name__}"
            ) from err

        num_bits = field_schema.bits_required()
        packer.write_uint(ordinal, num_bits)
        return

    # Bounded integer
    if (
        field_schema.python_type is int
        and field_schema.min_value is not None
        and field_schema.max_value is not None
    ):
        if not isinstance(value, int):
            raise EncodeError(
                f"Field {field_schema.name}: expected int, got {type(value).__name__}"
            )

        min_val = int(field_schema.min_value)
        max_val = int(field_schema.max_value)

        if value < min_val or value > max_val:
            raise EncodeError(
                f"Field {field_schema.name}: value {value} out of bounds [{min_val}, {max_val}]"
            )

        # Encode as offset from min_value
        offset = value - min_val
        num_bits = field_schema.bits_required()
        packer.write_uint(offset, num_bits)
        return

    # Bounded float (DCCL-style: scale to integer)
    if field_schema.python_type is float:
        if not isinstance(value, (int, float)):
            raise EncodeError(
                f"Field {field_schema.name}: expected float, got {type(value).__name__}"
            )

        if field_schema.min_value is None or field_schema.max_value is None:
            raise EncodeError(
                f"Field {field_schema.name}: float requires min/max bounds"
            )

        precision = field_schema.precision or 0
        min_val = float(field_schema.min_value)
        max_val = float(field_schema.max_value)

        # Scale to integer
        scaled = round((value - min_val) * (10 ** precision))

        # Validate range
        max_scaled = round((max_val - min_val) * (10 ** precision))
        if scaled < 0 or scaled > max_scaled:
            raise EncodeError(
                f"Field {field_schema.name}: value {value} out of bounds "
                f"[{min_val}, {max_val}]"
            )

        # Encode as bounded integer
        num_bits = field_schema.bits_required()
        packer.write_uint(scaled, num_bits)
        return

    # Fixed-length bytes
    if field_schema.is_bytes and field_schema.max_length is not None:
        if not isinstance(value, bytes):
            raise EncodeError(
                f"Field {field_schema.name}: expected bytes, got {type(value).__name__}"
            )

        expected_length = field_schema.max_length
        if len(value) != expected_length:
            raise EncodeError(
                f"Field {field_schema.name}: expected {expected_length} bytes, "
                f"got {len(value)} bytes"
            )

        packer.write_bytes(value)
        return

    # Fixed-length string
    if field_schema.is_str and field_schema.max_length is not None:
        if not isinstance(value, str):
            raise EncodeError(
                f"Field {field_schema.name}: expected str, got {type(value).__name__}"
            )

        expected_length = field_schema.max_length
        if len(value) != expected_length:
            raise EncodeError(
                f"Field {field_schema.name}: expected {expected_length} characters, "
                f"got {len(value)} characters"
            )

        # Encode as UTF-8 bytes
        encoded_str = value.encode("utf-8")
        packer.write_bytes(encoded_str)
        return

    # Unsupported type
    raise EncodeError(
        f"Field {field_schema.name}: unsupported type {field_schema.python_type} "
        f"or missing constraints"
    )
