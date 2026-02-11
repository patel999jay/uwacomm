"""CRC (Cyclic Redundancy Check) implementations.

This module provides CRC-16 and CRC-32 checksums commonly used for
error detection in underwater communications.
"""

from __future__ import annotations

import struct


def crc16(data: bytes, poly: int = 0x1021, init: int = 0xFFFF) -> int:
    """Calculate CRC-16 checksum.

    Uses CRC-16-CCITT polynomial by default, which is common in telecommunications
    and underwater acoustic modems.

    Args:
        data: Data to checksum
        poly: CRC polynomial (default: 0x1021 for CRC-16-CCITT)
        init: Initial CRC value (default: 0xFFFF)

    Returns:
        16-bit CRC value

    Example:
        >>> data = b"Hello, World!"
        >>> checksum = crc16(data)
        >>> hex(checksum)
        '0x...'
    """
    crc = init

    for byte in data:
        crc ^= byte << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1

        crc &= 0xFFFF  # Keep only 16 bits

    return crc


def crc16_bytes(data: bytes, poly: int = 0x1021, init: int = 0xFFFF) -> bytes:
    """Calculate CRC-16 checksum and return as 2 bytes (big-endian).

    Args:
        data: Data to checksum
        poly: CRC polynomial
        init: Initial CRC value

    Returns:
        2 bytes representing the CRC value

    Example:
        >>> data = b"Hello, World!"
        >>> crc_bytes = crc16_bytes(data)
        >>> len(crc_bytes)
        2
    """
    crc = crc16(data, poly, init)
    return struct.pack(">H", crc)  # Big-endian unsigned short


def crc32(data: bytes) -> int:
    """Calculate CRC-32 checksum.

    Uses the standard CRC-32 polynomial (IEEE 802.3) compatible with
    zlib.crc32() and binascii.crc32().

    Args:
        data: Data to checksum

    Returns:
        32-bit CRC value

    Example:
        >>> data = b"Hello, World!"
        >>> checksum = crc32(data)
        >>> hex(checksum)
        '0x...'
    """
    import zlib

    # zlib.crc32 returns a signed int in Python 2, unsigned in Python 3
    # Ensure it's unsigned
    return zlib.crc32(data) & 0xFFFFFFFF


def crc32_bytes(data: bytes) -> bytes:
    """Calculate CRC-32 checksum and return as 4 bytes (big-endian).

    Args:
        data: Data to checksum

    Returns:
        4 bytes representing the CRC value

    Example:
        >>> data = b"Hello, World!"
        >>> crc_bytes = crc32_bytes(data)
        >>> len(crc_bytes)
        4
    """
    crc = crc32(data)
    return struct.pack(">I", crc)  # Big-endian unsigned int


def verify_crc16(
    data: bytes, expected_crc: int | bytes, poly: int = 0x1021, init: int = 0xFFFF
) -> bool:
    """Verify CRC-16 checksum.

    Args:
        data: Data to verify
        expected_crc: Expected CRC value (int or 2 bytes)
        poly: CRC polynomial
        init: Initial CRC value

    Returns:
        True if CRC matches, False otherwise

    Example:
        >>> data = b"Hello, World!"
        >>> checksum = crc16(data)
        >>> verify_crc16(data, checksum)
        True
    """
    if isinstance(expected_crc, bytes):
        if len(expected_crc) != 2:
            raise ValueError(f"CRC-16 must be 2 bytes, got {len(expected_crc)}")
        expected_crc = struct.unpack(">H", expected_crc)[0]

    actual_crc = crc16(data, poly, init)
    return actual_crc == expected_crc


def verify_crc32(data: bytes, expected_crc: int | bytes) -> bool:
    """Verify CRC-32 checksum.

    Args:
        data: Data to verify
        expected_crc: Expected CRC value (int or 4 bytes)

    Returns:
        True if CRC matches, False otherwise

    Example:
        >>> data = b"Hello, World!"
        >>> checksum = crc32(data)
        >>> verify_crc32(data, checksum)
        True
    """
    if isinstance(expected_crc, bytes):
        if len(expected_crc) != 4:
            raise ValueError(f"CRC-32 must be 4 bytes, got {len(expected_crc)}")
        expected_crc = struct.unpack(">I", expected_crc)[0]

    actual_crc = crc32(data)
    return actual_crc == expected_crc
