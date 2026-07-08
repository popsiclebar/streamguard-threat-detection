"""Tests for Kafka-compatible security-event serialization.

Kafka transports bytes, so these tests protect the conversion between
StreamGuard's typed Pydantic events and the JSON bytes sent through a topic.
"""

from datetime import UTC, datetime
from uuid import UUID

from streamguard.domain import DeadLetterMessage, DetectionResult, SecurityEvent
from streamguard.infrastructure.kafka.serialization import (
    serialize_dead_letter,
    serialize_detection_result,
    deserialize_security_event,
    serialize_security_event,
)


def event_payload() -> dict[str, object]:
    """Build a valid event payload for serialization tests."""
    return {
        "schema_version": "1.0",
        "event_id": "50e7935d-8c80-49ef-9613-a846c88b1220",
        "timestamp": "2026-06-22T08:30:00Z",
        "source_ip": "10.10.1.12",
        "destination_ip": "172.16.0.20",
        "source_port": 52311,
        "destination_port": 22,
        "protocol": "TCP",
        "duration_ms": 192.4,
        "source_bytes": 1450,
        "destination_bytes": 8300,
        "packet_count": 20,
        "failed_connections": 12,
        "tcp_flag_count": 4,
    }


def test_security_event_serialization_round_trips() -> None:
    """A validated event should serialize to bytes and deserialize unchanged."""
    event = SecurityEvent.model_validate(event_payload())

    payload = serialize_security_event(event)
    restored_event = deserialize_security_event(payload)

    assert isinstance(payload, bytes)
    assert restored_event == event


def test_detection_result_serialization_produces_json_bytes() -> None:
    """Detection results should serialize into Kafka-ready JSON bytes."""
    result = DetectionResult(
        schema_version="1.0",
        detection_id=UUID("00000000-0000-0000-0000-000000000001"),
        event_id=UUID("50e7935d-8c80-49ef-9613-a846c88b1220"),
        processed_at=datetime(2026, 6, 22, 8, 30, tzinfo=UTC),
        model_name="baseline_rules",
        model_version="0.1.0",
        feature_version="1.0.0",
        anomaly_score=0.7,
        is_anomaly=True,
        threshold=0.7,
        inference_time_ms=1.0,
        device="cpu",
        status="completed",
        error_code=None,
    )

    payload = serialize_detection_result(result)

    assert isinstance(payload, bytes)
    assert b'"status":"completed"' in payload


def test_dead_letter_serialization_produces_json_bytes() -> None:
    """Dead-letter messages should serialize into Kafka-ready JSON bytes."""
    message = DeadLetterMessage(
        schema_version="1.0",
        failed_at=datetime(2026, 6, 22, 8, 30, tzinfo=UTC),
        source_topic="security-events.raw",
        source_partition=0,
        source_offset=1,
        error_type="ValidationError",
        error_message="invalid payload",
        raw_payload="{}",
    )

    payload = serialize_dead_letter(message)

    assert isinstance(payload, bytes)
    assert b'"error_type":"ValidationError"' in payload
