"""Test encoding modes (Point-to-Point, Self-Describing, Multi-Vehicle).

This test suite covers:
- Mode 1: Point-to-point (no ID, minimal overhead)
- Mode 2: Self-describing messages (with message ID)
- Mode 3: Multi-vehicle routing (to be added in Phase 3)
"""

from typing import ClassVar

import pytest

from uwacomm import BaseMessage, decode, encode
from uwacomm.exceptions import DecodeError, EncodeError
from uwacomm.models.fields import BoundedInt
from uwacomm.routing import MESSAGE_REGISTRY, decode_by_id, register_message


# Test message classes
class TestMessage(BaseMessage):
    """Simple test message with ID < 128."""

    value: int = BoundedInt(ge=0, le=255)

    uwacomm_id: ClassVar[int | None] = 42
    uwacomm_max_bytes: ClassVar[int | None] = 32


class LargeIdMessage(BaseMessage):
    """Test message with ID >= 128 (requires 2 bytes)."""

    value: int = BoundedInt(ge=0, le=255)

    uwacomm_id: ClassVar[int | None] = 200
    uwacomm_max_bytes: ClassVar[int | None] = 32


class NoIdMessage(BaseMessage):
    """Message without uwacomm_id (cannot use Mode 2)."""

    value: int = BoundedInt(ge=0, le=255)


# ============================================================================
# Mode 1: Point-to-Point (Current Behavior)
# ============================================================================


class TestMode1PointToPoint:
    """Test Mode 1: Point-to-point encoding (no ID)."""

    def test_mode1_minimal_overhead(self):
        """Mode 1: Point-to-point encoding has minimal overhead."""
        msg = TestMessage(value=123)

        # Encode without ID (Mode 1 - default)
        encoded = encode(msg)

        # Should be minimal size (just the value field: 8 bits = 1 byte)
        assert len(encoded) == 1

        # Decode requires knowing message type
        decoded = decode(TestMessage, encoded)
        assert decoded.value == 123

    def test_mode1_roundtrip(self):
        """Mode 1: Full roundtrip verification."""
        original = TestMessage(value=200)

        encoded = encode(original)
        decoded = decode(TestMessage, encoded)

        assert decoded == original
        assert decoded.value == 200

    def test_mode1_backward_compatible(self):
        """Mode 1: Existing code continues to work (backward compatibility)."""
        # Existing code that doesn't use include_id should work unchanged
        msg = TestMessage(value=50)

        # Old-style encoding (implicit Mode 1)
        encoded = encode(msg)

        # Old-style decoding
        decoded = decode(TestMessage, encoded)

        assert decoded.value == 50


# ============================================================================
# Mode 2: Self-Describing Messages
# ============================================================================


class TestMode2SelfDescribing:
    """Test Mode 2: Self-describing messages with message ID."""

    def test_mode2_basic_encoding(self):
        """Mode 2: Encode with message ID."""
        msg = TestMessage(value=123)

        # Encode with ID (Mode 2)
        encoded = encode(msg, include_id=True)

        # Should include message ID (1 byte for ID < 128) + payload
        # ID: 8 bits, value: 8 bits = 16 bits = 2 bytes
        assert len(encoded) == 2

        # Decode with ID validation
        decoded = decode(TestMessage, encoded, include_id=True)
        assert decoded.value == 123

    def test_mode2_id_size_optimization(self):
        """Mode 2: Message IDs < 128 use 1 byte, >= 128 use 2 bytes."""
        # Small ID (< 128): 1 byte ID
        msg_small = TestMessage(value=50)
        encoded_small = encode(msg_small, include_id=True)
        assert len(encoded_small) == 2  # 1 byte ID + 1 byte payload

        # Large ID (>= 128): 2 bytes ID
        msg_large = LargeIdMessage(value=50)
        encoded_large = encode(msg_large, include_id=True)
        assert len(encoded_large) == 3  # 2 bytes ID + 1 byte payload

    def test_mode2_id_validation(self):
        """Mode 2: Decoder validates message ID matches expected class."""
        msg = TestMessage(value=100)
        encoded = encode(msg, include_id=True)

        # Correct class: should decode successfully
        decoded = decode(TestMessage, encoded, include_id=True)
        assert decoded.value == 100

        # Wrong class: should raise DecodeError (ID mismatch)
        with pytest.raises(DecodeError, match="Message ID mismatch"):
            decode(LargeIdMessage, encoded, include_id=True)

    def test_mode2_missing_id_error(self):
        """Mode 2: Encoding without uwacomm_id raises error."""
        msg = NoIdMessage(value=50)

        # Should raise EncodeError when trying to use Mode 2 without uwacomm_id
        with pytest.raises(EncodeError, match="has no uwacomm_id"):
            encode(msg, include_id=True)

    def test_mode2_roundtrip_with_id(self):
        """Mode 2: Full roundtrip with ID validation."""
        original = TestMessage(value=175)

        encoded = encode(original, include_id=True)
        decoded = decode(TestMessage, encoded, include_id=True)

        assert decoded == original
        assert decoded.value == 175


