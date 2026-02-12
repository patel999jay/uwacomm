#!/usr/bin/env python3
"""Demonstrate all three encoding modes with generic underwater vehicle messages.

This example shows:
- Mode 1: Point-to-point (maximum compression)
- Mode 2: Self-describing messages (logging, replay)
- Mode 3: Multi-vehicle routing (swarm robotics)
- Broadcast patterns for swarm coordination
"""

from generic_uw_messages import (
    VehicleStatus,
    SensorData,
    WaypointCommand,
    FormationUpdate,
    CommandAck
)
from uwacomm import (
    encode, decode,
    encode_with_routing, decode_with_routing,
    register_message, decode_by_id
)


def demo_mode1_point_to_point():
    """Mode 1: Point-to-point (maximum compression).

    Use case: Single AUV ↔ Topside station
    Advantage: 8.2% smaller than DCCL, zero overhead
    """
    print("=" * 80)
    print("MODE 1: POINT-TO-POINT (MAXIMUM COMPRESSION)")
    print("=" * 80)
    print()
    print("Scenario: Single AUV sending periodic status to topside")
    print()

    # Create vehicle status message
    status = VehicleStatus(
        position_lat=42.358894,
        position_lon=-71.063611,
        depth_m=125.50,
        heading_deg=45.0,
        speed_ms=1.25,
        battery_pct=78
    )

    # Encode (Mode 1 - no ID, minimal overhead)
    encoded = encode(status)

    print(f"Message: VehicleStatus")
    print(f"  Position: ({status.position_lat:.6f}, {status.position_lon:.6f})")
    print(f"  Depth: {status.depth_m}m")
    print(f"  Heading: {status.heading_deg}°")
    print(f"  Speed: {status.speed_ms} m/s")
    print(f"  Battery: {status.battery_pct}%")
    print()
    print(f"Encoded size: {len(encoded)} bytes")
    print(f"Binary (hex): {encoded.hex()}")
    print()

    # Decode (decoder knows message type)
    decoded = decode(VehicleStatus, encoded)
    print(f"Decoded successfully: ✓")
    print(f"  Depth: {decoded.depth_m}m, Battery: {decoded.battery_pct}%")
    print()
    print("-" * 80)
    print()


def demo_mode2_self_describing():
    """Mode 2: Self-describing messages.

    Use case: Logging to files, message replay, ad-hoc communications
    Advantage: Auto-decode without knowing message type upfront
    """
    print("=" * 80)
    print("MODE 2: SELF-DESCRIBING MESSAGES (LOGGING & REPLAY)")
    print("=" * 80)
    print()
    print("Scenario: Logging multiple message types to file for later analysis")
    print()

    # Register all message types that might be received
    register_message(VehicleStatus)
    register_message(SensorData)
    register_message(WaypointCommand)

    # Create sensor data message
    sensors = SensorData(
        water_temp_c=12.3,
        salinity_psu=35.2,
        pressure_bar=125.5,
        dissolved_oxygen=6.8,
        turbidity_ntu=15.0
    )

    # Encode with ID (Mode 2)
    encoded = encode(sensors, include_id=True)

    print(f"Message: SensorData (ID={SensorData.uwacomm_id})")
    print(f"  Water temp: {sensors.water_temp_c}°C")
    print(f"  Salinity: {sensors.salinity_psu} PSU")
    print(f"  Pressure: {sensors.pressure_bar} bar")
    print(f"  Dissolved O2: {sensors.dissolved_oxygen} mg/L")
    print(f"  Turbidity: {sensors.turbidity_ntu} NTU")
    print()
    print(f"Encoded size: {len(encoded)} bytes (includes message ID)")
    print()

    # Auto-decode by ID (don't need to know the type!)
    decoded = decode_by_id(encoded)
    print(f"Auto-decoded as: {type(decoded).__name__}")
    print(f"  Water temp: {decoded.water_temp_c}°C")
    print(f"  Salinity: {decoded.salinity_psu} PSU")
    print()

    # Simulate logging multiple message types
    print("Simulating message log:")
    messages = [
        VehicleStatus(position_lat=42.36, position_lon=-71.06, depth_m=100.0,
                     heading_deg=90.0, speed_ms=1.5, battery_pct=75),
        SensorData(water_temp_c=11.5, salinity_psu=34.8, pressure_bar=100.0,
                  dissolved_oxygen=7.2, turbidity_ntu=12.0),
        WaypointCommand(target_lat=42.37, target_lon=-71.07, target_depth=150.0,
                       radius_m=10.0, speed_ms=1.0, waypoint_id=3)
    ]

    for msg in messages:
        enc = encode(msg, include_id=True)
        dec = decode_by_id(enc)
        print(f"  Logged: {type(dec).__name__} ({len(enc)} bytes)")

    print()
    print("-" * 80)
    print()


