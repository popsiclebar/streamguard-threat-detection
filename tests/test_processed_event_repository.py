"""Tests for processed-event idempotency repositories.

Processed-event repositories remember which detection was produced for an event
ID. This lets the API and future workers return or reuse prior results instead
of creating duplicates.
"""

from uuid import UUID

import pytest

from streamguard.infrastructure.memory import InMemoryProcessedEventRepository
from streamguard.infrastructure.redis_state import RedisProcessedEventRepository


class FakeRedis:
    """Minimal fake Redis client for processed-event repository tests."""

    def __init__(self) -> None:
        """Create an empty string store with recorded TTLs."""
        self.strings: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def setex(self, name: str, time: int, value: str) -> object:
        """Store one string value and its requested TTL."""
        self.strings[name] = value
        self.ttls[name] = time
        return True

    def get(self, name: str) -> str | None:
        """Return one stored string value."""
        return self.strings.get(name)


def test_memory_processed_event_repository_round_trips_marker() -> None:
    """The memory repository should map event IDs to detection IDs."""
    repository = InMemoryProcessedEventRepository()
    event_id = UUID("50e7935d-8c80-49ef-9613-a846c88b1220")
    detection_id = UUID("00000000-0000-0000-0000-000000000001")

    repository.mark_processed(event_id, detection_id)

    assert repository.get_detection_id(event_id) == detection_id


def test_redis_processed_event_repository_round_trips_marker() -> None:
    """The Redis repository should store processed markers as UUID strings."""
    fake_redis = FakeRedis()
    repository = RedisProcessedEventRepository(fake_redis, ttl_seconds=60)
    event_id = UUID("50e7935d-8c80-49ef-9613-a846c88b1220")
    detection_id = UUID("00000000-0000-0000-0000-000000000001")

    repository.mark_processed(event_id, detection_id)

    assert repository.get_detection_id(event_id) == detection_id
    assert fake_redis.ttls[f"streamguard:event:{event_id}:processed"] == 60


def test_redis_processed_event_repository_returns_none_for_missing_marker() -> None:
    """Missing Redis markers should be represented as None."""
    repository = RedisProcessedEventRepository(FakeRedis())

    assert repository.get_detection_id(UUID("50e7935d-8c80-49ef-9613-a846c88b1220")) is None


def test_redis_processed_event_repository_rejects_invalid_ttl() -> None:
    """Invalid processed-event TTLs should fail at construction time."""
    with pytest.raises(ValueError, match="ttl_seconds"):
        RedisProcessedEventRepository(FakeRedis(), ttl_seconds=0)
