#!/usr/bin/env python3
"""Basic usage example for uwacomm.

This example demonstrates:
1. Defining a message with Pydantic
2. Encoding to compact binary format
3. Decoding back to a Pydantic model
4. Calculating message sizes
"""

from __future__ import annotations

from pydantic import Field

from uwacomm import BaseMessage, decode, encode, encoded_size, field_sizes


# Define a message class
class StatusReport(BaseMessage):
    """Underwater vehicle status report.

    This message uses bounded fields to enable compact encoding.
    """

    vehicle_id: int = Field(ge=0, le=255, description="Vehicle ID (0-255)")
    depth_cm: int = Field(ge=0, le=10000, description="Depth in centimeters (0-100m)")
    battery_pct: int = Field(ge=0, le=100, description="Battery percentage (0-100)")
    active: bool = Field(description="Vehicle active flag")


def main() -> None:
    """Run the basic usage example."""
    print("=" * 60)
    print("uwacomm Basic Usage Example")
    print("=" * 60)
    print()

    # Create a message instance
    print("1. Creating a status report message...")
    msg = StatusReport(vehicle_id=42, depth_cm=2500, battery_pct=87, active=True)

    print(f"   Vehicle ID: {msg.vehicle_id}")
    print(f"   Depth: {msg.depth_cm} cm ({msg.depth_cm / 100:.1f} m)")
    print(f"   Battery: {msg.battery_pct}%")
    print(f"   Active: {msg.active}")
    print()

    # Analyze field sizes
    print("2. Analyzing field sizes...")
    sizes = field_sizes(StatusReport)
    for field_name, bits in sizes.items():
        print(f"   {field_name}: {bits} bits")

    total_bits = sum(sizes.values())
    total_bytes = encoded_size(StatusReport)
    print(f"   Total: {total_bits} bits = {total_bytes} bytes")
    print()

    # Encode the message
    print("3. Encoding to compact binary format...")
    encoded_data = encode(msg)

    print(f"   Encoded size: {len(encoded_data)} bytes")
    print(f"   Hex: {encoded_data.hex()}")
    print(f"   Binary: {' '.join(format(b, '08b') for b in encoded_data)}")
    print()

    # Decode the message
    print("4. Decoding from binary...")
    decoded_msg = decode(StatusReport, encoded_data)

    print(f"   Vehicle ID: {decoded_msg.vehicle_id}")
    print(f"   Depth: {decoded_msg.depth_cm} cm")
    print(f"   Battery: {decoded_msg.battery_pct}%")
    print(f"   Active: {decoded_msg.active}")
    print()

    # Verify round-trip
    print("5. Verifying round-trip...")
    if decoded_msg == msg:
        print("   ✓ Round-trip successful! Messages match.")
    else:
        print("   ✗ Round-trip failed! Messages don't match.")
    print()

    # Compare to naive encoding
    print("6. Comparing to naive JSON encoding...")

    json_str = msg.model_dump_json()
    json_bytes = json_str.encode("utf-8")

    print(f"   uwacomm size: {len(encoded_data)} bytes")
    print(f"   JSON size: {len(json_bytes)} bytes")
    print(f"   Compression ratio: {len(json_bytes) / len(encoded_data):.1f}x")
    print()

    print("=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
