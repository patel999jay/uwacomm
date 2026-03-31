"""Performance benchmarks for multi-vehicle routing header encode/decode.

Measures the overhead of the routing header layer (Mode 3) including
encode_with_routing, decode_with_routing, and the decode_by_id dispatch path.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from uwacomm import BaseMessage, BoundedInt, encode
from uwacomm.routing import (
    decode_by_id,
    decode_with_routing,
    encode_with_routing,
    register_message,
)


class TelemetryMsg(BaseMessage):
    """Standard 3-field telemetry message used for routing benchmarks."""

    vehicle_id: int = BoundedInt(ge=0, le=255)
    depth_cm: int = BoundedInt(ge=0, le=10000)
    battery_pct: int = BoundedInt(ge=0, le=100)
    uwacomm_id: ClassVar[int | None] = 300


# Register once at module level so decode_by_id benchmark works
register_message(TelemetryMsg)


class TestRoutingEncodeSpeed:
    """Benchmark encode_with_routing() performance."""

    def test_encode_with_routing(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark encoding a message with a routing header attached."""
        msg = TelemetryMsg(vehicle_id=1, depth_cm=500, battery_pct=87)
        result = benchmark(encode_with_routing, msg, 1, 2)
        assert isinstance(result, bytes)

    def test_encode_with_routing_broadcast(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark encoding a broadcast message (dest_id=255)."""
        msg = TelemetryMsg(vehicle_id=1, depth_cm=500, battery_pct=87)
        result = benchmark(encode_with_routing, msg, 1, 255, 3, False)
        assert isinstance(result, bytes)


class TestRoutingDecodeSpeed:
    """Benchmark decode_with_routing() performance."""

    def test_decode_with_routing(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark decoding a message with routing header."""
        msg = TelemetryMsg(vehicle_id=1, depth_cm=500, battery_pct=87)
        encoded = encode_with_routing(msg, source_id=1, dest_id=2)
        result = benchmark(decode_with_routing, TelemetryMsg, encoded)
        assert result is not None
        routing_header, decoded_msg = result
        assert decoded_msg.vehicle_id == 1

    def test_decode_by_id_dispatch(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark the message-ID dispatch path (no prior type knowledge)."""
        msg = TelemetryMsg(vehicle_id=1, depth_cm=500, battery_pct=87)
        encoded = encode(msg, include_id=True)
        result = benchmark(decode_by_id, encoded)
        assert result is not None


class TestRoutingRoundtripSpeed:
    """Benchmark full routing encode→decode roundtrip."""

    def test_roundtrip_point_to_point(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark point-to-point routing roundtrip (src=1, dest=2)."""
        msg = TelemetryMsg(vehicle_id=1, depth_cm=500, battery_pct=87)

        def roundtrip() -> tuple[object, TelemetryMsg]:
            data = encode_with_routing(msg, source_id=1, dest_id=2)
            return decode_with_routing(TelemetryMsg, data)

        header, decoded = benchmark(roundtrip)
        assert decoded.vehicle_id == msg.vehicle_id

    def test_roundtrip_high_priority(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark high-priority routing roundtrip (priority=3, ack_requested=True)."""
        msg = TelemetryMsg(vehicle_id=3, depth_cm=1200, battery_pct=45)

        def roundtrip() -> tuple[object, TelemetryMsg]:
            data = encode_with_routing(msg, source_id=3, dest_id=0, priority=3, ack_requested=True)
            return decode_with_routing(TelemetryMsg, data)

        header, decoded = benchmark(roundtrip)
        assert decoded.vehicle_id == msg.vehicle_id


class TestRoutingVsBaseSpeed:
    """Compare routing overhead vs base encode/decode."""

    def test_encode_base(self, benchmark: pytest.FixtureRequest) -> None:
        """Baseline: encode without routing header."""
        msg = TelemetryMsg(vehicle_id=1, depth_cm=500, battery_pct=87)
        result = benchmark(encode, msg)
        assert isinstance(result, bytes)

    def test_encode_with_routing_overhead(self, benchmark: pytest.FixtureRequest) -> None:
        """Compare: encode with routing header (shows routing overhead)."""
        msg = TelemetryMsg(vehicle_id=1, depth_cm=500, battery_pct=87)
        result = benchmark(encode_with_routing, msg, 1, 2)
        assert isinstance(result, bytes)
