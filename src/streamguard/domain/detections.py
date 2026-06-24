"""Detection-result schemas returned by StreamGuard.

Detection results are the public output of the scoring pipeline. Keeping this
contract explicit makes the API response, worker output, and future stored alert
records use the same field names and validation rules.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DetectionResult(BaseModel):
    """Versioned result produced after StreamGuard scores one security event."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    detection_id: UUID
    event_id: UUID
    processed_at: datetime
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    feature_version: str = Field(min_length=1)
    anomaly_score: float = Field(ge=0)
    is_anomaly: bool
    threshold: float = Field(ge=0)
    inference_time_ms: float = Field(ge=0)
    device: Literal["cpu", "cuda", "mps"]
    status: Literal["completed", "failed"]
    error_code: str | None = None

    @field_validator("processed_at")
    @classmethod
    def processed_at_must_include_timezone(cls, value: datetime) -> datetime:
        """Reject naive datetimes so result timestamps are safe to sort and compare."""
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("processed_at must be timezone-aware")
        return value
