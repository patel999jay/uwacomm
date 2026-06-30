"""Pydantic message modeling for uwacomm.

This module provides the BaseMessage class and field utilities for defining
compact binary messages using Pydantic.
"""

from __future__ import annotations

from .base import BaseMessage
from .fields import BoundedInt, FixedBytes, FixedStr, VarBytes, VarList, VarStr

__all__ = [
    "BaseMessage",
    "BoundedInt",
    "FixedBytes",
    "FixedStr",
    "VarBytes",
    "VarStr",
    "VarList",
]
