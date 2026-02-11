"""Schema introspection for Pydantic models.

This module provides utilities to analyze Pydantic models and extract
encoding-relevant information such as field types, bounds, and bit requirements.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from typing import Any, List, Optional, Type, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from ..exceptions import SchemaError


@dataclass(frozen=True)
class FieldSchema:
    """Schema information for a single field.

    Attributes:
        name: Field name
        python_type: Python type annotation
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
    """

    name: str
    python_type: Type[Any]
    required: bool
    default: Any
    min_value: Optional[int | float]
    max_value: Optional[int | float]
    min_length: Optional[int]
    max_length: Optional[int]
    enum_type: Optional[Type[enum.Enum]]
    is_list: bool
    is_bytes: bool
    is_str: bool

    def bits_required(self) -> int:
        """Calculate the minimum number of bits required to encode this field.

        Returns:
            Number of bits required

        Raises:
            SchemaError: If field type is not supported or constraints are missing
        """
        # Boolean: 1 bit
        if self.python_type is bool:
            return 1

        # Enum: log2(num_values) bits
        if self.enum_type is not None:
            num_values = len(self.enum_type)
            if num_values == 0:
                raise SchemaError(f"Enum {self.enum_type} has no values")
            if num_values == 1:
                return 1  # Single value, still need 1 bit
            return math.ceil(math.log2(num_values))

        # Bounded integer: calculate bits from range
        if self.python_type is int and self.min_value is not None and self.max_value is not None:
            return self._bits_for_bounded_int(int(self.min_value), int(self.max_value))

        # Fixed-length bytes/str: length * 8 bits
        if (self.is_bytes or self.is_str) and self.max_length is not None:
            if self.min_length is not None and self.min_length != self.max_length:
                raise SchemaError(
                    f"Field {self.name}: variable-length bytes/str not supported in v0.1.0. "
                    f"Use fixed length (min_length == max_length)."
                )
            return self.max_length * 8

        # Fixed-length list: not implemented in v0.1.0
        if self.is_list:
            raise SchemaError(
                f"Field {self.name}: array support is limited in v0.1.0. "
                f"Use fixed-length bytes for byte arrays."
            )

        # Unsupported or missing constraints
        if self.python_type is int:
            raise SchemaError(
                f"Field {self.name}: integer fields require ge= and le= constraints "
                f"for compact encoding."
            )

        if self.python_type is float:
            raise SchemaError(
                f"Field {self.name}: float encoding not supported in v0.1.0 "
                f"(planned for v0.2.0)"
            )

        raise SchemaError(
            f"Field {self.name}: unsupported type {self.python_type}. "
            f"Supported: bool, bounded int, enum, fixed bytes/str."
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

    def __init__(self, model_class: Type[BaseModel]) -> None:
        """Initialize schema from a Pydantic model.

        Args:
            model_class: Pydantic model class to introspect
        """
        self.model_class = model_class
        self.fields: List[FieldSchema] = []
        self._introspect()

    @classmethod
    def from_model(cls, model_class: Type[BaseModel]) -> MessageSchema:
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
        for constraint in field_info.metadata:
            if hasattr(constraint, "ge"):
                min_value = constraint.ge
            if hasattr(constraint, "le"):
                max_value = constraint.le
            if hasattr(constraint, "min_length"):
                min_length = constraint.min_length
            if hasattr(constraint, "max_length"):
                max_length = constraint.max_length

        # Determine field type characteristics
        enum_type = None
        is_list = False
        is_bytes = False
        is_str = False

        # Check for enum
        if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
            enum_type = annotation

        # Check for list
        list_origin = get_origin(annotation)
        if list_origin is list:
            is_list = True
            # Get element type
            list_args = get_args(annotation)
            if list_args:
                annotation = list_args[0]

        # Check for bytes/str
        if annotation is bytes:
            is_bytes = True
        if annotation is str:
            is_str = True

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