def demo_mode3_multi_vehicle():
    """Mode 3: Multi-vehicle routing.

    Use case: Swarm robotics, multi-AUV missions, mesh networks
    Advantage: Built-in source/dest addressing, priority, ACK support
    """
    print("=" * 80)
    print("MODE 3: MULTI-VEHICLE ROUTING (SWARM COORDINATION)")
    print("=" * 80)
    print()
    print("Scenario: 3 AUVs coordinating with topside station (ID=0)")
    print()

    # Vehicle 3 sends status to topside
    print("1. Vehicle 3 → Topside (high priority, ACK requested)")
    status = VehicleStatus(
        position_lat=42.360,
        position_lon=-71.065,
        depth_m=150.0,
        heading_deg=90.0,
        speed_ms=1.5,
        battery_pct=65
    )

    encoded = encode_with_routing(
        status,
        source_id=3,
        dest_id=0,      # Topside
        priority=2,     # High priority
        ack_requested=True
    )

    print(f"   Encoded size: {len(encoded)} bytes (includes routing + ID)")

    # Topside receives
    routing, decoded = decode_with_routing(VehicleStatus, encoded)
    print(f"   Topside received:")
    print(f"     From vehicle: {routing.source_id}")
    print(f"     Priority: {routing.priority} (0=low, 3=high)")
    print(f"     ACK requested: {routing.ack_requested}")
    print(f"     Vehicle at depth: {decoded.depth_m}m, battery: {decoded.battery_pct}%")
    print()

    # Topside sends ACK back
    print("2. Topside → Vehicle 3 (ACK response)")
    ack = CommandAck(
        acked_msg_id=10,  # VehicleStatus message ID
        ack_status=0,     # Success
        error_code=0
    )

    ack_encoded = encode_with_routing(
        ack,
        source_id=0,
        dest_id=3,
        priority=3  # Urgent (ACK)
    )
    print(f"   ACK size: {len(ack_encoded)} bytes")
    print()

    # Topside sends waypoint command to Vehicle 1
    print("3. Topside → Vehicle 1 (waypoint command)")
    waypoint = WaypointCommand(
        target_lat=42.365,
        target_lon=-71.070,
        target_depth=100.0,
        radius_m=10.0,
        speed_ms=1.0,
        waypoint_id=5
    )

    cmd_encoded = encode_with_routing(
        waypoint,
        source_id=0,
        dest_id=1,
        priority=2,
        ack_requested=True
    )

    routing, cmd = decode_with_routing(WaypointCommand, cmd_encoded)
    print(f"   Vehicle 1 received waypoint:")
    print(f"     Target: ({cmd.target_lat:.6f}, {cmd.target_lon:.6f}) @ {cmd.target_depth}m")
    print(f"     Speed: {cmd.speed_ms} m/s, Radius: {cmd.radius_m}m")
    print()

    print("-" * 80)
    print()


