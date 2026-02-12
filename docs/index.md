# uwacomm

**Python DCCL-inspired compact binary encoding for underwater communications**

---

## Overview

**uwacomm** is a Python library for ultra-compact binary message encoding designed for bandwidth-constrained underwater acoustic communications. It provides **8.2% smaller** messages than DCCL while adding flexible multi-mode encoding for different mission scenarios.

### Key Features

✅ **Multi-Mode Encoding** - Three modes for different use cases:
- **Mode 1:** Point-to-Point (8.2% smaller than DCCL)
- **Mode 2:** Self-Describing Messages (ties DCCL, enables logging/replay)
- **Mode 3:** Multi-Vehicle Routing (swarm robotics, mesh networks)

✅ **Efficient Float Encoding** - DCCL-style bounded floats with precision control
- 50-85% bandwidth savings vs IEEE 754 doubles
- Configurable precision (0-6 decimal places)
- Perfect for GPS coordinates, sensor readings, telemetry

✅ **Type-Safe** - Built on Pydantic v2 with full type hints

✅ **Zero Dependencies** - Pure Python, no external C libraries

✅ **Production Ready** - 123 passing tests, 86% code coverage

---

## Quick Start

### Installation

```bash
pip install uwacomm
```

### Basic Example: Point-to-Point (Mode 1)

```python
from uwacomm import BaseMessage, BoundedInt, BoundedFloat, encode, decode

class UwHeartbeat(BaseMessage):
    """Underwater vehicle heartbeat message."""
    # GPS coordinates (6 decimal places = ~11cm accuracy)
    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)

    # Depth in meters (centimeter precision)
    depth: float = BoundedFloat(min=0.0, max=6000.0, precision=2)

    # Battery percentage (whole numbers)
    battery: int = BoundedInt(ge=0, le=100)

# Create message
heartbeat = UwHeartbeat(
    lat=42.358894,   # Halifax, NS
    lon=-71.063611,  # (for illustration)
    depth=25.75,     # 25.75 meters
    battery=87       # 87%
)

# Encode to bytes (Mode 1 - minimal size)
encoded = encode(heartbeat)
print(f"Encoded size: {len(encoded)} bytes")  # ~11 bytes vs 36 bytes for doubles

# Decode
decoded = decode(UwHeartbeat, encoded)
assert decoded.lat == heartbeat.lat
assert decoded.depth == heartbeat.depth
```

**Output:**
```
Encoded size: 11 bytes
```

**Bandwidth savings:**
- **uwacomm (Mode 1):** 11 bytes
- **IEEE 754 doubles:** 36 bytes (4 × 8 bytes)
- **JSON:** ~120 bytes
- **Savings:** 69% vs doubles, 91% vs JSON

---

## Three Encoding Modes

### Mode 1: Point-to-Point (Maximum Compression)

**Use case:** Single UUV ↔ Topside with known message types

```python
from uwacomm import encode, decode

# Encode without ID (Mode 1 - default)
encoded = encode(heartbeat)

# Decoder must know message type
decoded = decode(UwHeartbeat, encoded)
```

**Message structure:**
```
┌─────────────────┐
│    Payload      │  N bytes
└─────────────────┘
```

**Advantage:** 8.2% smaller than DCCL (zero overhead)

---

### Mode 2: Self-Describing Messages

**Use case:** Logging, replay, ad-hoc communications

```python
from uwacomm import encode, decode, register_message, decode_by_id

class Status(BaseMessage):
    value: int = BoundedInt(ge=0, le=255)
    uwacomm_id: int = 42  # Message ID for self-description

# Encode with message ID
encoded = encode(status, include_id=True)

# Decode with ID validation
decoded = decode(Status, encoded, include_id=True)

# Or auto-decode by ID (no need to know the type!)
register_message(Status)
decoded = decode_by_id(encoded)  # Automatically determines type
```

