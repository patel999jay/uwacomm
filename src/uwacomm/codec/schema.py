"""Schema introspection for Pydantic models.

This module provides utilities to analyze Pydantic models and extract
encoding-relevant information such as field types, bounds, and bit requirements.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from typing import Any, Optional, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from ..exceptions import SchemaError


@dataclass(frozen=True)
class FieldSchema:
    """Schema information for a single field.

    Attributes:
        name: Field name
        python_type: Python type annotation (element type for lists)
        required: Whether field is required (not Optional)
        default: Default value if any
        min_value: Minimum value constraint (for numeric types)
        max_value: Maximum value constraint (for numeric types)
        min_length: Minimum length constraint (for bytes/str/list)
        max_length: Maximum length constraint (for bytes/str/list)
        enum_type: Enum class if field is an enum
        is_list: Whether field is a list/array
        is_bytes: Whether field is bytes type
        is_str: Whether field is str type
        precision: Decimal precision for float fields (DCCL-style)
        is_nested: Whether field is a nested BaseModel subclass
        nested_class: The nested model class (when is_nested is True)
        is_varlen: Whether field is variable-length (bytes/str/list with length prefix)
        item_min_value: Minimum value for VarList elements
        item_max_value: Maximum value for VarList elements
        item_precision: Decimal precision for float VarList elements
        item_is_bool: Whether VarList elements are booleans
    """

    name: str
    python_type: type[Any]
    required: bool
    default: Any
    min_value: int | float | None
    max_value: int | float | None
    min_length: int | None
    max_length: int | None
    enum_type: type[enum.Enum] | None
    is_list: bool
    is_bytes: bool
    is_str: bool
    precision: int | None = None
    is_nested: bool = False
    nested_class: Any = None  # type[BaseModel] | None
    is_varlen: bool = False
    item_min_value: int | float | None = None
    item_max_value: int | float | None = None
    item_precision: int | None = None
    item_is_bool: bool = False

    def bits_required(self) -> int:
        """Calculate the number of bits required to encode this field.

        For variable-length fields, returns the MAXIMUM possible bits.
        For nested messages, returns the total bits of the nested schema.

        Returns:
            Number of bits required (max for varlen fields)

        Raises:
            SchemaError: If field type is not supported or constraints are missing
        """
        # Nested message: sum the nested schema's bits inline
        if self.is_nested and self.nested_class is not None:
            nested_schema = MessageSchema.from_model(self.nested_class)
            return nested_schema.total_bits()

        # Variable-length bytes/str: length-prefix bits + max payload bits
        if self.is_varlen and (self.is_bytes or self.is_str):
            max_len = self.max_length or 0
            if max_len == 0:
                return 1
            length_bits = self._bits_for_bounded_int(0, max_len)
            return length_bits + max_len * 8

        # Variable-length list: length-prefix bits + max element bits
        if self.is_varlen and self.is_list:
            max_len = self.max_length or 0
            if max_len == 0:
                return 1
            length_bits = self._bits_for_bounded_int(0, max_len)
            element_bits = self._item_bits()
            return length_bits + max_len * element_bits

        # Boolean: 1 bit
        if self.python_type is bool:
            return 1

        # Enum: log2(num_values) bits
        if self.enum_type is not None:
            num_values = len(self.enum_type)
            if num_values == 0:
                raise SchemaError(f"Enum {self.enum_type} has no values")
            if num_values == 1:
                return 1
            return math.ceil(math.log2(num_values))

        # Bounded integer: calculate bits from range
        if self.python_type is int and self.min_value is not None and self.max_value is not None:
            return self._bits_for_bounded_int(int(self.min_value), int(self.max_value))

        # Bounded float: scale to int and calculate bits (DCCL-style)
        if self.python_type is float:
            if self.min_value is None or self.max_value is None:
                raise SchemaError(
                    f"Field {self.name}: float requires ge= and le= constraints "
                    f"(e.g., Field(ge=-100.0, le=100.0))"
                )
            precision = self.precision or 0
            min_val = float(self.min_value)
            max_val = float(self.max_value)
            max_scaled = round((max_val - min_val) * (10**precision))
            return self._bits_for_bounded_int(0, max_scaled)

        # Fixed-length bytes/str: length * 8 bits
        if (self.is_bytes or self.is_str) and self.max_length is not None:
            return self.max_length * 8

        # List without VarList helper: error
        if self.is_list:
            raise SchemaError(
                f"Field {self.name}: list fields require the VarList() helper with "
                f"max_length and item constraints (item_ge, item_le)."
            )

        # Unsupported or missing constraints
        if self.python_type is int:
            raise SchemaError(
                f"Field {self.name}: integer fields require ge= and le= constraints "
                f"for compact encoding."
            )

        raise SchemaError(
            f"Field {self.name}: unsupported type {self.python_type}. "
            f"Supported: bool, bounded int/float, enum, fixed/variable bytes/str, "
            f"variable list, nested BaseMessage."
        )

    def _item_bits(self) -> int:
        """Bits required per VarList element."""
        if self.item_is_bool:
            return 1
        if self.item_min_value is not None and self.item_max_value is not None:
            if self.item_precision is not None:
                max_scaled = round(
                    (float(self.item_max_value) - float(self.item_min_value))
                    * (10**self.item_precision)
                )
                return self._bits_for_bounded_int(0, max_scaled)
            return self._bits_for_bounded_int(int(self.item_min_value), int(self.item_max_value))
        raise SchemaError(
            f"Field {self.name}: VarList with non-bool elements requires item_ge and item_le"
        )

    @staticmethod
    def _bits_for_bounded_int(min_val: int, max_val: int) -> int:
        """Calculate bits needed for a bounded integer.

        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            Number of bits required

        Raises:
            SchemaError: If constraints are invalid
        """
        if min_val > max_val:
            raise SchemaError(f"Invalid bounds: min={min_val} > max={max_val}")

        # Handle the range
        range_size = max_val - min_val + 1

        if range_size <= 0:
            raise SchemaError(f"Invalid range size: {range_size}")

        if range_size == 1:
            return 1  # Single value, still need 1 bit

        # Calculate bits needed
        return math.ceil(math.log2(range_size))


class MessageSchema:
    """Schema information for an entire message.

    This class introspects a Pydantic model and extracts all encoding-relevant
    information for each field.

    Example:
        >>> schema = MessageSchema.from_model(StatusReport)
        >>> for field in schema.fields:
        ...     print(f"{field.name}: {field.bits_required()} bits")
    """

    def __init__(self, model_class: type[BaseModel]) -> None:
        """Initialize schema from a Pydantic model.

        Args:
            model_class: Pydantic model class to introspect
        """
        self.model_class = model_class
        self.fields: list[FieldSchema] = []
        self._introspect()

    @classmethod
    def from_model(cls, model_class: type[BaseModel]) -> MessageSchema:
        """Create a schema from a Pydantic model.

        Args:
            model_class: Pydantic model class

        Returns:
            MessageSchema instance
        """
        return cls(model_class)

    def _introspect(self) -> None:
        """Introspect the model and populate field schemas."""
        # Get model fields (Pydantic v2 API)
        model_fields = self.model_class.model_fields

        for field_name, field_info in model_fields.items():
            field_schema = self._extract_field_schema(field_name, field_info)
            self.fields.append(field_schema)

    def _extract_field_schema(self, name: str, field_info: FieldInfo) -> FieldSchema:
        """Extract schema information from a Pydantic FieldInfo.

        Args:
            name: Field name
            field_info: Pydantic FieldInfo object

        Returns:
            FieldSchema with extracted information
        """
        # Get the annotation type
        annotation = field_info.annotation
        if annotation is None:
            raise SchemaError(f"Field {name} has no type annotation")

        # Check if Optional (Union[T, None])
        origin = get_origin(annotation)
        args = get_args(annotation)
        is_optional = False

        if origin is type(Optional[int]):  # Union type
            # Filter out NoneType
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                annotation = non_none_args[0]
                is_optional = True
            else:
                raise SchemaError(f"Field {name}: complex Union types not supported")

        required = field_info.is_required() and not is_optional
        default = field_info.default if field_info.default is not None else None

        # Extract constraints from metadata
        min_value = None
        max_value = None
        min_length = None
        max_length = None

        # Pydantic v2 stores constraints in metadata
        precision = None
        for constraint in field_info.metadata:
            if hasattr(constraint, "ge"):
                min_value = constraint.ge
            if hasattr(constraint, "le"):
                max_value = constraint.le
            if hasattr(constraint, "min_length"):
                min_length = constraint.min_length
            if hasattr(constraint, "max_length"):
                max_length = constraint.max_length

        # Extract precision from json_schema_extra for float fields
        if (
            annotation is float
            and hasattr(field_info, "json_schema_extra")
            and isinstance(field_info.json_schema_extra, dict)
        ):
            precision_value = field_info.json_schema_extra.get("precision", 0)
            # Ensure precision is an int
            if isinstance(precision_value, int):
                precision = precision_value
            elif isinstance(precision_value, (float, str)):
                precision = int(precision_value)
            else:
                precision = 0

        # Determine field type characteristics
        enum_type = None
        is_list = False
        is_bytes = False
        is_str = False
        is_nested = False
        nested_class = None
        is_varlen = False
        item_min_value: int | float | None = None
        item_max_value: int | float | None = None
        item_precision: int | None = None
        item_is_bool = False

        # Check for nested BaseModel subclass (before list/bytes/str)
        if (
            isinstance(annotation, type)
            and issubclass(annotation, BaseModel)
            and annotation is not BaseModel
        ):
            is_nested = True
            nested_class = annotation
        else:
            # Check for enum
            if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
                enum_type = annotation

            # Check for list; reassign annotation to element type
            list_origin = get_origin(annotation)
            if list_origin is list:
                is_list = True
                list_args = get_args(annotation)
                if list_args:
                    annotation = list_args[0]

                # Extract per-element constraints from VarList json_schema_extra
                jse = field_info.json_schema_extra
                if isinstance(jse, dict):
                    _ige = jse.get("item_ge")
                    _ile = jse.get("item_le")
                    _ipr = jse.get("item_precision")
                    if isinstance(_ige, (int, float)):
                        item_min_value = _ige
                    if isinstance(_ile, (int, float)):
                        item_max_value = _ile
                    if isinstance(_ipr, int):
                        item_precision = _ipr

                if annotation is bool:
                    item_is_bool = True

            # Check for bytes/str (element type after list unwrap, or direct)
            if annotation is bytes:
                is_bytes = True
            if annotation is str:
                is_str = True

        # Determine variable-length: list with max_length, or bytes/str where min != max
        if not is_nested and (
            is_list
            and max_length is not None
            or (is_bytes or is_str)
            and max_length is not None
            and (min_length is None or min_length != max_length)
        ):
            is_varlen = True

        return FieldSchema(
            name=name,
            python_type=annotation,
            required=required,
            default=default,
            min_value=min_value,
            max_value=max_value,
            min_length=min_length,
            max_length=max_length,
            enum_type=enum_type,
            is_list=is_list,
            is_bytes=is_bytes,
            is_str=is_str,
            precision=precision,
            is_nested=is_nested,
            nested_class=nested_class,
            is_varlen=is_varlen,
            item_min_value=item_min_value,
            item_max_value=item_max_value,
            item_precision=item_precision,
            item_is_bool=item_is_bool,
        )

    def total_bits(self) -> int:
        """Calculate total bits required for the entire message.

        Returns:
            Total bits required

        Raises:
            SchemaError: If any field has invalid schema
        """
        return sum(field.bits_required() for field in self.fields)

    def total_bytes(self) -> int:
        """Calculate total bytes required (rounded up).

        Returns:
            Total bytes required
        """
        bits = self.total_bits()
        return (bits + 7) // 8  # Round up to nearest byte
