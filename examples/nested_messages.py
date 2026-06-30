#!/usr/bin/env python3
"""Nested message encoding example for uwacomm (v0.4.0).

This example demonstrates:
1. Defining a nested BaseMessage as a field type
2. Two-level deep nesting
3. Bit-level size calculation across nested structures
4. Encoding / decoding in all three modes
"""

from __future__ import annotations

from typing import ClassVar

from uwacomm import (
    BaseMessage,
    BoundedInt,
    decode,
    encode,
    encoded_bits,
    encoded_size,
    field_sizes,
    register_message,
)
from uwacomm.models.fields import BoundedFloat

# ---------------------------------------------------------------------------
# Message definitions
# ---------------------------------------------------------------------------


class GPSPosition(BaseMessage):
    """Compact GPS coordinate: lat ±90°, lon ±180° at 1 µdeg precision."""

    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)  # 28 bits
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)  # 29 bits


class VehicleStatus(BaseMessage):
    """Top-level status message with an inline nested GPSPosition."""

    vehicle_id: int = BoundedInt(ge=0, le=255)  # 8 bits
    position: GPSPosition  # 57 bits inline — no length prefix
    depth_cm: int = BoundedInt(ge=0, le=50000)  # 16 bits
    battery: int = BoundedInt(ge=0, le=100)  # 7 bits

    uwacomm_id: ClassVar[int | None] = 20


# Two-level nesting: Outer → Middle → Inner
class InnerSensor(BaseMessage):
    temp_raw: int = BoundedInt(ge=0, le=1023)  # 10 bits, 10-bit ADC reading
    pressure_raw: int = BoundedInt(ge=0, le=4095)  # 12 bits, 12-bit ADC reading


class SensorBundle(BaseMessage):
    sensor_a: InnerSensor
    sensor_b: InnerSensor
    valid: bool  # 1 bit


register_message(VehicleStatus)


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------


def print_sizes(cls: type[BaseMessage], label: str) -> None:
    print(f"\n{label}")
    print(f"  Total: {encoded_bits(cls)} bits = {encoded_size(cls)} bytes")
    for name, bits in field_sizes(cls).items():
        print(f"  {name:15s}: {bits:3d} bits")


def demo_mode1() -> None:
    """Mode 1: raw bytes, no overhead."""
    print("\n--- Mode 1 (no overhead) ---")
    pos = GPSPosition(lat=44.648766, lon=-63.575237)
    msg = VehicleStatus(vehicle_id=7, position=pos, depth_cm=1250, battery=83)

    data = encode(msg)
    decoded = decode(VehicleStatus, data)

    print(f"Encoded: {data.hex()}  ({len(data)} bytes)")
    print(f"vehicle_id : {decoded.vehicle_id}")
    print(f"lat        : {decoded.position.lat:.6f}°")
    print(f"lon        : {decoded.position.lon:.6f}°")
    print(f"depth_cm   : {decoded.depth_cm} cm")
    print(f"battery    : {decoded.battery}%")


def demo_mode2() -> None:
    """Mode 2: 1-byte message ID prefix enables self-describing decode."""
    print("\n--- Mode 2 (with message ID) ---")
    pos = GPSPosition(lat=0.0, lon=0.0)
    msg = VehicleStatus(vehicle_id=1, position=pos, depth_cm=0, battery=100)

    data = encode(msg, include_id=True)
    decoded = decode(VehicleStatus, data, include_id=True)
    print(f"Encoded (with ID byte): {data.hex()}  ({len(data)} bytes)")
    print(f"Message ID in registry: {VehicleStatus.uwacomm_id}")
    print(f"Decoded battery: {decoded.battery}%")


def demo_two_level_nesting() -> None:
    """Two-level deep nesting with two InnerSensor fields."""
    print("\n--- Two-level nesting ---")
    bundle = SensorBundle(
        sensor_a=InnerSensor(temp_raw=512, pressure_raw=2048),
        sensor_b=InnerSensor(temp_raw=999, pressure_raw=4095),
        valid=True,
    )
    data = encode(bundle)
    decoded = decode(SensorBundle, data)

    print(f"Encoded: {data.hex()}  ({len(data)} bytes)")
    print(f"sensor_a.temp_raw     : {decoded.sensor_a.temp_raw}")
    print(f"sensor_a.pressure_raw : {decoded.sensor_a.pressure_raw}")
    print(f"sensor_b.temp_raw     : {decoded.sensor_b.temp_raw}")
    print(f"sensor_b.pressure_raw : {decoded.sensor_b.pressure_raw}")
    print(f"valid                 : {decoded.valid}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 55)
    print("uwacomm v0.4.0 — Nested Message Encoding")
    print("=" * 55)

    print_sizes(GPSPosition, "GPSPosition field sizes")
    print_sizes(VehicleStatus, "VehicleStatus field sizes (position = 57 bits inline)")
    print_sizes(SensorBundle, "SensorBundle field sizes (2-level nesting)")

    demo_mode1()
    demo_mode2()
    demo_two_level_nesting()
