# Message Definition

Messages in uwacomm are defined as Python classes that inherit from `BaseMessage` (a Pydantic `BaseModel` subclass). Field annotations and constraints drive the bit-level encoding — no schema file, no code generation step.

---

## Basic Structure

```python
from typing import ClassVar
from uwacomm import BaseMessage, BoundedInt
from uwacomm.models.fields import BoundedFloat

class VehicleStatus(BaseMessage):
    vehicle_id: int = BoundedInt(ge=0, le=255)    # 8 bits
    depth_cm: int = BoundedInt(ge=0, le=50000)    # 16 bits
    battery: int = BoundedInt(ge=0, le=100)        # 7 bits
    active: bool                                   # 1 bit

    # Optional class-level metadata
    uwacomm_id: ClassVar[int | None] = 10         # enables Mode 2/3
    uwacomm_max_bytes: ClassVar[int | None] = 64  # enforces size limit
```

`ClassVar` fields are **not encoded** — they carry schema metadata only.

---

## Field Types

### Boolean — 1 bit

```python
active: bool          # False=0, True=1
```

### Bounded Integer

Use `BoundedInt(ge=, le=)` or plain `Field(ge=, le=)`. The encoder packs only the minimum bits needed for the range.

```python
from uwacomm import BoundedInt
from pydantic import Field

vehicle_id: int = BoundedInt(ge=0, le=255)    # 8 bits  (range 256)
depth_cm: int = BoundedInt(ge=0, le=50000)    # 16 bits (range 50001)
nibble: int = Field(ge=0, le=15)              # 4 bits  (range 16)
```

Bits = `ceil(log2(max − min + 1))`.

### Bounded Float

DCCL-style: scale to integer → encode as bounded int.

```python
from uwacomm.models.fields import BoundedFloat

lat: float = BoundedFloat(min=-90.0,  max=90.0,  precision=6)  # 28 bits
lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)  # 29 bits
temp: float = BoundedFloat(min=-20.0, max=40.0,  precision=1)  # 10 bits
```

Formula: `scaled = round((value − min) × 10^precision)`, bits = `ceil(log2(max_scaled + 1))`.

| Precision | Resolution | Example use |
|-----------|------------|-------------|
| 0 | 1.0 | Battery % |
| 1 | 0.1 | Temperature |
| 2 | 0.01 | Depth (m) |
| 6 | 0.000001 | GPS coordinates |

### Enum

```python
import enum
from uwacomm import BaseMessage

class Mode(enum.Enum):
    IDLE = 0
    SURVEY = 1
    RETURN = 2
    EMERGENCY = 3

class MissionState(BaseMessage):
    mode: Mode    # 2 bits (4 values → ceil(log2(4)) = 2)
```

### Fixed-Length Bytes

```python
from uwacomm import FixedBytes, FixedStr

checksum: bytes = FixedBytes(length=4)   # always 32 bits
callsign: str   = FixedStr(length=8)    # always 64 bits (ASCII)
```

---

## Variable-Length Fields (v0.4.0)

Variable-length fields write a compact **length prefix** before the actual data. On-wire size grows with actual content — an empty field costs only the prefix bits.

Length prefix width = `ceil(log2(max_length + 1))` bits.

### VarBytes

```python
from uwacomm.models.fields import VarBytes

payload: bytes = VarBytes(max_length=64)
# max bits: ceil(log2(65))=7 prefix + 64×8=512 payload = 519 bits
# empty:    7 bits (just the prefix)
```

### VarStr

ASCII strings only. Non-ASCII input raises `EncodeError` at encode time.

```python
from uwacomm.models.fields import VarStr

callsign: str = VarStr(max_length=8)
# max bits: ceil(log2(9))=4 prefix + 8×8=64 payload = 68 bits
```

### VarList

Variable-length list of bounded integers, booleans, or floats.

```python
from uwacomm.models.fields import VarList

# List of bounded ints
depths: list[int] = VarList(max_length=8, item_ge=0, item_le=1000)
# prefix: ceil(log2(9))=4 bits, each element: ceil(log2(1001))=10 bits

# List of booleans (1 bit per element)
flags: list[bool] = VarList(max_length=8)
# prefix: 4 bits, each flag: 1 bit

# List of bounded floats
temps: list[float] = VarList(max_length=4, item_ge=-20.0, item_le=40.0, item_precision=1)
# prefix: ceil(log2(5))=3 bits, each temp: ceil(log2(601))=10 bits
```

