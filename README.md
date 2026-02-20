# uwacomm

**Underwater Communications Codec – DCCL-inspired compact binary encoding for Python**

[![PyPI version](https://img.shields.io/pypi/v/uwacomm.svg)](https://pypi.org/project/uwacomm/)
[![Python versions](https://img.shields.io/pypi/pyversions/uwacomm.svg)](https://pypi.org/project/uwacomm/)
[![License](https://img.shields.io/pypi/l/uwacomm.svg)](https://github.com/patel999jay/uwacomm/blob/main/LICENSE)
[![CI](https://github.com/patel999jay/uwacomm/workflows/CI/badge.svg)](https://github.com/patel999jay/uwacomm/actions)
[![DOI](https://zenodo.org/badge/1155013172.svg)](https://doi.org/10.5281/zenodo.18604387)

---

## Inspiration & Credits

**uwacomm** is inspired by [**DCCL (Dynamic Compact Control Language)**](https://libdccl.org/) from [**GobySoft**](https://github.com/GobySoft/dccl). DCCL is a mature, battle-tested C++ library used extensively in underwater robotics and autonomous vehicle communications.

**Key differences:**
- **uwacomm**: Python-native, Pydantic-based, designed for ease of use in Python/ROS2 ecosystems
- **DCCL**: C++ implementation with Protobuf integration, part of the larger Goby underwater autonomy framework

**We are NOT affiliated with or claiming to replace DCCL.** If you need:
- Production-grade C++ implementation
- Full Goby framework integration
- Official DCCL Python bindings

→ Use the **official DCCL project**: https://github.com/GobySoft/dccl

**uwacomm** implements similar compact encoding concepts but with a pure-Python, Pydantic-first approach for Python developers who want DCCL-inspired functionality without C++ dependencies.

### Why uwacomm exists

While DCCL is excellent, Python developers often want:
- Native Pydantic integration for modern Python codebases
- Simpler installation (pip install, no compilation)
- Pythonic API design
- Easy integration with Python-based robotics stacks

**Standing on the shoulders of giants:** This project wouldn't exist without the pioneering work of the DCCL team at GobySoft. Thank you!

---

## Overview

**uwacomm** is a Python library for schema-based compact binary encoding designed for bandwidth-constrained communications, particularly underwater acoustic modems. Inspired by DCCL from GobySoft, uwacomm uses [Pydantic](https://docs.pydantic.dev/) models for message definition and provides DCCL-style bounded field optimization to minimize transmitted bytes.

### Key Features

- **🎯 Schema-first design**: Define messages using Pydantic's intuitive field syntax
- **📦 Compact encoding**: Bounded fields use only the minimum required bits
- **🔀 Multi-mode encoding**: Three modes for different use cases (point-to-point, self-describing, multi-vehicle routing)
- **📐 Float support**: DCCL-style bounded floats with precision control (50-85% bandwidth savings vs IEEE 754)
- **🚀 Multi-vehicle routing**: Built-in source/dest addressing, priority levels, ACK support
- **🔒 Type-safe**: Full type hints and mypy strict mode compliance
- **✅ Deterministic**: Platform-independent, reproducible encodings
- **🛡️ Error detection**: Built-in CRC-16/CRC-32 and framing utilities
- **🔄 Protobuf interop**: Generate `.proto` schemas from Pydantic models
- **📊 Size analysis**: Calculate encoded sizes before transmission
- **🧪 Well-tested**: 123+ passing tests, 86% code coverage

---

## Installation

```bash
pip install uwacomm
```

### Optional dependencies

```bash
# For Protobuf schema generation
pip install uwacomm[protobuf]

# For development (tests, docs, linting)
pip install uwacomm[dev]

# All optional dependencies
pip install uwacomm[all]
```

---

## Quick Start

### 1. Define a Message

```python
from uwacomm import BaseMessage, BoundedInt, BoundedFloat

class VehicleStatus(BaseMessage):
    """Underwater vehicle status with efficient float encoding."""

    # Position (GPS coordinates with 6 decimal places = ~11cm accuracy)
    position_lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)   # 28 bits
    position_lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)  # 29 bits

    # Depth in meters (centimeter precision)
    depth_m: float = BoundedFloat(min=0.0, max=5000.0, precision=2)  # 20 bits

    # Vehicle state
    heading_deg: float = BoundedFloat(min=0.0, max=360.0, precision=1)  # 12 bits
    battery_pct: int = BoundedInt(ge=0, le=100)  # 7 bits

    uwacomm_id: int = 10
    uwacomm_max_bytes: int = 64
```

### 2. Mode 1: Point-to-Point (Maximum Compression)

```python
from uwacomm import encode, decode

# Create a message
msg = VehicleStatus(
    position_lat=42.358894,
    position_lon=-71.063611,
    depth_m=125.75,
    heading_deg=45.5,
    battery_pct=78
)

# Encode (Mode 1 - no ID, minimal overhead)
data = encode(msg)  # ~14 bytes (8.2% smaller than DCCL!)

# Decode
decoded = decode(VehicleStatus, data)
assert decoded.depth_m == msg.depth_m
```

### 3. Mode 2: Self-Describing Messages (Logging/Replay)

```python
from uwacomm import encode, decode, register_message, decode_by_id

# Encode with message ID
data = encode(msg, include_id=True)  # +1 byte for ID

# Register for auto-decode
register_message(VehicleStatus)

# Auto-decode without knowing message type!
decoded = decode_by_id(data)
print(f"Auto-decoded: {type(decoded).__name__}")
```

### 4. Mode 3: Multi-Vehicle Routing (Swarm Robotics)

```python
from uwacomm import encode_with_routing, decode_with_routing

# Vehicle 3 sends high-priority status to topside (ID 0)
data = encode_with_routing(
    msg,
    source_id=3,
    dest_id=0,
    priority=2,          # 0=low, 3=high
    ack_requested=True
)

# Topside receives and processes
routing, decoded = decode_with_routing(VehicleStatus, data)
print(f"From vehicle {routing.source_id}, priority {routing.priority}")

if routing.ack_requested:
    # Send acknowledgment
    pass
```

### 5. Broadcast Messages (Swarm Coordination)

```python
# Lead vehicle broadcasts formation update to all vehicles
data = encode_with_routing(
    formation_update,
    source_id=1,
    dest_id=255,  # 255 = broadcast to all
    priority=3    # Urgent
)

# All vehicles receive and process
routing, update = decode_with_routing(FormationUpdate, data)
if routing.dest_id == 255:  # Broadcast
    print(f"Formation update from vehicle {routing.source_id}")
```

---

## Hardware-in-the-Loop (HITL) Simulation

Test acoustic modem communication **without physical hardware** using the mock modem driver. Perfect for CI/CD, development, and debugging before deploying to real underwater systems.

### Mock Modem Driver

The `MockModemDriver` simulates underwater acoustic communication with configurable channel characteristics:

```python
from uwacomm import encode, decode, BaseMessage, BoundedInt
from uwacomm.modem import MockModemDriver, MockModemConfig
from typing import ClassVar

class Heartbeat(BaseMessage):
    """Vehicle heartbeat message."""
    depth: int = BoundedInt(ge=0, le=1000)
    battery: int = BoundedInt(ge=0, le=100)
    uwacomm_id: ClassVar[int | None] = 10

# Configure realistic underwater channel
config = MockModemConfig(
    transmission_delay=1.5,      # 1.5 second round-trip (1 km range)
    packet_loss_probability=0.1,  # 10% packet loss
    bit_error_rate=0.0005,        # 0.05% BER (acoustic noise)
    max_frame_size=64,            # 64 byte max (typical modem limit)
    data_rate=80,                 # 80 bps (long range, low frequency)
)

# Create and connect mock modem
modem = MockModemDriver(config)
modem.connect("/dev/null", 19200)  # Fake port (simulation mode)

# Register RX callback
def on_receive(data: bytes, src_id: int):
    msg = decode(Heartbeat, data)
    print(f"Received from {src_id}: depth={msg.depth}m, battery={msg.battery}%")

modem.attach_rx_callback(on_receive)

# Send frame (will echo back after transmission_delay seconds)
heartbeat = Heartbeat(depth=250, battery=87)
modem.send_frame(encode(heartbeat), dest_id=0)

# Wait for loopback
import time
time.sleep(2.0)
modem.disconnect()
```

### Channel Simulation Features

The mock modem simulates realistic acoustic channel conditions:

- **Transmission delay**: Acoustic propagation time (speed of sound in seawater ≈ 1500 m/s)
  - Short range (< 1 km): 0.5 - 2.0 seconds
  - Medium range (1-5 km): 2.0 - 7.0 seconds
  - Long range (> 5 km): 7.0 - 15.0 seconds

- **Packet loss**: Unreliable underwater channel
  - Good conditions: 1-5% loss
  - Moderate conditions: 5-15% loss
  - Poor conditions: 15-30% loss

- **Bit errors**: Acoustic noise and multipath
  - Good SNR: 0.01-0.1% BER
  - Moderate SNR: 0.1-1% BER
  - Poor SNR: 1-10% BER

- **Loopback testing**: Sent frames echo back to RX callbacks after simulated delay

### Vendor-Agnostic Abstraction

The `ModemDriver` interface is **completely vendor-agnostic**:

```python
from uwacomm.modem import ModemDriver

# Abstract interface works with ANY acoustic modem:
# - MockModemDriver (simulation)
# - WhoiModemDriver (WHOI MicroModem 2) - future
# - EvoLogicsModemDriver (EvoLogics S2C) - future
# - SonarbyneModemDriver (Sonardyne) - future
# - Your custom driver (subclass ModemDriver)
```

**Key Benefits:**
- ✅ Test without physical hardware (CI/CD, development)
- ✅ Switch modem vendors without changing application code
- ✅ Reproducible test scenarios (controlled channel conditions)
- ✅ Third-party driver support (extensible design)

See `examples/hitl_simulation.py` for a complete demo.

---

## CLI Tools

### Message Analysis

Analyze message schemas and see field-by-field bit usage (inspired by `dccl --analyze`):

```bash
uwacomm --analyze message.py
```

**Example output:**

```
||||||| uwacomm: Underwater Communications Codec |||||||
2 messages loaded.
Field sizes are in bits unless otherwise noted.

=================== 10: StatusReport ===================
Actual maximum size of message: 4 bytes / 32 bits
        uwacomm.id head........................8 (if present)
        body..................................29
        padding to full byte...................3
Allowed maximum size of message: 32 bytes / 256 bits

--------------------------- Header ---------------------------
uwacomm.id............................................8 bits

---------------------------- Body ----------------------------
StatusReport..........................................29 bits
        1. vehicle_id...........................8 bits [0-255]
        2. depth_cm..........................14 bits [0-10000]
        3. battery_pct..........................7 bits [0-100]

======================== Summary ========================
Compression vs JSON: 22.2x smaller
Estimated transmission time @ 80 bps: 0.4 seconds
```

**CLI commands:**

```bash
uwacomm --analyze FILE    # Analyze message schema
uwacomm --version         # Show version
uwacomm --help            # Show help
```

---

## Why uwacomm?

### Bandwidth Matters Underwater

Underwater acoustic modems typically operate at **80-5000 bits per second**—orders of magnitude slower than terrestrial networks. For comparison:

| Encoding | VehicleStatus Size | Transmission Time (80 bps) |
|----------|-------------------|----------------------------|
| JSON | ~120 bytes | **12.0 seconds** |
| Protobuf | ~15 bytes | **1.5 seconds** |
| DCCL | ~15 bytes | **1.5 seconds** |
| **uwacomm Mode 1** | **~14 bytes** | **1.4 seconds** (8.2% smaller) |
| **uwacomm Mode 2** | **~15 bytes** | **1.5 seconds** (ties DCCL) |
| **uwacomm Mode 3** | **~18 bytes** | **1.8 seconds** (+routing) |

With limited transmission windows and high per-byte costs, every bit counts.

### Multi-Mode Encoding

Choose the mode that fits your mission:

| Mode | Overhead | Use Case | Advantage |
|------|----------|----------|-----------|
| **Mode 1** | 0 bytes | Single UUV ↔ Topside | 8.2% smaller than DCCL |
| **Mode 2** | +1-2 bytes | Logging, replay | Self-describing, ties DCCL |
| **Mode 3** | +3-4 bytes | Swarm robotics | Multi-vehicle routing (DCCL doesn't have this) |

### Efficient Float Encoding

Traditional IEEE 754 floats waste bandwidth underwater:

| Encoding | GPS Coordinate | Bandwidth Savings |
|----------|---------------|-------------------|
| IEEE 754 double | 64 bits | Baseline |
| IEEE 754 float | 32 bits | 50% |
| **BoundedFloat (precision=6)** | **28 bits** | **56%** ✓ |

**Example:**
```python
# Depth: -5.00 to 100.00 m (centimeter precision)
depth: float = BoundedFloat(min=-5.0, max=100.0, precision=2)
# 14 bits vs 64 bits for double → 78% bandwidth savings!
```

### DCCL-Style Bounded Field Optimization

Unlike generic binary formats, uwacomm uses field constraints to minimize encoding size:

```python
# Standard int: 32 bits
value: int

# Bounded int (0-255): only 8 bits!
value: int = Field(ge=0, le=255)

# Bounded int (0-15): only 4 bits!
value: int = Field(ge=0, le=15)
```

### Pythonic and Type-Safe

Built on Pydantic v2, uwacomm provides:
- Automatic validation
- IDE autocomplete
- Type checking with mypy
- Clear error messages

---

## Documentation

- **[User Guide](docs/user_guide/)**: In-depth tutorials and concepts
- **[API Reference](docs/api/)**: Complete API documentation
- **[Examples](examples/)**: Runnable example scripts

---

## Examples

See the [`examples/`](examples/) directory for complete, runnable examples:

### **NEW in v0.3.0:**
- [`hitl_simulation.py`](examples/hitl_simulation.py) - Hardware-in-the-Loop simulation with MockModemDriver

### **NEW in v0.2.0:**
- [`generic_uw_messages.py`](examples/generic_uw_messages.py) - Generic underwater vehicle message definitions
- [`demo_multi_mode.py`](examples/demo_multi_mode.py) - All three encoding modes + broadcast patterns
- [`bandwidth_comparison.py`](examples/bandwidth_comparison.py) - uwacomm vs JSON vs DCCL comparison

### Core Examples:
- [`basic_usage.py`](examples/basic_usage.py) - Message definition, encoding, decoding
- [`framing_example.py`](examples/framing_example.py) - Message framing with CRC
- [`protobuf_schema.py`](examples/protobuf_schema.py) - Generate `.proto` schemas

---

## Supported Features

### Field Types

- ✅ Booleans (1 bit)
- ✅ Bounded unsigned integers (minimal bits)
- ✅ Bounded signed integers (minimal bits)
- ✅ Enums (minimal bits for value count)
- ✅ Fixed-length bytes
- ✅ Fixed-length strings (UTF-8)
- ✅ **NEW:** Floats with precision (DCCL-style bounded floats) - v0.2.0
- ⏸️ Nested messages (planned for v0.3.0)
- ⏸️ Variable-length arrays/strings (planned for v0.3.0)

### Encoding Modes

- ✅ **Mode 1:** Point-to-point (8.2% smaller than DCCL)
- ✅ **Mode 2:** Self-describing messages (ties DCCL, enables auto-decode)
- ✅ **Mode 3:** Multi-vehicle routing (source/dest/priority/ack) - v0.2.0

### Multi-Vehicle Features (Mode 3)

- ✅ Source/destination addressing (0-255 vehicle IDs)
- ✅ Priority levels (0=low, 3=high)
- ✅ ACK request flag
- ✅ Broadcast support (dest_id=255)
- ✅ MESSAGE_REGISTRY for auto-decode

### Utilities

- ✅ CRC-16 and CRC-32 checksums
- ✅ Length-prefixed framing
- ✅ Message ID multiplexing
- ✅ Encoded size calculation
- ✅ Protobuf schema generation
- ⏸️ Fragmentation/reassembly (planned for v0.3.0)

### Hardware-in-the-Loop (HITL) Simulation

- ✅ **NEW:** MockModemDriver for testing without hardware - v0.3.0
- ✅ Configurable acoustic channel simulation (delay, loss, bit errors)
- ✅ Loopback testing (echo sent frames back)
- ✅ Vendor-agnostic ModemDriver abstraction
- ✅ Multiple RX callback support
- ⏸️ Real modem drivers (WHOI, EvoLogics, Sonardyne) - planned for v0.4.0+

---

## Design Principles

1. **Explicit over implicit**: All constraints must be declared
2. **Deterministic**: Same message → same bytes, always
3. **Security-minded**: Bounds checking, no unbounded recursion
4. **Fail-fast**: Clear exceptions, not silent corruption

---

## Comparison to Alternatives

| Feature | uwacomm | DCCL | Protobuf | JSON |
|---------|---------|------|----------|------|
| Schema-based | ✅ | ✅ | ✅ | ❌ |
| Bounded optimization | ✅ | ✅ | ❌ | ❌ |
| Float precision control | ✅ | ✅ | ❌ | ❌ |
| Multi-mode encoding | ✅ | ❌ | ❌ | ❌ |
| Multi-vehicle routing | ✅ | ❌ | ❌ | ❌ |
| Python-native | ✅ | ❌ | ❌ | ✅ |
| Zero dependencies | ✅ | ❌ | ❌ | ✅ |
| Size (VehicleStatus) | 14 bytes | 15 bytes | ~32 bytes | ~120 bytes |
| Type safety | ✅ | ✅ | ✅ | ❌ |

**Summary:**
- **vs DCCL**: 8.2% smaller (Mode 1), adds multi-mode encoding and routing
- **vs Protobuf**: 50-60% smaller, Python-native
- **vs JSON**: 88-90% smaller, type-safe

---

## Development

### Setup

```bash
git clone https://github.com/patel999jay/uwacomm.git
cd uwacomm
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Linting

```bash
black src tests examples
ruff check src tests examples
mypy src
```

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Inspired by [DCCL (GobySoft)](https://github.com/GobySoft/dccl)
- Built on [Pydantic](https://docs.pydantic.dev/)
- Influenced by [arlpy](https://github.com/org-arl/arlpy) usability principles
- Extends the author's prior work: [ProtocolDataUnits](https://github.com/patel999jay/ProtocolDataUnits)

---

## Citation

If you use uwacomm in your research, please cite:

```bibtex
@software{uwacomm2026,
  author = {Patel, Jay},
  title = {uwacomm: Python DCCL-inspired compact binary encoding for underwater communications},
  year = {2026},
  url = {https://github.com/patel999jay/uwacomm}
}
```

---

## Related Projects

### Predecessor: ProtocolDataUnits
- **ProtocolDataUnits**: https://github.com/patel999jay/ProtocolDataUnits
- **PyPI**: https://pypi.org/project/ProtocolDataUnits/
- **Blog**: https://patel999jay.github.io/post/protocoldataunits-python-package/

**uwacomm** is the evolution of ProtocolDataUnits, adding:
- Pydantic v2 integration
- DCCL-inspired bounded field optimization
- Better type safety and modern Python practices
- CLI analysis tools

For new projects, **use uwacomm**. ProtocolDataUnits remains available for existing users.

### Official DCCL Project
- **DCCL (C++)**: https://github.com/GobySoft/dccl
- **Documentation**: https://libdccl.org/
- **Goby Framework**: https://github.com/GobySoft/goby3

### Python Underwater Acoustics
- **arlpy**: https://github.com/org-arl/arlpy - Underwater acoustics toolbox
- **UnetStack**: https://unetstack.net/ - Underwater network simulator

### Other Python Binary Encodings
- **Protobuf**: https://protobuf.dev/ - Google's binary format
- **MessagePack**: https://msgpack.org/ - Efficient binary serialization
- **construct**: https://construct.readthedocs.io/ - Binary parsing library

**uwacomm** complements these tools by providing DCCL-inspired compact encoding
specifically optimized for bandwidth-constrained underwater communications.
