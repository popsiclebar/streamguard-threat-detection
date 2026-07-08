"""Tests for Kafka-compatible topic administration helpers."""

import pytest

from streamguard.infrastructure.kafka.admin import TopicSpec, ensure_topics, required_topic_specs


class FakeFuture:
    """Fake topic-creation future returned by a Kafka admin client."""

    def __init__(self, exc: Exception | None = None) -> None:
        """Create a future that either succeeds or raises the given exception."""
        self._exc = exc

    def result(self) -> None:
        """Resolve the fake future."""
        if self._exc is not None:
            raise self._exc


class FakeAdminClient:
    """Fake admin client that records requested topic names."""

    def __init__(self, exc: Exception | None = None) -> None:
        """Create a fake admin client with optional create failure."""
        self.topic_names: list[str] = []
        self._exc = exc

    def create_topics(self, new_topics: list[object]) -> dict[str, FakeFuture]:
        """Record topic names and return fake futures."""
        self.topic_names = [topic.topic for topic in new_topics]  # type: ignore[attr-defined]
        return {name: FakeFuture(self._exc) for name in self.topic_names}


def test_required_topic_specs_uses_configured_names() -> None:
    """Required topic specs should mirror configured StreamGuard topic names."""
    specs = required_topic_specs(
        raw_topic="raw",
        detection_topic="completed",
        dead_letter_topic="dead",
    )

    assert specs == [
        TopicSpec("raw"),
        TopicSpec("completed"),
        TopicSpec("dead"),
    ]


def test_ensure_topics_requests_all_topics() -> None:
    """Topic creation should request each required topic and return their names."""
    admin_client = FakeAdminClient()

    topic_names = ensure_topics(admin_client, [TopicSpec("raw"), TopicSpec("completed")])

    assert topic_names == ["raw", "completed"]
    assert admin_client.topic_names == ["raw", "completed"]


def test_ensure_topics_ignores_already_exists_errors() -> None:
    """Re-running topic creation should tolerate broker already-exists responses."""
    admin_client = FakeAdminClient(RuntimeError("topic already exists"))

    topic_names = ensure_topics(admin_client, [TopicSpec("raw")])

    assert topic_names == ["raw"]


def test_ensure_topics_ignores_redpanda_already_exists_errors() -> None:
    """Redpanda reports existing topics with a symbolic TOPIC_ALREADY_EXISTS code."""
    admin_client = FakeAdminClient(RuntimeError("KafkaError{code=TOPIC_ALREADY_EXISTS}"))

    topic_names = ensure_topics(admin_client, [TopicSpec("raw")])

    assert topic_names == ["raw"]


def test_ensure_topics_raises_other_creation_errors() -> None:
    """Unexpected topic creation errors should fail the setup script."""
    admin_client = FakeAdminClient(RuntimeError("broker unavailable"))

    with pytest.raises(RuntimeError, match="failed to create topic raw"):
        ensure_topics(admin_client, [TopicSpec("raw")])
