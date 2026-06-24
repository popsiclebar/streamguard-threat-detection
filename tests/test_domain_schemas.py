"""Tests for StreamGuard's first versioned domain schemas.

These tests focus on the validation boundary: good input should become typed
Python objects, while malformed input should be rejected before detection logic
runs.
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from streamguard.domain import DetectionResult, SecurityEvent


def valid_event_payload() -> dict[str, object]:
    """Build a complete event payload that individual tests can safely modify."""
    return {
        "schema_version": "1.0",
        "event_id": "50e7935d-8c80-49ef-9613-a846c88b1220",
        "timestamp": "2026-06-22T08:30:00Z",
        "source_ip": "10.10.1.12",
        "destination_ip": "172.16.0.20",
        "source_port": 52311,
        "destination_port": 443,
        "protocol": "TCP",
        "duration_ms": 192.4,
        "source_bytes": 1450,
        "destination_bytes": 8300,
        "packet_count": 41,
        "failed_connections": 0,
        "tcp_flag_count": 4,
    }


def valid_detection_payload() -> dict[str, object]:
    """Build a complete detection payload that individual tests can safely modify."""
    return {
        "schema_version": "1.0",
        "detection_id": "82e7967d-c7bf-4a36-9bff-16fd750ae984",
        "event_id": "50e7935d-8c80-49ef-9613-a846c88b1220",
        "processed_at": datetime(2026, 6, 22, 8, 30, 1, tzinfo=UTC),
        "model_name": "baseline_rules",
        "model_version": "0.1.0",
        "feature_version": "1.0.0",
        "anomaly_score": 0.82,
        "is_anomaly": True,
        "threshold": 0.7,
        "inference_time_ms": 1.5,
        "device": "cpu",
        "status": "completed",
        "error_code": None,
    }


def test_security_event_accepts_valid_payload() -> None:
    """A valid JSON-like payload should become a typed SecurityEvent object."""
    event = SecurityEvent.model_validate(valid_event_payload())

    assert event.schema_version == "1.0"
    assert event.event_id == UUID("50e7935d-8c80-49ef-9613-a846c88b1220")
    assert str(event.source_ip) == "10.10.1.12"


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("source_port", -1),
        ("destination_port", 70000),
        ("duration_ms", -0.1),
        ("source_bytes", -1),
        ("packet_count", -1),
    ],
)
def test_security_event_rejects_out_of_range_values(
    field_name: str,
    bad_value: object,
) -> None:
    """Numeric limits reject invalid network-event values near the boundary."""
    payload = valid_event_payload()
    payload[field_name] = bad_value

    with pytest.raises(ValidationError):
        SecurityEvent.model_validate(payload)


def test_security_event_rejects_unknown_protocol() -> None:
    """Literal protocol validation keeps unsupported protocol names out."""
    payload = valid_event_payload()
    payload["protocol"] = "HTTP"

    with pytest.raises(ValidationError):
        SecurityEvent.model_validate(payload)


def test_security_event_rejects_naive_timestamp() -> None:
    """Timestamps must include timezone information for reliable comparisons."""
    payload = valid_event_payload()
    payload["timestamp"] = datetime(2026, 6, 22, 8, 30, 0)

    with pytest.raises(ValidationError):
        SecurityEvent.model_validate(payload)


def test_security_event_rejects_extra_fields() -> None:
    """Extra fields are rejected so API callers cannot silently change the contract."""
    payload = valid_event_payload()
    payload["unexpected"] = "not part of schema v1"

    with pytest.raises(ValidationError):
        SecurityEvent.model_validate(payload)


def test_detection_result_accepts_valid_payload() -> None:
    """A valid detection payload should become a typed DetectionResult object."""
    result = DetectionResult.model_validate(valid_detection_payload())

    assert result.model_name == "baseline_rules"
    assert result.device == "cpu"
    assert result.is_anomaly is True


def test_detection_result_rejects_naive_processed_at() -> None:
    """Detection timestamps must also include timezone information."""
    payload = valid_detection_payload()
    payload["processed_at"] = datetime(2026, 6, 22, 8, 30, 1)

    with pytest.raises(ValidationError):
        DetectionResult.model_validate(payload)


def test_detection_result_rejects_unknown_device() -> None:
    """Device validation keeps the output contract limited to supported runtimes."""
    payload = valid_detection_payload()
    payload["device"] = "tpu"

    with pytest.raises(ValidationError):
        DetectionResult.model_validate(payload)
