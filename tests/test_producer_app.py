"""Tests for the StreamGuard sample event producer application.

The tests use a fake publisher so producer behavior is covered without needing
a running Kafka-compatible broker.
"""

from pathlib import Path

import pytest

from apps.producer.main import load_events_jsonl, publish_events
from streamguard.domain import SecurityEvent


class FakePublisher:
    """Collect published events for producer tests."""

    def __init__(self) -> None:
        """Create an empty published-event list."""
        self.events: list[SecurityEvent] = []
        self.flushed = False

    def publish(self, event: SecurityEvent) -> None:
        """Record one published event."""
        self.events.append(event)

    def flush(self) -> None:
        """Record that publishing was flushed."""
        self.flushed = True


def test_load_events_jsonl_reads_sample_events() -> None:
    """The checked-in sample JSONL file should contain valid security events."""
    events = load_events_jsonl(Path("data/sample/events.jsonl"))

    assert len(events) == 2
    assert all(isinstance(event, SecurityEvent) for event in events)


def test_load_events_jsonl_reports_line_number_for_invalid_event(tmp_path: Path) -> None:
    """Invalid JSONL input should fail with a helpful line number."""
    input_file = tmp_path / "events.jsonl"
    input_file.write_text('{"schema_version":"1.0"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 1"):
        load_events_jsonl(input_file)


def test_publish_events_sends_all_events_and_flushes() -> None:
    """Publishing should send each event through the publisher and flush once."""
    events = load_events_jsonl(Path("data/sample/events.jsonl"))
    publisher = FakePublisher()

    published_count = publish_events(events, publisher, events_per_second=1000)

    assert published_count == 2
    assert publisher.events == events
    assert publisher.flushed is True


def test_publish_events_rejects_non_positive_rate() -> None:
    """A non-positive publish rate is invalid because it cannot produce a delay."""
    publisher = FakePublisher()

    with pytest.raises(ValueError, match="events_per_second"):
        publish_events([], publisher, events_per_second=0)
