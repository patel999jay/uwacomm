"""Bit-level packing and unpacking utilities.

This module provides low-level bit manipulation for compact binary encoding.
All operations are deterministic and big-endian by default.
"""

from __future__ import annotations


class BitPacker:
    """Packs values bit-by-bit into a byte buffer.

    This class maintains an internal bit buffer and provides methods to write
    individual bits, integers of arbitrary bit width, and other primitives.

    Example:
        >>> packer = BitPacker()
        >>> packer.write_bool(True)
        >>> packer.write_uint(42, num_bits=7)
        >>> packer.write_bool(False)
        >>> data = packer.to_bytes()
    """

    def __init__(self) -> None:
        """Initialize an empty bit packer."""
        self._bits: list[int] = []  # List of 0s and 1s

    def write_bool(self, value: bool) -> None:
        """Write a boolean as a single bit.

        Args:
            value: Boolean value to write (True=1, False=0)
        """
        self._bits.append(1 if value else 0)

    def write_uint(self, value: int, num_bits: int) -> None:
        """Write an unsigned integer using the specified number of bits.

        Args:
            value: Unsigned integer value to write (must be >= 0)
            num_bits: Number of bits to use for encoding (1-64)

        Raises:
            ValueError: If value is negative or doesn't fit in num_bits
        """
        if value < 0:
            raise ValueError(f"write_uint requires non-negative value, got {value}")
        if num_bits < 1 or num_bits > 64:
            raise ValueError(f"num_bits must be 1-64, got {num_bits}")

        max_value = (1 << num_bits) - 1
        if value > max_value:
            raise ValueError(f"Value {value} requires more than {num_bits} bits (max: {max_value})")

        # Write bits from most significant to least significant (big-endian)
        for i in range(num_bits - 1, -1, -1):
            bit = (value >> i) & 1
            self._bits.append(bit)

    def write_int(self, value: int, num_bits: int) -> None:
        """Write a signed integer using two's complement encoding.

        Args:
            value: Signed integer value to write
            num_bits: Number of bits to use for encoding (2-64)

        Raises:
            ValueError: If value doesn't fit in num_bits using two's complement
        """
        if num_bits < 2 or num_bits > 64:
            raise ValueError(f"num_bits must be 2-64 for signed integers, got {num_bits}")

        min_value = -(1 << (num_bits - 1))
        max_value = (1 << (num_bits - 1)) - 1

        if value < min_value or value > max_value:
            raise ValueError(
                f"Value {value} doesn't fit in {num_bits} bits (range: {min_value} to {max_value})"
            )

        # Convert to unsigned representation using two's complement
        if value < 0:
            unsigned_value = (1 << num_bits) + value
        else:
            unsigned_value = value

        self.write_uint(unsigned_value, num_bits)

    def write_bytes(self, data: bytes) -> None:
        """Write raw bytes (byte-aligned).

        Args:
            data: Bytes to write
        """
        for byte in data:
            self.write_uint(byte, 8)

    def bit_length(self) -> int:
        """Return the current number of bits written.

        Returns:
            Number of bits in the buffer
        """
        return len(self._bits)

    def to_bytes(self) -> bytes:
        """Convert the bit buffer to bytes.

        If the number of bits is not a multiple of 8, the last byte
        is padded with zeros on the right (LSB side).

        Returns:
            Packed bytes
        """
        if not self._bits:
            return b""

        # Pad to byte boundary with zeros
        padded_bits = self._bits + [0] * ((-len(self._bits)) % 8)

        # Convert to bytes
        result = bytearray()
        for i in range(0, len(padded_bits), 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | padded_bits[i + j]
            result.append(byte)

        return bytes(result)


class BitUnpacker:
    """Unpacks values bit-by-bit from a byte buffer.

    This class reads from a byte buffer and provides methods to extract
    individual bits, integers of arbitrary bit width, and other primitives.

    Example:
        >>> unpacker = BitUnpacker(data)
        >>> flag = unpacker.read_bool()
        >>> value = unpacker.read_uint(7)
        >>> another_flag = unpacker.read_bool()
    """

    def __init__(self, data: bytes) -> None:
        """Initialize a bit unpacker with the given data.

        Args:
            data: Byte buffer to unpack
        """
        self._bits: list[int] = []
        for byte in data:
            for i in range(7, -1, -1):
                self._bits.append((byte >> i) & 1)
        self._position = 0

    def read_bool(self) -> bool:
        """Read a single bit as a boolean.

        Returns:
            Boolean value (1=True, 0=False)

        Raises:
            IndexError: If no more bits are available
        """
        if self._position >= len(self._bits):
            raise IndexError("Attempted to read past end of bit buffer")

        value = self._bits[self._position] == 1
        self._position += 1
        return value

    def read_uint(self, num_bits: int) -> int:
        """Read an unsigned integer of the specified bit width.

        Args:
            num_bits: Number of bits to read (1-64)

        Returns:
            Unsigned integer value

        Raises:
            ValueError: If num_bits is out of range
            IndexError: If not enough bits are available
        """
        if num_bits < 1 or num_bits > 64:
            raise ValueError(f"num_bits must be 1-64, got {num_bits}")

        if self._position + num_bits > len(self._bits):
            raise IndexError(
                f"Not enough bits: need {num_bits}, have {len(self._bits) - self._position}"
            )

        value = 0
        for _ in range(num_bits):
            value = (value << 1) | self._bits[self._position]
            self._position += 1

        return value

    def read_int(self, num_bits: int) -> int:
        """Read a signed integer using two's complement encoding.

        Args:
            num_bits: Number of bits to read (2-64)

        Returns:
            Signed integer value

        Raises:
            ValueError: If num_bits is out of range
            IndexError: If not enough bits are available
        """
        if num_bits < 2 or num_bits > 64:
            raise ValueError(f"num_bits must be 2-64 for signed integers, got {num_bits}")

        unsigned_value = self.read_uint(num_bits)

        # Check sign bit (MSB)
        sign_bit = 1 << (num_bits - 1)
        if unsigned_value & sign_bit:
            # Negative number: convert from two's complement
            return unsigned_value - (1 << num_bits)
        else:
            return unsigned_value

    def read_bytes(self, num_bytes: int) -> bytes:
        """Read raw bytes (byte-aligned).

        Args:
            num_bytes: Number of bytes to read

        Returns:
            Bytes read from buffer

        Raises:
            IndexError: If not enough bytes are available
        """
        result = bytearray()
        for _ in range(num_bytes):
            result.append(self.read_uint(8))
        return bytes(result)

    def bits_remaining(self) -> int:
        """Return the number of bits remaining in the buffer.

        Returns:
            Number of unread bits
        """
        return len(self._bits) - self._position

    def position(self) -> int:
        """Return the current bit position.

        Returns:
            Current read position in bits
        """
        return self._position
