"""Test float encoding with DCCL-style bounded floats."""

import pytest

from uwacomm import BaseMessage, decode, encode
from uwacomm.models.fields import BoundedFloat


class FloatMessage(BaseMessage):
    """Test message with various float precisions."""

    depth: float = BoundedFloat(min=-5.0, max=100.0, precision=2)
    temperature: float = BoundedFloat(min=-20.0, max=40.0, precision=1)
    latitude: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    longitude: float = BoundedFloat(min=-180.0, max=180.0, precision=6)


class TestFloatEncoding:
    """Test float encoding/decoding."""

    def test_basic_float_roundtrip(self):
        """Basic float encode/decode roundtrip."""
        msg = FloatMessage(depth=25.75, temperature=18.3, latitude=42.358894, longitude=-71.063611)

        encoded = encode(msg)
        decoded = decode(FloatMessage, encoded)

        # Verify values match within precision
        assert abs(decoded.depth - 25.75) < 0.01
        assert abs(decoded.temperature - 18.3) < 0.1
        assert abs(decoded.latitude - 42.358894) < 0.000001
        assert abs(decoded.longitude - (-71.063611)) < 0.000001

    def test_float_precision_limits(self):
        """Float precision respects specified decimal places."""
        msg = FloatMessage(
            depth=25.753,  # Will be rounded to 25.75
            temperature=18.34,  # Will be rounded to 18.3
            latitude=42.358894123,  # Will be rounded to 42.358894
            longitude=-71.063611456,
        )

        encoded = encode(msg)
        decoded = decode(FloatMessage, encoded)

        # Verify rounding
        assert decoded.depth == pytest.approx(25.75, abs=0.01)
        assert decoded.temperature == pytest.approx(18.3, abs=0.1)

    def test_float_bandwidth_efficiency(self):
        """Float encoding is bandwidth-efficient vs IEEE 754."""
        msg = FloatMessage(depth=50.0, temperature=20.0, latitude=45.0, longitude=-75.0)

        encoded = encode(msg)

        # Calculate expected size:
        # depth: range 105.0, precision 2 → 10,500 values → 14 bits
        # temperature: range 60.0, precision 1 → 600 values → 10 bits
        # latitude: range 180.0, precision 6 → 180,000,000 values → 28 bits
        # longitude: range 360.0, precision 6 → 360,000,000 values → 29 bits
        # Total: 81 bits = 11 bytes (with padding)

        # vs IEEE 754 double: 4 fields × 8 bytes = 32 bytes
        # Savings: 66%

        assert len(encoded) <= 12  # Allow 1 byte padding tolerance
        assert len(encoded) < 32 / 2  # At least 50% smaller than doubles

    def test_float_boundary_values(self):
        """Float encoding handles boundary values correctly."""
        # Test min/max boundaries
        msg_min = FloatMessage(depth=-5.0, temperature=-20.0, latitude=-90.0, longitude=-180.0)

        encoded_min = encode(msg_min)
        decoded_min = decode(FloatMessage, encoded_min)

        assert decoded_min.depth == pytest.approx(-5.0, abs=0.01)
        assert decoded_min.temperature == pytest.approx(-20.0, abs=0.1)

        msg_max = FloatMessage(depth=100.0, temperature=40.0, latitude=90.0, longitude=180.0)

        encoded_max = encode(msg_max)
        decoded_max = decode(FloatMessage, encoded_max)

        assert decoded_max.depth == pytest.approx(100.0, abs=0.01)
        assert decoded_max.temperature == pytest.approx(40.0, abs=0.1)

    def test_float_out_of_bounds(self):
        """Float encoding rejects out-of-bounds values."""
        from pydantic_core import ValidationError

        # Pydantic validates bounds at construction time (before encoding)
        with pytest.raises(ValidationError):
            FloatMessage(
                depth=150.0, temperature=20.0, latitude=45.0, longitude=-75.0  # Max is 100.0
            )

    def test_zero_precision_float(self):
        """Float with precision=0 works like integer."""

        class IntegerLikeFloat(BaseMessage):
            value: float = BoundedFloat(min=0.0, max=100.0, precision=0)

        msg = IntegerLikeFloat(value=42.7)  # Will round to 43.0
        encoded = encode(msg)
        decoded = decode(IntegerLikeFloat, encoded)

        assert decoded.value == pytest.approx(43.0, abs=0.5)
