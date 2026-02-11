#!/usr/bin/env python3
"""Message framing example for uwacomm.

This example demonstrates:
1. Framing messages with length prefix and CRC
2. Using message IDs for multiplexing
3. Error detection with CRC checksums
"""

from __future__ import annotations

from typing import ClassVar, Optional

from pydantic import Field

from uwacomm import BaseMessage, decode, encode, frame_with_id, unframe_with_id


class StatusReport(BaseMessage):
    """Status report message."""

    vehicle_id: int = Field(ge=0, le=255)
    depth_cm: int = Field(ge=0, le=10000)
    battery_pct: int = Field(ge=0, le=100)

    uwacomm_id: ClassVar[Optional[int]] = 10


class CommandMessage(BaseMessage):
    """Command message."""

    target_depth_cm: int = Field(ge=0, le=10000)
    emergency_surface: bool

    uwacomm_id: ClassVar[Optional[int]] = 20


def main() -> None:
    """Run the framing example."""
    print("=" * 60)
    print("uwacomm Message Framing Example")
    print("=" * 60)
    print()

    # Create messages
    status = StatusReport(vehicle_id=5, depth_cm=3000, battery_pct=75)
    command = CommandMessage(target_depth_cm=2000, emergency_surface=False)

    # Encode messages
    status_encoded = encode(status)
    command_encoded = encode(command)

    print(f"1. Raw message sizes:")
    print(f"   Status: {len(status_encoded)} bytes")
    print(f"   Command: {len(command_encoded)} bytes")
    print()

    # Frame with message IDs and CRC
    print("2. Framing messages with ID and CRC-32...")
    status_framed = frame_with_id(
        status_encoded, message_id=StatusReport.uwacomm_id or 0, crc="crc32"
    )
    command_framed = frame_with_id(
        command_encoded, message_id=CommandMessage.uwacomm_id or 0, crc="crc32"
    )

    print(f"   Status framed: {len(status_framed)} bytes")
    print(f"   Command framed: {len(command_framed)} bytes")
    print()

    # Simulate transmission and reception
    print("3. Simulating transmission...")
    transmitted_frames = [status_framed, command_framed]
    received_frames = transmitted_frames.copy()  # Perfect channel simulation
    print(f"   Transmitted {len(transmitted_frames)} frames")
    print()

    # Receive and route messages
    print("4. Receiving and routing messages...")
    for i, frame in enumerate(received_frames, 1):
        print(f"   Frame {i}:")

        # Unframe and get message ID
        msg_id, payload = unframe_with_id(frame, crc="crc32")
        print(f"     Message ID: {msg_id}")
        print(f"     Payload size: {len(payload)} bytes")

        # Route based on message ID
        if msg_id == 10:
            decoded = decode(StatusReport, payload)
            print(f"     Type: StatusReport")
            print(f"     Vehicle: {decoded.vehicle_id}")
            print(f"     Depth: {decoded.depth_cm} cm")
            print(f"     Battery: {decoded.battery_pct}%")

        elif msg_id == 20:
            decoded = decode(CommandMessage, payload)
            print(f"     Type: CommandMessage")
            print(f"     Target depth: {decoded.target_depth_cm} cm")
            print(f"     Emergency surface: {decoded.emergency_surface}")

        else:
            print(f"     Unknown message ID: {msg_id}")

        print()

    # Demonstrate error detection
    print("5. Demonstrating CRC error detection...")
    print("   Corrupting frame...")
    corrupted_frame = bytearray(status_framed)
    corrupted_frame[10] ^= 0xFF  # Flip all bits in one byte
    corrupted_frame = bytes(corrupted_frame)

    try:
        msg_id, payload = unframe_with_id(corrupted_frame, crc="crc32")
        print("   ✗ Error: Corruption not detected!")
    except Exception as e:
        print(f"   ✓ Corruption detected: {e}")
    print()

    print("=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
