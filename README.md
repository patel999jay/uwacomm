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
- **🔒 Type-safe**: Full type hints and mypy strict mode compliance
- **✅ Deterministic**: Platform-independent, reproducible encodings
- **🛡️ Error detection**: Built-in CRC-16/CRC-32 and framing utilities
- **🔄 Protobuf interop**: Generate `.proto` schemas from Pydantic models
- **📊 Size analysis**: Calculate encoded sizes before transmission
- **🧪 Well-tested**: Comprehensive unit, integration, and property-based tests

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
from pydantic import Field
from uwacomm import BaseMessage

class StatusReport(BaseMessage):
    """Underwater vehicle status report."""

    vehicle_id: int = Field(ge=0, le=255)        # 8 bits
    depth_cm: int = Field(ge=0, le=10000)        # 14 bits
    battery_pct: int = Field(ge=0, le=100)       # 7 bits
    active: bool                                  # 1 bit

    # Optional: specify max bytes and message ID
    uwacomm_max_bytes: ClassVar[Optional[int]] = 16
    uwacomm_id: ClassVar[Optional[int]] = 10
```

### 2. Encode and Decode

```python
from uwacomm import encode, decode

# Create a message
msg = StatusReport(
    vehicle_id=42,
    depth_cm=2500,
    battery_pct=87,
    active=True
)

# Encode to compact binary
data = encode(msg)  # 4 bytes (30 bits rounded up)

# Decode back
decoded = decode(StatusReport, data)
assert decoded == msg
```

### 3. Add Framing for Transmission

```python
from uwacomm import frame_with_id, unframe_with_id

# Frame with message ID and CRC-32
framed = frame_with_id(data, message_id=10, crc="crc32")

# Transmit over acoustic modem...

# Receive and unframe
msg_id, payload = unframe_with_id(framed, crc="crc32")
decoded = decode(StatusReport, payload)
```

### 4. Analyze Message Size

```python
from uwacomm import encoded_size, field_sizes

# Get total encoded size
size = encoded_size(StatusReport)  # 4 bytes

# Get per-field bit usage
sizes = field_sizes(StatusReport)
# {'vehicle_id': 8, 'depth_cm': 14, 'battery_pct': 7, 'active': 1}
```

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

| Encoding | Message Size | Transmission Time (80 bps) |
|----------|--------------|----------------------------|
| JSON | 95 bytes | **9.5 seconds** |
| Protobuf | 12 bytes | **1.2 seconds** |
| **uwacomm** | **4 bytes** | **0.4 seconds** |

With limited transmission windows and high per-byte costs, every bit counts.

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

- [`basic_usage.py`](examples/basic_usage.py) - Message definition, encoding, decoding
- [`framing_example.py`](examples/framing_example.py) - Message framing with CRC
- [`protobuf_schema.py`](examples/protobuf_schema.py) - Generate `.proto` schemas
- [`underwater_comms.py`](examples/underwater_comms.py) - Realistic UUV scenario

---

## Supported Features (v0.1.0)

### Field Types

- ✅ Booleans (1 bit)
- ✅ Bounded unsigned integers (minimal bits)
- ✅ Bounded signed integers (minimal bits)
- ✅ Enums (minimal bits for value count)
- ✅ Fixed-length bytes
- ✅ Fixed-length strings (UTF-8)
- ⏸️ Floats with precision (planned for v0.2.0)
- ⏸️ Nested messages (planned for v0.2.0)
- ⏸️ Variable-length arrays/strings (planned for v0.2.0)

### Utilities

- ✅ CRC-16 and CRC-32 checksums
- ✅ Length-prefixed framing
- ✅ Message ID multiplexing
- ✅ Encoded size calculation
- ✅ Protobuf schema generation
- ⏸️ Fragmentation/reassembly (planned for v0.2.0)

---

## Design Principles

1. **Explicit over implicit**: All constraints must be declared
2. **Deterministic**: Same message → same bytes, always
3. **Security-minded**: Bounds checking, no unbounded recursion
4. **Fail-fast**: Clear exceptions, not silent corruption

---

## Comparison to Alternatives

| Feature | uwacomm | Protobuf | JSON | MessagePack |
|---------|--------|----------|------|-------------|
| Schema-based | ✅ | ✅ | ❌ | ❌ |
| Bounded optimization | ✅ | ❌ | ❌ | ❌ |
| Python-native | ✅ | ❌ | ✅ | ✅ |
| Size (status msg) | 4 bytes | 12 bytes | 95 bytes | 30 bytes |
| Type safety | ✅ | ✅ | ❌ | ❌ |

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
