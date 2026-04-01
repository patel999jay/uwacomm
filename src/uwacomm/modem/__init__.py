"""Acoustic modem driver abstraction layer.

This module provides a vendor-agnostic interface for acoustic modems, enabling:

- **Hardware-in-the-Loop (HITL) simulation**: Test without physical hardware
- **Multi-vendor support**: WHOI, EvoLogics, Sonardyne, custom modems
- **Swappable backends**: Switch modems without changing application code

## Available Drivers

### MockModemDriver (v0.3.0+)
Simulated modem for testing without hardware. Features:
- Configurable transmission delay (acoustic propagation)
- Probabilistic packet loss (unreliable channel)
- Bit error injection (acoustic noise)
- Loopback testing (echo sent frames)

### Future Drivers (v0.4.0+)
- **WhoiModemDriver**: WHOI MicroModem 2 adapter (via whoi_interface)
- **EvoLogicsModemDriver**: EvoLogics S2C modem adapter
- **SonarbyneModemDriver**: Sonardyne modem adapter
- **CustomDriver**: User-defined drivers for proprietary hardware

## Quick Start

```python
from uwacomm import encode, decode, BaseMessage, BoundedInt
from uwacomm.modem import MockModemDriver, MockModemConfig

# Define message
class Heartbeat(BaseMessage):
    depth: int = BoundedInt(ge=0, le=1000)
    uwacomm_id: int = 10

# Configure mock modem
config = MockModemConfig(
    transmission_delay=1.5,  # 1.5 second round-trip
    packet_loss_probability=0.1,  # 10% loss
)

# Create and connect modem
modem = MockModemDriver(config)
modem.connect("/dev/null", 19200)

# Register RX callback
def on_receive(data: bytes, src_id: int):
    msg = decode(Heartbeat, data)
    print(f"Received from {src_id}: depth={msg.depth}m")

modem.attach_rx_callback(on_receive)

# Send frame
msg = Heartbeat(depth=250)
modem.send_frame(encode(msg), dest_id=0)

# Wait for loopback
import time
time.sleep(2.0)
modem.disconnect()
```

## Design Philosophy

The `ModemDriver` abstraction is **completely vendor-agnostic**:
- NOT tied to WHOI, EvoLogics, or any specific manufacturer
- Uses common interface patterns (Strategy/Adapter)
- Enables third-party driver development without modifying uwacomm core
- Supports both testing (mock) and production (real hardware) workflows
"""

from uwacomm.modem.config import MockModemConfig
from uwacomm.modem.driver import ModemDriver
from uwacomm.modem.mock import MockModemDriver

__all__ = [
    "ModemDriver",
    "MockModemDriver",
    "MockModemConfig",
]
