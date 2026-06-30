"""Unit tests for variable-length fields: VarBytes, VarStr, VarList (v0.4.0)."""

from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from uwacomm import (
    BaseMessage,
    BoundedInt,
    EncodeError,
    decode,
    encode,
    encoded_bits,
    field_sizes,
)
from uwacomm.models.fields import VarBytes, VarList, VarStr

# ---------------------------------------------------------------------------
# Message definitions
# ---------------------------------------------------------------------------


class VarBytesMsg(BaseMessage):
    header: int = BoundedInt(ge=0, le=255)  # 8 bits
    payload: bytes = VarBytes(max_length=64)  # 7-bit prefix + up to 512 bits


class VarStrMsg(BaseMessage):
    name: str = VarStr(max_length=16)


class VarIntListMsg(BaseMessage):
    count: int = BoundedInt(ge=0, le=15)  # 4 bits
    depths: list[int] = VarList(max_length=8, item_ge=0, item_le=1000)


class VarBoolListMsg(BaseMessage):
    flags: list[bool] = VarList(max_length=8)


class VarFloatListMsg(BaseMessage):
    temps: list[float] = VarList(max_length=4, item_ge=-20.0, item_le=40.0, item_precision=1)


class MixedMsg(BaseMessage):
    """Message combining fixed and variable-length fields."""

    vehicle_id: int = BoundedInt(ge=0, le=255)
    callsign: str = VarStr(max_length=8)
    sensor_data: bytes = VarBytes(max_length=32)
    readings: list[int] = VarList(max_length=4, item_ge=0, item_le=100)

    uwacomm_id: ClassVar[int | None] = 30


# ---------------------------------------------------------------------------
# VarBytes tests
# ---------------------------------------------------------------------------


class TestVarBytes:
    def test_empty_payload_roundtrip(self) -> None:
        msg = VarBytesMsg(header=0, payload=b"")
        decoded = decode(VarBytesMsg, encode(msg))
        assert decoded.payload == b""
        assert decoded.header == 0

    def test_partial_payload_roundtrip(self) -> None:
        msg = VarBytesMsg(header=42, payload=b"\xde\xad\xbe\xef")
        decoded = decode(VarBytesMsg, encode(msg))
        assert decoded.payload == b"\xde\xad\xbe\xef"

    def test_max_length_payload_roundtrip(self) -> None:
        data = bytes(range(64))
        msg = VarBytesMsg(header=255, payload=data)
        decoded = decode(VarBytesMsg, encode(msg))
        assert decoded.payload == data

    def test_different_lengths_give_different_sizes(self) -> None:
        short = encode(VarBytesMsg(header=0, payload=b"AB"))
        long_ = encode(VarBytesMsg(header=0, payload=b"ABCDEFGH"))
        assert len(long_) > len(short)

    def test_encoding_is_deterministic(self) -> None:
        msg = VarBytesMsg(header=1, payload=b"\x00\xff")
        assert encode(msg) == encode(msg)

    def test_all_byte_values_preserved(self) -> None:
        payload = bytes(range(256 % 65))  # 64 bytes of varied values
        msg = VarBytesMsg(header=0, payload=payload[:64])
        decoded = decode(VarBytesMsg, encode(msg))
        assert decoded.payload == payload[:64]

    def test_max_size_from_schema(self) -> None:
        # header: 8 bits, payload length prefix: 7 bits, payload: 64*8=512 bits → 527 bits max
        bits = encoded_bits(VarBytesMsg)
        assert bits == 8 + 7 + 64 * 8  # 527

    def test_pydantic_rejects_oversized_payload(self) -> None:
        with pytest.raises(ValidationError):
            VarBytesMsg(header=0, payload=b"x" * 65)


# ---------------------------------------------------------------------------
# VarStr tests
# ---------------------------------------------------------------------------


class TestVarStr:
    def test_empty_string_roundtrip(self) -> None:
        msg = VarStrMsg(name="")
        decoded = decode(VarStrMsg, encode(msg))
        assert decoded.name == ""

    def test_short_string_roundtrip(self) -> None:
        msg = VarStrMsg(name="ALPHA")
        decoded = decode(VarStrMsg, encode(msg))
        assert decoded.name == "ALPHA"

    def test_full_length_string_roundtrip(self) -> None:
        msg = VarStrMsg(name="0123456789ABCDEF")
        decoded = decode(VarStrMsg, encode(msg))
        assert decoded.name == "0123456789ABCDEF"

    def test_non_ascii_raises_encode_error(self) -> None:
        msg = VarStrMsg.model_construct(name="café")
        with pytest.raises(EncodeError, match="ASCII"):
            encode(msg)

    def test_different_lengths_produce_different_byte_counts(self) -> None:
        short = encode(VarStrMsg(name="HI"))
        long_ = encode(VarStrMsg(name="HELLO WORLD"))
        assert len(long_) > len(short)

    def test_schema_max_size(self) -> None:
        # length prefix: ceil(log2(17)) = 5 bits, max payload: 16*8=128 → 133 bits max
        bits = encoded_bits(VarStrMsg)
        assert bits == 5 + 16 * 8  # 133

    def test_pydantic_rejects_too_long_string(self) -> None:
        with pytest.raises(ValidationError):
            VarStrMsg(name="x" * 17)


# ---------------------------------------------------------------------------
# VarList[int] tests
# ---------------------------------------------------------------------------


