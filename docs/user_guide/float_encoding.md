# Float Encoding

uwacomm supports bandwidth-efficient float encoding using DCCL-style bounded floats with precision control.

## Overview

Traditional IEEE 754 floats and doubles use fixed-size representations:
- **IEEE 754 float**: 32 bits
- **IEEE 754 double**: 64 bits

For bandwidth-constrained underwater communications, this is wasteful. Most sensor values don't need the full range or precision of IEEE 754.

uwacomm's **bounded floats** scale values to integers based on their expected range and precision, dramatically reducing bandwidth.

---

## How It Works

### DCCL-Style Encoding Algorithm

```
1. Scale to integer:
   scaled_value = round((value - min) × 10^precision)

2. Calculate bits needed:
   max_scaled = round((max - min) × 10^precision)
   bits = ceil(log2(max_scaled + 1))

3. Encode as bounded integer:
   encode_uint(scaled_value, bits)
```

### Decoding Algorithm

```
1. Decode scaled integer:
   scaled_value = decode_uint(bits)

2. Descale to float:
   value = min + (scaled_value / 10^precision)
```

---

## Bandwidth Savings

### Example: Depth Sensor

```python
from uwacomm import BaseMessage, BoundedFloat

class DepthReading(BaseMessage):
    # Depth: -5.00 to 100.00 meters (centimeter precision)
    depth_m: float = BoundedFloat(min=-5.0, max=100.0, precision=2)
```

**Bandwidth comparison:**
- **IEEE 754 double**: 64 bits
- **IEEE 754 float**: 32 bits
- **BoundedFloat**: 14 bits
- **Savings**: 78% vs double, 56% vs float

**Calculation:**
```
Range: -5.00 to 100.00 = 105.00 meters
Precision: 2 decimal places = 0.01 resolution
Distinct values: 105.00 / 0.01 = 10,500 values
Bits needed: ceil(log2(10500)) = 14 bits
```

### Example: GPS Coordinates

```python
class Position(BaseMessage):
    # Latitude: -90.000000° to 90.000000° (microdegree precision)
    latitude: float = BoundedFloat(min=-90.0, max=90.0, precision=6)

    # Longitude: -180.000000° to 180.000000°
    longitude: float = BoundedFloat(min=-180.0, max=180.0, precision=6)
```

**Latitude bandwidth:**
- Range: 180.0° × 10^6 = 180,000,000 distinct values
- Bits: ceil(log2(180000000)) = 28 bits vs 64 bits for double
- **Savings: 56%**

**Longitude bandwidth:**
- Range: 360.0° × 10^6 = 360,000,000 distinct values
- Bits: ceil(log2(360000000)) = 29 bits
- **Savings: 55%**

---

## Precision Levels

The `precision` parameter determines the number of decimal places:

| Precision | Resolution | Use Case | Example |
|-----------|------------|----------|---------|
| 0 | 1.0 | Integer-like values | Battery % (87.0) |
| 1 | 0.1 | Temperature | 18.3°C |
| 2 | 0.01 | Depth, altitude | 25.75 m |
| 3 | 0.001 | Precise depth | 25.753 m |
| 4 | 0.0001 | High-precision sensors | 25.7531 m |
| 5 | 0.00001 | Very high precision | 25.75312 m |
| 6 | 0.000001 | GPS coordinates | 42.358894° |

**Note:** Higher precision requires more bits. Choose the minimum precision needed for your application.

---

## Usage Examples

### Basic Float Encoding

```python
from uwacomm import BaseMessage, BoundedFloat, encode, decode

class Telemetry(BaseMessage):
    depth: float = BoundedFloat(min=-5.0, max=100.0, precision=2)
    temperature: float = BoundedFloat(min=-20.0, max=40.0, precision=1)
    battery: float = BoundedFloat(min=0.0, max=100.0, precision=1)

msg = Telemetry(
    depth=25.75,      # Encoded as 3075 (scaled integer)
    temperature=18.3,  # Encoded as 383
    battery=87.5       # Encoded as 875
)

encoded = encode(msg)  # ~4 bytes vs 24 bytes for IEEE 754 doubles
decoded = decode(Telemetry, encoded)

assert abs(decoded.depth - 25.75) < 0.01
assert abs(decoded.temperature - 18.3) < 0.1
assert abs(decoded.battery - 87.5) < 0.1
```

