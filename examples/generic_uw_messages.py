#!/usr/bin/env python3
"""Generic underwater vehicle messages for demonstration.

These messages demonstrate typical underwater vehicle communication patterns
without revealing any proprietary message structures.

Usage: uwacomm --analyze generic_uw_messages.py
"""

from uwacomm import BaseMessage, BoundedInt, BoundedFloat
from typing import ClassVar, Optional


# ============================================================================
# Telemetry Messages
# ============================================================================

class VehicleStatus(BaseMessage):
    """Generic vehicle status message (similar to heartbeat).

    Typical use: Periodic status updates from vehicle to topside.
    Frequency: Every 10-30 seconds depending on mission phase.
    """
    # Position (GPS when surfaced, dead reckoning when submerged)
    position_lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    position_lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)

    # Depth in meters (typical max depth for most AUVs)
    depth_m: float = BoundedFloat(min=0.0, max=5000.0, precision=2)

    # Vehicle state
    heading_deg: float = BoundedFloat(min=0.0, max=360.0, precision=1)
    speed_ms: float = BoundedFloat(min=0.0, max=3.0, precision=2)  # 0-3 m/s typical
    battery_pct: int = BoundedInt(ge=0, le=100)

    uwacomm_id: ClassVar[Optional[int]] = 10
    uwacomm_max_bytes: ClassVar[Optional[int]] = 64


class SensorData(BaseMessage):
    """Generic environmental sensor data.

    Typical use: Scientific data collection during surveys.
    Frequency: Every 1-5 minutes depending on mission.
    """
    # Water properties (CTD-like sensors)
    water_temp_c: float = BoundedFloat(min=-2.0, max=35.0, precision=1)
    salinity_psu: float = BoundedFloat(min=0.0, max=40.0, precision=2)
    pressure_bar: float = BoundedFloat(min=0.0, max=500.0, precision=2)

    # Optional sensors
    dissolved_oxygen: float = BoundedFloat(min=0.0, max=15.0, precision=2)  # mg/L
    turbidity_ntu: float = BoundedFloat(min=0.0, max=1000.0, precision=1)  # NTU

    uwacomm_id: ClassVar[Optional[int]] = 20
    uwacomm_max_bytes: ClassVar[Optional[int]] = 64


class NavigationUpdate(BaseMessage):
    """Generic navigation data (DVL + IMU fusion).

    Typical use: High-rate navigation updates for control systems.
    Frequency: 1-10 Hz depending on mission phase.
    """
    # Current position estimate (fused from GPS/DVL/dead reckoning)
    est_lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    est_lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)
    est_depth: float = BoundedFloat(min=0.0, max=5000.0, precision=2)

    # Velocity (DVL-like, body frame)
    vel_north: float = BoundedFloat(min=-5.0, max=5.0, precision=3)  # m/s
    vel_east: float = BoundedFloat(min=-5.0, max=5.0, precision=3)   # m/s
    vel_down: float = BoundedFloat(min=-2.0, max=2.0, precision=3)   # m/s

    # Orientation (IMU)
    roll_deg: float = BoundedFloat(min=-180.0, max=180.0, precision=1)
    pitch_deg: float = BoundedFloat(min=-90.0, max=90.0, precision=1)

    uwacomm_id: ClassVar[Optional[int]] = 30
    uwacomm_max_bytes: ClassVar[Optional[int]] = 96


# ============================================================================
# Command Messages
# ============================================================================

class WaypointCommand(BaseMessage):
    """Generic waypoint command.

    Typical use: Send vehicle to specific location.
    Direction: Topside → Vehicle or Vehicle → Vehicle (swarm).
    """
    target_lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    target_lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)
    target_depth: float = BoundedFloat(min=0.0, max=5000.0, precision=2)

    # Tolerances
    radius_m: float = BoundedFloat(min=1.0, max=100.0, precision=1)
    speed_ms: float = BoundedFloat(min=0.5, max=2.0, precision=1)

    # Waypoint ID for tracking
    waypoint_id: int = BoundedInt(ge=0, le=255)

    uwacomm_id: ClassVar[Optional[int]] = 100
    uwacomm_max_bytes: ClassVar[Optional[int]] = 64


