"""Abstract interface for acoustic modem drivers.

This module provides a vendor-agnostic abstraction layer for acoustic modems,
enabling:
- Hardware-in-the-Loop (HITL) simulation with MockModemDriver
- Real hardware support via vendor-specific driver implementations
- Swappable modem backends without changing application code

Design Pattern: Strategy Pattern / Adapter Pattern
- ModemDriver: Abstract interface (vendor-agnostic)
- MockModemDriver: Simulation implementation (testing without hardware)
- WhoiModemDriver, EvoLogicsModemDriver, etc.: Real hardware adapters (future)

The abstraction is intentionally NOT tied to any specific modem vendor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class ModemDriver(ABC):
    """Abstract interface for acoustic modem drivers.

    This interface defines the common operations for all acoustic modems,
    regardless of vendor. Implementations include:

    - **MockModemDriver**: Simulated modem for HITL testing (no hardware required)
    - **WhoiModemDriver**: WHOI MicroModem 2 adapter (future, via whoi_interface)
    - **EvoLogicsModemDriver**: EvoLogics S2C modem adapter (future)
    - **SonarbyneModemDriver**: Sonardyne modem adapter (future)
    - **CustomDriver**: User-defined drivers for proprietary hardware

    All drivers share the same interface, enabling:
    - Easy testing with mock modems before hardware deployment
    - Switching modem vendors without changing application code
    - Third-party driver development without modifying uwacomm core

    Examples:
        ```python
        # Use mock modem for testing
        from uwacomm.modem import MockModemDriver, MockModemConfig

        config = MockModemConfig(transmission_delay=1.5, packet_loss_probability=0.1)
        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)

        def on_receive(data: bytes, src_id: int):
            print(f"Received {len(data)} bytes from {src_id}")

        modem.attach_rx_callback(on_receive)
        modem.send_frame(b"hello", dest_id=0)
        modem.disconnect()
        ```

        ```python
        # Future: Use real WHOI modem (same interface!)
        from uwacomm.modem import WhoiModemDriver  # Future implementation

        modem = WhoiModemDriver()
        modem.connect("/dev/ttyUSB0", 19200)  # Real serial port
        # ... same attach_rx_callback, send_frame, disconnect calls
        ```
    """

    @abstractmethod
    def connect(self, port: str, baudrate: int = 19200) -> None:
        """Connect to acoustic modem (real or simulated).

        For real modems, this establishes serial/TCP connection and initializes
        the hardware. For mock modems, this starts the simulation.

        Args:
            port: Serial port (e.g., "/dev/ttyUSB0") or TCP address
            baudrate: Serial baud rate (default 19200 for most acoustic modems)

        Raises:
            ConnectionError: If connection fails (real modem only)

        Examples:
            ```python
            # Mock modem (always succeeds)
            modem.connect("/dev/null", 19200)

            # Real modem (may fail if hardware not present)
            modem.connect("/dev/ttyUSB0", 19200)
            ```
        """
        pass

    @abstractmethod
    def send_frame(self, data: bytes, dest_id: int) -> None:
        """Send data frame to destination vehicle.

        For real modems, this transmits acoustic data frame over underwater channel.
        For mock modems, this simulates transmission with configurable delay/loss.

        Args:
            data: Payload bytes to transmit (should be encoded uwacomm message)
            dest_id: Destination vehicle ID (0-255, 255=broadcast)

        Raises:
            ValueError: If dest_id out of range or data too large for modem
            RuntimeError: If modem not connected or transmission fails

        Examples:
            ```python
            from uwacomm import encode, BaseMessage, BoundedInt

            class Heartbeat(BaseMessage):
                depth: int = BoundedInt(ge=0, le=1000)
                uwacomm_id: int = 10

            msg = Heartbeat(depth=250)
            encoded = encode(msg)
            modem.send_frame(encoded, dest_id=0)  # Send to topside (ID 0)
            ```
        """
        pass

    @abstractmethod
    def attach_rx_callback(self, callback: Callable[[bytes, int], None]) -> None:
        """Register callback for received frames.

        The callback is invoked whenever a data frame is received from another
        vehicle. Multiple callbacks can be registered (they'll all be called).

        Args:
            callback: Function with signature (data: bytes, src_id: int) -> None
                - data: Received payload bytes (decode with uwacomm.decode)
                - src_id: Source vehicle ID (0-255)

        Examples:
            ```python
            from uwacomm import decode, BaseMessage

            class Heartbeat(BaseMessage):
                depth: int
                uwacomm_id: int = 10

            def on_receive(data: bytes, src_id: int):
                msg = decode(Heartbeat, data)
                print(f"Vehicle {src_id} at depth {msg.depth}m")

            modem.attach_rx_callback(on_receive)
            ```
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from modem.

        For real modems, this closes serial/TCP connection.
        For mock modems, this stops the simulation.

        Examples:
            ```python
            modem.connect("/dev/ttyUSB0", 19200)
            # ... do work ...
            modem.disconnect()  # Clean up
            ```
        """
        pass
