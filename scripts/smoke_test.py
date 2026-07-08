"""Run a local end-to-end streaming smoke test for StreamGuard.

The smoke test assumes Redis and Redpanda are already running through Docker
Compose. It creates topics, replays sample JSONL events, runs the detector
worker for a fixed number of messages, and verifies completed detections appear.
"""

from argparse import ArgumentParser, Namespace
from subprocess import run
from sys import executable

from confluent_kafka import Consumer

from streamguard.config import AppSettings, load_settings
from streamguard.infrastructure.kafka.admin import (
    create_admin_client,
    ensure_topics,
    required_topic_specs,
)


def ensure_streaming_topics(settings: AppSettings) -> list[str]:
    """Create the topics required by the smoke test."""
    return ensure_topics(
        create_admin_client(settings.kafka_bootstrap_servers),
        required_topic_specs(
            raw_topic=settings.kafka_raw_topic,
            detection_topic=settings.kafka_detection_topic,
            dead_letter_topic=settings.kafka_dead_letter_topic,
        ),
    )


def run_python_module(module: str, args: list[str]) -> None:
    """Run one Python module and fail if it exits unsuccessfully."""
    run([executable, "-m", module, *args], check=True)


def consume_completed_count(settings: AppSettings, expected_count: int) -> int:
    """Consume completed detection messages and return how many were observed."""
    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": "streamguard-smoke-test",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    observed_count = 0
    try:
        consumer.subscribe([settings.kafka_detection_topic])
        while observed_count < expected_count:
            message = consumer.poll(5.0)
            if message is None:
                break
            if message.error():
                raise RuntimeError(str(message.error()))
            observed_count += 1
    finally:
        consumer.close()
    return observed_count


def parse_args() -> Namespace:
    """Parse command-line options for the smoke test."""
    parser = ArgumentParser(description="Run StreamGuard's local streaming smoke test.")
    parser.add_argument(
        "--input",
        default="data/sample/events.jsonl",
        help="JSONL sample events to publish.",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=2,
        help="Number of completed detections expected.",
    )
    return parser.parse_args()


def main() -> None:
    """Run producer, detector worker, and completed-topic verification."""
    args = parse_args()
    settings = load_settings()
    ensured_topics = ensure_streaming_topics(settings)
    print("ensured topics: " + ", ".join(ensured_topics))

    run_python_module(
        "apps.producer.main",
        ["--input", args.input, "--events-per-second", "1000"],
    )
    run_python_module(
        "apps.detector.main",
        ["--max-messages", str(args.expected_count)],
    )

    completed_count = consume_completed_count(settings, args.expected_count)
    if completed_count < args.expected_count:
        raise RuntimeError(
            f"expected {args.expected_count} completed detections, observed {completed_count}"
        )
    print(f"smoke test passed: observed {completed_count} completed detections")


if __name__ == "__main__":
    main()
