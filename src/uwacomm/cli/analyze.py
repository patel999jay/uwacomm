"""Message analysis CLI command."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any

from ..codec.schema import MessageSchema
from ..models.base import BaseMessage
from ..utils.sizing import encoded_size, field_sizes


def analyze_file(file_path: Path) -> None:
    """Analyze all BaseMessage classes in a Python file.

    Args:
        file_path: Path to Python file containing message definitions
    """
    # Load the Python module
    spec = importlib.util.spec_from_file_location("user_module", file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["user_module"] = module
    spec.loader.exec_module(module)

    # Find all BaseMessage subclasses
    message_classes = []
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if obj is not BaseMessage and issubclass(obj, BaseMessage):
            # Only include classes defined in this file (not imported)
            if obj.__module__ == "user_module":
                message_classes.append(obj)

    if not message_classes:
        print(f"No BaseMessage classes found in {file_path}")
        return

    # Print header
    print("|" * 7, "uwacomm: Underwater Communications Codec", "|" * 7)
    print(f"{len(message_classes)} message{'s' if len(message_classes) != 1 else ''} loaded.")
    print("Field sizes are in bits unless otherwise noted.")
    print()

    # Analyze each message class
    for msg_class in message_classes:
        analyze_message_class(msg_class)


def analyze_message_class(msg_class: type[BaseMessage]) -> None:
    """Analyze a single message class and print detailed breakdown.

    Args:
        msg_class: Message class to analyze
    """
    # Get message ID if present
    msg_id = getattr(msg_class, "uwacomm_id", None)
    max_bytes = getattr(msg_class, "uwacomm_max_bytes", None)

    # Header line
    if msg_id is not None:
        print(f"{'=' * 19} {msg_id}: {msg_class.__name__} {'=' * 19}")
    else:
        print(f"{'=' * 19} {msg_class.__name__} {'=' * 19}")

    # Get schema and field sizes
    schema = MessageSchema.from_model(msg_class)

    # Create a sample instance to get field sizes
    # Build kwargs with default values
    sample_kwargs: dict[str, Any] = {}
    for field_schema in schema.fields:
        if field_schema.python_type is bool:
            sample_kwargs[field_schema.name] = False
        elif field_schema.enum_type is not None:
            # Use first enum value
            sample_kwargs[field_schema.name] = list(field_schema.enum_type)[0]
        elif field_schema.min_value is not None:
            sample_kwargs[field_schema.name] = field_schema.min_value
        elif field_schema.is_bytes and field_schema.max_length is not None:
            sample_kwargs[field_schema.name] = b"\x00" * field_schema.max_length
        elif field_schema.is_str and field_schema.max_length is not None:
            sample_kwargs[field_schema.name] = "x" * field_schema.max_length
        else:
            sample_kwargs[field_schema.name] = 0

    try:
        sample_msg = msg_class(**sample_kwargs)
        sizes = field_sizes(sample_msg)
        total_bits = sum(sizes.values())
        total_bytes = encoded_size(sample_msg)
    except Exception:
        # Fallback if we can't create a sample
        total_bits = sum(field_schema.bits_required() for field_schema in schema.fields)
        total_bytes = (total_bits + 7) // 8
        sizes = {field_schema.name: field_schema.bits_required() for field_schema in schema.fields}

    # Calculate padding
    padding_bits = (total_bytes * 8) - total_bits

    # Size summary
    print(f"Actual maximum size of message: {total_bytes} bytes / {total_bytes * 8} bits")
    if msg_id is not None:
        print(f"        uwacomm.id head{'.' * 24}{8} (if present)")
    print(f"        body{'.' * 34}{total_bits}")
    if padding_bits > 0:
        print(f"        padding to full byte{'.' * 19}{padding_bits}")
    if max_bytes is not None:
        print(f"Allowed maximum size of message: {max_bytes} bytes / {max_bytes * 8} bits")
    print()

    # Header section
    if msg_id is not None:
        print(f"{'-' * 27} Header {'-' * 27}")
        print(f"uwacomm.id{'.' * 44}{8} bits")
        print()

    # Body section
    print(f"{'-' * 28} Body {'-' * 28}")
    print(f"{msg_class.__name__}{'.' * (54 - len(msg_class.__name__))}{total_bits} bits")

    # Field-by-field breakdown
    for i, field_schema in enumerate(schema.fields, 1):
        field_name = field_schema.name
        bits = sizes.get(field_name, field_schema.bits_required())

        # Build field info string
        info_parts = []

        # Add bounds for integers
        if field_schema.min_value is not None and field_schema.max_value is not None:
            info_parts.append(f"[{field_schema.min_value}-{field_schema.max_value}]")

        # Add enum info
        if field_schema.enum_type is not None:
            num_values = len(list(field_schema.enum_type))
            info_parts.append(f"(enum: {num_values} values)")

        # Format field line
        field_info = " ".join(info_parts) if info_parts else ""
        field_desc = f"{i}. {field_name}"

        if field_info:
            # Calculate dots needed for alignment
            dots_needed = 54 - len(field_desc) - len(str(bits)) - len(" bits") - len(field_info) - 1
            dots = "." * max(1, dots_needed)
            print(f"        {field_desc}{dots}{bits} bits {field_info}")
        else:
            dots_needed = 54 - len(field_desc) - len(str(bits)) - len(" bits")
            dots = "." * max(1, dots_needed)
            print(f"        {field_desc}{dots}{bits} bits")

    print()

    # Summary section
    print(f"{'=' * 24} Summary {'=' * 24}")

    # Compression estimate (vs JSON)
    # Rough estimate: JSON ~= 20 bytes per field + field name lengths
    json_estimate = sum(20 + len(f.name) for f in schema.fields)
    compression_ratio = json_estimate / total_bytes if total_bytes > 0 else 1.0
    print(f"Compression vs JSON: {compression_ratio:.1f}x smaller")

    # Transmission time estimate @ 80 bps (typical acoustic modem)
    transmission_time = (total_bytes * 8) / 80.0
    print(f"Estimated transmission time @ 80 bps: {transmission_time:.1f} seconds")

    print()
