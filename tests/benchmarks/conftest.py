"""Shared fixtures for performance benchmarks.

Defines reusable message types and encoded payloads used across all benchmark
files. Messages represent realistic small, medium, and large underwater vehicle
telemetry payloads.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from uwacomm import BaseMessage, BoundedInt, FixedBytes, encode
from uwacomm.models.fields import BoundedFloat


class SmallMessage(BaseMessage):
    """Minimal 3-field message — baseline benchmark."""

    vehicle_id: int = BoundedInt(ge=0, le=255)
    depth_cm: int = BoundedInt(ge=0, le=10000)
    battery_pct: int = BoundedInt(ge=0, le=100)
    uwacomm_id: ClassVar[int | None] = 100


class MediumMessage(BaseMessage):
    """Typical 7-field underwater vehicle telemetry message."""

    vehicle_id: int = BoundedInt(ge=0, le=255)
    depth_cm: int = BoundedInt(ge=0, le=10000)
    latitude: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    longitude: float = BoundedFloat(min=-180.0, max=180.0, precision=6)
    battery_pct: int = BoundedInt(ge=0, le=100)
    speed_knots: float = BoundedFloat(min=0.0, max=10.0, precision=2)
    heading_deg: float = BoundedFloat(min=0.0, max=360.0, precision=1)
    uwacomm_id: ClassVar[int | None] = 101


class LargeMessage(BaseMessage):
    """Large message with fixed-byte payload — requires fragmentation."""

    sensor_data: bytes = FixedBytes(length=100)
    vehicle_id: int = BoundedInt(ge=0, le=255)
    sequence: int = BoundedInt(ge=0, le=65535)
    uwacomm_id: ClassVar[int | None] = 102


@pytest.fixture
def small_msg() -> SmallMessage:
    return SmallMessage(vehicle_id=42, depth_cm=1500, battery_pct=87)


@pytest.fixture
def medium_msg() -> MediumMessage:
    return MediumMessage(
        vehicle_id=1,
        depth_cm=500,
        latitude=44.1234,
        longitude=-63.5678,
        battery_pct=92,
        speed_knots=2.5,
        heading_deg=180.0,
    )


@pytest.fixture
def large_msg() -> LargeMessage:
    return LargeMessage(sensor_data=b"x" * 100, vehicle_id=5, sequence=1234)


@pytest.fixture
def small_encoded(small_msg: SmallMessage) -> bytes:
    return encode(small_msg)


@pytest.fixture
def medium_encoded(medium_msg: MediumMessage) -> bytes:
    return encode(medium_msg)


@pytest.fixture
def large_encoded(large_msg: LargeMessage) -> bytes:
    return encode(large_msg)
