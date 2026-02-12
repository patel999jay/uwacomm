"""Multi-vehicle routing support for uwacomm.

This module provides:
- Mode 2: Self-describing messages with MESSAGE_REGISTRY
- Mode 3: Multi-vehicle routing with RoutingHeader (to be implemented)
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from uwacomm.codec.decoder import decode as _decode_base
from uwacomm.codec.bitpack import BitUnpacker
from uwacomm.exceptions import DecodeError

T = TypeVar("T", bound=BaseModel)


# ============================================================================
# Mode 2: Self-Describing Messages
# ============================================================================

# Global registry: message_id -> message_class
MESSAGE_REGISTRY: dict[int, type[BaseModel]] = {}


def register_message(message_class: type[BaseModel]) -> None:
    """Register a message class for auto-decode by ID.

    This enables decode_by_id() to automatically determine the message type
    from the embedded message ID in the binary data (Mode 2).

    Args:
        message_class: Pydantic message class with uwacomm_id attribute

    Raises:
        ValueError: If message_class has no uwacomm_id or ID already registered

    Example:
        >>> from examples.uw_vehicle_messages import UwHeartbeat, BatteryReport
        >>> register_message(UwHeartbeat)
        >>> register_message(BatteryReport)
        >>> # Now decode_by_id() can auto-detect message type
    """
    msg_id = getattr(message_class, 'uwacomm_id', None)
    if msg_id is None:
        raise ValueError(
            f"{message_class.__name__} has no uwacomm_id attribute. "
            f"Cannot register for auto-decode."
        )

    if not isinstance(msg_id, int) or msg_id < 0 or msg_id > 32767:
        raise ValueError(
            f"uwacomm_id must be an integer 0-32767, got {msg_id}"
        )

    # Check for conflicts
    if msg_id in MESSAGE_REGISTRY:
        existing = MESSAGE_REGISTRY[msg_id]
        if existing is not message_class:
            raise ValueError(
                f"Message ID {msg_id} already registered to {existing.__name__}. "
                f"Cannot register {message_class.__name__} with the same ID."
            )
        # Already registered, no-op
        return

    MESSAGE_REGISTRY[msg_id] = message_class


def decode_by_id(data: bytes) -> BaseModel:
    """Auto-decode message using embedded message ID (Mode 2).

    This function peeks at the message ID in the binary data, looks up the
    corresponding message class in MESSAGE_REGISTRY, and decodes the message.

    Args:
        data: Encoded bytes with message ID header (Mode 2 format)

    Returns:
        Decoded message (type determined by ID)

    Raises:
        DecodeError: If message ID not registered or data is invalid

    Example:
        >>> # Register all message types first
        >>> register_message(UwHeartbeat)
        >>> register_message(BatteryReport)
        >>>
        >>> # Receive unknown message over acoustic modem
        >>> received_bytes = b'\\x69...'  # ID 105 (UwHeartbeat)
        >>>
        >>> # Auto-decode without knowing the type
        >>> msg = decode_by_id(received_bytes)
        >>> if isinstance(msg, UwHeartbeat):
        ...     print(f"Heartbeat at depth {msg.depth}")
    """
    if not data:
        raise DecodeError("Cannot decode empty data")

    try:
        # Read message ID using varint-style encoding
        unpacker = BitUnpacker(data)

        # Read high bit to determine ID size
        high_bit = unpacker.read_bool()

        if not high_bit:
            # 1 byte: 0xxxxxxx (7 bits for ID, range 0-127)
            msg_id = unpacker.read_uint(7)
        else:
            # 2 bytes: 1xxxxxxx xxxxxxxx (15 bits for ID, range 0-32767)
            msg_id = unpacker.read_uint(15)

    except IndexError as e:
        raise DecodeError(f"Truncated data while reading message ID: {e}") from e

    # Look up message class
    message_class = MESSAGE_REGISTRY.get(msg_id)
    if message_class is None:
        registered_ids = sorted(MESSAGE_REGISTRY.keys())
        raise DecodeError(
            f"Unknown message ID: {msg_id}. "
            f"Registered IDs: {registered_ids}. "
            f"Did you forget to call register_message()?"
        )

    # Decode with ID validation
    return _decode_base(message_class, data, include_id=True)


# ============================================================================
# Mode 3: Multi-Vehicle Routing
# ============================================================================

from dataclasses import dataclass

from uwacomm.codec.encoder import encode as _encode_base


@dataclass
class RoutingHeader:
    """Routing header for multi-vehicle communication.

    Based on WHOI micromodem conventions for multi-vehicle systems.

    Attributes:
        source_id: Source vehicle ID (0-255)
        dest_id: Destination vehicle ID (0-255, 255=broadcast)
        priority: Message priority (0=low, 3=high)
        ack_requested: Whether acknowledgment is requested

    Encoding:
        - source_id: 8 bits
        - dest_id: 8 bits
        - priority: 2 bits
        - ack_requested: 1 bit
        Total: 19 bits (~3 bytes when byte-aligned)

    Example:
        >>> header = RoutingHeader(source_id=3, dest_id=0, priority=2, ack_requested=True)
        >>> # Vehicle 3 sends high-priority message to topside (ID 0) with ACK request
    """
    source_id: int      # 0-255
    dest_id: int        # 0-255 (255 = broadcast)
    priority: int = 0   # 0-3 (0=low, 3=high)
    ack_requested: bool = False

    def __post_init__(self):
        """Validate routing header values."""
        if not 0 <= self.source_id <= 255:
            raise ValueError(f"source_id must be 0-255, got {self.source_id}")
        if not 0 <= self.dest_id <= 255:
            raise ValueError(f"dest_id must be 0-255, got {self.dest_id}")
        if not 0 <= self.priority <= 3:
            raise ValueError(f"priority must be 0-3, got {self.priority}")


def encode_with_routing(
    message: BaseModel,
    source_id: int,
    dest_id: int,
    priority: int = 0,
    ack_requested: bool = False
) -> bytes:
    """Encode message with routing header (Mode 3).

    This creates a self-describing, routable message suitable for multi-vehicle
    systems, swarm robotics, or mesh networks.

    Args:
        message: Message to encode
        source_id: Source vehicle ID (0-255)
        dest_id: Destination vehicle ID (0-255, 255=broadcast)
        priority: Message priority (0=low, 3=high), default 0
        ack_requested: Whether acknowledgment is requested, default False

    Returns:
        Encoded bytes with routing header + message ID + payload

    Raises:
        ValueError: If routing parameters are out of range
        EncodeError: If message encoding fails

    Example:
        >>> from examples.uw_vehicle_messages import UwHeartbeat
        >>> heartbeat = UwHeartbeat(lat=42358894, lon=-71063611, ...)
        >>> # Vehicle 3 sends to topside (ID 0)
        >>> encoded = encode_with_routing(heartbeat, source_id=3, dest_id=0, priority=2)
        >>> # Size: 3 bytes routing + 1 byte ID + 21 bytes payload = 25 bytes
    """
    # Create and validate routing header
    routing = RoutingHeader(source_id, dest_id, priority, ack_requested)

    # Delegate to encoder with routing parameter
    from uwacomm.codec.encoder import encode as _encode_base
    return _encode_base(message, routing=routing)


def decode_with_routing(
    message_class: type[T],
    data: bytes
) -> tuple[RoutingHeader, T]:
    """Decode message with routing header (Mode 3).

    Args:
        message_class: Expected message class
        data: Encoded bytes with routing header + message ID + payload

    Returns:
        Tuple of (routing_header, decoded_message)

    Raises:
        DecodeError: If decoding fails or data is invalid

    Example:
        >>> from examples.uw_vehicle_messages import UwHeartbeat
        >>> # Receive message from acoustic modem
        >>> routing, heartbeat = decode_with_routing(UwHeartbeat, received_bytes)
        >>> print(f"From vehicle {routing.source_id}, priority {routing.priority}")
        >>> if routing.ack_requested:
        ...     print("ACK requested - send acknowledgment")
    """
    # Delegate to decoder with routing parameter
    from uwacomm.codec.decoder import decode as _decode_base
    return _decode_base(message_class, data, routing=True)
