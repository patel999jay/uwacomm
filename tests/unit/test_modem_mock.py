"""Tests for mock modem driver."""

from __future__ import annotations

import time

import pytest

from uwacomm.modem import MockModemConfig, MockModemDriver


class TestMockModemConfig:
    """Tests for MockModemConfig validation."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MockModemConfig()

        assert config.transmission_delay == 1.0
        assert config.packet_loss_probability == 0.05
        assert config.bit_error_rate == 0.0001
        assert config.max_frame_size == 64
        assert config.data_rate == 80
        assert config.enable_broadcast is True
        assert config.enable_routing is True

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = MockModemConfig(
            transmission_delay=2.5,
            packet_loss_probability=0.15,
            bit_error_rate=0.01,
            max_frame_size=32,
            data_rate=200,
            enable_broadcast=False,
            enable_routing=False,
        )

        assert config.transmission_delay == 2.5
        assert config.packet_loss_probability == 0.15
        assert config.bit_error_rate == 0.01
        assert config.max_frame_size == 32
        assert config.data_rate == 200
        assert config.enable_broadcast is False
        assert config.enable_routing is False

    def test_negative_delay_raises(self) -> None:
        """Test that negative transmission delay raises ValueError."""
        with pytest.raises(ValueError, match="transmission_delay must be >= 0"):
            MockModemConfig(transmission_delay=-1.0)

    def test_invalid_loss_probability_raises(self) -> None:
        """Test that invalid packet loss probability raises ValueError."""
        with pytest.raises(ValueError, match="packet_loss_probability must be 0.0-1.0"):
            MockModemConfig(packet_loss_probability=1.5)

        with pytest.raises(ValueError, match="packet_loss_probability must be 0.0-1.0"):
            MockModemConfig(packet_loss_probability=-0.1)

    def test_invalid_ber_raises(self) -> None:
        """Test that invalid bit error rate raises ValueError."""
        with pytest.raises(ValueError, match="bit_error_rate must be 0.0-1.0"):
            MockModemConfig(bit_error_rate=1.5)

        with pytest.raises(ValueError, match="bit_error_rate must be 0.0-1.0"):
            MockModemConfig(bit_error_rate=-0.1)

    def test_invalid_frame_size_raises(self) -> None:
        """Test that invalid max frame size raises ValueError."""
        with pytest.raises(ValueError, match="max_frame_size must be > 0"):
            MockModemConfig(max_frame_size=0)

        with pytest.raises(ValueError, match="max_frame_size must be > 0"):
            MockModemConfig(max_frame_size=-10)

    def test_invalid_data_rate_raises(self) -> None:
        """Test that invalid data rate raises ValueError."""
        with pytest.raises(ValueError, match="data_rate must be > 0"):
            MockModemConfig(data_rate=0)

        with pytest.raises(ValueError, match="data_rate must be > 0"):
            MockModemConfig(data_rate=-100)


class TestMockModemDriver:
    """Tests for MockModemDriver."""

    def test_default_initialization(self) -> None:
        """Test driver initialization with default config."""
        modem = MockModemDriver()

        assert modem.config.transmission_delay == 1.0
        assert modem.rx_queue.empty()
        assert len(modem.rx_callbacks) == 0
        assert modem._running is False

    def test_custom_config_initialization(self) -> None:
        """Test driver initialization with custom config."""
        config = MockModemConfig(transmission_delay=2.0, packet_loss_probability=0.2)
        modem = MockModemDriver(config)

        assert modem.config.transmission_delay == 2.0
        assert modem.config.packet_loss_probability == 0.2

    def test_connect_disconnect(self) -> None:
        """Test modem connection and disconnection."""
        modem = MockModemDriver()

        # Initially not running
        assert modem._running is False

        # Connect starts simulation
        modem.connect("/dev/null", 19200)
        assert modem._running is True

        # Disconnect stops simulation
        modem.disconnect()
        assert modem._running is False

    def test_double_connect_is_safe(self) -> None:
        """Test that double connect doesn't crash."""
        modem = MockModemDriver()
        modem.connect("/dev/null", 19200)
        modem.connect("/dev/null", 19200)  # Should be safe
        assert modem._running is True
        modem.disconnect()

    def test_double_disconnect_is_safe(self) -> None:
        """Test that double disconnect doesn't crash."""
        modem = MockModemDriver()
        modem.connect("/dev/null", 19200)
        modem.disconnect()
        modem.disconnect()  # Should be safe
        assert modem._running is False

    def test_send_frame_not_connected_raises(self) -> None:
        """Test that sending without connecting raises RuntimeError."""
        modem = MockModemDriver()

        with pytest.raises(RuntimeError, match="MockModem not connected"):
            modem.send_frame(b"test", dest_id=0)

    def test_send_frame_invalid_dest_id_raises(self) -> None:
        """Test that invalid destination ID raises ValueError."""
        modem = MockModemDriver()
        modem.connect("/dev/null", 19200)

        with pytest.raises(ValueError, match="dest_id must be 0-255"):
            modem.send_frame(b"test", dest_id=-1)

        with pytest.raises(ValueError, match="dest_id must be 0-255"):
            modem.send_frame(b"test", dest_id=256)

        modem.disconnect()

    def test_send_frame_too_large_raises(self) -> None:
        """Test that oversized frame raises ValueError."""
        config = MockModemConfig(max_frame_size=10)
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        with pytest.raises(ValueError, match="exceeds max_frame_size"):
            modem.send_frame(b"x" * 11, dest_id=0)

        modem.disconnect()

    def test_loopback_with_no_loss(self) -> None:
        """Test loopback frame reception with 0% packet loss."""
        config = MockModemConfig(
            transmission_delay=0.1,  # Fast for testing
            packet_loss_probability=0.0,  # No loss
            bit_error_rate=0.0,  # No errors
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        # Track received frames
        received: list[tuple[bytes, int]] = []

        def on_receive(data: bytes, src_id: int) -> None:
            received.append((data, src_id))

        modem.attach_rx_callback(on_receive)

        # Send frame
        test_data = b"\x01\x02\x03\x04"
        modem.send_frame(test_data, dest_id=42)

        # Wait for loopback
        time.sleep(0.3)

        # Verify received
        assert len(received) == 1
        assert received[0] == (test_data, 42)

        modem.disconnect()

    def test_loopback_with_100_percent_loss(self) -> None:
        """Test that 100% packet loss prevents reception."""
        config = MockModemConfig(
            transmission_delay=0.1,
            packet_loss_probability=1.0,  # 100% loss
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        # Track received frames
        received: list[tuple[bytes, int]] = []

        def on_receive(data: bytes, src_id: int) -> None:
            received.append((data, src_id))

        modem.attach_rx_callback(on_receive)

        # Send frame
        modem.send_frame(b"\x01\x02\x03", dest_id=0)

        # Wait
        time.sleep(0.3)

        # Should not be received
        assert len(received) == 0

        modem.disconnect()

    def test_multiple_rx_callbacks(self) -> None:
        """Test that multiple RX callbacks are all invoked."""
        config = MockModemConfig(
            transmission_delay=0.1,
            packet_loss_probability=0.0,
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        # Register 3 callbacks
        received_1: list[bytes] = []
        received_2: list[bytes] = []
        received_3: list[bytes] = []

        modem.attach_rx_callback(lambda data, src: received_1.append(data))
        modem.attach_rx_callback(lambda data, src: received_2.append(data))
        modem.attach_rx_callback(lambda data, src: received_3.append(data))

        # Send frame
        test_data = b"\xAA\xBB\xCC"
        modem.send_frame(test_data, dest_id=0)

        # Wait
        time.sleep(0.3)

        # All callbacks should have been invoked
        assert len(received_1) == 1
        assert len(received_2) == 1
        assert len(received_3) == 1
        assert received_1[0] == test_data
        assert received_2[0] == test_data
        assert received_3[0] == test_data

        modem.disconnect()

    def test_rx_callback_exception_doesnt_crash(self) -> None:
        """Test that exception in RX callback doesn't crash modem."""
        config = MockModemConfig(
            transmission_delay=0.1,
            packet_loss_probability=0.0,
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        # Register callback that raises exception
        def bad_callback(data: bytes, src_id: int) -> None:
            raise RuntimeError("Callback error!")

        # And a good callback
        received: list[bytes] = []

        def good_callback(data: bytes, src_id: int) -> None:
            received.append(data)

        modem.attach_rx_callback(bad_callback)
        modem.attach_rx_callback(good_callback)

        # Send frame
        modem.send_frame(b"\x01\x02", dest_id=0)

        # Wait
        time.sleep(0.3)

        # Good callback should still have received
        assert len(received) == 1

        modem.disconnect()

    def test_bit_error_injection(self) -> None:
        """Test that bit errors are injected when BER > 0."""
        config = MockModemConfig(
            transmission_delay=0.1,
            packet_loss_probability=0.0,
            bit_error_rate=0.5,  # 50% BER (very high for testing)
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        # Send same data multiple times
        test_data = b"\xFF\xFF\xFF\xFF"  # All 1s
        received: list[bytes] = []

        modem.attach_rx_callback(lambda data, src: received.append(data))

        # Send 10 times
        for _ in range(10):
            modem.send_frame(test_data, dest_id=0)

        # Wait for all
        time.sleep(1.5)

        # At least some should have bit errors (very unlikely all are identical with 50% BER)
        assert len(received) == 10
        corrupted_count = sum(1 for data in received if data != test_data)
        assert corrupted_count > 0  # Should have at least some errors

        modem.disconnect()

    def test_no_bit_errors_when_ber_zero(self) -> None:
        """Test that no bit errors occur when BER is 0."""
        config = MockModemConfig(
            transmission_delay=0.1,
            packet_loss_probability=0.0,
            bit_error_rate=0.0,  # No errors
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        test_data = b"\xAA\xBB\xCC\xDD"
        received: list[bytes] = []

        modem.attach_rx_callback(lambda data, src: received.append(data))

        # Send multiple times
        for _ in range(5):
            modem.send_frame(test_data, dest_id=0)

        # Wait
        time.sleep(0.8)

        # All should be identical (no errors)
        assert len(received) == 5
        assert all(data == test_data for data in received)

        modem.disconnect()

    def test_transmission_delay_is_respected(self) -> None:
        """Test that transmission delay is roughly correct."""
        config = MockModemConfig(
            transmission_delay=0.5,  # 500ms delay
            packet_loss_probability=0.0,
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        received: list[float] = []
        send_time = time.time()

        def on_receive(data: bytes, src_id: int) -> None:
            received.append(time.time())

        modem.attach_rx_callback(on_receive)

        # Send frame
        modem.send_frame(b"\x01\x02", dest_id=0)

        # Wait
        time.sleep(0.8)

        # Should have received exactly 1 frame
        assert len(received) == 1

        # Delay should be approximately 500ms (allow some tolerance)
        actual_delay = received[0] - send_time
        assert 0.4 < actual_delay < 0.7  # 400-700ms range (allows for scheduling jitter)

        modem.disconnect()

    def test_multiple_frames_in_flight(self) -> None:
        """Test sending multiple frames before they're received (queue behavior)."""
        config = MockModemConfig(
            transmission_delay=0.2,
            packet_loss_probability=0.0,
        )
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        received: list[bytes] = []
        modem.attach_rx_callback(lambda data, src: received.append(data))

        # Send 5 frames quickly
        for i in range(5):
            modem.send_frame(bytes([i]), dest_id=0)
            time.sleep(0.05)  # Send faster than reception

        # Wait for all to arrive
        time.sleep(0.5)

        # All 5 should be received
        assert len(received) == 5
        assert received == [bytes([i]) for i in range(5)]

        modem.disconnect()