class MissionCommand(BaseMessage):
    """Generic mission control command.

    Typical use: Control mission execution (start, pause, abort, etc.).
    Direction: Topside → Vehicle or Lead Vehicle → Swarm.
    """
    # Command types: 0=abort, 1=start, 2=pause, 3=resume, 4=surface, etc.
    command_type: int = BoundedInt(ge=0, le=15)
    mission_id: int = BoundedInt(ge=0, le=255)

    # Generic parameters (meaning depends on command_type)
    param1: int = BoundedInt(ge=0, le=65535)
    param2: int = BoundedInt(ge=0, le=65535)

    uwacomm_id: ClassVar[Optional[int]] = 101
    uwacomm_max_bytes: ClassVar[Optional[int]] = 32


# ============================================================================
# Acknowledgment Messages
# ============================================================================

class CommandAck(BaseMessage):
    """Generic command acknowledgment.

    Typical use: Acknowledge receipt and status of commands.
    Direction: Vehicle → Topside or Vehicle → Vehicle.
    """
    acked_msg_id: int = BoundedInt(ge=0, le=255)
    ack_status: int = BoundedInt(ge=0, le=3)  # 0=success, 1=pending, 2=failed, 3=unknown
    error_code: int = BoundedInt(ge=0, le=255)

    uwacomm_id: ClassVar[Optional[int]] = 200
    uwacomm_max_bytes: ClassVar[Optional[int]] = 16


# ============================================================================
# Swarm Coordination Messages
# ============================================================================

class FormationUpdate(BaseMessage):
    """Generic formation update for swarm coordination.

    Typical use: Multi-vehicle formation flying.
    Direction: Lead Vehicle → Followers (broadcast).
    """
    leader_id: int = BoundedInt(ge=0, le=255)
    formation_type: int = BoundedInt(ge=0, le=15)  # 0=line, 1=grid, 2=circle, etc.

    # Relative offsets for this vehicle
    offset_north: float = BoundedFloat(min=-1000.0, max=1000.0, precision=1)
    offset_east: float = BoundedFloat(min=-1000.0, max=1000.0, precision=1)
    offset_depth: float = BoundedFloat(min=-100.0, max=100.0, precision=1)

    uwacomm_id: ClassVar[Optional[int]] = 50
    uwacomm_max_bytes: ClassVar[Optional[int]] = 48


if __name__ == "__main__":
    # Quick demonstration
    from uwacomm import encode

    print("Generic Underwater Vehicle Messages")
    print("=" * 80)

    # Example 1: VehicleStatus
    status = VehicleStatus(
        position_lat=42.358894,
        position_lon=-71.063611,
        depth_m=125.75,
        heading_deg=45.5,
        speed_ms=1.25,
        battery_pct=78
    )
    encoded = encode(status)
    print(f"VehicleStatus:      {len(encoded):3d} bytes (lat, lon, depth, heading, speed, battery)")

    # Example 2: SensorData
    sensors = SensorData(
        water_temp_c=12.3,
        salinity_psu=35.2,
        pressure_bar=125.5,
        dissolved_oxygen=6.8,
        turbidity_ntu=15.0
    )
    encoded = encode(sensors)
    print(f"SensorData:         {len(encoded):3d} bytes (temp, salinity, pressure, O2, turbidity)")

    # Example 3: NavigationUpdate
    nav = NavigationUpdate(
        est_lat=42.360,
        est_lon=-71.065,
        est_depth=150.0,
        vel_north=1.2,
        vel_east=0.5,
        vel_down=-0.1,
        roll_deg=2.5,
        pitch_deg=-1.3
    )
    encoded = encode(nav)
    print(f"NavigationUpdate:   {len(encoded):3d} bytes (position, velocity, orientation)")

    # Example 4: WaypointCommand
    waypoint = WaypointCommand(
        target_lat=42.365,
        target_lon=-71.070,
        target_depth=100.0,
        radius_m=10.0,
        speed_ms=1.5,
        waypoint_id=5
    )
    encoded = encode(waypoint)
    print(f"WaypointCommand:    {len(encoded):3d} bytes (target position, radius, speed)")

    # Example 5: CommandAck
    ack = CommandAck(
        acked_msg_id=100,
        ack_status=0,
        error_code=0
    )
    encoded = encode(ack)
    print(f"CommandAck:         {len(encoded):3d} bytes (msg_id, status, error_code)")

    print()
    print("All messages demonstrate bandwidth-efficient encoding for underwater comms.")
