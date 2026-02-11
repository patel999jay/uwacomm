# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
