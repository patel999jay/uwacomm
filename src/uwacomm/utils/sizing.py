"""Message size calculation utilities.

This module provides functions to calculate the encoded size of messages
without actually encoding them.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..codec.schema import MessageSchema


def encoded_size(message_or_class: BaseModel | type[BaseModel]) -> int:
    """Calculate the encoded size of a message in bytes.

    This function can take either a message instance or a message class.
    The size is calculated from the schema and does not depend on field values
    (except for variable-length fields, which are not yet supported in v0.1.0).

    Args:
        message_or_class: Message instance or class to calculate size for

    Returns:
        Size in bytes (rounded up to nearest byte)

    Raises:
        SchemaError: If schema is invalid or contains unsupported features

    Example:
        >>> class Status(BaseMessage):
        ...     vehicle_id: int = Field(ge=0, le=255)
        ...     active: bool
        >>> encoded_size(Status)
        2  # 8 bits + 1 bit = 9 bits = 2 bytes
        >>> msg = Status(vehicle_id=42, active=True)
        >>> encoded_size(msg)
        2
    """
    # Get the class if we were passed an instance
    if isinstance(message_or_class, BaseModel):
        message_class = type(message_or_class)
    else:
        message_class = message_or_class

    # Introspect schema
    schema = MessageSchema.from_model(message_class)

    # Calculate total size
    return schema.total_bytes()


def encoded_bits(message_or_class: BaseModel | type[BaseModel]) -> int:
    """Calculate the encoded size of a message in bits.

    Args:
        message_or_class: Message instance or class to calculate size for

    Returns:
        Size in bits

    Raises:
        SchemaError: If schema is invalid or contains unsupported features

    Example:
        >>> encoded_bits(Status)
        9  # 8 bits + 1 bit
    """
    # Get the class if we were passed an instance
    if isinstance(message_or_class, BaseModel):
        message_class = type(message_or_class)
    else:
        message_class = message_or_class

    # Introspect schema
    schema = MessageSchema.from_model(message_class)

    # Calculate total bits
    return schema.total_bits()


def field_sizes(message_or_class: BaseModel | type[BaseModel]) -> dict[str, int]:
    """Get the size in bits of each field in a message.

    Args:
        message_or_class: Message instance or class to analyze

    Returns:
        Dictionary mapping field names to their size in bits

    Raises:
        SchemaError: If schema is invalid or contains unsupported features

    Example:
        >>> sizes = field_sizes(Status)
        >>> sizes
        {'vehicle_id': 8, 'active': 1}
    """
    # Get the class if we were passed an instance
    if isinstance(message_or_class, BaseModel):
        message_class = type(message_or_class)
    else:
        message_class = message_or_class

    # Introspect schema
    schema = MessageSchema.from_model(message_class)

    # Calculate size for each field
    return {field.name: field.bits_required() for field in schema.fields}
