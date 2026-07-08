"""Dead-letter message schemas for invalid streaming payloads.

Dead letters preserve enough context to debug malformed Kafka messages without
pretending the original event was successfully processed.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeadLetterMessage(BaseModel):
    """Versioned record written when a raw event message cannot be processed."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    failed_at: datetime
    source_topic: str = Field(min_length=1)
    source_partition: int = Field(ge=0)
    source_offset: int = Field(ge=0)
    error_type: str = Field(min_length=1)
    error_message: str = Field(min_length=1)
    raw_payload: str

    @field_validator("failed_at")
    @classmethod
    def failed_at_must_include_timezone(cls, value: datetime) -> datetime:
        """Reject naive datetimes so dead-letter records sort reliably."""
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("failed_at must be timezone-aware")
        return value