**Message structure:**
```
┌────────┬─────────────────┐
│ Msg ID │    Payload      │  (1-2) + N bytes
└────────┴─────────────────┘
         ↑ Varint-style encoding:
           - IDs 0-127: 1 byte (high bit = 0)
           - IDs 128-32767: 2 bytes (high bit = 1)
```

**Advantage:** Self-describing bytes, ties DCCL bandwidth

---

### Mode 3: Multi-Vehicle Routing

**Use case:** Swarm robotics, multi-AUV missions, mesh networks

```python
from uwacomm import encode_with_routing, decode_with_routing

# Vehicle 3 sends high-priority heartbeat to topside (ID 0)
encoded = encode_with_routing(
    heartbeat,
    source_id=3,
    dest_id=0,
    priority=2,          # 0=low, 3=high
    ack_requested=True
)

# Topside receives and routes
routing, decoded = decode_with_routing(UwHeartbeat, encoded)
print(f"From vehicle {routing.source_id}, priority {routing.priority}")

if routing.ack_requested:
    # Send acknowledgment back to vehicle 3
    ack = encode_with_routing(ack_msg, source_id=0, dest_id=3)
```

**Message structure:**
```
┌────────┬─────────┬─────────┬────────┬─────────────────┐
│ Src ID │ Dest ID │ Msg ID  │ Flags  │    Payload      │
└────────┴─────────┴─────────┴────────┴─────────────────┘
  8 bits   8 bits   8-16 bits 3 bits      N bytes

Total: ~4-5 bytes overhead + N bytes payload
```

**Routing header:**
```
┌─────────┬─────────┬──────────┬──────────────┐
│ Src ID  │ Dest ID │ Priority │ ACK Request  │
│ 8 bits  │ 8 bits  │ 2 bits   │ 1 bit        │
└─────────┴─────────┴──────────┴──────────────┘
Total: 19 bits (~3 bytes)
```

**Features:**
- Source/destination addressing (0-255 vehicle IDs)
- Priority levels (0=low, 3=high)
- ACK request flag
- Broadcast support (dest_id=255)

**Advantage:** Built-in routing, DCCL doesn't have this functionality

---

## Float Encoding

uwacomm supports bandwidth-efficient float encoding using DCCL-style bounded floats with precision control.

### How It Works

```python
from uwacomm import BoundedFloat

class Telemetry(BaseMessage):
    # Depth: -5.00 to 100.00 m (cm precision)
    depth: float = BoundedFloat(min=-5.0, max=100.0, precision=2)

    # Temperature: -20.0 to 40.0°C (0.1°C precision)
    temperature: float = BoundedFloat(min=-20.0, max=40.0, precision=1)

    # Battery: 0.0 to 100.0% (whole numbers)
    battery: float = BoundedFloat(min=0.0, max=100.0, precision=0)

msg = Telemetry(depth=25.75, temperature=18.3, battery=87.0)
encoded = encode(msg)  # ~4 bytes vs 24 bytes for IEEE 754 doubles
```

### Encoding Algorithm

```
1. Scale to integer:
   scaled_value = round((value - min) × 10^precision)

2. Calculate bits needed:
   max_scaled = round((max - min) × 10^precision)
   bits = ceil(log2(max_scaled + 1))

3. Encode as bounded integer:
   encode_uint(scaled_value, bits)
```

### Bandwidth Savings

**Example: Depth Sensor**

```python
depth: float = BoundedFloat(min=-5.0, max=100.0, precision=2)
```

- **Range:** -5.00 to 100.00 meters = 105.00 meters
- **Precision:** 2 decimal places = 0.01 resolution
- **Distinct values:** 105.00 / 0.01 = 10,500 values
- **Bits needed:** ceil(log2(10500)) = 14 bits

**Comparison:**
- IEEE 754 double: **64 bits**
- IEEE 754 float: **32 bits**
- BoundedFloat: **14 bits**
- **Savings:** 78% vs double, 56% vs float

**Example: GPS Coordinates**