### Underwater Vehicle Position

```python
class VehiclePosition(BaseMessage):
    # GPS coordinates (6 decimal places = ~11cm accuracy)
    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)

    # Depth (centimeter precision)
    depth: float = BoundedFloat(min=0.0, max=6000.0, precision=2)

    # Altitude above seafloor (centimeter precision)
    altitude: float = BoundedFloat(min=0.0, max=100.0, precision=2)

position = VehiclePosition(
    lat=42.358894,   # Halifax, NS
    lon=-71.063611,  # Boston, MA (for illustration)
    depth=2575.50,   # 2575.50 meters
    altitude=3.25    # 3.25 meters
)

encoded = encode(position)  # ~15 bytes vs 32 bytes for doubles
```

### Sensor Readings

```python
class SensorData(BaseMessage):
    # Temperature (0.1°C precision)
    water_temp: float = BoundedFloat(min=-2.0, max=35.0, precision=1)

    # Pressure (0.01 bar precision)
    pressure: float = BoundedFloat(min=0.0, max=600.0, precision=2)

    # Salinity (0.01 PSU precision)
    salinity: float = BoundedFloat(min=0.0, max=40.0, precision=2)

    # pH (0.01 precision)
    ph: float = BoundedFloat(min=0.0, max=14.0, precision=2)

sensors = SensorData(
    water_temp=12.3,
    pressure=258.75,
    salinity=35.12,
    ph=8.14
)

encoded = encode(sensors)  # ~6 bytes vs 32 bytes for doubles
# Bandwidth savings: 81%!
```

---

## Precision vs Bandwidth Trade-off

### Depth Example with Different Precisions

```python
# Precision 0: Meter resolution
depth_m: float = BoundedFloat(min=0.0, max=6000.0, precision=0)
# Distinct values: 6,000 → 13 bits

# Precision 1: Decimeter resolution
depth_dm: float = BoundedFloat(min=0.0, max=6000.0, precision=1)
# Distinct values: 60,000 → 16 bits

# Precision 2: Centimeter resolution
depth_cm: float = BoundedFloat(min=0.0, max=6000.0, precision=2)
# Distinct values: 600,000 → 20 bits

# Precision 3: Millimeter resolution
depth_mm: float = BoundedFloat(min=0.0, max=6000.0, precision=3)
# Distinct values: 6,000,000 → 23 bits
```

**Recommendation:** Use the minimum precision needed for your application. Going from precision=2 to precision=3 adds 3 bits for questionable value in most underwater applications.

---

## Boundary Handling

### Automatic Validation

Pydantic validates bounds at construction time:

```python
class Depth(BaseMessage):
    depth: float = BoundedFloat(min=-5.0, max=100.0, precision=2)

# Valid
msg = Depth(depth=50.0)  # ✓

# Out of bounds - raises ValidationError
msg = Depth(depth=150.0)  # ✗ pydantic_core.ValidationError
```

### Rounding Behavior

Values are rounded to the specified precision:

```python
class Temp(BaseMessage):
    temperature: float = BoundedFloat(min=-20.0, max=40.0, precision=1)

msg = Temp(temperature=18.34)  # Stored as 18.3 (rounded to 0.1)
msg = Temp(temperature=18.37)  # Stored as 18.4 (rounded to 0.1)
```

---

## Real-World Bandwidth Analysis

### Acoustic Modem @ 80 bps

**Traditional (IEEE 754 doubles):**
```
Position message: 4 floats × 64 bits = 256 bits = 32 bytes
Transmission time: 32 bytes × 8 / 80 bps = 3.2 seconds
```

**BoundedFloat:**
```
Position message: lat(28) + lon(29) + depth(20) + alt(14) = 91 bits ≈ 12 bytes
Transmission time: 12 bytes × 8 / 80 bps = 1.2 seconds
```

