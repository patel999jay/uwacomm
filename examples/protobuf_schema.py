#!/usr/bin/env python3
"""Protobuf schema generation example for uwacomm.

This example demonstrates:
1. Generating .proto schemas from Pydantic models
2. Documenting field constraints
3. Interoperability considerations
"""

from __future__ import annotations

import enum
from typing import ClassVar, Optional

from pydantic import Field

from uwacomm import BaseMessage
from uwacomm.protobuf import to_proto_schema


class MissionPhase(enum.Enum):
    """Mission phase enumeration."""

    STARTUP = 1
    TRANSIT = 2
    SURVEY = 3
    RETURN = 4
    SHUTDOWN = 5


class UnderwaterVehicleStatus(BaseMessage):
    """Complete underwater vehicle status message."""

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
    """Run the protobuf schema generation example."""
    print("=" * 60)
    print("uwacomm Protobuf Schema Generation Example")
    print("=" * 60)
    print()

    # Generate proto schema
    print("1. Generating .proto schema...")
    proto_schema = to_proto_schema(
        UnderwaterVehicleStatus, package="underwater.messages", syntax="proto3"
    )

    print()
    print("=" * 60)
    print("Generated .proto schema:")
    print("=" * 60)
    print(proto_schema)
    print("=" * 60)
    print()

    # Save to file
    output_file = "underwater_vehicle_status.proto"
    print(f"2. Saving schema to {output_file}...")

    with open(output_file, "w") as f:
        f.write(proto_schema)

    print(f"   ✓ Schema saved to {output_file}")
    print()

    # Display interoperability notes
    print("3. Interoperability Notes:")
    print()
    print("   • The generated .proto is for DOCUMENTATION and SCHEMA EXCHANGE")
    print("   • uwacomm compact encoding ≠ Protobuf wire format")
    print("   • Use uwacomm encoding for bandwidth-constrained channels")
    print("   • Use Protobuf encoding for general-purpose serialization")
    print()
    print("   Example workflow:")
    print("   1. Define schema in Pydantic (once)")
    print("   2. Generate .proto for other languages/tools")
    print("   3. Encode with uwacomm for acoustic transmission")
    print("   4. Convert to Protobuf for ROS2/logging (future v0.2.0+)")
    print()

    # Show size comparison
    print("4. Encoding Size Analysis:")
    print()

    from uwacomm import encode, encoded_size, field_sizes

    msg = UnderwaterVehicleStatus(
        vehicle_id=42,
        mission_phase=MissionPhase.SURVEY,
        mission_time_sec=3600,
        latitude_e7=377950000,  # 37.795° N
        longitude_e7=-1223970000,  # -122.397° W
        depth_cm=5000,
        battery_pct=75,
        water_detected=False,
        emergency=False,
    )

    sizes = field_sizes(msg)
    total_bits = sum(sizes.values())
    total_bytes = encoded_size(msg)

    print("   Field-by-field bit usage:")
    for field_name, bits in sizes.items():
        print(f"     {field_name:20s}: {bits:3d} bits")

    print()
    print(f"   Total (uwacomm compact): {total_bits} bits = {total_bytes} bytes")
    print()

    # Compare to JSON
    json_bytes = len(msg.model_dump_json().encode("utf-8"))
    print(f"   JSON size: {json_bytes} bytes")
    print(f"   Compression ratio: {json_bytes / total_bytes:.1f}x smaller with uwacomm")
    print()

    print("=" * 60)
    print("Example complete!")
    print(f"Output file: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
