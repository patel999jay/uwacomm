"""Mock acoustic modem driver for Hardware-in-the-Loop (HITL) simulation.

This module provides MockModemDriver, a simulated acoustic modem that enables
testing and development without physical hardware. It simulates:

- Transmission delays (acoustic propagation time)
- Packet loss (unreliable underwater channel)
- Bit errors (acoustic noise and multipath)
- Loopback testing (echo sent frames back to RX callbacks)

Design Patterns:
- Queue-based decoupling: Producer-consumer pattern for async I/O
- Background threads: Non-blocking RX processing
- Channel simulation: Probabilistic packet loss and delay injection
"""

from __future__ import annotations

import random
from queue import Queue
from threading import Thread
from time import sleep
from typing import Callable

from uwacomm.modem.config import MockModemConfig
from uwacomm.modem.driver import ModemDriver


class MockModemDriver(ModemDriver):
    """Simulated acoustic modem for testing without hardware.

    This driver simulates underwater acoustic communication with configurable
    channel characteristics (delay, loss, bit errors). Perfect for:

    - CI/CD testing without physical modems
    - Development and debugging before hardware deployment
    - Reproducible test scenarios with controlled channel conditions
    - Load testing and stress testing multi-vehicle systems

    The driver operates in loopback mode: sent frames are echoed back to
    registered RX callbacks after simulated acoustic delay. This enables
    full-stack testing of encode → transmit → receive → decode pipelines.

    Attributes:
        config: Mock modem configuration (channel parameters)
        rx_queue: Queue for received frames (producer-consumer pattern)
        rx_callbacks: List of registered RX callbacks
        _running: Background thread control flag

    Examples:
        ```python
        from uwacomm import encode, decode, BaseMessage, BoundedInt
        from uwacomm.modem import MockModemDriver, MockModemConfig

        class Heartbeat(BaseMessage):
            depth: int = BoundedInt(ge=0, le=1000)
            battery: int = BoundedInt(ge=0, le=100)
            uwacomm_id: int = 10

        # Configure mock modem with 10% packet loss, 1.5 second delay
        config = MockModemConfig(
            transmission_delay=1.5,
            packet_loss_probability=0.1,
        )

        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        # Register RX callback
        def on_receive(data: bytes, src_id: int):
            msg = decode(Heartbeat, data)
            print(f"Received from {src_id}: depth={msg.depth}, battery={msg.battery}")

        modem.attach_rx_callback(on_receive)

        # Send frame (will echo back after 1.5 seconds if not lost)
        heartbeat = Heartbeat(depth=250, battery=87)
        encoded = encode(heartbeat)
        modem.send_frame(encoded, dest_id=0)

        # Wait for loopback
        sleep(2.0)
        modem.disconnect()
        ```
    """

    def __init__(self, config: MockModemConfig | None = None) -> None:
        """Initialize mock modem driver.

        Args:
            config: Mock modem configuration. If None, uses default config.
        """
        self.config = config if config is not None else MockModemConfig()
        self.rx_queue: Queue[tuple[bytes, int]] = Queue()
        self.rx_callbacks: list[Callable[[bytes, int], None]] = []
        self._running = False

    def connect(self, port: str, baudrate: int = 19200) -> None:
        """Simulate connection to modem.

        For mock modem, this doesn't perform actual I/O - it just starts
        the background RX processing thread.

        Args:
            port: Fake port (ignored, can be any string like "/dev/null")
            baudrate: Fake baudrate (ignored)

        Examples:
            ```python
            modem = MockModemDriver()
            modem.connect("/dev/null", 19200)  # Starts simulation
            ```
        """
        if self._running:
            print("[MockModem] Already connected")
            return

        print(f"[MockModem] Connected to {port} @ {baudrate} baud (simulation mode)")
        print(
            f"[MockModem] Channel config: delay={self.config.transmission_delay}s, "
            f"loss={self.config.packet_loss_probability:.1%}, "
            f"BER={self.config.bit_error_rate:.2%}"
        )

        self._running = True
        # Start background RX processing thread
        rx_thread = Thread(target=self._rx_loop, daemon=True, name="MockModem-RX")
        rx_thread.start()

    def send_frame(self, data: bytes, dest_id: int) -> None:
        """Simulate transmission with acoustic channel effects.

        This simulates underwater acoustic propagation:
        1. Check if packet is lost (probabilistic)
        2. If not lost, schedule delayed reception (acoustic delay)
        3. Optionally inject bit errors (configurable BER)

        Args:
            data: Payload bytes to transmit
            dest_id: Destination vehicle ID (0-255)

        Raises:
            ValueError: If dest_id out of range or data exceeds max_frame_size
            RuntimeError: If modem not connected

        Examples:
            ```python
            modem.send_frame(b"\\x01\\x02\\x03", dest_id=5)
            # Frame echoed back to RX callbacks after transmission_delay seconds
            ```
        """
        if not self._running:
            raise RuntimeError(
                "MockModem not connected. Call connect() before send_frame()."
            )

        # Validate destination ID
        if not 0 <= dest_id <= 255:
            raise ValueError(f"dest_id must be 0-255, got {dest_id}")

        # Validate frame size
        if len(data) > self.config.max_frame_size:
            raise ValueError(
                f"Data size {len(data)} exceeds max_frame_size "
                f"{self.config.max_frame_size}"
            )

        # Simulate packet loss
        if random.random() < self.config.packet_loss_probability:
            print(
                f"[MockModem] Frame lost in channel "
                f"({len(data)} bytes to ID {dest_id})"
            )
            return

        # Simulate bit errors (if BER > 0)
        if self.config.bit_error_rate > 0:
            data = self._inject_bit_errors(data)

        print(f"[MockModem] Sent {len(data)} bytes to ID {dest_id}")

        # Schedule delayed reception (loopback with acoustic delay)
        def delayed_rx() -> None:
            sleep(self.config.transmission_delay)
            self.rx_queue.put((data, dest_id))

        rx_thread = Thread(target=delayed_rx, daemon=True, name="MockModem-Delayed-RX")
        rx_thread.start()

    def attach_rx_callback(self, callback: Callable[[bytes, int], None]) -> None:
        """Register callback for received frames.

        Multiple callbacks can be registered - all will be invoked when
        a frame is received.

        Args:
            callback: Function(data: bytes, src_id: int) -> None

        Examples:
            ```python
            def my_callback(data: bytes, src_id: int):
                print(f"Got {len(data)} bytes from {src_id}")

            modem.attach_rx_callback(my_callback)
            ```
        """
        self.rx_callbacks.append(callback)
        print(f"[MockModem] Registered RX callback (total: {len(self.rx_callbacks)})")

    def disconnect(self) -> None:
        """Stop simulation and disconnect.

        This stops the background RX thread and cleans up resources.

        Examples:
            ```python
            modem.disconnect()  # Stop simulation
            ```
        """
        if not self._running:
            print("[MockModem] Already disconnected")
            return

        self._running = False
        print("[MockModem] Disconnected")

    def _rx_loop(self) -> None:
        """Background thread processes received frames.

        This runs continuously while modem is connected, checking the RX queue
        for new frames and invoking registered callbacks.
        """
        print("[MockModem] RX processing thread started")
        while self._running:
            if not self.rx_queue.empty():
                data, src_id = self.rx_queue.get()
                print(f"[MockModem] Received {len(data)} bytes from ID {src_id}")

                # Invoke all registered callbacks
                for callback in self.rx_callbacks:
                    try:
                        callback(data, src_id)
                    except Exception as e:
                        print(f"[MockModem] RX callback error: {e}")

            # Small sleep to avoid busy-waiting
            sleep(0.01)

        print("[MockModem] RX processing thread stopped")

    def _inject_bit_errors(self, data: bytes) -> bytes:
        """Inject random bit errors based on configured BER.

        Args:
            data: Original data bytes

        Returns:
            Data with probabilistic bit errors injected
        """
        if self.config.bit_error_rate == 0:
            return data

        # Convert to mutable bytearray
        corrupted = bytearray(data)
        num_bits = len(data) * 8
        num_errors = 0

        # Flip bits with probability = BER
        for byte_idx in range(len(corrupted)):
            for bit_idx in range(8):
                if random.random() < self.config.bit_error_rate:
                    corrupted[byte_idx] ^= 1 << bit_idx  # Flip bit
                    num_errors += 1

        if num_errors > 0:
            print(
                f"[MockModem] Injected {num_errors} bit errors "
                f"({num_errors / num_bits:.2%} BER)"
            )

        return bytes(corrupted)
