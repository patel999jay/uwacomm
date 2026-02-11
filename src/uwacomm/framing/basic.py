"""Basic message framing utilities.

This module provides length-prefixed framing and CRC-protected framing
for reliable transmission over acoustic channels.
"""

from __future__ import annotations

import struct
from typing import Literal, Optional

from ..exceptions import FramingError
from ..utils.crc import crc16, crc16_bytes, crc32, crc32_bytes, verify_crc16, verify_crc32

CRCType = Literal["crc16", "crc32"]


def frame_message(
    payload: bytes,
    *,
    length_prefix: bool = True,
    crc: Optional[CRCType] = None,
) -> bytes:
    """Frame a message with optional length prefix and CRC.

    The frame structure is:
    - [Length (4 bytes, optional)] [Payload] [CRC (2 or 4 bytes, optional)]

    Args:
        payload: Message payload to frame
        length_prefix: If True, prepend 4-byte big-endian length field
        crc: CRC type to append ('crc16' or 'crc32'), or None for no CRC

    Returns:
        Framed message

    Example:
        >>> payload = b"Hello"
        >>> framed = frame_message(payload, crc="crc16")
        >>> len(framed) > len(payload)
        True
    """
    result = bytearray()

    # Length prefix (payload length only, not including length field or CRC)
    if length_prefix:
        result.extend(struct.pack(">I", len(payload)))

    # Payload
    result.extend(payload)

    # CRC (computed over length + payload if length prefix is present)
    if crc == "crc16":
        crc_value = crc16_bytes(bytes(result))
        result.extend(crc_value)
    elif crc == "crc32":
        crc_value = crc32_bytes(bytes(result))
        result.extend(crc_value)
    elif crc is not None:
        raise ValueError(f"Invalid CRC type: {crc}. Must be 'crc16', 'crc32', or None")

    return bytes(result)


def unframe_message(
    framed: bytes,
    *,
    length_prefix: bool = True,
    crc: Optional[CRCType] = None,
    validate_length: bool = True,
) -> bytes:
    """Unframe a message and validate length/CRC.

    Args:
        framed: Framed message to unpack
        length_prefix: If True, expect 4-byte big-endian length field
        crc: CRC type to verify ('crc16' or 'crc32'), or None for no CRC
        validate_length: If True, validate that frame length matches length prefix

    Returns:
        Original payload (without length prefix or CRC)

    Raises:
        FramingError: If frame is malformed, CRC fails, or length mismatch

    Example:
        >>> framed = frame_message(b"Hello", crc="crc16")
        >>> payload = unframe_message(framed, crc="crc16")
        >>> payload
        b'Hello'
    """
    if not framed:
        raise FramingError("Cannot unframe empty data")

    position = 0

    # Read length prefix
    expected_payload_length: Optional[int] = None
    if length_prefix:
        if len(framed) < 4:
            raise FramingError(f"Frame too short for length prefix: {len(framed)} bytes")

        expected_payload_length = struct.unpack(">I", framed[0:4])[0]
        position = 4

    # Determine CRC size
    crc_size = 0
    if crc == "crc16":
        crc_size = 2
    elif crc == "crc32":
        crc_size = 4
    elif crc is not None:
        raise ValueError(f"Invalid CRC type: {crc}")

    # Calculate where payload ends
    if len(framed) < position + crc_size:
        raise FramingError(
            f"Frame too short: need at least {position + crc_size} bytes, "
            f"got {len(framed)} bytes"
        )

    payload_end = len(framed) - crc_size
    payload = framed[position:payload_end]

    # Validate length if length prefix present
    if length_prefix and validate_length and expected_payload_length is not None:
        if len(payload) != expected_payload_length:
            raise FramingError(
                f"Length mismatch: prefix says {expected_payload_length} bytes, "
                f"but got {len(payload)} bytes"
            )

    # Verify CRC (computed over everything except the CRC itself)
    if crc is not None:
        data_with_length = framed[:payload_end]
        crc_bytes = framed[payload_end:]

        if crc == "crc16":
            if not verify_crc16(data_with_length, crc_bytes):
                raise FramingError("CRC-16 verification failed")
        elif crc == "crc32":
            if not verify_crc32(data_with_length, crc_bytes):
                raise FramingError("CRC-32 verification failed")

    return payload


def frame_with_id(
    payload: bytes,
    message_id: int,
    *,
    crc: Optional[CRCType] = None,
) -> bytes:
    """Frame a message with a message ID and optional CRC.

    The frame structure is:
    - [Length (4 bytes)] [Message ID (2 bytes)] [Payload] [CRC (optional)]

    This is useful for multiplexing multiple message types over a single channel.

    Args:
        payload: Message payload to frame
        message_id: Message type ID (0-65535)
        crc: CRC type to append

    Returns:
        Framed message with ID

    Raises:
        ValueError: If message_id is out of range

    Example:
        >>> payload = b"Hello"
        >>> framed = frame_with_id(payload, message_id=42, crc="crc16")
    """
    if not 0 <= message_id <= 65535:
        raise ValueError(f"Message ID must be 0-65535, got {message_id}")

    # Build frame: length (4) + id (2) + payload
    total_payload_length = 2 + len(payload)
    result = bytearray()
    result.extend(struct.pack(">I", total_payload_length))  # Length includes ID
    result.extend(struct.pack(">H", message_id))  # Message ID
    result.extend(payload)

    # Add CRC
    if crc == "crc16":
        result.extend(crc16_bytes(bytes(result)))
    elif crc == "crc32":
        result.extend(crc32_bytes(bytes(result)))
    elif crc is not None:
        raise ValueError(f"Invalid CRC type: {crc}")

    return bytes(result)


def unframe_with_id(
    framed: bytes,
    *,
    crc: Optional[CRCType] = None,
) -> tuple[int, bytes]:
    """Unframe a message with message ID.

    Args:
        framed: Framed message with ID
        crc: CRC type to verify

    Returns:
        Tuple of (message_id, payload)

    Raises:
        FramingError: If frame is malformed or CRC fails

    Example:
        >>> framed = frame_with_id(b"Hello", message_id=42, crc="crc16")
        >>> msg_id, payload = unframe_with_id(framed, crc="crc16")
        >>> msg_id
        42
        >>> payload
        b'Hello'
    """
    # Unframe with length prefix
    full_payload = unframe_message(framed, length_prefix=True, crc=crc, validate_length=True)

    # Extract message ID
    if len(full_payload) < 2:
        raise FramingError(f"Payload too short for message ID: {len(full_payload)} bytes")

    message_id = struct.unpack(">H", full_payload[0:2])[0]
    payload = full_payload[2:]

    return message_id, payload
