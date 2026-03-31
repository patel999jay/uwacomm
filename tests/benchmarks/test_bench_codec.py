"""Performance benchmarks for the core codec (encode/decode) and fragmentation.

Measures throughput of the encode/decode engine across small, medium, and large
message payloads, plus full roundtrip and fragmentation/reassembly performance.
"""

from __future__ import annotations

import pytest

from uwacomm import decode, encode
from uwacomm.fragmentation import fragment_message, reassemble_fragments

from .conftest import LargeMessage, MediumMessage, SmallMessage


class TestEncodeSpeed:
    """Benchmark encode() performance across message sizes."""

    def test_encode_small_message(
        self, benchmark: pytest.FixtureRequest, small_msg: SmallMessage
    ) -> None:
        """Benchmark encoding a minimal 3-field message."""
        result = benchmark(encode, small_msg)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_encode_medium_message(
        self, benchmark: pytest.FixtureRequest, medium_msg: MediumMessage
    ) -> None:
        """Benchmark encoding a typical 7-field telemetry message."""
        result = benchmark(encode, medium_msg)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_encode_large_message(
        self, benchmark: pytest.FixtureRequest, large_msg: LargeMessage
    ) -> None:
        """Benchmark encoding a large 100-byte fixed-payload message."""
        result = benchmark(encode, large_msg)
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestDecodeSpeed:
    """Benchmark decode() performance across message sizes."""

    def test_decode_small_message(
        self, benchmark: pytest.FixtureRequest, small_encoded: bytes
    ) -> None:
        """Benchmark decoding a minimal message."""
        result = benchmark(decode, SmallMessage, small_encoded)
        assert isinstance(result, SmallMessage)

    def test_decode_medium_message(
        self, benchmark: pytest.FixtureRequest, medium_encoded: bytes
    ) -> None:
        """Benchmark decoding a typical telemetry message."""
        result = benchmark(decode, MediumMessage, medium_encoded)
        assert isinstance(result, MediumMessage)

    def test_decode_large_message(
        self, benchmark: pytest.FixtureRequest, large_encoded: bytes
    ) -> None:
        """Benchmark decoding a large fixed-payload message."""
        result = benchmark(decode, LargeMessage, large_encoded)
        assert isinstance(result, LargeMessage)


class TestRoundtripSpeed:
    """Benchmark full encode→decode roundtrip performance."""

    def test_roundtrip_small(
        self, benchmark: pytest.FixtureRequest, small_msg: SmallMessage
    ) -> None:
        """Benchmark full encode+decode roundtrip for a small message."""

        def roundtrip() -> SmallMessage:
            data = encode(small_msg)
            return decode(SmallMessage, data)

        result = benchmark(roundtrip)
        assert result.vehicle_id == small_msg.vehicle_id
        assert result.depth_cm == small_msg.depth_cm
        assert result.battery_pct == small_msg.battery_pct

    def test_roundtrip_medium(
        self, benchmark: pytest.FixtureRequest, medium_msg: MediumMessage
    ) -> None:
        """Benchmark full encode+decode roundtrip for a medium telemetry message."""

        def roundtrip() -> MediumMessage:
            data = encode(medium_msg)
            return decode(MediumMessage, data)

        result = benchmark(roundtrip)
        assert result.vehicle_id == medium_msg.vehicle_id

    def test_roundtrip_large(
        self, benchmark: pytest.FixtureRequest, large_msg: LargeMessage
    ) -> None:
        """Benchmark full encode+decode roundtrip for a large message."""

        def roundtrip() -> LargeMessage:
            data = encode(large_msg)
            return decode(LargeMessage, data)

        result = benchmark(roundtrip)
        assert result.vehicle_id == large_msg.vehicle_id
        assert result.sensor_data == large_msg.sensor_data


class TestFragmentationSpeed:
    """Benchmark fragmentation and reassembly throughput."""

    def test_fragment_small_message(
        self, benchmark: pytest.FixtureRequest, small_encoded: bytes
    ) -> None:
        """Benchmark fragmenting a small already-encoded payload."""
        result = benchmark(fragment_message, small_encoded, 64)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_fragment_large_message(
        self, benchmark: pytest.FixtureRequest, large_encoded: bytes
    ) -> None:
        """Benchmark fragmenting a large encoded payload across multiple frames."""
        result = benchmark(fragment_message, large_encoded, 64)
        assert isinstance(result, list)
        assert len(result) > 1

    def test_reassemble_fragments(
        self, benchmark: pytest.FixtureRequest, large_encoded: bytes
    ) -> None:
        """Benchmark reassembling fragments back into the original payload."""
        fragments = fragment_message(large_encoded, max_fragment_size=64)
        result = benchmark(reassemble_fragments, fragments)
        assert result == large_encoded

    def test_fragment_and_reassemble_roundtrip(
        self, benchmark: pytest.FixtureRequest, large_encoded: bytes
    ) -> None:
        """Benchmark the full fragment→reassemble roundtrip."""

        def roundtrip() -> bytes:
            frags = fragment_message(large_encoded, max_fragment_size=64)
            return reassemble_fragments(frags)

        result = benchmark(roundtrip)
        assert result == large_encoded