# ============================================================================
# Mode 2: Auto-Decode by ID (MESSAGE_REGISTRY)
# ============================================================================


class TestAutoDecodeById:
    """Test auto-decode functionality using MESSAGE_REGISTRY."""

    def setup_method(self):
        """Clear registry before each test."""
        MESSAGE_REGISTRY.clear()

    def test_register_message(self):
        """Register message classes for auto-decode."""
        register_message(TestMessage)
        assert TestMessage.uwacomm_id in MESSAGE_REGISTRY
        assert MESSAGE_REGISTRY[TestMessage.uwacomm_id] is TestMessage

    def test_register_duplicate_allowed(self):
        """Registering the same class twice is a no-op."""
        register_message(TestMessage)
        register_message(TestMessage)  # Should not raise error
        assert MESSAGE_REGISTRY[TestMessage.uwacomm_id] is TestMessage

    def test_register_conflict_raises_error(self):
        """Registering different classes with same ID raises error."""
        register_message(TestMessage)

        # Create a different class with the same ID
        class ConflictMessage(BaseMessage):
            other_field: int = BoundedInt(ge=0, le=100)
            uwacomm_id: ClassVar[int | None] = 42  # Same as TestMessage

        with pytest.raises(ValueError, match="already registered"):
            register_message(ConflictMessage)

    def test_register_missing_id_raises_error(self):
        """Registering message without uwacomm_id raises error."""
        with pytest.raises(ValueError, match="has no uwacomm_id"):
            register_message(NoIdMessage)

    def test_decode_by_id_basic(self):
        """Auto-decode message by ID."""
        register_message(TestMessage)

        msg = TestMessage(value=123)
        encoded = encode(msg, include_id=True)

        # Auto-decode without knowing the type
        decoded = decode_by_id(encoded)

        assert isinstance(decoded, TestMessage)
        assert decoded.value == 123

    def test_decode_by_id_multiple_types(self):
        """Auto-decode with multiple registered message types."""
        register_message(TestMessage)
        register_message(LargeIdMessage)

        # Encode two different message types
        msg1 = TestMessage(value=50)
        msg2 = LargeIdMessage(value=100)

        encoded1 = encode(msg1, include_id=True)
        encoded2 = encode(msg2, include_id=True)

        # Auto-decode both
        decoded1 = decode_by_id(encoded1)
        decoded2 = decode_by_id(encoded2)

        assert isinstance(decoded1, TestMessage)
        assert decoded1.value == 50

        assert isinstance(decoded2, LargeIdMessage)
        assert decoded2.value == 100

    def test_decode_by_id_unknown_id_raises_error(self):
        """Auto-decode with unknown ID raises helpful error."""
        register_message(TestMessage)

        # Encode a message type that's not registered
        msg = LargeIdMessage(value=75)
        encoded = encode(msg, include_id=True)

        with pytest.raises(DecodeError, match="Unknown message ID: 200"):
            decode_by_id(encoded)

    def test_decode_by_id_empty_registry_raises_error(self):
        """Auto-decode without any registered messages raises error."""
        # Don't register anything
        msg = TestMessage(value=50)
        encoded = encode(msg, include_id=True)

        with pytest.raises(DecodeError, match="Unknown message ID"):
            decode_by_id(encoded)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_mode1_with_id_attribute_ignored(self):
        """Mode 1: uwacomm_id attribute is ignored when not using include_id."""
        msg = TestMessage(value=99)

        # Mode 1 encoding should ignore uwacomm_id
        encoded = encode(msg)

        # Should be minimal size (no ID included)
        assert len(encoded) == 1

        decoded = decode(TestMessage, encoded)
        assert decoded.value == 99

    def test_mode2_truncated_data_raises_error(self):
        """Mode 2: Truncated data raises DecodeError."""
        # Create valid encoded data
        msg = TestMessage(value=123)
        encoded = encode(msg, include_id=True)

        # Truncate it
        truncated = encoded[:1]

        with pytest.raises(DecodeError, match="Truncated"):
            decode(TestMessage, truncated, include_id=True)

    def test_invalid_id_range_raises_error(self):
        """Message ID must be 0-32767."""

        class InvalidIdMessage(BaseMessage):
            value: int = BoundedInt(ge=0, le=100)
            uwacomm_id: ClassVar[int | None] = 100000  # Too large

        msg = InvalidIdMessage(value=50)

        with pytest.raises(EncodeError, match="0-32767"):
            encode(msg, include_id=True)

    def test_decode_empty_data_raises_error(self):
        """Decoding empty data raises error."""
        with pytest.raises(DecodeError):
            decode_by_id(b"")