**VarList parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `max_length` | `int` | Maximum number of elements (required) |
| `item_ge` | `int \| float` | Minimum element value (required for int/float) |
| `item_le` | `int \| float` | Maximum element value (required for int/float) |
| `item_precision` | `int` | Decimal precision for float elements |

### Size comparison: empty vs full

```python
from uwacomm import encode, encoded_bits

class Msg(BaseMessage):
    id: int = BoundedInt(ge=0, le=255)
    data: bytes = VarBytes(max_length=32)

print(encoded_bits(Msg))                             # 8 + 6 + 256 = 270 bits (max)
print(len(encode(Msg(id=1, data=b""))))              # 2 bytes (id + empty prefix)
print(len(encode(Msg(id=1, data=bytes(32)))))        # 34 bytes (id + prefix + 32 bytes)
```

---

## Nested Messages (v0.4.0)

Any `BaseMessage` subclass can be used as a field type. Its fields are packed **inline** into the parent bitstream — no length prefix, no ID overhead.

```python
class GPSPosition(BaseMessage):
    lat: float = BoundedFloat(min=-90.0, max=90.0,  precision=6)  # 28 bits
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)  # 29 bits

class VehicleStatus(BaseMessage):
    vehicle_id: int = BoundedInt(ge=0, le=255)  # 8 bits
    position: GPSPosition                        # 57 bits inline (28 + 29)
    depth_cm: int = BoundedInt(ge=0, le=50000)  # 16 bits
    battery: int = BoundedInt(ge=0, le=100)      # 7 bits
    # Total: 8 + 57 + 16 + 7 = 88 bits = 11 bytes
```

```python
from uwacomm import encode, decode, encoded_bits

msg = VehicleStatus(
    vehicle_id=7,
    position=GPSPosition(lat=44.648766, lon=-63.575237),
    depth_cm=1250,
    battery=83,
)
data = encode(msg)        # 11 bytes, no overhead vs a flat message
decoded = decode(VehicleStatus, data)
print(decoded.position.lat)  # 44.648766
```

Two-level nesting is supported:

```python
class InnerSensor(BaseMessage):
    temp_raw: int = BoundedInt(ge=0, le=1023)     # 10 bits
    pressure_raw: int = BoundedInt(ge=0, le=4095) # 12 bits

class SensorBundle(BaseMessage):
    sensor_a: InnerSensor   # 22 bits inline
    sensor_b: InnerSensor   # 22 bits inline
    valid: bool             # 1 bit
    # Total: 45 bits = 6 bytes
```

`field_sizes()` reports the total nested bit count as a single entry:

```python
from uwacomm import field_sizes
print(field_sizes(VehicleStatus))
# {'vehicle_id': 8, 'position': 57, 'depth_cm': 16, 'battery': 7}
```

---

## ClassVar Metadata

These class-level annotations are **never encoded** but control encoding behaviour:

| Attribute | Type | Purpose |
|-----------|------|---------|
| `uwacomm_id` | `ClassVar[int \| None]` | Message ID for Mode 2 / Mode 3 encoding |
| `uwacomm_max_bytes` | `ClassVar[int \| None]` | Maximum encoded size; `EncodeError` if exceeded |

```python
class Command(BaseMessage):
    cmd: int = BoundedInt(ge=0, le=255)

    uwacomm_id: ClassVar[int | None] = 5
    uwacomm_max_bytes: ClassVar[int | None] = 32  # hard limit: 32 bytes
```

---

## Size Analysis

```python
from uwacomm import encoded_bits, encoded_size, field_sizes

print(encoded_bits(VehicleStatus))   # 88
print(encoded_size(VehicleStatus))   # 11  (bytes)
print(field_sizes(VehicleStatus))    # per-field bit breakdown
```

For variable-length fields, `encoded_bits()` / `encoded_size()` returns the **maximum** possible size (prefix + max payload).

---

## Related pages

- [Encoding and Decoding](encoding.md) — `encode()` / `decode()` / `encode_with_routing()`
- [Float Encoding](float_encoding.md) — `BoundedFloat` in depth
- [Multi-Mode Encoding](multi_mode_encoding.md) — choosing Mode 1 / 2 / 3
