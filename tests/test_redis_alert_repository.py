"""Tests for the Redis-backed alert repository using a fake Redis client.

The fake client keeps these as unit tests. Real Redis integration can be tested
later when Docker Compose services become part of the normal workflow.
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from streamguard.domain import DetectionResult
from streamguard.infrastructure.redis_alerts import RedisAlertRepository


class FakeRedis:
    """Minimal in-memory stand-in for the Redis commands used by the repository."""

    def __init__(self) -> None:
        """Create empty string and list stores."""
        self.strings: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.ttls: dict[str, int] = {}

    def setex(self, name: str, time: int, value: str) -> object:
        """Store a string value and remember its requested TTL."""
        self.strings[name] = value
        self.ttls[name] = time
        return True

    def lpush(self, name: str, *values: str) -> object:
        """Push values to the start of a fake Redis list."""
        current_values = self.lists.setdefault(name, [])
        for value in values:
            current_values.insert(0, value)
        return len(current_values)

    def ltrim(self, name: str, start: int, end: int) -> object:
        """Trim a fake Redis list using Redis-style inclusive end indexes."""
        self.lists[name] = self.lists.get(name, [])[start : end + 1]
        return True

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        """Return a slice from a fake Redis list using inclusive end indexes."""
        return self.lists.get(name, [])[start : end + 1]

    def get(self, name: str) -> str | None:
        """Return a stored fake Redis string value."""
        return self.strings.get(name)


def detection_result(
    *,
    detection_id: str,
    anomaly_score: float,
) -> DetectionResult:
    """Build a valid detection result for Redis repository tests."""
    return DetectionResult(
        schema_version="1.0",
        detection_id=UUID(detection_id),
        event_id=UUID("50e7935d-8c80-49ef-9613-a846c88b1220"),
        processed_at=datetime(2026, 6, 22, 8, 30, tzinfo=UTC),
        model_name="baseline_rules",
        model_version="0.1.0",
        feature_version="1.0.0",
        anomaly_score=anomaly_score,
        is_anomaly=anomaly_score >= 0.7,
        threshold=0.7,
        inference_time_ms=1.0,
        device="cpu",
        status="completed",
        error_code=None,
    )


def test_redis_repository_saves_and_lists_recent_results() -> None:
    """Saved results should round-trip through Redis serialization."""
    fake_redis = FakeRedis()
    repository = RedisAlertRepository(fake_redis)
    first = detection_result(
        detection_id="00000000-0000-0000-0000-000000000001",
        anomaly_score=0.2,
    )
    second = detection_result(
        detection_id="00000000-0000-0000-0000-000000000002",
        anomaly_score=0.8,
    )

    repository.save(first)
    repository.save(second)

    assert repository.list_recent() == [second, first]


def test_redis_repository_filters_by_minimum_score() -> None:
    """Score filtering should work after results are loaded back from Redis."""
    fake_redis = FakeRedis()
    repository = RedisAlertRepository(fake_redis)
    repository.save(
        detection_result(
            detection_id="00000000-0000-0000-0000-000000000001",
            anomaly_score=0.2,
        )
    )
    anomaly = detection_result(
        detection_id="00000000-0000-0000-0000-000000000002",
        anomaly_score=0.8,
    )
    repository.save(anomaly)

    assert repository.list_recent(minimum_score=0.7) == [anomaly]


def test_redis_repository_gets_result_by_detection_id() -> None:
    """The repository should retrieve one alert detail by detection ID."""
    fake_redis = FakeRedis()
    repository = RedisAlertRepository(fake_redis)
    result = detection_result(
        detection_id="00000000-0000-0000-0000-000000000001",
        anomaly_score=0.8,
    )

    repository.save(result)

    assert repository.get(result.detection_id) == result


def test_redis_repository_uses_ttl_and_retention_limit() -> None:
    """Redis saves should request TTLs and trim the recent-alert list."""
    fake_redis = FakeRedis()
    repository = RedisAlertRepository(fake_redis, max_results=1, ttl_seconds=60)
    first = detection_result(
        detection_id="00000000-0000-0000-0000-000000000001",
        anomaly_score=0.2,
    )
    second = detection_result(
        detection_id="00000000-0000-0000-0000-000000000002",
        anomaly_score=0.8,
    )

    repository.save(first)
    repository.save(second)

    assert repository.list_recent() == [second]
    assert set(fake_redis.ttls.values()) == {60}


def test_redis_repository_rejects_invalid_limits() -> None:
    """Invalid Redis repository settings should fail at construction or read time."""
    fake_redis = FakeRedis()

    with pytest.raises(ValueError, match="max_results"):
        RedisAlertRepository(fake_redis, max_results=0)

    with pytest.raises(ValueError, match="ttl_seconds"):
        RedisAlertRepository(fake_redis, ttl_seconds=0)

    with pytest.raises(ValueError, match="limit"):
        RedisAlertRepository(fake_redis).list_recent(limit=0)
