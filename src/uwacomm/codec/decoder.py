"""Compact binary decoder for Pydantic messages.

This module provides the decode() function that converts compact binary data
back to a Pydantic message instance.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from ..exceptions import DecodeError
from .bitpack import BitUnpacker
from .schema import FieldSchema, MessageSchema

T = TypeVar("T", bound=BaseModel)


def decode(
    message_class: type[T], data: bytes, include_id: bool = False, routing: bool = False
) -> T | tuple[Any, T]:
    """Decode compact binary data to a Pydantic message.

    This function uses schema introspection to decode fields in the same order
    and format as they were encoded.

    Args:
        message_class: Pydantic message class to decode to
        data: Binary data to decode
        include_id: If True, expect message ID prefix for self-describing messages (Mode 2)
        routing: If True, expect routing header prefix (Mode 3)

    Returns:
        Decoded message instance (Mode 1/2) or tuple (RoutingHeader, message) (Mode 3)

    Raises:
        SchemaError: If message schema is invalid
        DecodeError: If data is truncated, corrupted, or doesn't match schema

    Examples:
        ```python
        from uwacomm import BaseMessage, BoundedInt, encode, decode

        class Status(BaseMessage):
            vehicle_id: int = BoundedInt(ge=0, le=255)
            active: bool
            uwacomm_id: int = 10

        msg = Status(vehicle_id=42, active=True)
        data = encode(msg)

        # Mode 1: Point-to-point
        decoded = decode(Status, data)

        # Mode 2: Self-describing (with ID validation)
        decoded = decode(Status, data, include_id=True)

        # Mode 3: Multi-vehicle routing
        routing, decoded = decode(Status, data, routing=True)
        print(f"From vehicle {routing.source_id}")
        ```
    """
    # Introspect the schema
    schema = MessageSchema.from_model(message_class)

    # Create bit unpacker
    unpacker = BitUnpacker(data)

    routing_header = None

    # Mode 3: Decode routing header
    if routing:
        try:
            source_id = unpacker.read_uint(8)
            dest_id = unpacker.read_uint(8)
            priority = unpacker.read_uint(2)
            ack_requested = unpacker.read_bool()

            # Import here to avoid circular dependency
            from ..routing import RoutingHeader

            routing_header = RoutingHeader(source_id, dest_id, priority, ack_requested)

            # Routing always includes message ID
            include_id = True
        except IndexError as e:
            raise DecodeError(f"Truncated data while decoding routing header: {e}") from e

    # Mode 2: Decode and validate message ID
    if include_id:
        try:
            # Read high bit to determine ID size
            # 1 byte: 0xxxxxxx (7 bits for ID, range 0-127)
            # 2 bytes: 1xxxxxxx xxxxxxxx (15 bits for ID, range 0-32767)
            high_bit = unpacker.read_bool()
            decoded_id = unpacker.read_uint(7) if not high_bit else unpacker.read_uint(15)

            # Validate against expected message class ID
            expected_id = getattr(message_class, "uwacomm_id", None)
            if expected_id is not None and decoded_id != expected_id:
                raise DecodeError(
                    f"Message ID mismatch: decoded {decoded_id}, expected {expected_id} "
                    f"for {message_class.__name__}"
                )
        except IndexError as e:
            raise DecodeError(f"Truncated data while decoding message ID: {e}") from e

    # Decode each field
    field_values: dict[str, Any] = {}
    for field_schema in schema.fields:
        try:
            value = _decode_field(unpacker, field_schema)
            field_values[field_schema.name] = value
        except IndexError as e:
            raise DecodeError(
                f"Truncated data while decoding field {field_schema.name}: {e}"
            ) from e
        except Exception as e:
            raise DecodeError(f"Error decoding field {field_schema.name}: {e}") from e

    # Create message instance
    try:
        decoded_message = message_class(**field_values)

        # Return with routing header if Mode 3
        if routing_header is not None:
            return (routing_header, decoded_message)

        return decoded_message
    except Exception as e:
        raise DecodeError(f"Failed to construct {message_class.__name__}: {e}") from e


def _decode_field(unpacker: BitUnpacker, field_schema: FieldSchema) -> Any:
    """Decode a single field value.

    Args:
        unpacker: BitUnpacker to read from
        field_schema: Schema information for the field

    Returns:
        Decoded field value

    Raises:
        DecodeError: If data is invalid
        IndexError: If data is truncated
    """
    # Boolean
    if field_schema.python_type is bool:
        return unpacker.read_bool()

    # Enum
    if field_schema.enum_type is not None:
        num_bits = field_schema.bits_required()
        ordinal = unpacker.read_uint(num_bits)

        # Convert ordinal back to enum value
        enum_values = list(field_schema.enum_type)
        if ordinal >= len(enum_values):
            raise DecodeError(
                f"Field {field_schema.name}: invalid enum ordinal {ordinal} "
                f"(only {len(enum_values)} values)"
            )

        return enum_values[ordinal]

    # Bounded integer
    if (
        field_schema.python_type is int
        and field_schema.min_value is not None
        and field_schema.max_value is not None
    ):
        num_bits = field_schema.bits_required()
        offset = unpacker.read_uint(num_bits)

        # Convert offset back to actual value
        min_val = int(field_schema.min_value)
        value = min_val + offset

        # Validate bounds (defensive check)
        max_val = int(field_schema.max_value)
        if value > max_val:
            raise DecodeError(
                f"Field {field_schema.name}: decoded value {value} exceeds max {max_val}"
            )

        return value

    # Bounded float (DCCL-style: descale from integer)
    if field_schema.python_type is float:
        if field_schema.min_value is None or field_schema.max_value is None:
            raise DecodeError(f"Field {field_schema.name}: float requires min/max bounds")

        precision = field_schema.precision or 0
        min_float = float(field_schema.min_value)
        max_float = float(field_schema.max_value)

        # Decode scaled integer
        max_scaled = round((max_float - min_float) * (10**precision))
        num_bits = field_schema._bits_for_bounded_int(0, max_scaled)
        scaled = unpacker.read_uint(num_bits)

        # Descale to float
        value = min_float + (scaled / (10**precision))

        # Validate bounds (defensive check)
        if value < min_float or value > max_float:
            raise DecodeError(
                f"Field {field_schema.name}: decoded value {value} out of bounds "
                f"[{min_float}, {max_float}]"
            )

        return value

    # Fixed-length bytes
    if field_schema.is_bytes and field_schema.max_length is not None:
        num_bytes = field_schema.max_length
        return unpacker.read_bytes(num_bytes)

    # Fixed-length string
    if field_schema.is_str and field_schema.max_length is not None:
        num_bytes = field_schema.max_length
        raw_bytes = unpacker.read_bytes(num_bytes)

        # Decode UTF-8
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise DecodeError(f"Field {field_schema.name}: invalid UTF-8 encoding: {e}") from e

    # Unsupported type
    raise DecodeError(
        f"Field {field_schema.name}: unsupported type {field_schema.python_type} "
        f"or missing constraints"
    )
