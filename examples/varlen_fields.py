#!/usr/bin/env python3
"""Variable-length field encoding example for uwacomm (v0.4.0).

This example demonstrates:
1. VarBytes  — variable-length binary payload with a compact length prefix
2. VarStr    — ASCII string with a compact length prefix
3. VarList   — variable-length list of bounded ints, bools, or floats
4. Mixed     — combining all three in one message
5. Size comparison: how actual on-wire bytes grow with content length
"""

from __future__ import annotations

from typing import ClassVar

from uwacomm import (
    BaseMessage,
    BoundedInt,
    decode,
    encode,
    encoded_bits,
    encoded_size,
    field_sizes,
)
from uwacomm.models.fields import VarBytes, VarList, VarStr

# ---------------------------------------------------------------------------
# Message definitions
# ---------------------------------------------------------------------------


class SonarPing(BaseMessage):
    """Raw sonar return: variable-length byte payload up to 64 bytes."""

    ping_id: int = BoundedInt(ge=0, le=255)  # 8 bits
    payload: bytes = VarBytes(max_length=64)  # 7-bit length prefix + up to 512 bits


class CallsignMsg(BaseMessage):
    """ASCII callsign, up to 8 characters."""

    callsign: str = VarStr(max_length=8)  # 4-bit length prefix + up to 64 bits


class DepthReadings(BaseMessage):
    """Up to 8 depth samples (0–1000 cm), packed at 10 bits each."""

    node_id: int = BoundedInt(ge=0, le=31)  # 5 bits
    depths: list[int] = VarList(max_length=8, item_ge=0, item_le=1000)  # 4-bit prefix


class StatusFlags(BaseMessage):
    """Up to 8 boolean sensor flags."""

    flags: list[bool] = VarList(max_length=8)  # 4-bit prefix + 1 bit per flag


class TemperatureLog(BaseMessage):
    """Up to 4 temperature readings in °C (−20 to 40 °C, 0.1 °C precision)."""

    readings: list[float] = VarList(max_length=4, item_ge=-20.0, item_le=40.0, item_precision=1)


class MissionUpdate(BaseMessage):
    """Combined mission update: fixed + all three variable-length field types."""

    vehicle_id: int = BoundedInt(ge=0, le=255)  # 8 bits
    callsign: str = VarStr(max_length=8)  # 4-bit prefix + ≤64 bits
    waypoint_data: bytes = VarBytes(max_length=32)  # 6-bit prefix + ≤256 bits
    depths: list[int] = VarList(max_length=4, item_ge=0, item_le=5000)  # 10 bits each

    uwacomm_id: ClassVar[int | None] = 42


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------


def print_schema(cls: type[BaseMessage], label: str) -> None:
    print(f"\n{label}")
    print(f"  Max on-wire: {encoded_bits(cls)} bits = {encoded_size(cls)} bytes")
    for name, bits in field_sizes(cls).items():
        print(f"  {name:16s}: {bits:4d} bits max")


def demo_varbytes() -> None:
    print("\n--- VarBytes: SonarPing ---")
    for payload in [b"", b"\xde\xad", bytes(range(32))]:
        msg = SonarPing(ping_id=1, payload=payload)
        data = encode(msg)
        decoded = decode(SonarPing, data)
        print(
            f"  payload={len(payload):2d} bytes → encoded {len(data)} bytes"
            f"  (decoded matches: {decoded.payload == payload})"
        )


def demo_varstr() -> None:
    print("\n--- VarStr: CallsignMsg ---")
    for callsign in ["", "AUV", "ORCA-001"]:
        msg = CallsignMsg(callsign=callsign)
        data = encode(msg)
        decoded = decode(CallsignMsg, data)
        print(
            f"  '{callsign}' ({len(callsign)} chars) → {len(data)} bytes"
            f"  (decoded: '{decoded.callsign}')"
        )


def demo_varlist_int() -> None:
    print("\n--- VarList[int]: DepthReadings ---")
    for depths in [[], [500], [0, 250, 500, 750, 900, 950, 1000, 100]]:
        msg = DepthReadings(node_id=3, depths=depths)
        data = encode(msg)
        decoded = decode(DepthReadings, data)
        print(f"  {len(depths)} items → {len(data)} bytes" f"  (decoded: {decoded.depths})")


def demo_varlist_bool() -> None:
    print("\n--- VarList[bool]: StatusFlags ---")
    for flags in [[], [True, False, True], [True] * 8]:
        msg = StatusFlags(flags=flags)
        data = encode(msg)
        decoded = decode(StatusFlags, data)
        print(f"  {len(flags)} flags → {len(data)} bytes" f"  (decoded: {decoded.flags})")


def demo_varlist_float() -> None:
    print("\n--- VarList[float]: TemperatureLog (0.1 °C precision) ---")
    for temps in [[], [-20.0, 0.0, 18.5, 36.6]]:
        msg = TemperatureLog(readings=temps)
        data = encode(msg)
        decoded = decode(TemperatureLog, data)
        rounded = [round(v, 1) for v in decoded.readings]
        print(f"  {temps} → {len(data)} bytes  (decoded: {rounded})")


def demo_mixed() -> None:
    print("\n--- Mixed: MissionUpdate ---")
    small = MissionUpdate(
        vehicle_id=1,
        callsign="A",
        waypoint_data=b"\x00",
        depths=[0],
    )
    large = MissionUpdate(
        vehicle_id=200,
        callsign="ORCA-001",
        waypoint_data=bytes(range(32)),
        depths=[0, 1000, 2500, 5000],
    )
    for label, msg in [("small", small), ("large", large)]:
        data = encode(msg)
        decoded = decode(MissionUpdate, data)
        print(
            f"  {label}: {len(data)} bytes"
            f"  callsign='{decoded.callsign}'"
            f"  depths={decoded.depths}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 55)
    print("uwacomm v0.4.0 — Variable-Length Field Encoding")
    print("=" * 55)

    print_schema(SonarPing, "SonarPing schema (VarBytes)")
    print_schema(CallsignMsg, "CallsignMsg schema (VarStr)")
    print_schema(DepthReadings, "DepthReadings schema (VarList[int])")
    print_schema(StatusFlags, "StatusFlags schema (VarList[bool])")
    print_schema(TemperatureLog, "TemperatureLog schema (VarList[float])")
    print_schema(MissionUpdate, "MissionUpdate schema (mixed)")

    demo_varbytes()
    demo_varstr()
    demo_varlist_int()
    demo_varlist_bool()
    demo_varlist_float()
    demo_mixed()