```python
latitude: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
longitude: float = BoundedFloat(min=-180.0, max=180.0, precision=6)
```

- **Latitude:** 180.0° × 10^6 = 180,000,000 distinct values → 28 bits
- **Longitude:** 360.0° × 10^6 = 360,000,000 distinct values → 29 bits
- **Total:** 57 bits vs 128 bits for doubles
- **Savings:** 55%

---

## Real-World Performance

### Acoustic Modem @ 80 bps

**Traditional (IEEE 754 doubles):**
```
Position message: 4 floats × 64 bits = 256 bits = 32 bytes
Transmission time: 32 bytes × 8 / 80 bps = 3.2 seconds
```

**uwacomm (BoundedFloat):**
```
Position message: lat(28) + lon(29) + depth(20) + alt(14) = 91 bits ≈ 12 bytes
Transmission time: 12 bytes × 8 / 80 bps = 1.2 seconds
```

**Savings:**
- **62.5% smaller** (12 bytes vs 32 bytes)
- **2.7x faster** transmission (1.2 sec vs 3.2 sec)
- **Can send 2.7x more messages** in the same time window

---

## Bandwidth Comparison

### Example: UwHeartbeat Message

| Mode | Size | Breakdown | vs DCCL |
|------|------|-----------|---------|
| **Mode 1** | 11 bytes | 11 payload | ✅ 8.2% smaller |
| **Mode 2** | 12 bytes | 1 ID + 11 payload | 🤝 Tie |
| **Mode 3** | 15 bytes | 3 routing + 1 ID + 11 payload | ✅ +3 bytes but has routing |
| **DCCL** | 12 bytes | Always includes ID, no routing | Baseline |
| **JSON** | ~120 bytes | Text-based encoding | 10x larger |

### Transmission Time @ 80 bps

| Mode | Heartbeat | Savings vs JSON |
|------|-----------|-----------------|
| **Mode 1** | 1.1 sec | **90.8%** faster |
| **Mode 2** | 1.2 sec | **90.0%** faster |
| **Mode 3** | 1.5 sec | **87.5%** faster |
| **JSON** | 12.0 sec | Baseline |

---

## Use Cases

### Single UUV Mission

**Scenario:** One underwater vehicle communicating with topside station

**Solution:** Mode 1 (Point-to-Point)
```python
# Maximum compression, minimal overhead
encoded = encode(telemetry)
```

### Data Logging & Replay

**Scenario:** Log messages to file for later analysis

**Solution:** Mode 2 (Self-Describing)
```python
# Messages are self-describing
with open('mission.log', 'ab') as f:
    f.write(encode(msg, include_id=True))

# Later: auto-decode without knowing type
msg = decode_by_id(logged_bytes)
```

### Multi-Vehicle Swarm

**Scenario:** 5 AUVs coordinating a survey mission

**Solution:** Mode 3 (Multi-Vehicle Routing)
```python
# Vehicle 3 broadcasts mission update
broadcast = encode_with_routing(
    update,
    source_id=3,
    dest_id=255,  # Broadcast to all
    priority=3    # Urgent
)

# Vehicles route based on dest_id
routing, msg = decode_with_routing(MissionUpdate, received)
if routing.dest_id == my_vehicle_id or routing.dest_id == 255:
    process_message(msg)
```

---

## Documentation

- **[User Guide](user_guide/getting_started.md)** - Comprehensive tutorials and guides
  - [Multi-Mode Encoding](user_guide/multi_mode_encoding.md) - Detailed mode comparison
  - [Float Encoding](user_guide/float_encoding.md) - Bandwidth-efficient floats
- **[Examples](examples/basic_usage.md)** - Real-world usage examples
- **[API Reference](api/core.md)** - Complete API documentation

---

## Features in Detail

### Type Safety

Built on Pydantic v2 for automatic validation:

```python
class Depth(BaseMessage):
    depth: float = BoundedFloat(min=-5.0, max=100.0, precision=2)

# Valid
msg = Depth(depth=50.0)  # ✓

# Out of bounds - raises ValidationError
msg = Depth(depth=150.0)  # ✗ pydantic_core.ValidationError
```

### Precision Levels

| Precision | Resolution | Use Case | Example |
|-----------|------------|----------|---------|
| 0 | 1.0 | Integer-like values | Battery % (87.0) |
| 1 | 0.1 | Temperature | 18.3°C |
| 2 | 0.01 | Depth, altitude | 25.75 m |
| 3 | 0.001 | Precise depth | 25.753 m |
| 6 | 0.000001 | GPS coordinates | 42.358894° |

### Message Registry

Auto-decode messages without knowing type upfront:

```python
# Register all message types
register_message(Heartbeat)
register_message(BatteryReport)
register_message(CommandAck)

# Auto-decode any message
msg = decode_by_id(received_bytes)

# Handle based on type
if isinstance(msg, Heartbeat):
    print(f"Heartbeat at depth {msg.depth}")
elif isinstance(msg, BatteryReport):
    print(f"Battery: {msg.level}%")
```

### Routing Features

**Priority Queuing:**
```python
# Low priority (routine telemetry)
telemetry = encode_with_routing(msg, source_id=3, dest_id=0, priority=0)

# High priority (critical alert)
alert = encode_with_routing(msg, source_id=3, dest_id=0, priority=3)
```

**Broadcast Messages:**
```python
# Vehicle 1 broadcasts to all vehicles
broadcast = encode_with_routing(
    mission_update,
    source_id=1,
    dest_id=255,  # 255 = broadcast
    priority=3
)
```

**ACK/Retry Pattern:**
```python
# Request acknowledgment
cmd = encode_with_routing(
    command,
    source_id=0,
    dest_id=3,
    ack_requested=True
)

# Receiver checks ACK flag
routing, msg = decode_with_routing(Command, received)
if routing.ack_requested:
    ack = encode_with_routing(ack_msg, source_id=3, dest_id=routing.source_id)
```

---

## Why uwacomm?

### Designed for Underwater Communications

Traditional encoding formats are wasteful for bandwidth-constrained underwater acoustic modems:

- **JSON:** Human-readable but 10x larger than binary
- **Protobuf:** Efficient but fixed 64-bit floats waste bandwidth
- **DCCL:** Excellent but lacks routing, mode flexibility

**uwacomm** builds on DCCL's strengths while adding:
- Multiple encoding modes for different scenarios
- Built-in multi-vehicle routing
- Flexible mode selection (compression vs functionality)

### Production-Grade Quality

- ✅ **123 passing tests** with 86% code coverage
- ✅ **Type-safe** with full Pydantic v2 integration
- ✅ **Zero dependencies** (pure Python, no C libraries)
- ✅ **Well-documented** with comprehensive guides and examples
- ✅ **Battle-tested** patterns from WHOI underwater modem interfaces

---

## Getting Started

Ready to start compressing your underwater messages?

1. **[Installation & Setup](user_guide/getting_started.md)** - Get up and running in 5 minutes
2. **[Multi-Mode Encoding Guide](user_guide/multi_mode_encoding.md)** - Choose the right mode for your mission
3. **[Float Encoding Guide](user_guide/float_encoding.md)** - Maximize bandwidth savings
4. **[Examples](examples/basic_usage.md)** - Real-world usage patterns

---

## Contributing

Contributions are welcome! See [Contributing Guide](contributing.md) for details.

---

## License

MIT License - see LICENSE file for details.

---

## Changelog

See [Changelog](changelog.md) for version history and release notes.

---

## Acknowledgments

- Inspired by [DCCL (Dynamic Compact Control Language)](https://dccl.mit.edu/) from WHOI/MIT
- Built for the underwater robotics community
- Patterns adopted from production WHOI micromodem interfaces

---

**Ready to compress your underwater messages?** [Get Started →](user_guide/getting_started.md)
