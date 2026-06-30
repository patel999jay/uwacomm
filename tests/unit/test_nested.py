"""Unit tests for nested BaseMessage encoding (v0.4.0)."""

from __future__ import annotations

from typing import ClassVar

import pytest

from uwacomm import (
    BaseMessage,
    BoundedInt,
    DecodeError,
    EncodeError,
    decode,
    encode,
    encoded_bits,
    encoded_size,
    field_sizes,
)
from uwacomm.models.fields import BoundedFloat

# ---------------------------------------------------------------------------
# Message definitions used across tests
# ---------------------------------------------------------------------------


class GPSPosition(BaseMessage):
    """Nested GPS coordinate message."""

    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)  # 28 bits
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)  # 29 bits


class VehicleStatus(BaseMessage):
    """Top-level message containing a nested GPSPosition."""

    vehicle_id: int = BoundedInt(ge=0, le=255)  # 8 bits
    position: GPSPosition
    depth_cm: int = BoundedInt(ge=0, le=50000)  # 16 bits
    battery: int = BoundedInt(ge=0, le=100)  # 7 bits

    uwacomm_id: ClassVar[int | None] = 20
    uwacomm_max_bytes: ClassVar[int | None] = 64


class InnerMsg(BaseMessage):
    x: int = BoundedInt(ge=0, le=15)  # 4 bits
    y: int = BoundedInt(ge=0, le=15)  # 4 bits


class MiddleMsg(BaseMessage):
    inner: InnerMsg
    z: int = BoundedInt(ge=0, le=3)  # 2 bits


class OuterMsg(BaseMessage):
    mid: MiddleMsg
    flag: bool  # 1 bit


# ---------------------------------------------------------------------------
# Basic round-trip
# ---------------------------------------------------------------------------


class TestNestedRoundTrip:
    def test_basic_nested_roundtrip(self) -> None:
        pos = GPSPosition(lat=44.648766, lon=-63.575237)
        msg = VehicleStatus(vehicle_id=7, position=pos, depth_cm=1250, battery=83)

        data = encode(msg)
        decoded = decode(VehicleStatus, data)

        assert decoded.vehicle_id == 7
        assert decoded.position.lat == pytest.approx(pos.lat, abs=1e-6)
        assert decoded.position.lon == pytest.approx(pos.lon, abs=1e-6)
        assert decoded.depth_cm == 1250
        assert decoded.battery == 83

    def test_nested_at_boundary_values(self) -> None:
        pos = GPSPosition(lat=-90.0, lon=180.0)
        msg = VehicleStatus(vehicle_id=0, position=pos, depth_cm=0, battery=0)

        decoded = decode(VehicleStatus, encode(msg))
        assert decoded.position.lat == pytest.approx(-90.0, abs=1e-6)
        assert decoded.position.lon == pytest.approx(180.0, abs=1e-6)
        assert decoded.vehicle_id == 0
        assert decoded.battery == 0

    def test_two_level_deep_nesting(self) -> None:
        inner = InnerMsg(x=7, y=12)
        mid = MiddleMsg(inner=inner, z=2)
        outer = OuterMsg(mid=mid, flag=True)

        decoded = decode(OuterMsg, encode(outer))
        assert decoded.mid.inner.x == 7
        assert decoded.mid.inner.y == 12
        assert decoded.mid.z == 2
        assert decoded.flag is True

    def test_multiple_roundtrips_are_deterministic(self) -> None:
        pos = GPSPosition(lat=42.358894, lon=-71.063611)
        msg = VehicleStatus(vehicle_id=3, position=pos, depth_cm=255, battery=50)
        data1 = encode(msg)
        data2 = encode(msg)
        assert data1 == data2

    def test_nested_with_mode2_id(self) -> None:
        pos = GPSPosition(lat=0.0, lon=0.0)
        msg = VehicleStatus(vehicle_id=1, position=pos, depth_cm=100, battery=60)
        data = encode(msg, include_id=True)
        decoded = decode(VehicleStatus, data, include_id=True)
        assert decoded.vehicle_id == 1


# ---------------------------------------------------------------------------
# Size calculation
# ---------------------------------------------------------------------------


class TestNestedSizing:
    def test_nested_encoded_size_correct(self) -> None:
        # GPSPosition: 28 + 29 = 57 bits
        # VehicleStatus: 8 + 57 + 16 + 7 = 88 bits = 11 bytes
        assert encoded_bits(VehicleStatus) == 88
        assert encoded_size(VehicleStatus) == 11

    def test_field_sizes_shows_nested_as_aggregate(self) -> None:
        sizes = field_sizes(VehicleStatus)
        assert sizes["vehicle_id"] == 8
        assert sizes["position"] == 57  # total of nested schema
        assert sizes["depth_cm"] == 16
        assert sizes["battery"] == 7

    def test_two_level_nesting_size(self) -> None:
        # InnerMsg: 4+4=8, MiddleMsg: 8+2=10, OuterMsg: 10+1=11 bits
        assert encoded_bits(OuterMsg) == 11
        assert encoded_size(OuterMsg) == 2


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestNestedErrors:
    def test_wrong_type_for_nested_field(self) -> None:
        msg = VehicleStatus.model_construct(
            vehicle_id=1,
            position="not_a_gps",  # wrong type
            depth_cm=0,
            battery=50,
        )
        with pytest.raises(EncodeError):
            encode(msg)

    def test_truncated_data_raises_decode_error(self) -> None:
        pos = GPSPosition(lat=10.0, lon=20.0)
        msg = VehicleStatus(vehicle_id=1, position=pos, depth_cm=100, battery=50)
        data = encode(msg)
        with pytest.raises(DecodeError):
            decode(VehicleStatus, data[:5])  # truncated
