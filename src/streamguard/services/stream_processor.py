"""Streaming message processor for StreamGuard detector workers.

This service owns the per-message workflow: decode a raw Kafka payload, validate
it as a security event, run detection, publish the result, or write a dead
letter when validation fails.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import ValidationError

from streamguard.domain import DeadLetterMessage
from streamguard.infrastructure.kafka.consumer import RawKafkaMessage
from streamguard.infrastructure.kafka.producer import DeadLetterPublisher, DetectionResultPublisher
from streamguard.infrastructure.kafka.serialization import deserialize_security_event
from streamguard.services import DetectionService
from streamguard.services.repositories import MetricsRepository


ProcessStatus = Literal["completed", "dead_lettered"]


class StreamMessageProcessor:
    """Process one raw Kafka event message through StreamGuard detection."""

    def __init__(
        self,
        *,
        detection_service: DetectionService,
        detection_publisher: DetectionResultPublisher,
        dead_letter_publisher: DeadLetterPublisher,
        metrics_repository: MetricsRepository | None = None,
    ) -> None:
        """Create a processor with injected service and publishers."""
        self._detection_service = detection_service
        self._detection_publisher = detection_publisher
        self._dead_letter_publisher = dead_letter_publisher
        self._metrics_repository = metrics_repository

    def process(self, message: RawKafkaMessage) -> ProcessStatus:
        """Process one raw message and publish either a result or dead letter."""
        try:
            event = deserialize_security_event(message.value)
        except (UnicodeDecodeError, ValidationError, ValueError) as exc:
            self._publish_dead_letter(message, exc)
            if self._metrics_repository is not None:
                self._metrics_repository.increment_invalid()
            return "dead_lettered"

        result = self._detection_service.detect(event)
        self._detection_publisher.publish(result)
        return "completed"

    def _publish_dead_letter(self, message: RawKafkaMessage, exc: Exception) -> None:
        """Build and publish a structured dead-letter record for one bad payload."""
        dead_letter = DeadLetterMessage(
            schema_version="1.0",
            failed_at=datetime.now(UTC),
            source_topic=message.topic,
            source_partition=message.partition,
            source_offset=message.offset,
            error_type=type(exc).__name__,
            error_message=str(exc),
            raw_payload=_decode_raw_payload(message.value),
        )
        self._dead_letter_publisher.publish(dead_letter)


def _decode_raw_payload(payload: bytes) -> str:
    """Decode payload bytes for dead-letter storage without raising errors."""
    return payload.decode("utf-8", errors="replace")
