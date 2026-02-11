"""Unit tests for CRC utilities."""

from __future__ import annotations

from uwacomm.utils.crc import (
    crc16,
    crc16_bytes,
    crc32,
    crc32_bytes,
    verify_crc16,
    verify_crc32,
)


class TestCRC16:
    """Test CRC-16 functionality."""

    def test_crc16_basic(self) -> None:
        """Test basic CRC-16 calculation."""
        data = b"Hello, World!"
        checksum = crc16(data)

        assert isinstance(checksum, int)
        assert 0 <= checksum <= 0xFFFF

    def test_crc16_deterministic(self) -> None:
        """Test CRC-16 is deterministic."""
        data = b"Test data"
        crc1 = crc16(data)
        crc2 = crc16(data)

        assert crc1 == crc2

    def test_crc16_different_data(self) -> None:
        """Test different data produces different CRC."""
        crc1 = crc16(b"Hello")
        crc2 = crc16(b"World")

        assert crc1 != crc2

    def test_crc16_bytes(self) -> None:
        """Test CRC-16 as bytes."""
        data = b"Test"
        crc_bytes = crc16_bytes(data)

        assert isinstance(crc_bytes, bytes)
        assert len(crc_bytes) == 2

    def test_verify_crc16_success(self) -> None:
        """Test successful CRC-16 verification."""
        data = b"Test data"
        checksum = crc16(data)

        assert verify_crc16(data, checksum) is True

    def test_verify_crc16_failure(self) -> None:
        """Test failed CRC-16 verification."""
        data = b"Test data"
        wrong_checksum = 0x1234

        assert verify_crc16(data, wrong_checksum) is False

    def test_verify_crc16_bytes(self) -> None:
        """Test CRC-16 verification with bytes."""
        data = b"Test data"
        checksum_bytes = crc16_bytes(data)

        assert verify_crc16(data, checksum_bytes) is True


class TestCRC32:
    """Test CRC-32 functionality."""

    def test_crc32_basic(self) -> None:
        """Test basic CRC-32 calculation."""
        data = b"Hello, World!"
        checksum = crc32(data)

        assert isinstance(checksum, int)
        assert 0 <= checksum <= 0xFFFFFFFF

    def test_crc32_deterministic(self) -> None:
        """Test CRC-32 is deterministic."""
        data = b"Test data"
        crc1 = crc32(data)
        crc2 = crc32(data)

        assert crc1 == crc2

    def test_crc32_different_data(self) -> None:
        """Test different data produces different CRC."""
        crc1 = crc32(b"Hello")
        crc2 = crc32(b"World")

        assert crc1 != crc2

    def test_crc32_bytes(self) -> None:
        """Test CRC-32 as bytes."""
        data = b"Test"
        crc_bytes = crc32_bytes(data)

        assert isinstance(crc_bytes, bytes)
        assert len(crc_bytes) == 4

    def test_verify_crc32_success(self) -> None:
        """Test successful CRC-32 verification."""
        data = b"Test data"
        checksum = crc32(data)

        assert verify_crc32(data, checksum) is True

    def test_verify_crc32_failure(self) -> None:
        """Test failed CRC-32 verification."""
        data = b"Test data"
        wrong_checksum = 0x12345678

        assert verify_crc32(data, wrong_checksum) is False

    def test_verify_crc32_bytes(self) -> None:
        """Test CRC-32 verification with bytes."""
        data = b"Test data"
        checksum_bytes = crc32_bytes(data)

        assert verify_crc32(data, checksum_bytes) is True


class TestCRCEdgeCases:
    """Test CRC edge cases."""

    def test_empty_data(self) -> None:
        """Test CRC of empty data."""
        crc16_val = crc16(b"")
        crc32_val = crc32(b"")

        assert isinstance(crc16_val, int)
        assert isinstance(crc32_val, int)

    def test_single_byte(self) -> None:
        """Test CRC of single byte."""
        data = b"\x42"

        crc16_val = crc16(data)
        crc32_val = crc32(data)

        assert 0 <= crc16_val <= 0xFFFF
        assert 0 <= crc32_val <= 0xFFFFFFFF

    def test_large_data(self) -> None:
        """Test CRC of large data."""
        data = b"\x00" * 10000

        crc16_val = crc16(data)
        crc32_val = crc32(data)

        assert verify_crc16(data, crc16_val)
        assert verify_crc32(data, crc32_val)
