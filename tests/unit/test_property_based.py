"""Property-based tests using hypothesis."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from pydantic import Field

from uwacomm import BaseMessage, decode, encode
from uwacomm.framing import frame_message, unframe_message
from uwacomm.utils.crc import crc16, crc32, verify_crc16, verify_crc32


class BoundedMessage(BaseMessage):
    """Message for property testing."""

    value: int = Field(ge=0, le=255)
    flag: bool


class TestCodecProperties:
    """Property-based tests for codec."""

    @given(value=st.integers(min_value=0, max_value=255), flag=st.booleans())
    def test_encode_decode_roundtrip(self, value: int, flag: bool) -> None:
        """Test encode/decode is invertible."""
        msg = BoundedMessage(value=value, flag=flag)
        data = encode(msg)
        decoded = decode(BoundedMessage, data)

        assert decoded.value == value
        assert decoded.flag == flag

    @given(
        value1=st.integers(min_value=0, max_value=255),
        value2=st.integers(min_value=0, max_value=255),
        flag1=st.booleans(),
        flag2=st.booleans(),
    )
    def test_encode_deterministic(self, value1: int, flag1: bool, value2: int, flag2: bool) -> None:
        """Test encoding is deterministic."""
        msg1a = BoundedMessage(value=value1, flag=flag1)
        msg1b = BoundedMessage(value=value1, flag=flag1)

        assert encode(msg1a) == encode(msg1b)

        # Different values should produce different encodings
        if value1 != value2 or flag1 != flag2:
            msg2 = BoundedMessage(value=value2, flag=flag2)
            assert encode(msg1a) != encode(msg2)


class TestFramingProperties:
    """Property-based tests for framing."""

    @given(payload=st.binary(min_size=0, max_size=1000))
    def test_frame_unframe_roundtrip_crc16(self, payload: bytes) -> None:
        """Test framing round-trip with CRC-16."""
        framed = frame_message(payload, length_prefix=True, crc="crc16")
        unframed = unframe_message(framed, length_prefix=True, crc="crc16")

        assert unframed == payload

    @given(payload=st.binary(min_size=0, max_size=1000))
    def test_frame_unframe_roundtrip_crc32(self, payload: bytes) -> None:
        """Test framing round-trip with CRC-32."""
        framed = frame_message(payload, length_prefix=True, crc="crc32")
        unframed = unframe_message(framed, length_prefix=True, crc="crc32")

        assert unframed == payload

    @given(payload=st.binary(min_size=1, max_size=100))
    def test_framing_increases_size(self, payload: bytes) -> None:
        """Test that framing adds bytes."""
        framed_length = frame_message(payload, length_prefix=True, crc=None)
        framed_crc = frame_message(payload, length_prefix=False, crc="crc16")
        framed_both = frame_message(payload, length_prefix=True, crc="crc32")

        assert len(framed_length) == len(payload) + 4
        assert len(framed_crc) == len(payload) + 2
        assert len(framed_both) == len(payload) + 4 + 4


class TestCRCProperties:
    """Property-based tests for CRC."""

    @given(data=st.binary(min_size=0, max_size=1000))
    def test_crc16_verify_roundtrip(self, data: bytes) -> None:
        """Test CRC-16 verification round-trip."""
        checksum = crc16(data)
        assert verify_crc16(data, checksum) is True

    @given(data=st.binary(min_size=0, max_size=1000))
    def test_crc32_verify_roundtrip(self, data: bytes) -> None:
        """Test CRC-32 verification round-trip."""
        checksum = crc32(data)
        assert verify_crc32(data, checksum) is True

    @given(data=st.binary(min_size=1, max_size=100))
    def test_crc_changes_with_data(self, data: bytes) -> None:
        """Test that changing data changes CRC."""
        checksum1 = crc16(data)

        # Flip a bit in the data
        modified = bytearray(data)
        modified[0] ^= 0x01
        checksum2 = crc16(bytes(modified))

        # CRC should be different (with very high probability)
        assert checksum1 != checksum2

    @given(data=st.binary(min_size=0, max_size=100))
    def test_crc_deterministic(self, data: bytes) -> None:
        """Test CRC is deterministic."""
        crc16_1 = crc16(data)
        crc16_2 = crc16(data)
        crc32_1 = crc32(data)
        crc32_2 = crc32(data)

        assert crc16_1 == crc16_2
        assert crc32_1 == crc32_2