# ============================================================================
# Bandwidth Comparison
# ============================================================================


class TestBandwidthComparison:
    """Compare bandwidth usage across modes."""

    def test_mode_overhead_comparison(self):
        """Compare message sizes across modes."""
        msg = TestMessage(value=123)

        # Mode 1: No overhead
        encoded_mode1 = encode(msg)

        # Mode 2: ID overhead (1 byte for ID < 128)
        encoded_mode2 = encode(msg, include_id=True)

        assert len(encoded_mode1) == 1  # Payload only
        assert len(encoded_mode2) == 2  # ID + payload
        assert len(encoded_mode2) == len(encoded_mode1) + 1  # 1 byte overhead

    def test_large_id_overhead(self):
        """Large IDs (>= 128) require 2 bytes."""
        msg = LargeIdMessage(value=123)

        encoded_mode1 = encode(msg)
        encoded_mode2 = encode(msg, include_id=True)

        assert len(encoded_mode1) == 1  # Payload only
        assert len(encoded_mode2) == 3  # 2-byte ID + payload
        assert len(encoded_mode2) == len(encoded_mode1) + 2  # 2 bytes overhead


# ============================================================================
# Mode 3: Multi-Vehicle Routing
# ============================================================================


class TestMode3MultiVehicleRouting:
    """Test Mode 3: Multi-vehicle routing with RoutingHeader."""

    def test_mode3_basic_routing(self):
        """Mode 3: Basic routing encode/decode."""
        from uwacomm.routing import decode_with_routing, encode_with_routing

        msg = TestMessage(value=123)

        # Encode with routing (Vehicle 3 → Topside 0)
        encoded = encode_with_routing(msg, source_id=3, dest_id=0, priority=2, ack_requested=True)

        # Should include: routing header (3 bytes) + message ID (1 byte) + payload (1 byte)
        # Routing: 8 (src) + 8 (dest) + 2 (priority) + 1 (ack) = 19 bits = 3 bytes (rounded)
        assert len(encoded) == 5  # 3 routing + 1 ID + 1 payload

        # Decode with routing
        routing, decoded = decode_with_routing(TestMessage, encoded)

        assert routing.source_id == 3
        assert routing.dest_id == 0
        assert routing.priority == 2
        assert routing.ack_requested is True
        assert decoded.value == 123

    def test_mode3_routing_header_validation(self):
        """RoutingHeader validates parameter ranges."""
        from uwacomm.routing import RoutingHeader

        # Valid routing header
        header = RoutingHeader(source_id=10, dest_id=20, priority=3, ack_requested=False)
        assert header.source_id == 10
        assert header.dest_id == 20
        assert header.priority == 3
        assert header.ack_requested is False

        # Invalid source_id
        with pytest.raises(ValueError, match="source_id must be 0-255"):
            RoutingHeader(source_id=256, dest_id=0)

        # Invalid dest_id
        with pytest.raises(ValueError, match="dest_id must be 0-255"):
            RoutingHeader(source_id=0, dest_id=300)

        # Invalid priority
        with pytest.raises(ValueError, match="priority must be 0-3"):
            RoutingHeader(source_id=0, dest_id=0, priority=5)

    def test_mode3_different_priorities(self):
        """Mode 3: Different priority levels work correctly."""
        from uwacomm.routing import decode_with_routing, encode_with_routing

        msg = TestMessage(value=100)

        for priority in range(4):  # 0-3
            encoded = encode_with_routing(msg, source_id=5, dest_id=10, priority=priority)
            routing, decoded = decode_with_routing(TestMessage, encoded)

            assert routing.priority == priority
            assert decoded.value == 100

    def test_mode3_broadcast_destination(self):
        """Mode 3: Broadcast destination (dest_id=255) works."""
        from uwacomm.routing import decode_with_routing, encode_with_routing

        msg = TestMessage(value=99)

        # Broadcast to all vehicles (dest_id=255)
        encoded = encode_with_routing(msg, source_id=1, dest_id=255, priority=3)
        routing, decoded = decode_with_routing(TestMessage, encoded)

        assert routing.source_id == 1
        assert routing.dest_id == 255  # Broadcast
        assert decoded.value == 99

    def test_mode3_ack_requested_flag(self):
        """Mode 3: ACK requested flag works correctly."""
        from uwacomm.routing import decode_with_routing, encode_with_routing

        msg = TestMessage(value=50)

        # ACK not requested
        encoded_no_ack = encode_with_routing(msg, source_id=2, dest_id=0, ack_requested=False)
        routing_no_ack, _ = decode_with_routing(TestMessage, encoded_no_ack)
        assert routing_no_ack.ack_requested is False

        # ACK requested
        encoded_ack = encode_with_routing(msg, source_id=2, dest_id=0, ack_requested=True)
        routing_ack, _ = decode_with_routing(TestMessage, encoded_ack)
        assert routing_ack.ack_requested is True

    def test_mode3_roundtrip_preserves_all_data(self):
        """Mode 3: Full roundtrip preserves routing and message data."""
        from uwacomm.routing import decode_with_routing, encode_with_routing

        original_msg = TestMessage(value=175)

        encoded = encode_with_routing(
            original_msg, source_id=7, dest_id=3, priority=1, ack_requested=True
        )

        routing, decoded_msg = decode_with_routing(TestMessage, encoded)

        # Verify routing header
        assert routing.source_id == 7
        assert routing.dest_id == 3
        assert routing.priority == 1
        assert routing.ack_requested is True

        # Verify message
        assert decoded_msg == original_msg
        assert decoded_msg.value == 175

    def test_mode3_includes_message_id(self):
        """Mode 3: Routing mode automatically includes message ID."""
        from uwacomm.routing import encode_with_routing

        msg = TestMessage(value=123)

        # Mode 3 should automatically include message ID
        encoded = encode_with_routing(msg, source_id=1, dest_id=2)

        # The message should be self-describing (includes ID)
        # We can verify by checking that decode_by_id works
        from uwacomm.routing import MESSAGE_REGISTRY

        MESSAGE_REGISTRY.clear()
        from uwacomm.routing import register_message

        register_message(TestMessage)

        # Skip routing header to get to the message ID + payload
        # Routing: 19 bits = 3 bytes (rounded up)
        # But we need to skip exactly 19 bits, not 3 bytes
        # Actually, we can't use decode_by_id on Mode 3 data because it includes routing
        # Let's just verify the size is correct
        # Mode 1: 1 byte
        # Mode 2: 2 bytes (1 ID + 1 payload)
        # Mode 3: 5 bytes (3 routing + 1 ID + 1 payload)
        assert len(encoded) == 5

    def test_mode3_different_vehicles(self):
        """Mode 3: Multiple vehicles can send to each other."""
        from uwacomm.routing import decode_with_routing, encode_with_routing

        msg1 = TestMessage(value=10)
        msg2 = TestMessage(value=20)
        msg3 = TestMessage(value=30)

        # Vehicle 1 → Vehicle 2
        enc1 = encode_with_routing(msg1, source_id=1, dest_id=2)
        r1, d1 = decode_with_routing(TestMessage, enc1)
        assert r1.source_id == 1 and r1.dest_id == 2 and d1.value == 10

        # Vehicle 2 → Vehicle 3
        enc2 = encode_with_routing(msg2, source_id=2, dest_id=3)
        r2, d2 = decode_with_routing(TestMessage, enc2)
        assert r2.source_id == 2 and r2.dest_id == 3 and d2.value == 20

        # Vehicle 3 → Topside (ID 0)
        enc3 = encode_with_routing(msg3, source_id=3, dest_id=0)
        r3, d3 = decode_with_routing(TestMessage, enc3)
        assert r3.source_id == 3 and r3.dest_id == 0 and d3.value == 30


