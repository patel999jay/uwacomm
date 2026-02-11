#!/usr/bin/env python3
"""Example: Using the generated .proto file.

This example demonstrates:
1. How to compile the generated .proto file with protoc
2. How to use the compiled protobuf Python code
3. Interoperability between uwacomm and Protobuf messages

Prerequisites:
    pip install protobuf

    # Install protobuf compiler (protoc):
    # Ubuntu/Debian: sudo apt-get install protobuf-compiler
    # macOS: brew install protobuf
    # Or download from: https://github.com/protocolbuffers/protobuf/releases

Usage:
    1. First run: python examples/protobuf_schema.py
       This generates underwater_vehicle_status.proto

    2. Compile the .proto file:
       protoc --python_out=. underwater_vehicle_status.proto

    3. Run this example:
       python examples/using_generated_proto.py
"""

from __future__ import annotations

import enum
import sys
from pathlib import Path
from typing import ClassVar, Optional

from pydantic import Field

from uwacomm import BaseMessage, encode, encoded_size


class MissionPhase(enum.Enum):
    """Mission phase enumeration."""

    STARTUP = 1
    TRANSIT = 2
    SURVEY = 3
    RETURN = 4
    SHUTDOWN = 5


class UnderwaterVehicleStatus(BaseMessage):
    """Complete underwater vehicle status message (same as protobuf_schema.py)."""

    # Vehicle identification
    vehicle_id: int = Field(ge=0, le=255, description="Unique vehicle identifier")

    # Mission state
    mission_phase: MissionPhase = Field(description="Current mission phase")
    mission_time_sec: int = Field(ge=0, le=86400, description="Mission elapsed time in seconds")

    # Navigation
    latitude_e7: int = Field(
        ge=-900000000, le=900000000, description="Latitude * 1e7 (decimal degrees)"
    )
    longitude_e7: int = Field(
        ge=-1800000000, le=1800000000, description="Longitude * 1e7 (decimal degrees)"
    )
    depth_cm: int = Field(ge=0, le=100000, description="Depth in centimeters (0-1000m)")

    # Vehicle health
    battery_pct: int = Field(ge=0, le=100, description="Battery state of charge")
    water_detected: bool = Field(description="Water intrusion alarm")
    emergency: bool = Field(description="Emergency flag")

    uwacomm_max_bytes: ClassVar[Optional[int]] = 64
    uwacomm_id: ClassVar[Optional[int]] = 100


