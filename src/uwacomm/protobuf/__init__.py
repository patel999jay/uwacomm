"""Protobuf interoperability for uwacomm.

This module provides utilities for generating .proto schemas from Pydantic models
and documenting conversion strategies.
"""

from __future__ import annotations

from .convert import proto_conversion_notes, to_proto_schema

__all__ = [
    "to_proto_schema",
    "proto_conversion_notes",
]
