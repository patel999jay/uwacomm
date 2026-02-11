"""End-to-end integration tests."""

from __future__ import annotations

import enum
from typing import ClassVar, Optional

import pytest
from pydantic import Field

from uwacomm import (
    BaseMessage,
    decode,
    encode,
    encoded_size,
    field_sizes,
    frame_with_id,
    to_proto_schema,
    unframe_with_id,
)


class MissionPhase(enum.Enum):
    """Mission phase enum."""

    STARTUP = 1
    TRANSIT = 2
    SURVEY = 3
    RETURN = 4
    SHUTDOWN = 5


class StatusReport(BaseMessage):
    """Underwater vehicle status report."""

    vehicle_id: int = Field(ge=0, le=255, description="Vehicle ID")
    mission_phase: MissionPhase = Field(description="Current mission phase")
    depth_cm: int = Field(ge=0, le=10000, description="Depth in centimeters")
    battery_pct: int = Field(ge=0, le=100, description="Battery percentage")
    emergency: bool = Field(description="Emergency flag")

    uwacomm_max_bytes: ClassVar[Optional[int]] = 32
    uwacomm_id: ClassVar[Optional[int]] = 10


class CommandMessage(BaseMessage):
    """Command message to vehicle."""

    target_depth_cm: int = Field(ge=0, le=10000)
    target_speed_dmps: int = Field(ge=0, le=200)  # decimeters per second
    abort: bool


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    def test_status_report_workflow(self) -> None:
        """Test complete status report workflow."""
        # 1. Create message
        status = StatusReport(
            vehicle_id=42,
            mission_phase=MissionPhase.SURVEY,
            depth_cm=2500,
            battery_pct=87,
            emergency=False,
        )

        # 2. Check encoded size
        size = encoded_size(status)
        assert size <= 32  # Within uwacomm_max_bytes

        # 3. Get field sizes for analysis
        sizes = field_sizes(status)
        assert "vehicle_id" in sizes
        assert "emergency" in sizes

        # 4. Encode message
        encoded_data = encode(status)
        assert len(encoded_data) == size

        # 5. Frame with message ID and CRC
        framed = frame_with_id(encoded_data, message_id=StatusReport.uwacomm_id or 0, crc="crc32")

        # 6. Simulate transmission (no-op in test)
        received_frame = framed

        # 7. Unframe and verify
        msg_id, payload = unframe_with_id(received_frame, crc="crc32")
        assert msg_id == 10

        # 8. Decode message
        decoded_status = decode(StatusReport, payload)

        # 9. Verify all fields
        assert decoded_status.vehicle_id == 42
        assert decoded_status.mission_phase == MissionPhase.SURVEY
        assert decoded_status.depth_cm == 2500
        assert decoded_status.battery_pct == 87
        assert decoded_status.emergency is False

    def test_command_message_workflow(self) -> None:
        """Test command message workflow."""
        # Create command
        cmd = CommandMessage(target_depth_cm=5000, target_speed_dmps=50, abort=False)

        # Encode and frame
        encoded = encode(cmd)
        framed = frame_with_id(encoded, message_id=20, crc="crc16")

        # Unframe and decode
        msg_id, payload = unframe_with_id(framed, crc="crc16")
        decoded_cmd = decode(CommandMessage, payload)

        # Verify
        assert decoded_cmd.target_depth_cm == 5000
        assert decoded_cmd.target_speed_dmps == 50
        assert decoded_cmd.abort is False

    def test_proto_schema_generation(self) -> None:
        """Test Protobuf schema generation."""
        proto = to_proto_schema(StatusReport, package="underwater.messages")

        # Verify proto structure
        assert 'syntax = "proto3"' in proto
        assert "package underwater.messages;" in proto
        assert "message StatusReport {" in proto
        assert "enum MissionPhase {" in proto

        # Verify fields
        assert "vehicle_id" in proto
        assert "mission_phase" in proto
        assert "depth_cm" in proto
        assert "battery_pct" in proto
        assert "emergency" in proto

    def test_size_optimization(self) -> None:
        """Test that compact encoding is actually compact."""
        # Create a message with well-bounded fields
        status = StatusReport(
            vehicle_id=100,
            mission_phase=MissionPhase.TRANSIT,
            depth_cm=1000,
            battery_pct=75,
            emergency=False,
        )

        # Get field sizes
        sizes = field_sizes(StatusReport)
        total_bits = sum(sizes.values())

        # vehicle_id: 8 bits (0-255)
        # mission_phase: 3 bits (5 values)
        # depth_cm: 14 bits (0-10000)
        # battery_pct: 7 bits (0-100)
        # emergency: 1 bit
        # Total: 8 + 3 + 14 + 7 + 1 = 33 bits = 5 bytes (rounded up)

        assert sizes["vehicle_id"] == 8
        assert sizes["mission_phase"] == 3
        assert sizes["depth_cm"] == 14
        assert sizes["battery_pct"] == 7
        assert sizes["emergency"] == 1
        assert total_bits == 33

        # Encoded size should be 5 bytes
        size = encoded_size(status)
        assert size == 5

        # Verify encoding works
        encoded = encode(status)
        assert len(encoded) == 5

        # Verify decoding works
        decoded = decode(StatusReport, encoded)
        assert decoded == status