def main() -> None:
    """Run the protobuf usage example."""
    print("=" * 70)
    print("Using Generated Protobuf Schema - Example")
    print("=" * 70)
    print()

    # Step 1: Check if .proto file exists
    proto_file = Path("underwater_vehicle_status.proto")
    if not proto_file.exists():
        print("⚠️  .proto file not found!")
        print()
        print("Please run the schema generation example first:")
        print("  python examples/protobuf_schema.py")
        print()
        return

    print(f"✓ Found {proto_file}")
    print()

    # Step 2: Check if compiled protobuf module exists
    pb2_file = Path("underwater_vehicle_status_pb2.py")
    if not pb2_file.exists():
        print("⚠️  Compiled protobuf module not found!")
        print()
        print("To compile the .proto file, run:")
        print("  protoc --python_out=. underwater_vehicle_status.proto")
        print()
        print("Installation:")
        print("  Ubuntu/Debian: sudo apt-get install protobuf-compiler")
        print("  macOS:         brew install protobuf")
        print("  Windows:       Download from https://github.com/protocolbuffers/protobuf/releases")
        print()
        return

    print(f"✓ Found compiled protobuf module: {pb2_file}")
    print()

    # Step 3: Import the generated protobuf module
    # Add current directory to Python path to allow import
    root_dir = Path(__file__).parent.parent.absolute()
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    try:
        import underwater_vehicle_status_pb2 as pb2

        print("✓ Successfully imported protobuf module")
        print()
    except ImportError as e:
        print(f"✗ Failed to import protobuf module: {e}")
        print()
        print("Make sure you have protobuf installed:")
        print("  pip install protobuf")
        print()
        print("Also ensure the module is in the Python path.")
        print(f"Tried to import from: {root_dir}")
        print()
        return

    # Step 4: Create a Pydantic message
    print("1. Creating message with uwacomm (Pydantic)...")
    uwacomm_msg = UnderwaterVehicleStatus(
        vehicle_id=42,
        mission_phase=MissionPhase.SURVEY,
        mission_time_sec=3600,
        latitude_e7=377950000,  # 37.795° N (San Francisco Bay)
        longitude_e7=-1223970000,  # -122.397° W
        depth_cm=5000,  # 50 meters
        battery_pct=75,
        water_detected=False,
        emergency=False,
    )
    print(f"   Vehicle: {uwacomm_msg.vehicle_id}")
    print(f"   Phase: {uwacomm_msg.mission_phase.name}")
    print(f"   Depth: {uwacomm_msg.depth_cm / 100:.1f} m")
    print()

    # Step 5: Convert to Protobuf message
    print("2. Converting to Protobuf message...")
    pb_msg = pb2.UnderwaterVehicleStatus()
    pb_msg.vehicle_id = uwacomm_msg.vehicle_id
    pb_msg.mission_phase = uwacomm_msg.mission_phase.value - 1  # Enum ordinals differ
    pb_msg.mission_time_sec = uwacomm_msg.mission_time_sec
    pb_msg.latitude_e7 = uwacomm_msg.latitude_e7
    pb_msg.longitude_e7 = uwacomm_msg.longitude_e7
    pb_msg.depth_cm = uwacomm_msg.depth_cm
    pb_msg.battery_pct = uwacomm_msg.battery_pct
    pb_msg.water_detected = uwacomm_msg.water_detected
    pb_msg.emergency = uwacomm_msg.emergency
    print("   ✓ Converted to Protobuf message")
    print()

    # Step 6: Compare encoding sizes
    print("3. Comparing encoding methods...")
    print()

    # uwacomm compact encoding
    uwacomm_encoded = encode(uwacomm_msg)
    uwacomm_size = len(uwacomm_encoded)

    # Protobuf wire format
    pb_encoded = pb_msg.SerializeToString()
    pb_size = len(pb_encoded)

    print(f"   uwacomm compact: {uwacomm_size} bytes")
    print(f"   Protobuf wire:  {pb_size} bytes")
    print(f"   Difference:     {pb_size - uwacomm_size} bytes")
    print()
    print(f"   uwacomm is {pb_size / uwacomm_size:.1f}x more compact!")
    print()

    # Step 7: Show encoding breakdown
    print("4. uwacomm encoding breakdown:")
    print()
    from uwacomm import field_sizes

    sizes = field_sizes(UnderwaterVehicleStatus)
    for field_name, bits in sizes.items():
        print(f"   {field_name:20s}: {bits:3d} bits")
    total_bits = sum(sizes.values())
    print(f"   {'Total':20s}: {total_bits:3d} bits = {encoded_size(uwacomm_msg)} bytes")
    print()

    # Step 8: Use cases
    print("5. When to use each encoding:")
    print()
    print("   ✓ Use uwacomm for:")
    print("     - Underwater acoustic modems (80-5000 bps)")
    print("     - Satellite links with limited bandwidth")
    print("     - Any severely bandwidth-constrained channel")
    print()
    print("   ✓ Use Protobuf for:")
    print("     - General-purpose RPC (gRPC)")
    print("     - Logging and data storage")
    print("     - ROS2 message serialization")
    print("     - Cross-language interoperability")
    print()

    # Step 9: Workflow recommendation
    print("6. Recommended workflow:")
    print()
    print("   1. Define schema in Pydantic (uwacomm)")
    print("   2. Generate .proto for documentation/interop")
    print("   3. Use uwacomm encoding for acoustic transmission")
    print("   4. Convert to Protobuf for ROS2/logging/analysis")
    print()

    print("=" * 70)
    print("Example complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
