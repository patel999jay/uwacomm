"""Unit tests for encoding/decoding."""

from __future__ import annotations

import enum
from typing import ClassVar, Optional

import pytest
from pydantic import Field

from uwacomm import BaseMessage, DecodeError, EncodeError, decode, encode, encoded_size


class Priority(enum.Enum):
    """Test enum."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class SimpleMessage(BaseMessage):
    """Simple test message."""

    vehicle_id: int = Field(ge=0, le=255)
    active: bool


class BoundedMessage(BaseMessage):
    """Message with various bounded fields."""

    small_int: int = Field(ge=0, le=15)  # 4 bits
    medium_int: int = Field(ge=0, le=1000)  # 10 bits
    negative_int: int = Field(ge=-100, le=100)  # 8 bits (range = 201)


class EnumMessage(BaseMessage):
    """Message with enum field."""

    priority: Priority
    id: int = Field(ge=0, le=255)


class BytesMessage(BaseMessage):
    """Message with bytes field."""

    payload: bytes = Field(min_length=4, max_length=4)


class StringMessage(BaseMessage):
    """Message with string field."""

    callsign: str = Field(min_length=8, max_length=8)


class TestEncodeDecode:
    """Test basic encode/decode functionality."""

    def test_simple_message(self) -> None:
        """Test simple message encoding."""
        msg = SimpleMessage(vehicle_id=42, active=True)
        data = encode(msg)

        # 8 bits + 1 bit = 9 bits = 2 bytes
        assert len(data) == 2

        decoded = decode(SimpleMessage, data)
        assert decoded.vehicle_id == 42
        assert decoded.active is True

    def test_bounded_message(self) -> None:
        """Test bounded integer encoding."""
        msg = BoundedMessage(small_int=15, medium_int=500, negative_int=-50)
        data = encode(msg)

        # 4 + 10 + 8 = 22 bits = 3 bytes
        assert len(data) == 3

        decoded = decode(BoundedMessage, data)
        assert decoded.small_int == 15
        assert decoded.medium_int == 500
        assert decoded.negative_int == -50

    def test_enum_message(self) -> None:
        """Test enum encoding."""
        msg = EnumMessage(priority=Priority.HIGH, id=123)
        data = encode(msg)

        decoded = decode(EnumMessage, data)
        assert decoded.priority == Priority.HIGH
        assert decoded.id == 123

    def test_bytes_message(self) -> None:
        """Test bytes encoding."""
        msg = BytesMessage(payload=b"\x01\x02\x03\x04")
        data = encode(msg)

        assert len(data) == 4

        decoded = decode(BytesMessage, data)
        assert decoded.payload == b"\x01\x02\x03\x04"

    def test_string_message(self) -> None:
        """Test string encoding."""
        msg = StringMessage(callsign="ALPHA123")
        data = encode(msg)

        assert len(data) == 8

        decoded = decode(StringMessage, data)
        assert decoded.callsign == "ALPHA123"


class TestEncodeErrors:
    """Test encoding error handling."""

    def test_value_out_of_bounds(self) -> None:
        """Test out-of-bounds error."""
        # Use model_construct to bypass Pydantic validation
        msg = SimpleMessage.model_construct(vehicle_id=256, active=True)

        with pytest.raises(EncodeError, match="out of bounds"):
            encode(msg)

    def test_wrong_bytes_length(self) -> None:
        """Test bytes length mismatch."""
        # Use model_construct to bypass Pydantic validation
        msg = BytesMessage.model_construct(payload=b"\x01\x02")

        with pytest.raises(EncodeError, match="expected 4 bytes"):
            encode(msg)

    def test_wrong_string_length(self) -> None:
        """Test string length mismatch."""
        # Use model_construct to bypass Pydantic validation
        msg = StringMessage.model_construct(callsign="SHORT")

        with pytest.raises(EncodeError, match="expected 8 characters"):
            encode(msg)


class TestDecodeErrors:
    """Test decoding error handling."""

    def test_truncated_data(self) -> None:
        """Test truncated data error."""
        with pytest.raises(DecodeError, match="[Tt]runcated"):
            decode(SimpleMessage, b"\x42")  # Only 1 byte, need 2

    def test_invalid_enum(self) -> None:
        """Test invalid enum value."""
        # Manually construct data with invalid enum ordinal
        from uwacomm.codec.bitpack import BitPacker

        packer = BitPacker()
        packer.write_uint(3, 2)  # Invalid ordinal (only 0-2 valid for 3-value enum)
        packer.write_uint(0, 8)

        with pytest.raises(DecodeError, match="invalid enum"):
            decode(EnumMessage, packer.to_bytes())


class TestSizeCalculation:
    """Test size calculation utilities."""

    def test_encoded_size_class(self) -> None:
        """Test size calculation from class."""
        size = encoded_size(SimpleMessage)
        assert size == 2  # 9 bits = 2 bytes

    def test_encoded_size_instance(self) -> None:
        """Test size calculation from instance."""
        msg = SimpleMessage(vehicle_id=42, active=True)
        size = encoded_size(msg)
        assert size == 2

    def test_bounded_size(self) -> None:
        """Test size of bounded message."""
        size = encoded_size(BoundedMessage)
        assert size == 3  # 22 bits = 3 bytes


class TestMaxBytesConstraint:
    """Test uwacomm_max_bytes constraint."""

    def test_max_bytes_ok(self) -> None:
        """Test message within max_bytes."""

        class ConstrainedMessage(BaseMessage):
            value: int = Field(ge=0, le=255)

            uwacomm_max_bytes: ClassVar[Optional[int]] = 10

        msg = ConstrainedMessage(value=42)
        data = encode(msg)
        assert len(data) <= 10

    def test_max_bytes_exceeded(self) -> None:
        """Test message exceeding max_bytes."""

        class TooLargeMessage(BaseMessage):
            data: bytes = Field(min_length=100, max_length=100)

            uwacomm_max_bytes: ClassVar[Optional[int]] = 50

        msg = TooLargeMessage(data=b"\x00" * 100)

        with pytest.raises(EncodeError, match="exceeds uwacomm_max_bytes"):
            encode(msg)
