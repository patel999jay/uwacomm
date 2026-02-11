#!/usr/bin/env python3
"""Realistic underwater communications scenario.

This example simulates a complete underwater vehicle communications scenario
with multiple message types, bandwidth constraints, and error handling.
"""

from __future__ import annotations

import enum
import random
from typing import ClassVar, List, Optional

from pydantic import Field

from uwacomm import (
    BaseMessage,
    DecodeError,
    FramingError,
    decode,
    encode,
    encoded_size,
    frame_with_id,
    unframe_with_id,
)


class Priority(enum.Enum):
    """Message priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class StatusReport(BaseMessage):
    """Periodic vehicle status report."""

    vehicle_id: int = Field(ge=0, le=15, description="Vehicle ID (fleet of 16)")
    timestamp_sec: int = Field(ge=0, le=86400, description="Mission time in seconds")
    depth_dm: int = Field(ge=0, le=1000, description="Depth in decimeters (0-100m)")
    battery_pct: int = Field(ge=0, le=100, description="Battery percentage")
    priority: Priority = Field(description="Message priority")
    emergency: bool = Field(description="Emergency flag")

    uwacomm_id: ClassVar[Optional[int]] = 1
    uwacomm_max_bytes: ClassVar[Optional[int]] = 8


class WaypointCommand(BaseMessage):
    """Waypoint navigation command."""

    vehicle_id: int = Field(ge=0, le=15)
    waypoint_id: int = Field(ge=0, le=31, description="Waypoint number")
    target_depth_dm: int = Field(ge=0, le=1000, description="Target depth in decimeters")
    speed_dmps: int = Field(ge=0, le=50, description="Speed in decimeters per second")

    uwacomm_id: ClassVar[Optional[int]] = 2
    uwacomm_max_bytes: ClassVar[Optional[int]] = 8


class AcousticModem:
    """Simulated acoustic modem with bandwidth constraints."""

    def __init__(self, bandwidth_bps: int = 80, error_rate: float = 0.01):
        """Initialize modem.

        Args:
            bandwidth_bps: Channel bandwidth in bits per second
            error_rate: Simulated bit error rate (0.0 - 1.0)
        """
        self.bandwidth_bps = bandwidth_bps
        self.error_rate = error_rate
        self.transmitted_bytes = 0
        self.transmission_time = 0.0

    def transmit(self, data: bytes) -> bytes:
        """Simulate transmitting data over acoustic channel.

        Args:
            data: Data to transmit

        Returns:
            Received data (possibly corrupted)
        """
        # Calculate transmission time
        bits = len(data) * 8
        tx_time = bits / self.bandwidth_bps

        self.transmitted_bytes += len(data)
        self.transmission_time += tx_time

        # Simulate bit errors
        if random.random() < self.error_rate:
            # Corrupt one random byte
            corrupted = bytearray(data)
            error_pos = random.randint(0, len(corrupted) - 1)
            corrupted[error_pos] ^= random.randint(1, 255)
            return bytes(corrupted)

        return data

    def get_stats(self) -> dict[str, float]:
        """Get modem statistics."""
        return {
            "transmitted_bytes": self.transmitted_bytes,
            "transmission_time": self.transmission_time,
            "effective_rate_bps": (
                self.transmitted_bytes * 8 / self.transmission_time
                if self.transmission_time > 0
                else 0
            ),
        }


def main() -> None:
    """Run the underwater communications scenario."""
    print("=" * 70)
    print("uwacomm Underwater Communications Scenario")
    print("=" * 70)
    print()

    print("Scenario: AUV fleet status reporting over acoustic modem")
    print("Constraints: 80 bps channel, ~1% error rate, 4 vehicles")
    print()

    # Initialize modem
    modem = AcousticModem(bandwidth_bps=80, error_rate=0.01)

    # Create fleet status reports
    print("1. Creating vehicle status reports...")
    vehicles = [
        StatusReport(
            vehicle_id=i,
            timestamp_sec=3600 + i * 10,
            depth_dm=random.randint(100, 500),
            battery_pct=random.randint(60, 100),
            priority=Priority.NORMAL,
            emergency=False,
        )
        for i in range(4)
    ]

    for v in vehicles:
        size = encoded_size(v)
        print(f"   Vehicle {v.vehicle_id}: {size} bytes, {v.depth_dm / 10:.1f}m, {v.battery_pct}%")

    print()

    # Encode and frame messages
    print("2. Encoding and framing messages...")
    frames: List[bytes] = []

    for vehicle in vehicles:
        encoded = encode(vehicle)
        framed = frame_with_id(encoded, message_id=StatusReport.uwacomm_id or 0, crc="crc16")
        frames.append(framed)
        print(f"   Vehicle {vehicle.vehicle_id}: {len(framed)} bytes framed")

    total_bytes = sum(len(f) for f in frames)
    print(f"   Total transmission size: {total_bytes} bytes")
    print()

    # Transmit over acoustic channel
    print("3. Transmitting over acoustic channel...")
    received_frames = []
    successful = 0
    failed = 0

    for i, frame in enumerate(frames):
        print(f"   Transmitting vehicle {i} report...")
        received = modem.transmit(frame)
        received_frames.append(received)

        # Try to decode immediately to check
        try:
            msg_id, payload = unframe_with_id(received, crc="crc16")
            decode(StatusReport, payload)
            print(f"     ✓ Transmitted successfully")
            successful += 1
        except (FramingError, DecodeError) as e:
            print(f"     ✗ Transmission error: {type(e).__name__}")
            failed += 1

    print()

    # Display statistics
    print("4. Transmission Statistics:")
    stats = modem.get_stats()
    print(f"   Total bytes transmitted: {stats['transmitted_bytes']}")
    print(f"   Total transmission time: {stats['transmission_time']:.2f} seconds")
    print(f"   Effective rate: {stats['effective_rate_bps']:.1f} bps")
    print(f"   Successful: {successful}/{len(frames)}")
    print(f"   Failed: {failed}/{len(frames)}")
    print()

    # Receive and decode
    print("5. Receiving and decoding messages...")
    decoded_count = 0

    for i, frame in enumerate(received_frames):
        try:
            msg_id, payload = unframe_with_id(frame, crc="crc16")

            if msg_id == 1:
                status = decode(StatusReport, payload)
                decoded_count += 1
                print(f"   Vehicle {status.vehicle_id}:")
                print(f"     Depth: {status.depth_dm / 10:.1f} m")
                print(f"     Battery: {status.battery_pct}%")
                print(f"     Priority: {status.priority.name}")

        except (FramingError, DecodeError) as e:
            print(f"   Frame {i}: Decode failed - {type(e).__name__}")

    print()
    print(f"   Successfully decoded: {decoded_count}/{len(received_frames)} messages")
    print()

    # Compare to alternative encoding
    print("6. Comparison to JSON encoding:")

    import json

    json_size = sum(len(json.dumps(v.model_dump(mode="json")).encode()) for v in vehicles)
    uwacomm_size = sum(len(encode(v)) for v in vehicles)

    print(f"   uwacomm: {uwacomm_size} bytes")
    print(f"   JSON: {json_size} bytes")
    print(f"   Savings: {json_size - uwacomm_size} bytes ({(1 - uwacomm_size/json_size)*100:.1f}%)")
    print()

    json_tx_time = (json_size * 8) / modem.bandwidth_bps
    uwacomm_tx_time = (uwacomm_size * 8) / modem.bandwidth_bps

    print(f"   Transmission time (80 bps channel):")
    print(f"     uwacomm: {uwacomm_tx_time:.1f} seconds")
    print(f"     JSON: {json_tx_time:.1f} seconds")
    print(f"     Time saved: {json_tx_time - uwacomm_tx_time:.1f} seconds")
    print()

    print("=" * 70)
    print("Scenario complete!")
    print("=" * 70)


if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)
    main()
