"""Message fragmentation and reassembly for acoustic modems.

This module provides fragmentation support for splitting large messages across
multiple acoustic modem frames. Acoustic modems typically have strict frame
size limits (32-64 bytes), requiring larger messages to be fragmented.

Fragment Header Format (4 bytes):
    ┌─────────────┬─────────┬─────────┬─────────────────┐
    │ Fragment ID │ Seq Num │  Total  │  Data Chunk     │
    │  16 bits    │  8 bits │ 8 bits  │  N bytes        │
    └─────────────┴─────────┴─────────┴─────────────────┘

    - Fragment ID (16 bits): Unique ID for this fragmented message (0-65535)
    - Sequence Num (8 bits): Fragment index (0-255)
    - Total (8 bits): Total number of fragments (1-255)
    - Data Chunk (N bytes): Actual payload data

Design:
    - Fragment ID allows multiple messages to be fragmented simultaneously
    - Sequence number enables out-of-order reassembly
    - Total fragments count enables missing fragment detection
    - Maximum 255 fragments per message (max message size ≈ 15 KB with 64 byte frames)
"""

from __future__ import annotations

import struct
from collections.abc import Iterator

from uwacomm.exceptions import FragmentationError

# Fragment header format: >HBB = big-endian unsigned short, byte, byte
_FRAGMENT_HEADER_FORMAT = ">HBB"
_FRAGMENT_HEADER_SIZE = struct.calcsize(_FRAGMENT_HEADER_FORMAT)  # 4 bytes

# Global fragment ID counter (simple approach for v0.3.0)
_fragment_id_counter = 0


def fragment_message(
    data: bytes, max_fragment_size: int = 64, fragment_id: int | None = None
) -> list[bytes]:
    """Split message into fragments with headers.

    Each fragment includes a 4-byte header with fragment ID, sequence number,
    and total fragment count. This enables reassembly even if fragments arrive
    out of order or if multiple messages are being fragmented simultaneously.

    Args:
        data: Message bytes to fragment (typically encoded uwacomm message)
        max_fragment_size: Maximum size of each fragment in bytes (default 64).
            This should match your acoustic modem's max frame size.
            Header (4 bytes) is included in this size.
        fragment_id: Optional fragment ID (0-65535). If None, auto-generates
            a unique ID. Use explicit ID when you need to match fragments
            across different fragmentation calls.

    Returns:
        List of fragment bytes, each with header + data chunk.
        Empty list if input data is empty.

    Raises:
        FragmentationError: If max_fragment_size is too small (< 5 bytes) or
            if message requires more than 255 fragments.

    Examples:
        ```python
        from uwacomm import encode, BaseMessage, BoundedInt
        from uwacomm.fragmentation import fragment_message

        class LargeMessage(BaseMessage):
            data: bytes = FixedBytes(length=200)

        # Encode message
        msg = LargeMessage(data=b'x' * 200)
        encoded = encode(msg)  # ~200 bytes

        # Fragment for 64-byte modem frames
        fragments = fragment_message(encoded, max_fragment_size=64)
        # Returns: 4 fragments (200 bytes / 60 bytes per fragment ≈ 3.3 → 4)

        print(f"Original: {len(encoded)} bytes")
        print(f"Fragments: {len(fragments)} pieces")
        for i, frag in enumerate(fragments):
            print(f"  Fragment {i}: {len(frag)} bytes")
        ```
    """
    # Validate inputs
    if max_fragment_size < _FRAGMENT_HEADER_SIZE + 1:
        raise FragmentationError(
            f"max_fragment_size must be at least {_FRAGMENT_HEADER_SIZE + 1} bytes "
            f"(4 byte header + 1 byte data), got {max_fragment_size}"
        )

    if not data:
        return []

    # Calculate chunk size (data per fragment after header)
    chunk_size = max_fragment_size - _FRAGMENT_HEADER_SIZE

    # Calculate number of fragments needed
    num_fragments = (len(data) + chunk_size - 1) // chunk_size  # Ceiling division

    if num_fragments > 255:
        raise FragmentationError(
            f"Message requires {num_fragments} fragments, but maximum is 255. "
            f"Message size: {len(data)} bytes, chunk size: {chunk_size} bytes. "
            f"Increase max_fragment_size or reduce message size."
        )

    # Generate or use provided fragment ID
    global _fragment_id_counter
    if fragment_id is None:
        frag_id = _fragment_id_counter
        _fragment_id_counter = (_fragment_id_counter + 1) % 65536  # Wrap at 16 bits
    else:
        if not 0 <= fragment_id <= 65535:
            raise FragmentationError(f"fragment_id must be 0-65535, got {fragment_id}")
        frag_id = fragment_id

    # Create fragments
    fragments: list[bytes] = []
    for seq_num in range(num_fragments):
        # Extract data chunk
        start = seq_num * chunk_size
        end = min(start + chunk_size, len(data))
        chunk = data[start:end]

        # Build header
        header = struct.pack(
            _FRAGMENT_HEADER_FORMAT,
            frag_id,  # Fragment ID (16 bits)
            seq_num,  # Sequence number (8 bits)
            num_fragments,  # Total fragments (8 bits)
        )

        # Combine header + chunk
        fragment = header + chunk
        fragments.append(fragment)

    return fragments


