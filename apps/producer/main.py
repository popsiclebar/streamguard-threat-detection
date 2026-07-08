"""Command-line producer for replaying sample StreamGuard events.

This module reads JSONL security events, validates each line with Pydantic, and
publishes the events through a Kafka-compatible publisher.
"""

from argparse import ArgumentParser, Namespace
from collections.abc import Iterable
from pathlib import Path
from time import sleep

from streamguard.config import load_settings
from streamguard.domain import SecurityEvent
from streamguard.infrastructure.kafka.producer import (
    KafkaSecurityEventPublisher,
    SecurityEventPublisher,
)


def load_events_jsonl(path: Path) -> list[SecurityEvent]:
    """Load and validate security events from a JSONL file."""
    events: list[SecurityEvent] = []
    with path.open(encoding="utf-8") as event_file:
        for line_number, line in enumerate(event_file, start=1):
            stripped_line = line.strip()
            if not stripped_line:
                continue
            try:
                events.append(SecurityEvent.model_validate_json(stripped_line))
            except ValueError as exc:
                raise ValueError(f"invalid event on line {line_number}: {exc}") from exc
    return events


def publish_events(
    events: Iterable[SecurityEvent],
    publisher: SecurityEventPublisher,
    *,
    events_per_second: float,
) -> int:
    """Publish events at a fixed rate and return the number sent."""
    if events_per_second <= 0:
        raise ValueError("events_per_second must be greater than 0")

    delay_seconds = 1 / events_per_second
    published_count = 0
    for event in events:
        publisher.publish(event)
        published_count += 1
        sleep(delay_seconds)

    publisher.flush()
    return published_count


def parse_args() -> Namespace:
    """Parse command-line options for the producer application."""
    parser = ArgumentParser(description="Replay StreamGuard sample events to Kafka.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/sample/events.jsonl"),
        help="Path to a JSONL file containing one security event per line.",
    )
    parser.add_argument(
        "--events-per-second",
        type=float,
        default=None,
        help="Publish rate. Defaults to PRODUCER_EVENTS_PER_SECOND.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the producer from command-line arguments and environment settings."""
    args = parse_args()
    settings = load_settings()
    events_per_second = args.events_per_second or settings.producer_events_per_second
    publisher = KafkaSecurityEventPublisher(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_raw_topic,
    )
    published_count = publish_events(
        load_events_jsonl(args.input),
        publisher,
        events_per_second=events_per_second,
    )
    print(f"published {published_count} events to {settings.kafka_raw_topic}")


if __name__ == "__main__":
    main()
