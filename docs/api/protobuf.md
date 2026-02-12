# Protobuf Interoperability

Generate Protocol Buffer (.proto) schemas from uwacomm messages.

## Schema Generation

### to_proto_schema

::: uwacomm.to_proto_schema
    options:
      show_root_heading: true
      show_source: true

### proto_conversion_notes

::: uwacomm.proto_conversion_notes
    options:
      show_root_heading: true
      show_source: true

## Example Usage

```python
from uwacomm import BaseMessage, BoundedInt, BoundedFloat
from uwacomm import to_proto_schema

class VehicleStatus(BaseMessage):
    depth_m: float = BoundedFloat(min=0.0, max=100.0, precision=2)
    battery_pct: int = BoundedInt(ge=0, le=100)
    uwacomm_id: int = 10

# Generate .proto file
proto_schema = to_proto_schema(VehicleStatus)
print(proto_schema)

# Save to file
with open("vehicle_status.proto", "w") as f:
    f.write(proto_schema)
```

This generates a DCCL-compatible Protocol Buffer schema that can be used with the official DCCL library.
