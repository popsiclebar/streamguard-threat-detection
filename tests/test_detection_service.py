"""Tests for the detection use-case service.

These tests verify the first complete local detection workflow: validated event
input becomes extracted features, baseline score output, and a typed detection
result.
"""

from uuid import UUID

from streamguard.domain import DetectionResult, SecurityEvent
from streamguard.infrastructure.memory import (
    InMemoryAlertRepository,
    InMemoryProcessedEventRepository,
)
from streamguard.services import DetectionService


def event_payload(**overrides: object) -> dict[str, object]:
    """Build a valid event payload and allow focused tests to override fields."""
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return payload


def test_detection_service_returns_completed_detection_result() -> None:
    """A normal validated event should produce a completed non-anomalous result."""
    event = SecurityEvent.model_validate(event_payload())

    result = DetectionService().detect(event)

    assert isinstance(result, DetectionResult)
    assert result.schema_version == "1.0"
    assert result.event_id == UUID("50e7935d-8c80-49ef-9613-a846c88b1220")
    assert result.model_name == "baseline_rules"
    assert result.model_version == "0.1.0"
    assert result.feature_version == "1.0.0"
    assert result.device == "cpu"
    assert result.status == "completed"
    assert result.error_code is None
    assert result.inference_time_ms >= 0


def test_detection_service_marks_suspicious_event_as_anomaly() -> None:
    """The service should surface the baseline scorer's anomaly classification."""
    event = SecurityEvent.model_validate(
        event_payload(
            destination_port=22,
            failed_connections=12,
            packet_count=20,
        )
    )

    result = DetectionService().detect(event)

    assert result.is_anomaly is True
    assert result.anomaly_score == 0.7
    assert result.threshold == 0.7


def test_detection_service_generates_unique_detection_ids() -> None:
    """Each detection result should have its own ID, even for the same event."""
    event = SecurityEvent.model_validate(event_payload())
    service = DetectionService()

    first_result = service.detect(event)
    second_result = service.detect(event)

    assert first_result.detection_id != second_result.detection_id


def test_detection_service_saves_result_when_repository_is_configured() -> None:
    """DetectionService should persist completed results through its repository."""
    repository = InMemoryAlertRepository()
    event = SecurityEvent.model_validate(event_payload())
    service = DetectionService(alert_repository=repository)

    result = service.detect(event)

    assert repository.list_recent() == [result]


def test_detection_service_returns_existing_result_for_duplicate_event_id() -> None:
    """Configured idempotency should prevent duplicate detections for one event ID."""
    alert_repository = InMemoryAlertRepository()
    processed_repository = InMemoryProcessedEventRepository()
    event = SecurityEvent.model_validate(event_payload())
    service = DetectionService(
        alert_repository=alert_repository,
        processed_event_repository=processed_repository,
    )

    first_result = service.detect(event)
    second_result = service.detect(event)

    assert second_result == first_result
    assert alert_repository.list_recent() == [first_result]


def test_detection_service_recomputes_when_marker_points_to_missing_result() -> None:
    """If an idempotency marker is stale, the service should safely recompute."""
    alert_repository = InMemoryAlertRepository()
    processed_repository = InMemoryProcessedEventRepository()
    event = SecurityEvent.model_validate(event_payload())
    stale_detection_id = UUID("00000000-0000-0000-0000-000000000001")
    processed_repository.mark_processed(event.event_id, stale_detection_id)
    service = DetectionService(
        alert_repository=alert_repository,
        processed_event_repository=processed_repository,
    )

    result = service.detect(event)

    assert result.detection_id != stale_detection_id
    assert processed_repository.get_detection_id(event.event_id) == result.detection_id
