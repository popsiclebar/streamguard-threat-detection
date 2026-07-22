"""Tests for StreamGuard operational metrics repositories.

Metrics repositories store simple counters that help explain what the service is
doing while avoiding a full observability stack in the early learning phases.
"""

from streamguard.infrastructure.memory import InMemoryMetricsRepository
from streamguard.infrastructure.redis import RedisMetricsRepository
from streamguard.services import MetricsSnapshot


class FakeRedis:
    """Minimal fake Redis client for metrics repository tests."""

    def __init__(self) -> None:
        """Create an empty integer counter store."""
        self.values: dict[str, int] = {}

    def incr(self, name: str, amount: int = 1) -> object:
        """Increment one fake Redis integer key."""
        self.values[name] = self.values.get(name, 0) + amount
        return self.values[name]

    def mget(self, keys: list[str]) -> list[str | None]:
        """Read multiple fake Redis keys as strings."""
        return [str(self.values[key]) if key in self.values else None for key in keys]


def test_memory_metrics_repository_starts_at_zero() -> None:
    """Memory metrics should default to an all-zero snapshot."""
    assert InMemoryMetricsRepository().snapshot() == MetricsSnapshot()


def test_memory_metrics_repository_counts_activity() -> None:
    """Memory metrics should count processed, anomaly, duplicate, invalid, and failed events."""
    repository = InMemoryMetricsRepository()

    repository.increment_processed(is_anomaly=False)
    repository.increment_processed(is_anomaly=True)
    repository.increment_duplicate()
    repository.increment_invalid()
    repository.increment_failed()

    assert repository.snapshot() == MetricsSnapshot(
        processed_total=2,
        anomalies_total=1,
        duplicates_total=1,
        invalid_total=1,
        failed_total=1,
    )


def test_redis_metrics_repository_starts_at_zero() -> None:
    """Missing Redis counter keys should be treated as zero."""
    assert RedisMetricsRepository(FakeRedis()).snapshot() == MetricsSnapshot()


def test_redis_metrics_repository_counts_activity() -> None:
    """Redis metrics should increment and read back integer counter values."""
    repository = RedisMetricsRepository(FakeRedis())

    repository.increment_processed(is_anomaly=False)
    repository.increment_processed(is_anomaly=True)
    repository.increment_duplicate()
    repository.increment_invalid()
    repository.increment_failed()

    assert repository.snapshot() == MetricsSnapshot(
        processed_total=2,
        anomalies_total=1,
        duplicates_total=1,
        invalid_total=1,
        failed_total=1,
    )
