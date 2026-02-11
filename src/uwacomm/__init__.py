"""uwacomm: Underwater Communications Codec

A Python library for compact binary encoding inspired by DCCL (Dynamic Compact
Control Language) from GobySoft. Designed for bandwidth-constrained communications,
particularly underwater acoustic modems.

Inspired by: https://github.com/GobySoft/dccl

Key Features:
- Pydantic-based message modeling
- DCCL-style bounded field optimization
- Pure Python implementation (no C++ dependencies)
- Modern Python API design

Quick Start:
    >>> from uwacomm import BaseMessage, encode, decode
    >>> from pydantic import Field
    >>>
    >>> class StatusReport(BaseMessage):
    ...     vehicle_id: int = Field(ge=0, le=255)
    ...     depth_cm: int = Field(ge=0, le=10000)
    ...     battery_pct: int = Field(ge=0, le=100)
    ...     active: bool
    >>>
    >>> msg = StatusReport(vehicle_id=42, depth_cm=1500, battery_pct=87, active=True)
    >>> data = encode(msg)
    >>> decoded = decode(StatusReport, data)

For more information, see: https://github.com/patel999jay/uwacomm
"""

from __future__ import annotations

from .codec import decode, encode
from .exceptions import (
    DecodeError,
    EncodeError,
    FramingError,
    PyDCCLError,
    SchemaError,
    UwacommError,
)
from .framing import frame_message, frame_with_id, unframe_message, unframe_with_id
from .models import BaseMessage, BoundedInt, FixedBytes, FixedStr
from .protobuf import proto_conversion_notes, to_proto_schema
from .utils import (
    crc16,
    crc16_bytes,
    crc32,
    crc32_bytes,
    encoded_bits,
    encoded_size,
    field_sizes,
    verify_crc16,
    verify_crc32,
)

__version__ = "0.1.1"

__all__ = [
    # Core API
    "BaseMessage",
    "encode",
    "decode",
    # Field helpers
    "BoundedInt",
    "FixedBytes",
    "FixedStr",
    # Exceptions
    "UwacommError",
    "PyDCCLError",  # Backward compatibility alias
    "SchemaError",
    "EncodeError",
    "DecodeError",
    "FramingError",
    # Framing
    "frame_message",
    "unframe_message",
    "frame_with_id",
    "unframe_with_id",
    # CRC
    "crc16",
    "crc16_bytes",
    "crc32",
    "crc32_bytes",
    "verify_crc16",
    "verify_crc32",
    # Sizing
    "encoded_size",
    "encoded_bits",
    "field_sizes",
    # Protobuf
    "to_proto_schema",
    "proto_conversion_notes",
    # Version
    "__version__",
]
