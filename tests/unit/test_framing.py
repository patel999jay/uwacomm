"""Unit tests for framing utilities."""

from __future__ import annotations

import pytest

from uwacomm.exceptions import FramingError
from uwacomm.framing import frame_message, frame_with_id, unframe_message, unframe_with_id


class TestBasicFraming:
    """Test basic message framing."""

    def test_frame_no_options(self) -> None:
        """Test framing with no options."""
        payload = b"Hello, World!"
        framed = frame_message(payload, length_prefix=False, crc=None)

        # No framing added
        assert framed == payload

    def test_frame_with_length(self) -> None:
        """Test framing with length prefix."""
        payload = b"Hello"
        framed = frame_message(payload, length_prefix=True, crc=None)

        # 4-byte length + payload
        assert len(framed) == 4 + len(payload)

        unframed = unframe_message(framed, length_prefix=True, crc=None)
        assert unframed == payload

    def test_frame_with_crc16(self) -> None:
        """Test framing with CRC-16."""
        payload = b"Test data"
        framed = frame_message(payload, length_prefix=False, crc="crc16")

        # Payload + 2-byte CRC
        assert len(framed) == len(payload) + 2

        unframed = unframe_message(framed, length_prefix=False, crc="crc16")
        assert unframed == payload

    def test_frame_with_crc32(self) -> None:
        """Test framing with CRC-32."""
        payload = b"Test data"
        framed = frame_message(payload, length_prefix=False, crc="crc32")

        # Payload + 4-byte CRC
        assert len(framed) == len(payload) + 4

        unframed = unframe_message(framed, length_prefix=False, crc="crc32")
        assert unframed == payload

    def test_frame_with_all_options(self) -> None:
        """Test framing with all options."""
        payload = b"Complete frame test"
        framed = frame_message(payload, length_prefix=True, crc="crc32")

        # 4-byte length + payload + 4-byte CRC
        assert len(framed) == 4 + len(payload) + 4

        unframed = unframe_message(framed, length_prefix=True, crc="crc32")
        assert unframed == payload


class TestFramingErrors:
    """Test framing error handling."""

    def test_unframe_empty_data(self) -> None:
        """Test error on empty frame."""
        with pytest.raises(FramingError, match="empty"):
            unframe_message(b"", length_prefix=False, crc=None)

    def test_unframe_truncated_length(self) -> None:
        """Test error on truncated length prefix."""
        with pytest.raises(FramingError, match="too short"):
            unframe_message(b"\x00\x01", length_prefix=True, crc=None)

    def test_unframe_crc_mismatch(self) -> None:
        """Test error on CRC mismatch."""
        payload = b"Test"
        framed = frame_message(payload, length_prefix=False, crc="crc16")

        # Corrupt the CRC
        corrupted = framed[:-1] + b"\xff"

        with pytest.raises(FramingError, match="CRC.*verification failed"):
            unframe_message(corrupted, length_prefix=False, crc="crc16")

    def test_unframe_length_mismatch(self) -> None:
        """Test error on length mismatch."""
        # Manually construct frame with wrong length
        wrong_length = b"\x00\x00\x00\x10"  # Says 16 bytes
        payload = b"Short"  # Only 5 bytes

        framed = wrong_length + payload

        with pytest.raises(FramingError, match="[Ll]ength mismatch"):
            unframe_message(framed, length_prefix=True, crc=None, validate_length=True)

    def test_invalid_crc_type(self) -> None:
        """Test error on invalid CRC type."""
        with pytest.raises(ValueError, match="Invalid CRC type"):
            frame_message(b"Test", crc="crc64")  # type: ignore


class TestFramingWithID:
    """Test message framing with message ID."""

    def test_frame_with_id_basic(self) -> None:
        """Test framing with message ID."""
        payload = b"Hello"
        message_id = 42

        framed = frame_with_id(payload, message_id, crc=None)

        # 4-byte length + 2-byte ID + payload
        assert len(framed) == 4 + 2 + len(payload)

        decoded_id, decoded_payload = unframe_with_id(framed, crc=None)
        assert decoded_id == message_id
        assert decoded_payload == payload

    def test_frame_with_id_and_crc(self) -> None:
        """Test framing with ID and CRC."""
        payload = b"Test data"
        message_id = 123

        framed = frame_with_id(payload, message_id, crc="crc32")

        # 4-byte length + 2-byte ID + payload + 4-byte CRC
        assert len(framed) == 4 + 2 + len(payload) + 4

        decoded_id, decoded_payload = unframe_with_id(framed, crc="crc32")
        assert decoded_id == message_id
        assert decoded_payload == payload

    def test_frame_with_id_bounds(self) -> None:
        """Test message ID bounds checking."""
        payload = b"Test"

        # Valid IDs
        frame_with_id(payload, 0)
        frame_with_id(payload, 65535)

        # Invalid IDs
        with pytest.raises(ValueError, match="Message ID must be"):
            frame_with_id(payload, -1)

        with pytest.raises(ValueError, match="Message ID must be"):
            frame_with_id(payload, 65536)

    def test_unframe_with_id_truncated(self) -> None:
        """Test error on truncated message ID frame."""
        # Frame with only length field (says 2 bytes but has 0 bytes of payload)
        framed = b"\x00\x00\x00\x02"

        with pytest.raises(FramingError, match="[Ll]ength mismatch|too short"):
            unframe_with_id(framed, crc=None)


class TestRoundTrip:
    """Test round-trip framing/unframing."""

    def test_roundtrip_various_payloads(self) -> None:
        """Test round-trip with various payloads."""
        payloads = [
            b"",
            b"x",
            b"Short",
            b"A" * 100,
            b"\x00" * 50,
            b"\xff" * 75,
            bytes(range(256)),
        ]

        for payload in payloads:
            framed = frame_message(payload, length_prefix=True, crc="crc32")
            unframed = unframe_message(framed, length_prefix=True, crc="crc32")
            assert unframed == payload

    def test_roundtrip_with_id_various(self) -> None:
        """Test round-trip with ID for various messages."""
        test_cases = [
            (0, b"First message"),
            (100, b"Second message"),
            (65535, b"Last message"),
            (42, b""),
        ]

        for msg_id, payload in test_cases:
            framed = frame_with_id(payload, msg_id, crc="crc16")
            decoded_id, decoded_payload = unframe_with_id(framed, crc="crc16")

            assert decoded_id == msg_id
            assert decoded_payload == payload
