"""Message Fragmentation Demo.

This example demonstrates splitting large messages across multiple acoustic
modem frames using the fragmentation API. Acoustic modems typically have
strict frame size limits (32-64 bytes), requiring larger messages to be
fragmented for transmission.

Run this example:
    python examples/fragmentation_demo.py
"""

from __future__ import annotations

import random
import time
from typing import ClassVar

from uwacomm import BaseMessage, BoundedInt, FixedBytes, decode, encode
from uwacomm.exceptions import FragmentationError
from uwacomm.fragmentation import fragment_message, reassemble_fragments
from uwacomm.modem import MockModemConfig, MockModemDriver


class LargeTelemetryMessage(BaseMessage):
    """Large telemetry message that requires fragmentation."""

    sensor_data: bytes = FixedBytes(length=150)  # 150 bytes of sensor data
    vehicle_id: int = BoundedInt(ge=0, le=255)
    sequence: int = BoundedInt(ge=0, le=65535)
    uwacomm_id: ClassVar[int | None] = 20


def demo_basic_fragmentation() -> None:
    """Demonstrate basic fragmentation and reassembly."""
    print("=" * 70)
    print("Demo 1: Basic Fragmentation")
    print("=" * 70)
    print()

    # Create large message
    sensor_data = bytes(range(256))[:150]  # 150 bytes of dummy sensor data
    msg = LargeTelemetryMessage(sensor_data=sensor_data, vehicle_id=42, sequence=100)

    # Encode message
    encoded = encode(msg)
    print(f"Original message size: {len(encoded)} bytes")
    print()

    # Fragment for 64-byte modem frames
    max_frame_size = 64
    fragments = fragment_message(encoded, max_fragment_size=max_frame_size)

    print(f"Fragmented into {len(fragments)} pieces (max {max_frame_size} bytes each):")
    for i, frag in enumerate(fragments):
        print(f"  Fragment {i}: {len(frag)} bytes")
    print()

    # Reassemble
    reassembled = reassemble_fragments(fragments)
    print(f"Reassembled message size: {len(reassembled)} bytes")

    # Decode
    decoded = decode(LargeTelemetryMessage, reassembled)
    print(f"Decoded: vehicle_id={decoded.vehicle_id}, sequence={decoded.sequence}")
    print(f"✓ Perfect reconstruction: {decoded.sensor_data == sensor_data}")
    print()


def demo_out_of_order_delivery() -> None:
    """Demonstrate handling out-of-order fragment delivery."""
    print("=" * 70)
    print("Demo 2: Out-of-Order Fragment Delivery")
    print("=" * 70)
    print()

    # Create and fragment message
    msg = LargeTelemetryMessage(sensor_data=b"x" * 150, vehicle_id=99, sequence=200)
    encoded = encode(msg)
    fragments = fragment_message(encoded, max_fragment_size=64)

    print(f"Original fragment order: {list(range(len(fragments)))}")

    # Shuffle fragments (simulate out-of-order delivery)
    shuffled = fragments.copy()
    random.shuffle(shuffled)

    print("Shuffled delivery order: [scrambled]")
    print()

    # Reassemble (handles out-of-order automatically)
    reassembled = reassemble_fragments(shuffled)
    decoded = decode(LargeTelemetryMessage, reassembled)

    print("✓ Reassembled correctly despite out-of-order delivery")
    print(f"  vehicle_id={decoded.vehicle_id}, sequence={decoded.sequence}")
    print()


def demo_missing_fragment_detection() -> None:
    """Demonstrate detection of missing fragments."""
    print("=" * 70)
    print("Demo 3: Missing Fragment Detection")
    print("=" * 70)
    print()

    # Create and fragment message
    msg = LargeTelemetryMessage(sensor_data=b"y" * 150, vehicle_id=77, sequence=300)
    encoded = encode(msg)
    fragments = fragment_message(encoded, max_fragment_size=64)

    print(f"Total fragments: {len(fragments)}")

    # Simulate packet loss (remove fragment 1)
    lost_fragment = 1
    incomplete = fragments[:lost_fragment] + fragments[lost_fragment + 1 :]

    print(f"Lost fragment: {lost_fragment}")
    print(f"Received fragments: {len(incomplete)}/{len(fragments)}")
    print()

    # Try to reassemble (will fail)
    try:
        reassemble_fragments(incomplete)
        print("✗ Should have detected missing fragment!")
    except FragmentationError as e:
        print("✓ Missing fragment detected:")
        print(f"  Error: {e}")
    print()


