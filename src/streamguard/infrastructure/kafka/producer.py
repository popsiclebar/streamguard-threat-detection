"""Kafka-compatible producer adapter for StreamGuard security events.

The adapter wraps the concrete Confluent Kafka producer behind a small method so
application code can publish validated events without knowing client details.
"""

from typing import Protocol

from confluent_kafka import Producer

from streamguard.domain import DeadLetterMessage, DetectionResult, SecurityEvent
from streamguard.infrastructure.kafka.serialization import (
    serialize_dead_letter,
    serialize_detection_result,
    serialize_security_event,
)


class SecurityEventPublisher(Protocol):
    """Interface for publishing validated security events."""

    def publish(self, event: SecurityEvent) -> None:
        """Publish one validated security event."""

    def flush(self) -> None:
        """Wait for any buffered messages to finish sending."""


class DetectionResultPublisher(Protocol):
    """Interface for publishing completed detection results."""

    def publish(self, result: DetectionResult) -> None:
        """Publish one detection result."""

    def flush(self) -> None:
        """Wait for any buffered messages to finish sending."""


class DeadLetterPublisher(Protocol):
    """Interface for publishing dead-letter records."""

    def publish(self, message: DeadLetterMessage) -> None:
        """Publish one dead-letter record."""

    def flush(self) -> None:
        """Wait for any buffered messages to finish sending."""


class KafkaSecurityEventPublisher:
    """Publish security events to a Kafka-compatible topic."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
    ) -> None:
        """Create a publisher for one Kafka-compatible topic."""
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})
        self._topic = topic

    def publish(self, event: SecurityEvent) -> None:
        """Publish one event using event_id as the Kafka message key."""
        self._producer.produce(
            self._topic,
            key=str(event.event_id).encode("utf-8"),
            value=serialize_security_event(event),
        )
        self._producer.poll(0)

    def flush(self) -> None:
        """Wait for buffered Kafka messages to be delivered."""
        self._producer.flush()


class KafkaDetectionResultPublisher:
    """Publish completed detection results to a Kafka-compatible topic."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
    ) -> None:
        """Create a publisher for one completed-detections topic."""
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})
        self._topic = topic

    def publish(self, result: DetectionResult) -> None:
        """Publish one detection result using event_id as the message key."""
        self._producer.produce(
            self._topic,
            key=str(result.event_id).encode("utf-8"),
            value=serialize_detection_result(result),
        )
        self._producer.poll(0)

    def flush(self) -> None:
        """Wait for buffered Kafka messages to be delivered."""
        self._producer.flush()


class KafkaDeadLetterPublisher:
    """Publish invalid raw messages to a Kafka-compatible dead-letter topic."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
    ) -> None:
        """Create a publisher for one dead-letter topic."""
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})
        self._topic = topic

    def publish(self, message: DeadLetterMessage) -> None:
        """Publish one dead-letter record using topic/offset as the message key."""
        key = f"{message.source_topic}:{message.source_partition}:{message.source_offset}"
        self._producer.produce(
            self._topic,
            key=key.encode("utf-8"),
            value=serialize_dead_letter(message),
        )
        self._producer.poll(0)

    def flush(self) -> None:
        """Wait for buffered Kafka messages to be delivered."""
        self._producer.flush()
