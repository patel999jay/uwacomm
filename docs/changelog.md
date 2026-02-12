# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Multi-Mode Encoding**: Three encoding modes for different use cases
  - Mode 1: Point-to-Point (8.2% smaller than DCCL)
  - Mode 2: Self-Describing Messages (includes message ID)
  - Mode 3: Multi-Vehicle Routing (source/dest/priority/ack)
- **Float Support**: DCCL-style bounded floats with precision control
  - 50-85% bandwidth savings vs IEEE 754 doubles
  - Configurable precision (0-6 decimal places)
- **MESSAGE_REGISTRY**: Auto-decode messages by ID
- **RoutingHeader**: Multi-vehicle routing with priority and ACK support
- **Comprehensive Documentation**: Multi-mode and float encoding guides

### Changed
- Encoder/decoder now support `include_id` and `routing` parameters
- BoundedFloat field helper for efficient float encoding

---

## [0.1.1] - Previous Release

### Added
- Initial DCCL-inspired encoding implementation
- Support for bounded integers, enums, fixed strings, fixed bytes
- Pydantic v2 integration
- Basic framing support

---

_Full changelog will be updated upon release._
