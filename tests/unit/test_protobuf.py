"""Unit tests for Protobuf schema generation."""

from __future__ import annotations

import enum

from pydantic import Field

from uwacomm import BaseMessage
from uwacomm.protobuf import to_proto_schema


class Status(enum.Enum):
    """Test enum for protobuf generation."""

    IDLE = 1
    ACTIVE = 2
    ERROR = 3


class SimpleProtoMessage(BaseMessage):
    """Simple message for proto generation."""

    vehicle_id: int = Field(ge=0, le=255)
    active: bool


class ComplexProtoMessage(BaseMessage):
    """Complex message for proto generation."""

    small_value: int = Field(ge=0, le=15)
    large_value: int = Field(ge=0, le=1000000)
    signed_value: int = Field(ge=-1000, le=1000)
    status: Status
    flag: bool
    data: bytes = Field(min_length=8, max_length=8)
    name: str = Field(min_length=16, max_length=16)


class TestProtoSchemaGeneration:
    """Test Protobuf schema generation."""

    def test_simple_proto_schema(self) -> None:
        """Test simple proto schema generation."""
        proto = to_proto_schema(SimpleProtoMessage, package="test")

        assert 'syntax = "proto3"' in proto
        assert "package test;" in proto
        assert "message SimpleProtoMessage {" in proto
        assert "uint32 vehicle_id = 1;" in proto
        assert "bool active = 2;" in proto

    def test_complex_proto_schema(self) -> None:
        """Test complex proto schema generation."""
        proto = to_proto_schema(ComplexProtoMessage)

        assert "message ComplexProtoMessage {" in proto
        assert "uint32 small_value" in proto
        assert "uint32 large_value" in proto
        assert "int32 signed_value" in proto
        assert "Status status" in proto
        assert "bool flag" in proto
        assert "bytes data" in proto
        assert "string name" in proto

    def test_enum_generation(self) -> None:
        """Test enum definition generation."""
        proto = to_proto_schema(ComplexProtoMessage)

        # Check enum definition
        assert "enum Status {" in proto
        assert "IDLE = 0;" in proto
        assert "ACTIVE = 1;" in proto
        assert "ERROR = 2;" in proto

    def test_proto_comments(self) -> None:
        """Test that field comments are generated."""
        proto = to_proto_schema(ComplexProtoMessage)

        # Check for range comments
        assert "Range: [0, 15]" in proto or "uwacomm:" in proto

    def test_proto_syntax_version(self) -> None:
        """Test proto syntax version control."""
        proto3 = to_proto_schema(SimpleProtoMessage, syntax="proto3")
        proto2 = to_proto_schema(SimpleProtoMessage, syntax="proto2")

        assert 'syntax = "proto3"' in proto3
        assert 'syntax = "proto2"' in proto2

    def test_proto_package_optional(self) -> None:
        """Test proto generation without package."""
        proto = to_proto_schema(SimpleProtoMessage, package="")

        assert 'syntax = "proto3"' in proto
        assert "package" not in proto.split("\n")[1]  # Second line shouldn't have package

    def test_proto_type_mapping(self) -> None:
        """Test correct type mapping."""

        class TypeTestMessage(BaseMessage):
            tiny: int = Field(ge=0, le=10)  # Should be uint32
            huge: int = Field(ge=0, le=2**40)  # Should be uint64
            negative: int = Field(ge=-100, le=100)  # Should be int32

        proto = to_proto_schema(TypeTestMessage)

        assert "uint32 tiny" in proto
        assert "uint64 huge" in proto
        assert "int32 negative" in proto
