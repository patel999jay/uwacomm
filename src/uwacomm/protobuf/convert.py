"""Protobuf schema generation and conversion utilities.

This module provides utilities to generate .proto schema files from Pydantic models
and document conversion strategies between Pydantic and Protobuf.
"""

from __future__ import annotations

import enum
from typing import cast

from pydantic import BaseModel

from ..codec.schema import MessageSchema
from ..exceptions import SchemaError


def to_proto_schema(
    message_class: type[BaseModel],
    *,
    package: str = "",
    syntax: str = "proto3",
) -> str:
    """Generate a Protobuf .proto schema from a Pydantic message class.

    This generates a text .proto file that can be used with protoc or other
    Protobuf tools. The schema is informational and does NOT use the same
    wire format as uwacomm's compact encoding.

    Args:
        message_class: Pydantic message class to convert
        package: Optional Protobuf package name
        syntax: Protobuf syntax version ("proto2" or "proto3")

    Returns:
        .proto schema as a string

    Raises:
        SchemaError: If message contains unsupported types

    Example:
        >>> class Status(BaseMessage):
        ...     vehicle_id: int = Field(ge=0, le=255)
        ...     active: bool
        >>> proto = to_proto_schema(Status, package="underwater")
        >>> print(proto)
        syntax = "proto3";
        package underwater;
        ...
    """
    schema = MessageSchema.from_model(message_class)

    lines = []

    # Header
    lines.append(f'syntax = "{syntax}";')
    if package:
        lines.append(f"package {package};")
    lines.append("")

    # Generate enum definitions first
    enum_types = set()
    for field in schema.fields:
        if field.enum_type is not None:
            enum_types.add(field.enum_type)

    for enum_type in enum_types:
        lines.extend(_enum_to_proto(enum_type))
        lines.append("")

    # Message definition
    lines.append(f"message {message_class.__name__} {{")

    # Fields
    for i, field in enumerate(schema.fields, start=1):
        proto_type = _python_type_to_proto(field)
        field_comment = _field_comment(field)

        if field_comment:
            lines.append(f"  // {field_comment}")

        lines.append(f"  {proto_type} {field.name} = {i};")

    lines.append("}")

    return "\n".join(lines)


def _python_type_to_proto(field_schema) -> str:  # type: ignore[no-untyped-def]
    """Convert a Python type to Protobuf type.

    Args:
        field_schema: FieldSchema to convert

    Returns:
        Protobuf type string

    Raises:
        SchemaError: If type is not supported
    """
    # Boolean
    if field_schema.python_type is bool:
        return "bool"

    # Enum
    if field_schema.enum_type is not None:
        return cast(str, field_schema.enum_type.__name__)

    # Integer (use smallest matching protobuf type)
    if field_schema.python_type is int:
        if field_schema.min_value is not None and field_schema.max_value is not None:
            min_val = int(field_schema.min_value)
            max_val = int(field_schema.max_value)

            # Unsigned types
            if min_val >= 0:
                if max_val <= 2**32 - 1:
                    return "uint32"
                else:
                    return "uint64"
            # Signed types
            else:
                if min_val >= -(2**31) and max_val <= 2**31 - 1:
                    return "int32"
                else:
                    return "int64"

        # No bounds, default to int32
        return "int32"

    # Bytes
    if field_schema.is_bytes:
        return "bytes"

    # String
    if field_schema.is_str:
        return "string"

    # Float (not supported in v0.1.0, but included for future)
    if field_schema.python_type is float:
        return "double"

    raise SchemaError(f"Cannot convert type {field_schema.python_type} to Protobuf type")


def _field_comment(field_schema) -> str:  # type: ignore[no-untyped-def]
    """Generate a comment documenting field constraints.

    Args:
        field_schema: FieldSchema to document

    Returns:
        Comment string (without leading //)
    """
    comments = []

    # Bounds
    if field_schema.min_value is not None and field_schema.max_value is not None:
        comments.append(f"Range: [{field_schema.min_value}, {field_schema.max_value}]")

    # Length
    if field_schema.max_length is not None:
        if field_schema.min_length == field_schema.max_length:
            comments.append(f"Fixed length: {field_schema.max_length}")
        else:
            comments.append(f"Length: [{field_schema.min_length or 0}, {field_schema.max_length}]")

    # Bits required (uwacomm-specific)
    try:
        bits = field_schema.bits_required()
        comments.append(f"uwacomm: {bits} bits")
    except:  # noqa: E722
        pass

    return " | ".join(comments)


def _enum_to_proto(enum_type: type[enum.Enum]) -> list[str]:
    """Convert a Python enum to Protobuf enum definition.

    Args:
        enum_type: Enum class to convert

    Returns:
        List of lines for the enum definition
    """
    lines = [f"enum {enum_type.__name__} {{"]

    for i, member in enumerate(enum_type):
        # Protobuf enums must start with 0
        lines.append(f"  {member.name} = {i};")

    lines.append("}")
    return lines


def proto_conversion_notes() -> str:
    """Return documentation on Pydantic <-> Protobuf conversion strategies.

    Returns:
        Documentation string
    """
    return """
Pydantic <-> Protobuf Conversion Notes
======================================

## Schema Generation (Pydantic -> .proto)

The `to_proto_schema()` function generates .proto files from Pydantic models.
This is useful for:
- Documentation and interoperability
- Generating Protobuf bindings for other languages
- Schema exchange with non-Python systems

**Important:** The generated .proto schema is NOT compatible with uwacomm's
compact binary encoding. Use it for schema documentation only.

## Wire Format Compatibility

### uwacomm Compact Encoding
- Bounded fields use minimal bits (e.g., 0-255 = 8 bits)
- No field tags or wire types
- Big-endian byte order
- Designed for bandwidth-constrained channels

### Protobuf Wire Format
- Uses variable-length field tags
- Supports schema evolution (adding/removing fields)
- Little-endian varints
- Optimized for flexibility, not minimal size

**These formats are NOT compatible.** Choose based on your needs:
- Use uwacomm encoding for underwater/acoustic channels
- Use Protobuf encoding for general-purpose serialization

## Object Conversion (Future v0.2.0+)

Future versions may support:
- `pydantic_to_protobuf(msg)` - Convert Pydantic instance to Protobuf message
- `protobuf_to_pydantic(pb_msg)` - Convert Protobuf message to Pydantic instance

This would enable workflows like:
1. Define schema in Pydantic
2. Encode with uwacomm for acoustic transmission
3. Convert to Protobuf for logging/ROS2 integration

## Example Usage

```python
from uwacomm import BaseMessage, to_proto_schema
from pydantic import Field

class StatusReport(BaseMessage):
    vehicle_id: int = Field(ge=0, le=255)
    depth_cm: int = Field(ge=0, le=10000)
    active: bool

# Generate .proto schema
proto_schema = to_proto_schema(StatusReport, package="underwater")

# Save to file
with open("status_report.proto", "w") as f:
    f.write(proto_schema)
```

## Limitations (v0.1.0)

- No automatic object conversion (Pydantic <-> Protobuf instances)
- No Protobuf wire format encoding
- .proto generation is one-way (Pydantic -> .proto only)
"""