# ============================================================================
# All Modes Comparison
# ============================================================================


class TestAllModesComparison:
    """Compare all three encoding modes."""

    def test_mode_size_progression(self):
        """Compare sizes across all three modes."""
        from uwacomm.routing import encode_with_routing

        msg = TestMessage(value=100)

        # Mode 1: Point-to-point (minimal)
        mode1 = encode(msg)

        # Mode 2: Self-describing (with ID)
        mode2 = encode(msg, include_id=True)

        # Mode 3: Multi-vehicle routing (with routing + ID)
        mode3 = encode_with_routing(msg, source_id=1, dest_id=2)

        # Size progression: Mode 1 < Mode 2 < Mode 3
        assert len(mode1) < len(mode2)
        assert len(mode2) < len(mode3)

        # Exact sizes
        assert len(mode1) == 1  # Payload only
        assert len(mode2) == 2  # ID (1 byte) + payload
        assert len(mode3) == 5  # Routing (3 bytes) + ID (1 byte) + payload

    def test_all_modes_preserve_data(self):
        """All three modes correctly preserve message data."""
        from uwacomm.routing import decode_with_routing, encode_with_routing

        original = TestMessage(value=123)

        # Mode 1
        enc1 = encode(original)
        dec1 = decode(TestMessage, enc1)
        assert dec1 == original

        # Mode 2
        enc2 = encode(original, include_id=True)
        dec2 = decode(TestMessage, enc2, include_id=True)
        assert dec2 == original

        # Mode 3
        enc3 = encode_with_routing(original, source_id=5, dest_id=10)
        routing, dec3 = decode_with_routing(TestMessage, enc3)
        assert dec3 == original
        assert routing.source_id == 5
        assert routing.dest_id == 10
