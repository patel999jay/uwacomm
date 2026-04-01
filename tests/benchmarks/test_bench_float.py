"""Performance benchmarks for bounded float encoding.

Measures how BoundedFloat precision level affects encode/decode throughput.
Higher precision means more bits required, which costs more CPU time.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from uwacomm import BaseMessage, BoundedFloat, decode, encode


class LowPrecisionMsg(BaseMessage):
    """Two-decimal-place lat/lon — minimal bit usage."""

    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=2)
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=2)
    uwacomm_id: ClassVar[int | None] = 200


class MedPrecisionMsg(BaseMessage):
    """Six-decimal-place lat/lon — ~11 cm GPS accuracy."""

    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)
    uwacomm_id: ClassVar[int | None] = 201


class HighPrecisionMsg(BaseMessage):
    """Six-decimal-place lat/lon — maximum supported precision."""

    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)
    uwacomm_id: ClassVar[int | None] = 202


class TestFloatEncodingSpeed:
    """Benchmark BoundedFloat encode at different precision levels."""

    def test_encode_low_precision_float(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark encoding floats with precision=2 (smallest bit footprint)."""
        msg = LowPrecisionMsg(lat=44.12, lon=-63.56)
        result = benchmark(encode, msg)
        assert isinstance(result, bytes)

    def test_encode_med_precision_float(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark encoding floats with precision=6 (typical GPS)."""
        msg = MedPrecisionMsg(lat=44.123456, lon=-63.567890)
        result = benchmark(encode, msg)
        assert isinstance(result, bytes)

    def test_encode_high_precision_float(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark encoding floats with precision=8 (largest bit footprint)."""
        msg = HighPrecisionMsg(lat=44.12345678, lon=-63.56789012)
        result = benchmark(encode, msg)
        assert isinstance(result, bytes)


class TestFloatDecodingSpeed:
    """Benchmark BoundedFloat decode at different precision levels."""

    def test_decode_low_precision_float(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark decoding floats with precision=2."""
        encoded = encode(LowPrecisionMsg(lat=44.12, lon=-63.56))
        result = benchmark(decode, LowPrecisionMsg, encoded)
        assert abs(result.lat - 44.12) < 0.01

    def test_decode_med_precision_float(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark decoding floats with precision=6."""
        encoded = encode(MedPrecisionMsg(lat=44.123456, lon=-63.567890))
        result = benchmark(decode, MedPrecisionMsg, encoded)
        assert abs(result.lat - 44.123456) < 1e-4

    def test_decode_high_precision_float(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark decoding floats with precision=6."""
        encoded = encode(HighPrecisionMsg(lat=44.123456, lon=-63.567890))
        result = benchmark(decode, HighPrecisionMsg, encoded)
        assert abs(result.lat - 44.123456) < 1e-4


class TestFloatRoundtripSpeed:
    """Benchmark encode→decode roundtrip at each precision level."""

    def test_roundtrip_low_precision(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark full roundtrip with precision=2."""

        def roundtrip() -> LowPrecisionMsg:
            msg = LowPrecisionMsg(lat=44.12, lon=-63.56)
            return decode(LowPrecisionMsg, encode(msg))

        result = benchmark(roundtrip)
        assert abs(result.lat - 44.12) < 0.01

    def test_roundtrip_high_precision(self, benchmark: pytest.FixtureRequest) -> None:
        """Benchmark full roundtrip with precision=6."""

        def roundtrip() -> HighPrecisionMsg:
            msg = HighPrecisionMsg(lat=44.123456, lon=-63.567890)
            return decode(HighPrecisionMsg, encode(msg))

        result = benchmark(roundtrip)
        assert abs(result.lat - 44.123456) < 1e-4
