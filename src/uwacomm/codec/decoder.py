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


def decode(message_class: type[T], data: bytes) -> T:
    """Decode compact binary data to a Pydantic message.

    This function uses schema introspection to decode fields in the same order
    and format as they were encoded.

    Args:
        message_class: Pydantic message class to decode to
        data: Binary data to decode

    Returns:
        Decoded message instance

    Raises:
        SchemaError: If message schema is invalid
        DecodeError: If data is truncated, corrupted, or doesn't match schema

    Example:
        >>> data = encode(msg)
        >>> decoded = decode(Status, data)
    """
    # Introspect the schema
    schema = MessageSchema.from_model(message_class)

    # Create bit unpacker
    unpacker = BitUnpacker(data)

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
        return message_class(**field_values)
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
