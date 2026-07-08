"""Kafka-compatible consumer adapter for StreamGuard raw security events.

The adapter wraps Confluent Kafka's consumer so worker code can poll messages
through a tiny project-owned interface.
"""

from dataclasses import dataclass
from typing import Protocol

from confluent_kafka import Consumer


@dataclass(frozen=True)
class RawKafkaMessage:
    """Raw Kafka message data needed by the detector worker."""

    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes


class RawEventConsumer(Protocol):
    """Interface for consuming raw security-event messages."""

    def poll(self, timeout_seconds: float = 1.0) -> RawKafkaMessage | None:
        """Return one message, or None when no message is available."""

    def commit(self) -> None:
        """Commit the latest consumed offset."""

    def close(self) -> None:
        """Close the consumer and release network resources."""


class KafkaRawEventConsumer:
    """Consume raw security events from a Kafka-compatible topic."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
        group_id: str = "streamguard-detector",
    ) -> None:
        """Create a consumer subscribed to one raw security-event topic."""
        self._consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self._consumer.subscribe([topic])

    def poll(self, timeout_seconds: float = 1.0) -> RawKafkaMessage | None:
        """Poll one Kafka message and convert it into a project-owned object."""
        message = self._consumer.poll(timeout_seconds)
        if message is None:
            return None
        if message.error():
            raise RuntimeError(str(message.error()))
        value = message.value()
        if value is None:
            raise ValueError("raw Kafka message value cannot be empty")
        return RawKafkaMessage(
            topic=message.topic(),
            partition=message.partition(),
            offset=message.offset(),
            key=message.key(),
            value=value,
        )

    def commit(self) -> None:
        """Commit the current consumer position."""
        self._consumer.commit(asynchronous=False)

    def close(self) -> None:
        """Close the underlying Kafka consumer."""
        self._consumer.close()
