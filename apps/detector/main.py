"""Command-line detector worker for StreamGuard streaming ingestion.

This worker connects the Kafka-compatible raw event topic to the shared
DetectionService. It keeps the polling loop thin so detection behavior remains
testable outside Kafka.
"""

from argparse import ArgumentParser, Namespace

from streamguard.config import AppSettings, load_settings
from streamguard.infrastructure.kafka.consumer import KafkaRawEventConsumer, RawEventConsumer
from streamguard.infrastructure.kafka.producer import (
    DeadLetterPublisher,
    DetectionResultPublisher,
    KafkaDeadLetterPublisher,
    KafkaDetectionResultPublisher,
)
from streamguard.infrastructure.memory import (
    InMemoryAlertRepository,
    InMemoryMetricsRepository,
    InMemoryProcessedEventRepository,
)
from streamguard.infrastructure.postgres import PostgresDetectionHistoryRepository
from streamguard.infrastructure.redis import (
    RedisAlertRepository,
    RedisMetricsRepository,
    RedisProcessedEventRepository,
)
from streamguard.services import DetectionService, MetricsRepository
from streamguard.services.stream_processor import StreamMessageProcessor


def build_detection_service(settings: AppSettings) -> tuple[DetectionService, MetricsRepository]:
    """Build the detection service and metrics repository for the worker."""
    detection_history_repository = None
    if settings.detection_history_backend == "postgres":
        detection_history_repository = PostgresDetectionHistoryRepository.from_url(
            settings.postgres_url
        )

    if settings.alert_repository_backend == "redis":
        alert_repository = RedisAlertRepository.from_url(
            settings.redis_url,
            max_results=settings.recent_alert_limit,
            ttl_seconds=settings.alert_ttl_seconds,
        )
        processed_event_repository = RedisProcessedEventRepository.from_url(
            settings.redis_url,
            ttl_seconds=settings.processed_event_ttl_seconds,
        )
        metrics_repository = RedisMetricsRepository.from_url(settings.redis_url)
    else:
        alert_repository = InMemoryAlertRepository(max_results=settings.recent_alert_limit)
        processed_event_repository = InMemoryProcessedEventRepository()
        metrics_repository = InMemoryMetricsRepository()

    return (
        DetectionService(
            alert_repository=alert_repository,
            processed_event_repository=processed_event_repository,
            metrics_repository=metrics_repository,
            detection_history_repository=detection_history_repository,
        ),
        metrics_repository,
    )


def run_worker(
    *,
    consumer: RawEventConsumer,
    processor: StreamMessageProcessor,
    detection_publisher: DetectionResultPublisher,
    dead_letter_publisher: DeadLetterPublisher,
    max_messages: int | None = None,
) -> int:
    """Poll messages, process them, commit offsets, and return processed count."""
    processed_count = 0
    try:
        while max_messages is None or processed_count < max_messages:
            message = consumer.poll(timeout_seconds=1.0)
            if message is None:
                if max_messages is not None:
                    break
                continue

            processor.process(message)
            consumer.commit()
            processed_count += 1
    finally:
        detection_publisher.flush()
        dead_letter_publisher.flush()
        consumer.close()

    return processed_count


def parse_args() -> Namespace:
    """Parse command-line options for the detector worker."""
    parser = ArgumentParser(description="Consume StreamGuard raw events and publish detections.")
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Optional message limit for local smoke tests.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the detector worker from command-line arguments and environment settings."""
    args = parse_args()
    settings = load_settings()
    detection_service, metrics_repository = build_detection_service(settings)
    detection_publisher = KafkaDetectionResultPublisher(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_detection_topic,
    )
    dead_letter_publisher = KafkaDeadLetterPublisher(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_dead_letter_topic,
    )
    consumer = KafkaRawEventConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_raw_topic,
    )
    processor = StreamMessageProcessor(
        detection_service=detection_service,
        detection_publisher=detection_publisher,
        dead_letter_publisher=dead_letter_publisher,
        metrics_repository=metrics_repository,
    )
    processed_count = run_worker(
        consumer=consumer,
        processor=processor,
        detection_publisher=detection_publisher,
        dead_letter_publisher=dead_letter_publisher,
        max_messages=args.max_messages,
    )
    print(f"processed {processed_count} messages from {settings.kafka_raw_topic}")


if __name__ == "__main__":
    main()
