"""Tests for message fragmentation and reassembly."""

from __future__ import annotations

import random

import pytest

from uwacomm.exceptions import FragmentationError
from uwacomm.fragmentation import fragment_message, iter_fragments, reassemble_fragments


class TestFragmentMessage:
    """Tests for fragment_message() function."""

    def test_single_fragment_small_message(self) -> None:
        """Test that small message fits in single fragment."""
        data = b"hello"
        fragments = fragment_message(data, max_fragment_size=64)

        assert len(fragments) == 1
        assert len(fragments[0]) == 4 + 5  # 4 byte header + 5 byte data

    def test_multiple_fragments(self) -> None:
        """Test fragmenting message into multiple pieces."""
        data = b"x" * 200  # 200 bytes
        fragments = fragment_message(data, max_fragment_size=64)

        # With 64 byte max and 4 byte header: 60 bytes per fragment
        # 200 / 60 = 3.33... → 4 fragments
        assert len(fragments) == 4

        # Each fragment should be at most 64 bytes
        for frag in fragments:
            assert len(frag) <= 64

        # Last fragment might be smaller
        assert len(fragments[-1]) < 64

    def test_empty_data_returns_empty_list(self) -> None:
        """Test that empty data returns empty fragment list."""
        fragments = fragment_message(b"", max_fragment_size=64)
        assert fragments == []

    def test_exact_chunk_boundary(self) -> None:
        """Test message that exactly fills N fragments."""
        # With 64 byte max and 4 byte header: 60 bytes per fragment
        # 120 bytes should give exactly 2 fragments
        data = b"x" * 120
        fragments = fragment_message(data, max_fragment_size=64)

        assert len(fragments) == 2
        assert len(fragments[0]) == 64  # Full fragment
        assert len(fragments[1]) == 64  # Full fragment

    def test_custom_fragment_id(self) -> None:
        """Test using explicit fragment ID."""
        data = b"test data"
        fragments = fragment_message(data, max_fragment_size=64, fragment_id=12345)

        # Parse header to verify fragment ID
        import struct

        frag_id, seq_num, total = struct.unpack(">HBB", fragments[0][:4])
        assert frag_id == 12345
        assert seq_num == 0
        assert total == 1

    def test_max_fragment_size_too_small_raises(self) -> None:
        """Test that max_fragment_size < 5 raises error."""
        with pytest.raises(FragmentationError, match="must be at least 5 bytes"):
            fragment_message(b"test", max_fragment_size=4)

        with pytest.raises(FragmentationError, match="must be at least 5 bytes"):
            fragment_message(b"test", max_fragment_size=3)

    def test_too_many_fragments_required_raises(self) -> None:
        """Test that message requiring >255 fragments raises error."""
        # With 64 byte max and 4 byte header: 60 bytes per fragment
        # For >255 fragments: need > 255 * 60 = 15,300 bytes
        data = b"x" * 16000
        with pytest.raises(FragmentationError, match="requires .* fragments.*maximum is 255"):
            fragment_message(data, max_fragment_size=64)

    def test_fragment_id_out_of_range_raises(self) -> None:
        """Test that invalid fragment_id raises error."""
        with pytest.raises(FragmentationError, match="fragment_id must be 0-65535"):
            fragment_message(b"test", max_fragment_size=64, fragment_id=-1)

        with pytest.raises(FragmentationError, match="fragment_id must be 0-65535"):
            fragment_message(b"test", max_fragment_size=64, fragment_id=65536)

    def test_auto_increment_fragment_id(self) -> None:
        """Test that fragment ID auto-increments across calls."""
        import struct

        data = b"test"

        # Get current fragment ID
        frag1 = fragment_message(data, max_fragment_size=64)
        id1, _, _ = struct.unpack(">HBB", frag1[0][:4])

        # Next call should increment
        frag2 = fragment_message(data, max_fragment_size=64)
        id2, _, _ = struct.unpack(">HBB", frag2[0][:4])

        assert id2 == (id1 + 1) % 65536  # Wraps at 65536


