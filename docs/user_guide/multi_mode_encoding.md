# Multi-Mode Encoding

uwacomm supports three encoding modes designed for different underwater communication scenarios. Each mode offers different trade-offs between bandwidth efficiency and functionality.

## Overview

| Mode | Overhead | Use Case | Bandwidth vs DCCL |
|------|----------|----------|-------------------|
| **Mode 1: Point-to-Point** | 0 bytes | Single UUV ↔ Topside | ✅ 8.2% smaller |
| **Mode 2: Self-Describing** | +1-2 bytes | Logging, replay, ad-hoc comms | 🤝 Tie |
| **Mode 3: Multi-Vehicle Routing** | +3-4 bytes | Swarm robotics, mesh networks | ✅ Feature advantage |

## Message Structure by Mode

### Mode 1: Point-to-Point (Default)

```
┌─────────────────┐
│    Payload      │  N bytes
└─────────────────┘
```

**When to use:** Single vehicle communicating with topside, or any point-to-point link where both sides know the message type upfront.

**Advantages:**
- Maximum compression (8.2% smaller than DCCL)
- Zero overhead beyond payload
- Fastest encoding/decoding

**Example:**
```python
from uwacomm import BaseMessage, BoundedInt, encode, decode

class Heartbeat(BaseMessage):
    depth_cm: int = BoundedInt(ge=0, le=10000)
    battery_pct: int = BoundedInt(ge=0, le=100)

msg = Heartbeat(depth_cm=2575, battery_pct=87)
encoded = encode(msg)  # Mode 1 (default) - 3 bytes

# Decoder must know message type
decoded = decode(Heartbeat, encoded)
```

---

### Mode 2: Self-Describing Messages

```
┌────────┬─────────────────┐
│ Msg ID │    Payload      │  (1-2) + N bytes
└────────┴─────────────────┘
         ↑ Varint-style encoding:
           - IDs 0-127: 1 byte (high bit = 0)
           - IDs 128-32767: 2 bytes (high bit = 1)
```

**When to use:** Logging to files, message replay systems, ad-hoc communications where the receiver doesn't know the message type upfront.

**Advantages:**
- Self-describing (can determine message type from bytes alone)
- Auto-decode capability via `MESSAGE_REGISTRY`
- Ties DCCL bandwidth (both include message ID)

**Example:**
```python
from uwacomm import encode, decode, register_message, decode_by_id

# Encode with message ID
class Status(BaseMessage):
    value: int = BoundedInt(ge=0, le=255)
    uwacomm_id: ClassVar[int] = 42

encoded = encode(msg, include_id=True)  # Mode 2 - 4 bytes (1 ID + 3 payload)

# Decode with ID validation
decoded = decode(Status, encoded, include_id=True)

# Or auto-decode by ID (no need to know the type!)
register_message(Status)
decoded = decode_by_id(encoded)  # Automatically determines type
```

**Message ID Encoding:**
- **Small IDs (0-127):** 1 byte with high bit = 0 (`0xxxxxxx`)
- **Large IDs (128-32767):** 2 bytes with high bit = 1 (`1xxxxxxx xxxxxxxx`)

---

### Mode 3: Multi-Vehicle Routing

```
┌────────┬─────────┬─────────┬────────┬─────────────────┐
│ Src ID │ Dest ID │ Msg ID  │ Flags  │    Payload      │
└────────┴─────────┴─────────┴────────┴─────────────────┘
  8 bits   8 bits   8-16 bits 3 bits      N bytes

Total: ~4-5 bytes overhead + N bytes payload
```

**Routing Header Structure:**
```
┌─────────┬─────────┬──────────┬──────────────┐
│ Src ID  │ Dest ID │ Priority │ ACK Request  │
│ 8 bits  │ 8 bits  │ 2 bits   │ 1 bit        │
└─────────┴─────────┴──────────┴──────────────┘
Total: 19 bits (~3 bytes)
```