def demo_broadcast_pattern():
    """Demonstrate broadcast messaging for swarm coordination.

    Use case: Formation updates, mission updates to all vehicles
    """
    print("=" * 80)
    print("BROADCAST PATTERN (SWARM COORDINATION)")
    print("=" * 80)
    print()
    print("Scenario: Lead vehicle (ID=1) broadcasts formation update to swarm")
    print()

    # Lead vehicle broadcasts formation update
    formation = FormationUpdate(
        leader_id=1,
        formation_type=1,  # Grid formation
        offset_north=50.0,
        offset_east=25.0,
        offset_depth=10.0
    )

    # Encode with dest_id=255 (broadcast)
    broadcast_msg = encode_with_routing(
        formation,
        source_id=1,
        dest_id=255,  # 255 = broadcast to all
        priority=2
    )

    print(f"Lead Vehicle (ID=1) broadcasts:")
    print(f"  Message: FormationUpdate")
    print(f"  Destination: 255 (BROADCAST)")
    print(f"  Formation type: Grid")
    print(f"  Encoded size: {len(broadcast_msg)} bytes")
    print()

    # All vehicles receive and process
    routing, update = decode_with_routing(FormationUpdate, broadcast_msg)

    print(f"All vehicles receive:")
    print(f"  From: Vehicle {routing.source_id}")
    print(f"  Dest: {routing.dest_id} (broadcast)")
    print(f"  Formation: {update.formation_type}")
    print(f"  Offsets: N={update.offset_north}m, E={update.offset_east}m, D={update.offset_depth}m")
    print()

    # Simulate multiple vehicles processing
    vehicle_ids = [2, 3, 4, 5]
    print("Vehicles processing broadcast:")
    for vid in vehicle_ids:
        if routing.dest_id == 255 or routing.dest_id == vid:
            print(f"  Vehicle {vid}: Adjusting formation position")

    print()
    print("-" * 80)
    print()


def bandwidth_summary():
    """Show bandwidth comparison across modes."""
    print("=" * 80)
    print("BANDWIDTH SUMMARY")
    print("=" * 80)
    print()

    status = VehicleStatus(
        position_lat=42.358,
        position_lon=-71.064,
        depth_m=125.5,
        heading_deg=45.0,
        speed_ms=1.25,
        battery_pct=78
    )

    mode1 = encode(status)
    mode2 = encode(status, include_id=True)
    mode3 = encode_with_routing(status, source_id=3, dest_id=0)

    print(f"VehicleStatus message:")
    print(f"  Mode 1 (Point-to-Point):  {len(mode1):3d} bytes")
    print(f"  Mode 2 (Self-Describing): {len(mode2):3d} bytes  (+{len(mode2)-len(mode1)} bytes for ID)")
    print(f"  Mode 3 (Multi-Vehicle):   {len(mode3):3d} bytes  (+{len(mode3)-len(mode1)} bytes for routing+ID)")
    print()

    # Transmission time at 80 bps (typical acoustic modem)
    bps = 80
    print(f"Transmission time @ {bps} bps:")
    print(f"  Mode 1: {len(mode1) * 8 / bps:.2f} seconds")
    print(f"  Mode 2: {len(mode2) * 8 / bps:.2f} seconds")
    print(f"  Mode 3: {len(mode3) * 8 / bps:.2f} seconds")
    print()


def main():
    """Run all demonstrations."""
    demo_mode1_point_to_point()
    demo_mode2_self_describing()
    demo_mode3_multi_vehicle()
    demo_broadcast_pattern()
    bandwidth_summary()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✓ Mode 1: Maximum compression for point-to-point links")
    print("✓ Mode 2: Self-describing messages for logging and flexibility")
    print("✓ Mode 3: Multi-vehicle routing with priority and ACK support")
    print("✓ Broadcast: Efficient swarm coordination")
    print()
    print("Choose the mode that fits your mission requirements!")
    print()


if __name__ == "__main__":
    main()
