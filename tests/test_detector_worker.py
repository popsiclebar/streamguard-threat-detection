"""Tests for the detector worker polling loop.

The worker loop is tested with fake consumer and publisher objects so offset
commit and resource cleanup behavior is covered without a running broker.
"""

from streamguard.domain import DetectionResult
from streamguard.infrastructure.kafka.consumer import RawKafkaMessage
from apps.detector.main import run_worker


class FakeConsumer:
    """Return predefined raw messages to the worker loop."""

    def __init__(self, messages: list[RawKafkaMessage]) -> None:
        """Create a fake consumer with a queue of messages."""
        self.messages = messages
        self.commits = 0
        self.closed = False

    def poll(self, timeout_seconds: float = 1.0) -> RawKafkaMessage | None:
        """Return the next fake message, or None when empty."""
        if not self.messages:
            return None
        return self.messages.pop(0)

    def commit(self) -> None:
        """Record one committed offset."""
        self.commits += 1

    def close(self) -> None:
        """Record that the consumer was closed."""
        self.closed = True


class FakeProcessor:
    """Record messages processed by the worker loop."""

    def __init__(self) -> None:
        """Create an empty processed-message list."""
        self.messages: list[RawKafkaMessage] = []

    def process(self, message: RawKafkaMessage) -> str:
        """Record one processed message."""
        self.messages.append(message)
        return "completed"


class FakePublisher:
    """Record whether a publisher was flushed."""

    def __init__(self) -> None:
        """Create an unflushed fake publisher."""
        self.flushed = False

    def publish(self, result: DetectionResult) -> None:
        """Match publisher protocols; unused by the worker loop test."""

    def flush(self) -> None:
        """Record that the publisher was flushed."""
        self.flushed = True


def raw_message(offset: int) -> RawKafkaMessage:
    """Build a raw message with a distinct offset."""
    return RawKafkaMessage(
        topic="security-events.raw",
        partition=0,
        offset=offset,
        key=None,
        value=b"{}",
    )


def test_run_worker_processes_and_commits_limited_messages() -> None:
    """The worker loop should process messages, commit offsets, flush, and close."""
    consumer = FakeConsumer([raw_message(0), raw_message(1)])
    processor = FakeProcessor()
    detection_publisher = FakePublisher()
    dead_letter_publisher = FakePublisher()

    processed_count = run_worker(
        consumer=consumer,
        processor=processor,  # type: ignore[arg-type]
        detection_publisher=detection_publisher,
        dead_letter_publisher=dead_letter_publisher,
        max_messages=2,
    )

    assert processed_count == 2
    assert [message.offset for message in processor.messages] == [0, 1]
    assert consumer.commits == 2
    assert consumer.closed is True
    assert detection_publisher.flushed is True
    assert dead_letter_publisher.flushed is True
