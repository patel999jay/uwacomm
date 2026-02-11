"""Base message class and uwacomm-specific Pydantic configuration.

This module provides the BaseMessage class that all uwacomm messages should inherit from.
It also defines configuration options inspired by DCCL.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict


class BaseMessage(BaseModel):
    """Base class for all uwacomm messages.

    Messages should inherit from this class and define fields using Pydantic's
    Field() with appropriate constraints (ge, le, min_length, max_length, etc.).

    uwacomm-specific options can be configured as ClassVar attributes:

    Example:
        >>> from typing import ClassVar, Optional
        >>> from pydantic import Field
        >>> class StatusReport(BaseMessage):
        ...     vehicle_id: int = Field(ge=0, le=255)
        ...     depth_cm: int = Field(ge=0, le=10000)
        ...     battery_pct: int = Field(ge=0, le=100)
        ...
        ...     uwacomm_max_bytes: ClassVar[Optional[int]] = 16
        ...     uwacomm_id: ClassVar[Optional[int]] = 42

    Attributes:
        uwacomm_max_bytes: Maximum encoded size in bytes (optional, for validation)
        uwacomm_id: Message type ID (optional, for framing/routing)
        uwacomm_codec: Custom codec name (reserved for future use)
    """

    # ConfigDict for Pydantic v2
    model_config = ConfigDict(
        # Strict validation by default
        strict=False,
        # Allow arbitrary types (for future extensibility)
        arbitrary_types_allowed=True,
        # Validate on assignment
        validate_assignment=True,
        # Forbid extra fields not defined in schema
        extra="forbid",
    )

    # uwacomm-specific class variables (optional)
    uwacomm_max_bytes: ClassVar[int | None] = None
    uwacomm_id: ClassVar[int | None] = None
    uwacomm_codec: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hook called when a subclass is created.

        This allows us to extract uwacomm options from nested Config class
        (for backward compatibility) and set them as class variables for easy access.
        """
        super().__init_subclass__(**kwargs)

        # Extract uwacomm options from Config if present (backward compatibility)
        if hasattr(cls, "Config"):
            config = cls.Config
            # Support both old (dccl_*) and new (uwacomm_*) naming
            if hasattr(config, "uwacomm_max_bytes"):
                cls.uwacomm_max_bytes = config.uwacomm_max_bytes
            elif hasattr(config, "dccl_max_bytes"):
                cls.uwacomm_max_bytes = config.dccl_max_bytes

            if hasattr(config, "uwacomm_id"):
                cls.uwacomm_id = config.uwacomm_id
            elif hasattr(config, "dccl_id"):
                cls.uwacomm_id = config.dccl_id

            if hasattr(config, "uwacomm_codec"):
                cls.uwacomm_codec = config.uwacomm_codec
            elif hasattr(config, "dccl_codec"):
                cls.uwacomm_codec = config.dccl_codec
