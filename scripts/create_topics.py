"""Create Kafka-compatible topics required by StreamGuard.

Run this script after starting Redpanda/Kafka to ensure the raw events,
completed detections, and dead-letter topics exist.
"""

from streamguard.config import load_settings
from streamguard.infrastructure.kafka.admin import (
    create_admin_client,
    ensure_topics,
    required_topic_specs,
)


def main() -> None:
    """Create the required StreamGuard Kafka-compatible topics."""
    settings = load_settings()
    topic_specs = required_topic_specs(
        raw_topic=settings.kafka_raw_topic,
        detection_topic=settings.kafka_detection_topic,
        dead_letter_topic=settings.kafka_dead_letter_topic,
    )
    created_topics = ensure_topics(
        create_admin_client(settings.kafka_bootstrap_servers),
        topic_specs,
    )
    print("ensured topics: " + ", ".join(created_topics))


if __name__ == "__main__":
    main()