class TestReassembleFragments:
    """Tests for reassemble_fragments() function."""

    def test_reassemble_single_fragment(self) -> None:
        """Test reassembling single fragment."""
        original = b"hello world"
        fragments = fragment_message(original, max_fragment_size=64)

        reassembled = reassemble_fragments(fragments)
        assert reassembled == original

    def test_reassemble_multiple_fragments(self) -> None:
        """Test reassembling multiple fragments."""
        original = b"x" * 200
        fragments = fragment_message(original, max_fragment_size=64)

        reassembled = reassemble_fragments(fragments)
        assert reassembled == original

    def test_reassemble_out_of_order(self) -> None:
        """Test reassembling fragments delivered out of order."""
        original = b"x" * 200
        fragments = fragment_message(original, max_fragment_size=64)

        # Shuffle fragments
        shuffled = fragments.copy()
        random.shuffle(shuffled)

        # Should still reassemble correctly
        reassembled = reassemble_fragments(shuffled)
        assert reassembled == original

    def test_empty_fragment_list_raises(self) -> None:
        """Test that empty fragment list raises error."""
        with pytest.raises(FragmentationError, match="Cannot reassemble empty fragment list"):
            reassemble_fragments([])

    def test_fragment_too_short_raises(self) -> None:
        """Test that fragment < 4 bytes raises error."""
        with pytest.raises(FragmentationError, match="Fragment .* too short"):
            reassemble_fragments([b"abc"])  # Only 3 bytes, need 4 for header

    def test_missing_fragment_raises(self) -> None:
        """Test that missing fragment is detected."""
        original = b"x" * 200
        fragments = fragment_message(original, max_fragment_size=64)

        # Remove fragment 1
        del fragments[1]

        with pytest.raises(FragmentationError, match="Missing fragments.*\\[1\\]"):
            reassemble_fragments(fragments)

    def test_duplicate_fragment_raises(self) -> None:
        """Test that duplicate fragment is detected."""
        original = b"x" * 200
        fragments = fragment_message(original, max_fragment_size=64)

        # Duplicate fragment 0
        fragments.append(fragments[0])

        with pytest.raises(FragmentationError, match="Duplicate fragment.*sequence number 0"):
            reassemble_fragments(fragments)

    def test_mismatched_fragment_id_raises(self) -> None:
        """Test that mixed fragments from different messages raise error."""
        data1 = b"x" * 100
        data2 = b"y" * 100

        frags1 = fragment_message(data1, max_fragment_size=64, fragment_id=100)
        frags2 = fragment_message(data2, max_fragment_size=64, fragment_id=200)

        # Mix fragments from different messages
        mixed = [frags1[0], frags2[0]]

        with pytest.raises(FragmentationError, match="Fragment ID mismatch"):
            reassemble_fragments(mixed)

    def test_mismatched_total_count_raises(self) -> None:
        """Test that fragments with different totals raise error."""
        import struct

        data = b"x" * 100
        fragments = fragment_message(data, max_fragment_size=64)

        # Corrupt total count in second fragment
        header = struct.unpack(">HBB", fragments[1][:4])
        corrupted_header = struct.pack(">HBB", header[0], header[1], 99)  # Wrong total
        fragments[1] = corrupted_header + fragments[1][4:]

        with pytest.raises(FragmentationError, match="Total fragments mismatch"):
            reassemble_fragments(fragments)

    def test_roundtrip_various_sizes(self) -> None:
        """Test fragment/reassemble roundtrip for various data sizes."""
        test_sizes = [1, 10, 60, 61, 120, 200, 500, 1000]

        for size in test_sizes:
            original = bytes(range(256)) * (size // 256 + 1)
            original = original[:size]  # Exact size

            fragments = fragment_message(original, max_fragment_size=64)
            reassembled = reassemble_fragments(fragments)

            assert reassembled == original, f"Failed for size {size}"


class TestIterFragments:
    """Tests for iter_fragments() memory-efficient variant."""

    def test_iter_fragments_matches_fragment_message(self) -> None:
        """Test that iter_fragments produces same output as fragment_message."""
        data = b"x" * 200

        # Use explicit fragment ID to ensure same output
        frag_id = 12345

        # Using fragment_message
        fragments_list = fragment_message(data, max_fragment_size=64, fragment_id=frag_id)

        # Using iter_fragments
        fragments_iter = list(iter_fragments(data, max_fragment_size=64, fragment_id=frag_id))

        assert len(fragments_iter) == len(fragments_list)
        for i, (frag_iter, frag_list) in enumerate(zip(fragments_iter, fragments_list)):
            assert frag_iter == frag_list, f"Fragment {i} mismatch"

    def test_iter_fragments_empty_data(self) -> None:
        """Test that iter_fragments handles empty data."""
        fragments = list(iter_fragments(b"", max_fragment_size=64))
        assert fragments == []

    def test_iter_fragments_lazy_evaluation(self) -> None:
        """Test that iter_fragments doesn't store all fragments in memory."""
        data = b"x" * 1000

        # This should not create a full list
        iterator = iter_fragments(data, max_fragment_size=64)

        # Get first fragment
        first = next(iterator)
        assert len(first) == 64

        # Can continue getting fragments
        second = next(iterator)
        assert len(second) == 64

    def test_iter_fragments_can_reassemble(self) -> None:
        """Test that iter_fragments output can be reassembled."""
        original = b"x" * 200
        fragments = list(iter_fragments(original, max_fragment_size=64))

        reassembled = reassemble_fragments(fragments)
        assert reassembled == original


class TestFragmentationEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_fragment_size_exactly_header_plus_one(self) -> None:
        """Test minimum valid fragment size (5 bytes)."""
        data = b"hello world"
        fragments = fragment_message(data, max_fragment_size=5)

        # With 5 byte max and 4 byte header: 1 byte per fragment
        # 11 bytes → 11 fragments
        assert len(fragments) == 11

        # Each fragment should be exactly 5 bytes (4 header + 1 data)
        for frag in fragments[:-1]:
            assert len(frag) == 5

    def test_maximum_255_fragments(self) -> None:
        """Test maximum allowed fragments (255)."""
        # With 64 byte max and 4 byte header: 60 bytes per fragment
        # For exactly 255 fragments: 255 * 60 = 15,300 bytes
        data = b"x" * 15300
        fragments = fragment_message(data, max_fragment_size=64)

        assert len(fragments) == 255

        # Should reassemble correctly
        reassembled = reassemble_fragments(fragments)
        assert reassembled == data

    def test_binary_data_preservation(self) -> None:
        """Test that binary data (all byte values) is preserved."""
        # Test all possible byte values
        original = bytes(range(256)) * 10  # 2560 bytes with all byte values

        fragments = fragment_message(original, max_fragment_size=64)
        reassembled = reassemble_fragments(fragments)

        assert reassembled == original

    def test_concurrent_fragmentation_different_ids(self) -> None:
        """Test fragmenting multiple messages concurrently."""
        data1 = b"x" * 100
        data2 = b"y" * 100
        data3 = b"z" * 100

        # Fragment with explicit IDs
        frags1 = fragment_message(data1, max_fragment_size=64, fragment_id=1)
        frags2 = fragment_message(data2, max_fragment_size=64, fragment_id=2)
        frags3 = fragment_message(data3, max_fragment_size=64, fragment_id=3)

        # Each should reassemble correctly
        assert reassemble_fragments(frags1) == data1
        assert reassemble_fragments(frags2) == data2
        assert reassemble_fragments(frags3) == data3

    def test_single_byte_data(self) -> None:
        """Test fragmenting single byte."""
        data = b"A"
        fragments = fragment_message(data, max_fragment_size=64)

        assert len(fragments) == 1
        assert len(fragments[0]) == 5  # 4 byte header + 1 byte data

        reassembled = reassemble_fragments(fragments)
        assert reassembled == data

    def test_fragment_id_wraps_at_65536(self) -> None:
        """Test that fragment ID counter wraps at 65536."""
        import struct

        # Force counter to near wraparound
        from uwacomm import fragmentation

        original_counter = fragmentation._fragment_id_counter
        fragmentation._fragment_id_counter = 65535

        try:
            # This should use ID 65535
            frag1 = fragment_message(b"test", max_fragment_size=64)
            id1, _, _ = struct.unpack(">HBB", frag1[0][:4])
            assert id1 == 65535

            # Next should wrap to 0
            frag2 = fragment_message(b"test", max_fragment_size=64)
            id2, _, _ = struct.unpack(">HBB", frag2[0][:4])
            assert id2 == 0
        finally:
            # Restore original counter
            fragmentation._fragment_id_counter = original_counter
