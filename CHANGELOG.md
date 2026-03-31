# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-03-31

### Added

#### Phase 3: Performance Benchmarking
- `pytest-benchmark` infrastructure in `tests/benchmarks/`
- **Codec benchmarks** (`test_bench_codec.py`): encode, decode, roundtrip for small/medium/large messages
- **Float benchmarks** (`test_bench_float.py`): `BoundedFloat` encoding at low (precision=2), medium (precision=4), and high (precision=6) levels
- **Routing benchmarks** (`test_bench_routing.py`): `encode_with_routing`, `decode_with_routing`, `decode_by_id` dispatch path
- **Fragmentation benchmarks**: fragment, reassemble, and full roundtrip throughput
- `[tool.pytest-benchmark]` config in `pyproject.toml` (min_rounds=100, warmup, sort by mean)
- Benchmarks excluded from default `pytest` run via `norecursedirs`; run explicitly with `pytest tests/benchmarks/ --benchmark-only`

#### Phase 2: Message Fragmentation
- `fragment_message()` — splits encoded payloads into acoustic-modem-sized chunks with 4-byte headers
- `reassemble_fragments()` — reconstructs original payload; handles out-of-order, duplicates, missing fragments
- `iter_fragments()` — memory-efficient generator for streaming large messages
- 4-byte fragment header: Fragment ID (16-bit), Sequence (8-bit), Total (8-bit)
- Max 255 fragments per message (~15 KB at 64-byte frame size)
- `FragmentationError` for all failure modes
- 29 tests, 95% coverage (`tests/unit/test_fragmentation.py`)
- `examples/fragmentation_demo.py`

#### Phase 1: Hardware-in-the-Loop (HITL) Modem Simulation
- `MockModemDriver` — loopback acoustic channel simulator with configurable parameters
- `MockModemConfig` — dataclass for channel configuration (delay, packet loss, BER, frame size, data rate)
- `ModemDriver` — abstract base class for vendor-agnostic modem interface
- Queue-based producer-consumer architecture with background RX thread
- Probabilistic packet loss and bit error injection
- Multiple RX callback support
- 18 tests, ~99% modem module coverage (`tests/unit/test_modem_mock.py`)
- `examples/hitl_simulation.py`

### Changed
- Bumped version `0.1.1` → `0.3.0`
- `pyproject.toml`: added `pytest-benchmark>=4.0.0` to dev dependencies, registered `benchmark` marker, added `norecursedirs` to exclude benchmarks from default runs
- Fixed pre-existing `ruff` lint issues (`I001`, `UP035`) and `black` formatting in `src/uwacomm/fragmentation.py`, `modem/mock.py`, `modem/driver.py`, `__init__.py`

### CI/CD
- Added dual-platform CI (GitHub + Gitea) with platform detection
- PyPI publishing restricted to GitHub only (security best practice)
- Codecov integration for coverage upload

## [0.1.0] - 2026-02-10

### Added
- Initial release of **uwacomm** (Underwater Communications Codec)
- Pydantic-based message modeling with `BaseMessage`
- Compact binary encoding/decoding with bounded field optimization
- Support for: booleans, bounded integers, enums, fixed-length bytes/strings, fixed-size arrays
- Deterministic big-endian encoding
- CRC-16 and CRC-32 implementations
- Basic framing utilities (length prefix, CRC wrapping)
- Protobuf schema generation from Pydantic models
- Size calculation utilities
- **CLI tool** with `uwacomm --analyze` command for message schema analysis (inspired by DCCL)
- Comprehensive test suite with property-based tests (92 tests, 72% coverage)
- Full type hints and mypy strict mode compliance
- Documentation with mkdocs-material
- GitHub Actions CI/CD pipeline
- Proper attribution to DCCL (Dynamic Compact Control Language) from GobySoft

### Design Principles
- Schema-first approach inspired by DCCL (Dynamic Compact Control Language)
- Pydantic v2 as the primary message definition interface
- Explicit bounds enable compact encoding (fewer bits for constrained ranges)
- Deterministic, platform-independent serialization
- Security-conscious parsing with bounds checking

### Known Limitations (v0.1.0)
- Floating-point encoding not yet implemented (deferred to v0.2.0)
- Nested messages not supported in v0.1.0
- Variable-length arrays/strings use fixed-size encoding
- No zigzag or varint encoding yet
- Little-endian encoding not supported (big-endian only)

[Unreleased]: https://github.com/patel999jay/uwacomm/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/patel999jay/uwacomm/releases/tag/v0.1.0