class TestMultipleMessageTypes:
    """Test handling multiple message types."""

    def test_message_type_routing(self) -> None:
        """Test routing different message types by ID."""
        # Create different message types
        status = StatusReport(
            vehicle_id=1,
            mission_phase=MissionPhase.STARTUP,
            depth_cm=0,
            battery_pct=100,
            emergency=False,
        )

        command = CommandMessage(target_depth_cm=1000, target_speed_dmps=30, abort=False)

        # Encode and frame with different IDs
        status_framed = frame_with_id(encode(status), message_id=10, crc="crc32")
        command_framed = frame_with_id(encode(command), message_id=20, crc="crc32")

        # Simulate receiving frames
        frames = [status_framed, command_framed]

        # Route based on message ID
        for frame in frames:
            msg_id, payload = unframe_with_id(frame, crc="crc32")

            if msg_id == 10:
                decoded_status = decode(StatusReport, payload)
                assert decoded_status.vehicle_id == 1
                assert decoded_status.mission_phase == MissionPhase.STARTUP

            elif msg_id == 20:
                decoded_command = decode(CommandMessage, payload)
                assert decoded_command.target_depth_cm == 1000
                assert decoded_command.target_speed_dmps == 30

            else:
                pytest.fail(f"Unexpected message ID: {msg_id}")


class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_corrupted_frame_detection(self) -> None:
        """Test detection of corrupted frames."""
        status = StatusReport(
            vehicle_id=42,
            mission_phase=MissionPhase.SURVEY,
            depth_cm=2500,
            battery_pct=87,
            emergency=False,
        )

        framed = frame_with_id(encode(status), message_id=10, crc="crc32")

        # Corrupt a byte
        corrupted = bytearray(framed)
        corrupted[10] ^= 0xFF
        corrupted = bytes(corrupted)

        # Should raise FramingError due to CRC mismatch
        from uwacomm import FramingError

        with pytest.raises(FramingError, match="CRC"):
            unframe_with_id(corrupted, crc="crc32")

    def test_truncated_message_detection(self) -> None:
        """Test detection of truncated messages."""
        status = StatusReport(
            vehicle_id=42,
            mission_phase=MissionPhase.SURVEY,
            depth_cm=2500,
            battery_pct=87,
            emergency=False,
        )

        encoded = encode(status)

        # Truncate the data
        truncated = encoded[:-2]

        # Should raise DecodeError
        from uwacomm import DecodeError

        with pytest.raises(DecodeError, match="[Tt]runcated"):
            decode(StatusReport, truncated)