def reassemble_fragments(fragments: list[bytes]) -> bytes:
    """Reconstruct message from fragments.

    Validates fragment headers, checks for missing fragments, and reassembles
    data in correct order. Handles out-of-order fragments and detects errors.

    Args:
        fragments: List of fragment bytes (each with 4-byte header + data)

    Returns:
        Reassembled message bytes (original data before fragmentation)

    Raises:
        FragmentationError: If fragments are invalid, mismatched, or incomplete:
            - Empty fragment list
            - Fragment too short (< 4 bytes header)
            - Mismatched fragment IDs (fragments from different messages)
            - Missing fragments (gaps in sequence)
            - Duplicate fragments (same sequence number appears twice)
            - Total count mismatch

    Examples:
        ```python
        from uwacomm import encode, decode
        from uwacomm.fragmentation import fragment_message, reassemble_fragments

        # Original message
        original_data = b'x' * 200

        # Fragment
        fragments = fragment_message(original_data, max_fragment_size=64)

        # Simulate out-of-order delivery
        import random
        shuffled = fragments.copy()
        random.shuffle(shuffled)

        # Reassemble (handles out-of-order automatically)
        reassembled = reassemble_fragments(shuffled)

        assert reassembled == original_data  # Perfect reconstruction
        ```

        ```python
        # Detect missing fragment
        fragments = fragment_message(b'x' * 200, max_fragment_size=64)
        del fragments[1]  # Remove fragment 1

        try:
            reassemble_fragments(fragments)
        except FragmentationError as e:
            print(f"Missing fragment detected: {e}")
        ```
    """
    if not fragments:
        raise FragmentationError("Cannot reassemble empty fragment list")

    # Parse all fragment headers
    parsed_fragments: dict[int, tuple[int, int, bytes]] = {}  # seq_num -> (frag_id, total, data)

    first_frag_id: int | None = None
    first_total: int | None = None

    for i, fragment in enumerate(fragments):
        # Validate fragment size
        if len(fragment) < _FRAGMENT_HEADER_SIZE:
            raise FragmentationError(
                f"Fragment {i} too short: {len(fragment)} bytes "
                f"(minimum {_FRAGMENT_HEADER_SIZE} bytes for header)"
            )

        # Parse header
        header = fragment[:_FRAGMENT_HEADER_SIZE]
        data = fragment[_FRAGMENT_HEADER_SIZE:]

        frag_id, seq_num, total = struct.unpack(_FRAGMENT_HEADER_FORMAT, header)

        # First fragment sets expected fragment ID and total
        if first_frag_id is None:
            first_frag_id = frag_id
            first_total = total
        else:
            # Validate all fragments have same ID
            if frag_id != first_frag_id:
                raise FragmentationError(
                    f"Fragment ID mismatch: expected {first_frag_id}, got {frag_id} "
                    f"in fragment {i}. Fragments from different messages mixed?"
                )

            # Validate all fragments have same total
            if total != first_total:
                raise FragmentationError(
                    f"Total fragments mismatch: expected {first_total}, got {total} "
                    f"in fragment {i}"
                )

        # Check for duplicates
        if seq_num in parsed_fragments:
            raise FragmentationError(f"Duplicate fragment: sequence number {seq_num} appears twice")

        # Store fragment
        parsed_fragments[seq_num] = (frag_id, total, data)

    # Validate we have all fragments
    if first_total is None:
        raise FragmentationError("Internal error: first_total not set")

    expected_seq_nums = set(range(first_total))
    actual_seq_nums = set(parsed_fragments.keys())
    missing = expected_seq_nums - actual_seq_nums

    if missing:
        missing_sorted = sorted(missing)
        raise FragmentationError(
            f"Missing fragments: {missing_sorted}. "
            f"Expected {first_total} fragments, got {len(parsed_fragments)}"
        )

    # Reassemble in correct order
    reassembled_parts: list[bytes] = []
    for seq_num in range(first_total):
        _, _, data = parsed_fragments[seq_num]
        reassembled_parts.append(data)

    return b"".join(reassembled_parts)