**When to use:** Multi-vehicle systems, swarm robotics, mesh networks, or any scenario with more than 2 communicating nodes.

**Advantages:**
- Built-in source/destination addressing (0-255 vehicle IDs)
- Priority levels (0=low, 3=high)
- ACK request flag
- Broadcast support (dest_id=255)
- DCCL doesn't have this functionality

**Example:**
```python
from uwacomm import RoutingHeader, encode_with_routing, decode_with_routing

# Vehicle 3 sends high-priority heartbeat to topside (ID 0)
encoded = encode_with_routing(
    heartbeat,
    source_id=3,
    dest_id=0,
    priority=2,          # 0=low, 3=high
    ack_requested=True
)
# Size: 3 bytes routing + 1 byte ID + payload

# Topside receives and routes
routing, decoded = decode_with_routing(Heartbeat, encoded)
print(f"From vehicle {routing.source_id}, priority {routing.priority}")

if routing.ack_requested:
    # Send acknowledgment back to vehicle 3
    ack = encode_with_routing(ack_msg, source_id=0, dest_id=3)
```

**Routing Header Fields:**
- **source_id (8 bits):** Vehicle ID of sender (0-255)
- **dest_id (8 bits):** Vehicle ID of receiver (0-255, 255=broadcast)
- **priority (2 bits):** Message priority (0=low, 1=normal, 2=high, 3=urgent)
- **ack_requested (1 bit):** Whether sender expects acknowledgment

---

## Bandwidth Comparison

### Example: Heartbeat Message (23 bytes payload)

| Mode | Size | Breakdown | vs DCCL |
|------|------|-----------|---------|
| **Mode 1** | 23 bytes | 23 payload | ✅ -1 byte (4.2% smaller) |
| **Mode 2** | 24 bytes | 1 ID + 23 payload | 🤝 Tie |
| **Mode 3** | 27 bytes | 3 routing + 1 ID + 23 payload | ✅ +3 bytes but has routing |

**DCCL:** 24 bytes (always includes ID, no routing support)

### Transmission Time @ 80 bps (Typical Acoustic Modem)

| Mode | Heartbeat (23 bytes payload) | Savings vs JSON (~150 bytes) |
|------|------------------------------|------------------------------|
| **Mode 1** | 2.3 sec | **84.7%** faster |
| **Mode 2** | 2.4 sec | **84.0%** faster |
| **Mode 3** | 2.7 sec | **82.0%** faster |
| **JSON** | 15.0 sec | Baseline |

---

## Choosing the Right Mode

### Decision Tree

```
┌─────────────────────────────────┐
│ How many communicating nodes?   │
└────────┬────────────────────────┘
         │
    ┌────┴────┐
    │   2     │   Many (>2)
    │         │
    v         v
┌───────┐  ┌──────────────────┐
│ Known │  │   Mode 3:        │
│ type? │  │   Multi-Vehicle  │
│       │  │   Routing        │
│ Yes No│  └──────────────────┘
│  │  │ │
│  v  v │
│  M1 M2│
└───────┘

M1 = Mode 1 (Point-to-Point)
M2 = Mode 2 (Self-Describing)
```

### Quick Guide

**Use Mode 1 when:**
- Single UUV ↔ Topside communication
- Message type is known by both sides
- Maximum bandwidth efficiency needed
- Point-to-point link

**Use Mode 2 when:**
- Logging messages to file for later replay
- Message type not known upfront
- Need self-describing message format
- Building a message inspector/analyzer tool

**Use Mode 3 when:**
- Multiple vehicles communicating (swarm robotics)
- Mesh network topology
- Need source/destination addressing
- Priority-based message queuing
- ACK/retry mechanisms

---

## Auto-Decode by ID (Mode 2)

Mode 2 enables powerful auto-decode functionality using the message registry:

```python
from uwacomm import register_message, decode_by_id

# Register all message types your system uses
register_message(Heartbeat)
register_message(BatteryReport)
register_message(CommandAck)

# Now decode unknown messages automatically
received_bytes = acoustic_modem.receive()
msg = decode_by_id(received_bytes)

# Handle based on type
if isinstance(msg, Heartbeat):
    print(f"Heartbeat: depth={msg.depth_cm}cm")
elif isinstance(msg, BatteryReport):
    print(f"Battery: {msg.level}%")
elif isinstance(msg, CommandAck):
    print(f"Command acknowledged: {msg.cmd_id}")
```

---

## Multi-Vehicle Routing (Mode 3)

### Broadcast Messages

```python
# Vehicle 1 broadcasts mission update to all vehicles
broadcast_msg = encode_with_routing(
    mission_update,
    source_id=1,
    dest_id=255,  # 255 = broadcast
    priority=3     # Urgent
)
```

### Priority Queuing

```python
# Low priority (routine telemetry)
telemetry = encode_with_routing(msg, source_id=3, dest_id=0, priority=0)

# High priority (critical alert)
alert = encode_with_routing(msg, source_id=3, dest_id=0, priority=3)
```

### ACK/Retry Pattern

```python
# Sender: Request acknowledgment
cmd = encode_with_routing(
    command,
    source_id=0,
    dest_id=3,
    ack_requested=True
)
send_with_retry(cmd, max_retries=3)

# Receiver: Check if ACK needed
routing, msg = decode_with_routing(Command, received)
if routing.ack_requested:
    ack = encode_with_routing(ack_msg, source_id=3, dest_id=routing.source_id)
    acoustic_modem.send(ack)
```

---

## Performance Considerations

### Mode 1: Maximum Performance
- ✅ Smallest message size
- ✅ Fastest encode/decode
- ✅ Lowest latency
- ❌ Receiver must know message type

### Mode 2: Balanced
- ✅ Self-describing
- ✅ Flexible (unknown message types)
- ⚠️ +1-2 bytes overhead
- ✅ Ties DCCL bandwidth

### Mode 3: Feature-Rich
- ✅ Multi-vehicle addressing
- ✅ Priority queuing
- ✅ ACK support
- ⚠️ +3-4 bytes overhead
- ✅ Functionality DCCL lacks

---

## Migration Guide

### Upgrading from Mode 1 to Mode 2

```python
# Before (Mode 1)
encoded = encode(msg)
decoded = decode(MessageClass, encoded)

# After (Mode 2)
# Add uwacomm_id to message class
class MessageClass(BaseMessage):
    # ... fields ...
    uwacomm_id: ClassVar[int] = 42

encoded = encode(msg, include_id=True)
decoded = decode(MessageClass, encoded, include_id=True)

# Or use auto-decode
register_message(MessageClass)
decoded = decode_by_id(encoded)
```

### Upgrading from Mode 2 to Mode 3

```python
# Before (Mode 2)
encoded = encode(msg, include_id=True)
decoded = decode(MessageClass, encoded, include_id=True)

# After (Mode 3)
encoded = encode_with_routing(msg, source_id=1, dest_id=2)
routing, decoded = decode_with_routing(MessageClass, encoded)

# Access routing information
print(f"From: {routing.source_id}, To: {routing.dest_id}")
```

---

## Best Practices

1. **Start with Mode 1** for simple point-to-point systems
2. **Use Mode 2** when adding logging/replay capabilities
3. **Upgrade to Mode 3** when deploying multi-vehicle systems
4. **Document your message IDs** (use a central registry)
5. **Reserve ID ranges** for different subsystems (e.g., 0-99: telemetry, 100-199: commands)
6. **Use priority wisely** (don't make everything high priority)
7. **Broadcast sparingly** (it consumes bandwidth for all receivers)

---

## Examples

See the following examples for complete implementations:

- **Mode 1:** [Basic Usage](../examples/basic_usage.md)
- **Mode 2:** [Message Logging](../examples/message_logging.md)
- **Mode 3:** [Multi-Vehicle Swarm](../examples/multi_vehicle_swarm.md)
