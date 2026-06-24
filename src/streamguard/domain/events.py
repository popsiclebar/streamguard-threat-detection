"""Validated security-event schemas accepted by StreamGuard.

Security events enter the system from untrusted boundaries such as HTTP requests
and, later, Kafka messages. This module defines the strict Pydantic model that
turns loose JSON-like input into a safe Python object for feature extraction and
detection.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, field_validator


class SecurityEvent(BaseModel):
    """Versioned network security event accepted by the detection pipeline.

    A Pydantic model is both documentation and executable validation. It tells
    FastAPI, tests, and future Kafka consumers which fields are required, which
    types are allowed, and which values should be rejected before scoring starts.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    event_id: UUID
    timestamp: datetime
    source_ip: IPvAnyAddress
    destination_ip: IPvAnyAddress
    source_port: int = Field(ge=0, le=65535)
    destination_port: int = Field(ge=0, le=65535)
    protocol: Literal["TCP", "UDP", "ICMP"]
    duration_ms: float = Field(ge=0)
    source_bytes: int = Field(ge=0)
    destination_bytes: int = Field(ge=0)
    packet_count: int = Field(ge=0)
    failed_connections: int = Field(ge=0)
    tcp_flag_count: int = Field(ge=0)
    label: str | None = None

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        """Reject naive datetimes so events from different systems compare correctly."""
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("timestamp must be timezone-aware")
        return value
