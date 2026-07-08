"""Tests for processing raw Kafka messages through the detector workflow.

These tests avoid a real broker by using raw message objects and fake
publishers, while still exercising validation, DetectionService, and
dead-letter behavior.
"""

from streamguard.domain import DeadLetterMessage, DetectionResult, SecurityEvent
from streamguard.infrastructure.kafka.consumer import RawKafkaMessage
from streamguard.infrastructure.kafka.serialization import serialize_security_event
from streamguard.infrastructure.memory import (
    InMemoryAlertRepository,
    InMemoryMetricsRepository,
    InMemoryProcessedEventRepository,
)
from streamguard.services import DetectionService
from streamguard.services.stream_processor import StreamMessageProcessor


class FakeDetectionPublisher:
    """Collect detection results published by the stream processor."""

    def __init__(self) -> None:
        """Create an empty result collection."""
        self.results: list[DetectionResult] = []

    def publish(self, result: DetectionResult) -> None:
        """Record one detection result."""
        self.results.append(result)

    def flush(self) -> None:
        """Match the publisher protocol for tests."""


class FakeDeadLetterPublisher:
    """Collect dead-letter records published by the stream processor."""

    def __init__(self) -> None:
        """Create an empty dead-letter collection."""
        self.messages: list[DeadLetterMessage] = []

    def publish(self, message: DeadLetterMessage) -> None:
        """Record one dead-letter message."""
        self.messages.append(message)

    def flush(self) -> None:
        """Match the publisher protocol for tests."""


def event_payload(**overrides: object) -> dict[str, object]:
    """Build a valid security-event payload for stream processor tests."""
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return payload


def raw_message(payload: bytes) -> RawKafkaMessage:
    """Build a raw Kafka message object for tests."""
    return RawKafkaMessage(
        topic="security-events.raw",
        partition=0,
        offset=42,
        key=b"event-key",
        value=payload,
    )


def build_processor() -> tuple[
    StreamMessageProcessor,
    FakeDetectionPublisher,
    FakeDeadLetterPublisher,
    InMemoryMetricsRepository,
]:
    """Create a processor with in-memory state and fake publishers."""
    alert_repository = InMemoryAlertRepository()
    processed_event_repository = InMemoryProcessedEventRepository()
    metrics_repository = InMemoryMetricsRepository()
    detection_service = DetectionService(
        alert_repository=alert_repository,
        processed_event_repository=processed_event_repository,
        metrics_repository=metrics_repository,
    )
    detection_publisher = FakeDetectionPublisher()
    dead_letter_publisher = FakeDeadLetterPublisher()
    return (
        StreamMessageProcessor(
            detection_service=detection_service,
            detection_publisher=detection_publisher,
            dead_letter_publisher=dead_letter_publisher,
            metrics_repository=metrics_repository,
        ),
        detection_publisher,
        dead_letter_publisher,
        metrics_repository,
    )


def test_stream_processor_publishes_completed_detection() -> None:
    """A valid raw event should produce a completed detection result."""
    event = SecurityEvent.model_validate(event_payload())
    processor, detection_publisher, dead_letter_publisher, metrics_repository = build_processor()

    status = processor.process(raw_message(serialize_security_event(event)))

    assert status == "completed"
    assert len(detection_publisher.results) == 1
    assert detection_publisher.results[0].event_id == event.event_id
    assert detection_publisher.results[0].is_anomaly is True
    assert dead_letter_publisher.messages == []
    assert metrics_repository.snapshot().processed_total == 1


def test_stream_processor_dead_letters_invalid_payload() -> None:
    """A malformed raw payload should be published to the dead-letter topic."""
    processor, detection_publisher, dead_letter_publisher, metrics_repository = build_processor()

    status = processor.process(raw_message(b'{"schema_version":"1.0"}'))

    assert status == "dead_lettered"
    assert detection_publisher.results == []
    assert len(dead_letter_publisher.messages) == 1
    dead_letter = dead_letter_publisher.messages[0]
    assert dead_letter.source_topic == "security-events.raw"
    assert dead_letter.source_partition == 0
    assert dead_letter.source_offset == 42
    assert dead_letter.error_type in {"ValidationError", "ValueError"}
    assert metrics_repository.snapshot().invalid_total == 1