**Savings:**
- **62.5% smaller** (12 bytes vs 32 bytes)
- **2.7x faster** transmission (1.2 sec vs 3.2 sec)
- **Can send 2.7x more messages** in the same time window

---

## Zero-Precision Floats

Precision=0 encodes whole numbers, similar to integers:

```python
class BatteryLevel(BaseMessage):
    # Battery percentage: 0.0 to 100.0 (whole numbers only)
    level: float = BoundedFloat(min=0.0, max=100.0, precision=0)

msg = BatteryLevel(level=87.3)  # Rounded to 87.0
msg = BatteryLevel(level=87.8)  # Rounded to 88.0
```

**Use case:** When you want float semantics but only need integer precision.

---

## Common Patterns

### Underwater Vehicle Telemetry

```python
class UUVTelemetry(BaseMessage):
    # Position (GPS when surfaced)
    lat: float = BoundedFloat(min=-90.0, max=90.0, precision=6)
    lon: float = BoundedFloat(min=-180.0, max=180.0, precision=6)

    # Depth (centimeter precision, max 6km)
    depth: float = BoundedFloat(min=0.0, max=6000.0, precision=2)

    # Heading (0.1° precision)
    heading: float = BoundedFloat(min=0.0, max=360.0, precision=1)

    # Speed (0.1 m/s precision)
    speed: float = BoundedFloat(min=0.0, max=5.0, precision=1)

    # Battery (0.1% precision)
    battery: float = BoundedFloat(min=0.0, max=100.0, precision=1)

# Bandwidth: ~15 bytes vs 48 bytes for doubles
# Savings: 68.75%
```

### Environmental Sensors

```python
class WaterQuality(BaseMessage):
    temperature: float = BoundedFloat(min=-2.0, max=35.0, precision=1)   # °C
    salinity: float = BoundedFloat(min=0.0, max=40.0, precision=2)       # PSU
    pressure: float = BoundedFloat(min=0.0, max=600.0, precision=2)      # bar
    dissolved_o2: float = BoundedFloat(min=0.0, max=15.0, precision=2)   # mg/L
    ph: float = BoundedFloat(min=0.0, max=14.0, precision=2)             # pH
    turbidity: float = BoundedFloat(min=0.0, max=1000.0, precision=1)    # NTU

# Bandwidth: ~11 bytes vs 48 bytes for doubles
# Savings: 77%
```

---

## Best Practices

1. **Choose minimum precision needed** - Don't use precision=6 if precision=2 suffices
2. **Match sensor accuracy** - If sensor is ±0.1°C, use precision=1
3. **Consider physical limits** - Depth sensor max depth determines max value
4. **Test boundary cases** - Verify min/max values are sufficient
5. **Document units** - Comment the units and precision (e.g., "centimeters")
6. **Use type hints** - Help IDEs understand the types

---

## Migration from Scaled Integers

If you were previously using scaled integers (multiply by 100, encode as int), migration is straightforward:

**Before (manual scaling):**
```python
class OldMessage(BaseMessage):
    depth_cm: int = BoundedInt(ge=0, le=1000000)  # Depth in centimeters

msg = OldMessage(depth_cm=int(25.75 * 100))  # Manual scaling
```

**After (BoundedFloat):**
```python
class NewMessage(BaseMessage):
    depth: float = BoundedFloat(min=0.0, max=10000.0, precision=2)

msg = NewMessage(depth=25.75)  # Automatic scaling
```

**Benefits:**
- Cleaner API (no manual scaling)
- Self-documenting (precision in field definition)
- Type-safe (IDE knows it's a float)

---

## Performance

Float encoding performance is comparable to integer encoding:

- **Encoding:** Scale to int (1 multiplication, 1 addition, 1 round) + encode as int
- **Decoding:** Decode as int + descale to float (1 addition, 1 division)

The performance overhead is negligible compared to acoustic modem transmission time.

---

## Examples

See complete examples:
- [Underwater Telemetry](../examples/underwater_comms.md)
- [Sensor Data Logging](../examples/sensor_logging.md)
- [Multi-Vehicle Positioning](../examples/multi_vehicle_swarm.md)