def iter_fragments(
    data: bytes, max_fragment_size: int = 64, fragment_id: int | None = None
) -> Iterator[bytes]:
    """Iterate over fragments without storing all in memory.

    Memory-efficient alternative to fragment_message() for very large messages.
    Yields fragments one at a time instead of building a full list.

    Args:
        data: Message bytes to fragment
        max_fragment_size: Maximum fragment size in bytes (default 64)
        fragment_id: Optional fragment ID (0-65535)

    Yields:
        Fragment bytes (header + chunk) one at a time

    Raises:
        FragmentationError: Same as fragment_message()

    Examples:
        ```python
        from uwacomm.fragmentation import iter_fragments

        large_data = b'x' * 10000  # 10 KB message

        # Send fragments without storing all in memory
        for fragment in iter_fragments(large_data, max_fragment_size=64):
            modem.send_frame(fragment, dest_id=0)
            print(f"Sent fragment: {len(fragment)} bytes")
        ```
    """
    # Validate inputs (same as fragment_message)
    if max_fragment_size < _FRAGMENT_HEADER_SIZE + 1:
        raise FragmentationError(
            f"max_fragment_size must be at least {_FRAGMENT_HEADER_SIZE + 1} bytes, "
            f"got {max_fragment_size}"
        )

    if not data:
        return

    chunk_size = max_fragment_size - _FRAGMENT_HEADER_SIZE
    num_fragments = (len(data) + chunk_size - 1) // chunk_size

    if num_fragments > 255:
        raise FragmentationError(f"Message requires {num_fragments} fragments, but maximum is 255")

    # Generate or use provided fragment ID
    global _fragment_id_counter
    if fragment_id is None:
        frag_id = _fragment_id_counter
        _fragment_id_counter = (_fragment_id_counter + 1) % 65536
    else:
        if not 0 <= fragment_id <= 65535:
            raise FragmentationError(f"fragment_id must be 0-65535, got {fragment_id}")
        frag_id = fragment_id

    # Yield fragments one at a time
    for seq_num in range(num_fragments):
        start = seq_num * chunk_size
        end = min(start + chunk_size, len(data))
        chunk = data[start:end]

        header = struct.pack(_FRAGMENT_HEADER_FORMAT, frag_id, seq_num, num_fragments)

        yield header + chunk
