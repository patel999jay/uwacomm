"""Unit tests for bitpacking utilities."""

from __future__ import annotations

import pytest

from uwacomm.codec.bitpack import BitPacker, BitUnpacker


class TestBitPacker:
    """Test BitPacker functionality."""

    def test_write_bool(self) -> None:
        """Test writing boolean values."""
        packer = BitPacker()
        packer.write_bool(True)
        packer.write_bool(False)
        packer.write_bool(True)

        assert packer.bit_length() == 3
        data = packer.to_bytes()
        assert data == b"\xa0"  # 101 00000

    def test_write_uint(self) -> None:
        """Test writing unsigned integers."""
        packer = BitPacker()
        packer.write_uint(15, 4)  # 1111
        packer.write_uint(3, 2)  # 11
        packer.write_uint(0, 2)  # 00

        assert packer.bit_length() == 8
        assert packer.to_bytes() == b"\xfc"  # 11111100

    def test_write_uint_bounds(self) -> None:
        """Test uint bounds checking."""
        packer = BitPacker()

        # Valid values
        packer.write_uint(0, 8)
        packer.write_uint(255, 8)

        # Out of bounds
        with pytest.raises(ValueError, match="negative"):
            packer.write_uint(-1, 8)

        with pytest.raises(ValueError, match="more than"):
            packer.write_uint(256, 8)

    def test_write_int(self) -> None:
        """Test writing signed integers."""
        packer = BitPacker()
        packer.write_int(-1, 4)  # 1111 (two's complement)
        packer.write_int(3, 4)  # 0011

        assert packer.bit_length() == 8
        assert packer.to_bytes() == b"\xf3"  # 11110011

    def test_write_int_bounds(self) -> None:
        """Test signed int bounds."""
        packer = BitPacker()

        # 4-bit signed: -8 to 7
        packer.write_int(-8, 4)
        packer.write_int(7, 4)

        with pytest.raises(ValueError, match="doesn't fit"):
            packer.write_int(-9, 4)

        with pytest.raises(ValueError, match="doesn't fit"):
            packer.write_int(8, 4)

    def test_write_bytes(self) -> None:
        """Test writing raw bytes."""
        packer = BitPacker()
        packer.write_bytes(b"\x12\x34")

        assert packer.bit_length() == 16
        assert packer.to_bytes() == b"\x12\x34"

    def test_to_bytes_padding(self) -> None:
        """Test padding to byte boundary."""
        packer = BitPacker()
        packer.write_bool(True)  # 1 bit

        data = packer.to_bytes()
        assert len(data) == 1
        assert data == b"\x80"  # 10000000

    def test_empty_packer(self) -> None:
        """Test empty bit packer."""
        packer = BitPacker()
        assert packer.bit_length() == 0
        assert packer.to_bytes() == b""


class TestBitUnpacker:
    """Test BitUnpacker functionality."""

    def test_read_bool(self) -> None:
        """Test reading boolean values."""
        data = b"\xa0"  # 10100000
        unpacker = BitUnpacker(data)

        assert unpacker.read_bool() is True
        assert unpacker.read_bool() is False
        assert unpacker.read_bool() is True

    def test_read_uint(self) -> None:
        """Test reading unsigned integers."""
        data = b"\xfc"  # 11111100
        unpacker = BitUnpacker(data)

        assert unpacker.read_uint(4) == 15  # 1111
        assert unpacker.read_uint(2) == 3  # 11
        assert unpacker.read_uint(2) == 0  # 00

    def test_read_int(self) -> None:
        """Test reading signed integers."""
        data = b"\xf3"  # 11110011
        unpacker = BitUnpacker(data)

        assert unpacker.read_int(4) == -1  # 1111
        assert unpacker.read_int(4) == 3  # 0011

    def test_read_bytes(self) -> None:
        """Test reading raw bytes."""
        data = b"\x12\x34"
        unpacker = BitUnpacker(data)

        assert unpacker.read_bytes(2) == b"\x12\x34"

    def test_bits_remaining(self) -> None:
        """Test tracking remaining bits."""
        data = b"\xff"
        unpacker = BitUnpacker(data)

        assert unpacker.bits_remaining() == 8
        unpacker.read_uint(3)
        assert unpacker.bits_remaining() == 5

    def test_truncation_error(self) -> None:
        """Test error on reading past end."""
        data = b"\xff"
        unpacker = BitUnpacker(data)

        unpacker.read_uint(8)

        with pytest.raises(IndexError, match="past end"):
            unpacker.read_bool()


class TestRoundTrip:
    """Test round-trip encoding/decoding."""

    def test_roundtrip_bool(self) -> None:
        """Test bool round-trip."""
        packer = BitPacker()
        packer.write_bool(True)
        packer.write_bool(False)
        packer.write_bool(True)

        unpacker = BitUnpacker(packer.to_bytes())
        assert unpacker.read_bool() is True
        assert unpacker.read_bool() is False
        assert unpacker.read_bool() is True

    def test_roundtrip_mixed(self) -> None:
        """Test mixed types round-trip."""
        packer = BitPacker()
        packer.write_uint(42, 8)
        packer.write_bool(True)
        packer.write_int(-5, 4)
        packer.write_bytes(b"\x99")

        unpacker = BitUnpacker(packer.to_bytes())
        assert unpacker.read_uint(8) == 42
        assert unpacker.read_bool() is True
        assert unpacker.read_int(4) == -5
        assert unpacker.read_bytes(1) == b"\x99"