class TestVarIntList:
    def test_empty_list_roundtrip(self) -> None:
        msg = VarIntListMsg(count=0, depths=[])
        decoded = decode(VarIntListMsg, encode(msg))
        assert decoded.depths == []

    def test_single_element_roundtrip(self) -> None:
        msg = VarIntListMsg(count=1, depths=[500])
        decoded = decode(VarIntListMsg, encode(msg))
        assert decoded.depths == [500]

    def test_full_list_roundtrip(self) -> None:
        items = [0, 100, 200, 500, 750, 900, 999, 1000]
        msg = VarIntListMsg(count=8, depths=items)
        decoded = decode(VarIntListMsg, encode(msg))
        assert decoded.depths == items

    def test_boundary_values(self) -> None:
        msg = VarIntListMsg(count=2, depths=[0, 1000])
        decoded = decode(VarIntListMsg, encode(msg))
        assert decoded.depths == [0, 1000]

    def test_item_out_of_range_raises(self) -> None:
        msg = VarIntListMsg.model_construct(count=1, depths=[9999])
        with pytest.raises(EncodeError, match="out of bounds"):
            encode(msg)

    def test_schema_max_size(self) -> None:
        # depths: prefix=4 bits (0..8), 8 elements * ceil(log2(1001))=10 bits = 4+80=84 bits
        # count: 4 bits → total 88 bits = 11 bytes
        sizes = field_sizes(VarIntListMsg)
        assert sizes["depths"] == 4 + 8 * 10  # 84


# ---------------------------------------------------------------------------
# VarList[bool] tests
# ---------------------------------------------------------------------------


class TestVarBoolList:
    def test_empty_bool_list_roundtrip(self) -> None:
        msg = VarBoolListMsg(flags=[])
        decoded = decode(VarBoolListMsg, encode(msg))
        assert decoded.flags == []

    def test_bool_list_roundtrip(self) -> None:
        flags = [True, False, True, True, False]
        msg = VarBoolListMsg(flags=flags)
        decoded = decode(VarBoolListMsg, encode(msg))
        assert decoded.flags == flags

    def test_full_bool_list_roundtrip(self) -> None:
        flags = [True, False] * 4
        msg = VarBoolListMsg(flags=flags)
        decoded = decode(VarBoolListMsg, encode(msg))
        assert decoded.flags == flags

    def test_bool_list_size(self) -> None:
        # prefix: 4 bits (0..8), 8 bools * 1 bit = 4+8=12 bits
        sizes = field_sizes(VarBoolListMsg)
        assert sizes["flags"] == 4 + 8 * 1


# ---------------------------------------------------------------------------
# VarList[float] tests
# ---------------------------------------------------------------------------


class TestVarFloatList:
    def test_float_list_roundtrip(self) -> None:
        temps = [-20.0, 0.0, 18.5, 36.6]
        msg = VarFloatListMsg(temps=temps)
        decoded = decode(VarFloatListMsg, encode(msg))
        for orig, dec in zip(temps, decoded.temps):
            assert dec == pytest.approx(orig, abs=0.1)

    def test_empty_float_list_roundtrip(self) -> None:
        msg = VarFloatListMsg(temps=[])
        decoded = decode(VarFloatListMsg, encode(msg))
        assert decoded.temps == []

    def test_float_boundary_values(self) -> None:
        msg = VarFloatListMsg(temps=[-20.0, 40.0])
        decoded = decode(VarFloatListMsg, encode(msg))
        assert decoded.temps[0] == pytest.approx(-20.0, abs=0.1)
        assert decoded.temps[1] == pytest.approx(40.0, abs=0.1)


# ---------------------------------------------------------------------------
# Mixed field message
# ---------------------------------------------------------------------------


class TestMixedMessage:
    def test_mixed_message_roundtrip(self) -> None:
        msg = MixedMsg(
            vehicle_id=42,
            callsign="UUV-01",
            sensor_data=b"\x01\x02\x03",
            readings=[10, 55, 99],
        )
        decoded = decode(MixedMsg, encode(msg))
        assert decoded.vehicle_id == 42
        assert decoded.callsign == "UUV-01"
        assert decoded.sensor_data == b"\x01\x02\x03"
        assert decoded.readings == [10, 55, 99]

    def test_mixed_message_with_empty_varlen_fields(self) -> None:
        msg = MixedMsg(vehicle_id=0, callsign="", sensor_data=b"", readings=[])
        decoded = decode(MixedMsg, encode(msg))
        assert decoded.callsign == ""
        assert decoded.sensor_data == b""
        assert decoded.readings == []

    def test_mixed_message_mode2_roundtrip(self) -> None:
        msg = MixedMsg(vehicle_id=5, callsign="ALPHA", sensor_data=b"\xff\x00", readings=[0, 100])
        data = encode(msg, include_id=True)
        decoded = decode(MixedMsg, data, include_id=True)
        assert decoded.callsign == "ALPHA"
        assert decoded.readings == [0, 100]

    def test_different_payloads_differ_in_length(self) -> None:
        short_msg = MixedMsg(vehicle_id=1, callsign="A", sensor_data=b"\x00", readings=[0])
        long_msg = MixedMsg(
            vehicle_id=1,
            callsign="ABCDEFGH",
            sensor_data=bytes(range(32)),
            readings=[0, 25, 50, 100],
        )
        assert len(encode(long_msg)) > len(encode(short_msg))
