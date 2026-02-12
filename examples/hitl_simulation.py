"""Hardware-in-the-Loop (HITL) Simulation Example.

This example demonstrates using MockModemDriver to test acoustic modem
communication without physical hardware. Perfect for:
- CI/CD testing
- Development before hardware deployment
- Reproducible test scenarios
- Load testing multi-vehicle systems

The mock modem simulates:
- Acoustic propagation delay (round-trip time)
- Packet loss (unreliable underwater channel)
- Bit errors (acoustic noise)
- Loopback testing (echo sent frames back)

Run this example:
    python examples/hitl_simulation.py
"""

from __future__ import annotations

import time
from typing import ClassVar

from uwacomm import BaseMessage, BoundedInt, decode, encode
from uwacomm.modem import MockModemConfig, MockModemDriver


class Heartbeat(BaseMessage):
    """UUV heartbeat message with depth and battery status."""

    depth: int = BoundedInt(ge=0, le=1000)  # Depth in meters (0-1000m)
    battery: int = BoundedInt(ge=0, le=100)  # Battery percentage (0-100%)
    uwacomm_id: ClassVar[int | None] = 10  # Message ID for auto-decode


def main() -> None:
    """Run HITL simulation demo."""
    print("=" * 70)
    print("uwacomm Hardware-in-the-Loop (HITL) Simulation Demo")
    print("=" * 70)
    print()

    # ========================================================================
    # Step 1: Configure mock modem with realistic channel characteristics
    # ========================================================================
    print("Step 1: Configure mock modem")
    print("-" * 70)

    config = MockModemConfig(
        transmission_delay=1.5,  # 1.5 second round-trip (1 km range)
        packet_loss_probability=0.1,  # 10% packet loss (moderate conditions)
        bit_error_rate=0.0005,  # 0.05% BER (acoustic noise)
        max_frame_size=64,  # 64 byte max frame (typical acoustic modem)
        data_rate=80,  # 80 bps (low frequency, long range)
    )

    print(f"  Transmission delay: {config.transmission_delay} seconds")
    print(f"  Packet loss: {config.packet_loss_probability:.1%}")
    print(f"  Bit error rate: {config.bit_error_rate:.2%}")
    print(f"  Max frame size: {config.max_frame_size} bytes")
    print(f"  Data rate: {config.data_rate} bps")
    print()

    # ========================================================================
    # Step 2: Create and connect mock modem
    # ========================================================================
    print("Step 2: Create and connect mock modem")
    print("-" * 70)

    modem = MockModemDriver(config)
    modem.connect("/dev/null", 19200)  # Fake port (simulation mode)
    print()

    # ========================================================================
    # Step 3: Register RX callback to handle received messages
    # ========================================================================
    print("Step 3: Register RX callback")
    print("-" * 70)

    received_count = 0

    def on_receive(data: bytes, src_id: int) -> None:
        """Handle received acoustic frame."""
        nonlocal received_count
        received_count += 1

        try:
            # Decode uwacomm message
            msg = decode(Heartbeat, data)
            print(
                f"  ✓ Received heartbeat from vehicle {src_id}: "
                f"depth={msg.depth}m, battery={msg.battery}%"
            )
        except Exception as e:
            print(f"  ✗ Decode error: {e}")

    modem.attach_rx_callback(on_receive)
    print()

    # ========================================================================
    # Step 4: Send heartbeat messages
    # ========================================================================
    print("Step 4: Send heartbeat messages")
    print("-" * 70)

    # Send 5 heartbeats with varying depth/battery
    test_messages = [
        Heartbeat(depth=100, battery=95),
        Heartbeat(depth=250, battery=87),
        Heartbeat(depth=500, battery=72),
        Heartbeat(depth=750, battery=55),
        Heartbeat(depth=900, battery=38),
    ]

    for i, heartbeat in enumerate(test_messages, 1):
        encoded = encode(heartbeat)
        print(
            f"  [{i}/5] Sending heartbeat: depth={heartbeat.depth}m, "
            f"battery={heartbeat.battery}%, size={len(encoded)} bytes"
        )
        modem.send_frame(encoded, dest_id=0)  # Send to topside (ID 0)
        time.sleep(0.5)  # Stagger sends to avoid queue buildup

    print()

    # ========================================================================
    # Step 5: Wait for loopback responses
    # ========================================================================
    print("Step 5: Wait for loopback responses")
    print("-" * 70)
    print(
        f"  Waiting {config.transmission_delay * 2:.1f} seconds "
        f"for acoustic propagation..."
    )
    print()

    time.sleep(config.transmission_delay * 2 + 1.0)  # Wait for all responses

    # ========================================================================
    # Step 6: Summary
    # ========================================================================
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  Messages sent: {len(test_messages)}")
    print(f"  Messages received: {received_count}")
    print(
        f"  Packet loss: {(1 - received_count / len(test_messages)):.1%} "
        f"(expected ~{config.packet_loss_probability:.1%})"
    )
    print()

    if received_count == len(test_messages):
        print("  ✓ All messages received successfully!")
    elif received_count > 0:
        print(
            f"  ⚠ Some packet loss occurred ({len(test_messages) - received_count} "
            f"messages lost)"
        )
        print("    This is expected behavior with simulated channel loss")
    else:
        print("  ✗ No messages received (check configuration)")

    print()

    # ========================================================================
    # Step 7: Disconnect
    # ========================================================================
    print("Step 7: Disconnect mock modem")
    print("-" * 70)
    modem.disconnect()
    print()

    print("=" * 70)
    print("HITL simulation complete!")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  • Mock modem enables testing without physical hardware")
    print("  • Simulates realistic acoustic channel conditions")
    print("  • Perfect for CI/CD, development, and debugging")
    print("  • Same interface works with real hardware drivers (future)")
    print()


if __name__ == "__main__":
    main()
