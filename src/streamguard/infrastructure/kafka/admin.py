"""Kafka-compatible topic administration helpers for StreamGuard.

Topic administration is kept separate from producers and consumers so local
setup scripts can create required streams before the pipeline starts.
"""

from dataclasses import dataclass
from typing import Protocol

from confluent_kafka.admin import AdminClient, NewTopic


@dataclass(frozen=True)
class TopicSpec:
    """Configuration for one Kafka-compatible topic."""

    name: str
    partitions: int = 1
    replication_factor: int = 1


class TopicAdminClient(Protocol):
    """Small subset of topic-admin behavior used by setup scripts."""

    def create_topics(self, new_topics: list[NewTopic]) -> dict[str, object]:
        """Create topics and return topic futures keyed by topic name."""


def required_topic_specs(
    *,
    raw_topic: str,
    detection_topic: str,
    dead_letter_topic: str,
) -> list[TopicSpec]:
    """Return the StreamGuard topics needed for the streaming pipeline."""
    return [
        TopicSpec(raw_topic),
        TopicSpec(detection_topic),
        TopicSpec(dead_letter_topic),
    ]


def create_admin_client(bootstrap_servers: str) -> AdminClient:
    """Create a Confluent Kafka admin client for the configured broker."""
    return AdminClient({"bootstrap.servers": bootstrap_servers})


def ensure_topics(admin_client: TopicAdminClient, topic_specs: list[TopicSpec]) -> list[str]:
    """Create required topics and return the names that were requested.

    Kafka-compatible brokers treat topic creation as an asynchronous operation.
    The futures returned by `create_topics` are resolved here so setup scripts
    fail immediately if a topic cannot be created.
    """
    topics = [
        NewTopic(
            spec.name,
            num_partitions=spec.partitions,
            replication_factor=spec.replication_factor,
        )
        for spec in topic_specs
    ]
    futures = admin_client.create_topics(topics)
    for topic_name, future in futures.items():
        try:
            future.result()
        except Exception as exc:
            if not _is_topic_already_exists_error(exc):
                raise RuntimeError(f"failed to create topic {topic_name}: {exc}") from exc
    return [spec.name for spec in topic_specs]


def _is_topic_already_exists_error(exc: Exception) -> bool:
    """Return whether a broker exception means the topic already exists."""
    message = str(exc).lower()
    return "already exists" in message or "topic_already_exists" in message