def demo_modem_integration() -> None:
    """Demonstrate fragmentation with mock modem."""
    print("=" * 70)
    print("Demo 4: Integration with Mock Modem")
    print("=" * 70)
    print()

    # Configure mock modem
    config = MockModemConfig(
        transmission_delay=0.5,  # 500ms delay
        packet_loss_probability=0.0,  # No loss for this demo
        max_frame_size=64,
    )

    modem = MockModemDriver(config)
    modem.connect("/dev/null", 19200)
    print("[Modem] Connected")
    print()

    # Prepare message
    msg = LargeTelemetryMessage(sensor_data=b"z" * 150, vehicle_id=123, sequence=400)
    encoded = encode(msg)

    # Fragment
    fragments = fragment_message(encoded, max_fragment_size=config.max_frame_size)
    print(f"[TX] Sending {len(fragments)} fragments...")

    # Collect received fragments
    received_fragments: list[bytes] = []

    def on_receive(data: bytes, _src_id: int) -> None:
        """Collect received fragments."""
        received_fragments.append(data)
        print(f"  [RX] Received fragment {len(received_fragments)}/{len(fragments)}")

    modem.attach_rx_callback(on_receive)

    # Send all fragments
    for i, frag in enumerate(fragments):
        modem.send_frame(frag, dest_id=0)
        print(f"  [TX] Sent fragment {i + 1}/{len(fragments)}")
        time.sleep(0.1)  # Stagger sends

    # Wait for all fragments
    print()
    print("[Wait] Waiting for acoustic propagation...")
    time.sleep(config.transmission_delay * 2 + 0.5)

    # Reassemble
    if len(received_fragments) == len(fragments):
        reassembled = reassemble_fragments(received_fragments)
        decoded = decode(LargeTelemetryMessage, reassembled)
        print("[RX] ✓ All fragments received and reassembled")
        print(f"  vehicle_id={decoded.vehicle_id}, sequence={decoded.sequence}")
    else:
        print(f"[RX] ✗ Missing fragments: {len(fragments) - len(received_fragments)}")

    modem.disconnect()
    print("[Modem] Disconnected")
    print()


def demo_concurrent_messages() -> None:
    """Demonstrate fragmenting multiple messages simultaneously."""
    print("=" * 70)
    print("Demo 5: Concurrent Fragmented Messages")
    print("=" * 70)
    print()

    # Create 3 different messages
    messages = [
        LargeTelemetryMessage(sensor_data=b"a" * 150, vehicle_id=1, sequence=1),
        LargeTelemetryMessage(sensor_data=b"b" * 150, vehicle_id=2, sequence=2),
        LargeTelemetryMessage(sensor_data=b"c" * 150, vehicle_id=3, sequence=3),
    ]

    # Fragment each with unique fragment ID
    all_fragments = {}
    for i, msg in enumerate(messages):
        encoded = encode(msg)
        frag_id = 1000 + i
        fragments = fragment_message(encoded, max_fragment_size=64, fragment_id=frag_id)
        all_fragments[frag_id] = (fragments, msg)
        print(f"Message {i + 1} (ID {frag_id}): {len(fragments)} fragments")

    print()

    # Reassemble each message
    for frag_id, (fragments, original_msg) in all_fragments.items():
        reassembled = reassemble_fragments(fragments)
        decoded = decode(LargeTelemetryMessage, reassembled)
        match = decoded.sensor_data == original_msg.sensor_data
        print(f"Message ID {frag_id}: ✓ Reassembled correctly" if match else "✗ Failed")

    print()


def main() -> None:
    """Run all fragmentation demos."""
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "Message Fragmentation Demo" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    demo_basic_fragmentation()
    demo_out_of_order_delivery()
    demo_missing_fragment_detection()
    demo_modem_integration()
    demo_concurrent_messages()

    print("=" * 70)
    print("All Demos Complete!")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  • Fragmentation enables sending large messages over size-limited modems")
    print("  • Automatic reassembly handles out-of-order delivery")
    print("  • Missing fragments are detected with clear error messages")
    print("  • Fragment IDs allow concurrent fragmented messages")
    print("  • Integrates seamlessly with MockModemDriver for testing")
    print()


if __name__ == "__main__":
    main()
