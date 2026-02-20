"""Configuration for mock modem simulation.

This module provides configuration dataclasses for acoustic modem simulation,
enabling realistic Hardware-in-the-Loop (HITL) testing without physical hardware.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MockModemConfig:
    """Configuration for mock acoustic modem simulation.

    This configuration enables realistic simulation of underwater acoustic channels
    with configurable delays, packet loss, and bit errors. Use this to test
    your application logic before deploying to real hardware.

    Attributes:
        transmission_delay: Round-trip acoustic delay in seconds (default 1.0).
            Typical values:
            - Short range (< 1 km): 0.5 - 2.0 seconds
            - Medium range (1-5 km): 2.0 - 7.0 seconds
            - Long range (> 5 km): 7.0 - 15.0 seconds
            (Speed of sound in seawater ≈ 1500 m/s)

        packet_loss_probability: Probability of losing a packet (default 0.05).
            Typical values:
            - Good conditions: 0.01 - 0.05 (1-5% loss)
            - Moderate conditions: 0.05 - 0.15 (5-15% loss)
            - Poor conditions: 0.15 - 0.30 (15-30% loss)

        bit_error_rate: Probability of bit errors (default 0.0001 = 0.01%).
            Typical values for acoustic modems:
            - Good SNR: 0.0001 - 0.001 (0.01-0.1%)
            - Moderate SNR: 0.001 - 0.01 (0.1-1%)
            - Poor SNR: 0.01 - 0.1 (1-10%)
            Note: Most acoustic modems use FEC, so effective BER is lower

        max_frame_size: Maximum frame size in bytes (default 64).
            Typical acoustic modem limits:
            - WHOI MicroModem: 32 or 64 bytes
            - EvoLogics S2C: 64 bytes
            - Sonardyne AvTrak: 32 bytes

        data_rate: Data rate in bits per second (default 80 bps).
            Typical acoustic modem data rates:
            - Low frequency (long range): 40-200 bps
            - Medium frequency: 200-5000 bps
            - High frequency (short range): 5000-25000 bps

        enable_broadcast: Enable broadcast messages (dest_id=255), default True
        enable_routing: Enable multi-vehicle routing headers, default True

    Examples:
        ```python
        from uwacomm.modem import MockModemConfig, MockModemDriver

        # Good conditions, short range
        config = MockModemConfig(
            transmission_delay=0.5,  # 500ms round-trip
            packet_loss_probability=0.02,  # 2% loss
            data_rate=200,  # 200 bps
        )

        # Poor conditions, long range
        config = MockModemConfig(
            transmission_delay=10.0,  # 10 second round-trip
            packet_loss_probability=0.25,  # 25% loss
            bit_error_rate=0.01,  # 1% BER
            data_rate=40,  # 40 bps
        )

        modem = MockModemDriver(config)
        modem.connect("/dev/null", 19200)
        ```
    """

    # Acoustic channel parameters
    transmission_delay: float = 1.0  # seconds
    packet_loss_probability: float = 0.05  # 5% loss
    bit_error_rate: float = 0.0001  # 0.01% BER

    # Modem parameters
    max_frame_size: int = 64  # bytes
    data_rate: int = 80  # bits per second

    # Multi-vehicle networking
    enable_broadcast: bool = True
    enable_routing: bool = True

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.transmission_delay < 0:
            raise ValueError(f"transmission_delay must be >= 0, got {self.transmission_delay}")

        if not 0.0 <= self.packet_loss_probability <= 1.0:
            raise ValueError(
                f"packet_loss_probability must be 0.0-1.0, got {self.packet_loss_probability}"
            )

        if not 0.0 <= self.bit_error_rate <= 1.0:
            raise ValueError(f"bit_error_rate must be 0.0-1.0, got {self.bit_error_rate}")

        if self.max_frame_size <= 0:
            raise ValueError(f"max_frame_size must be > 0, got {self.max_frame_size}")

        if self.data_rate <= 0:
            raise ValueError(f"data_rate must be > 0, got {self.data_rate}")
