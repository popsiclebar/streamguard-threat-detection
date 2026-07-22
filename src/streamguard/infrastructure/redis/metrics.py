"""Redis-backed operational metrics repository for StreamGuard.

Redis counters are useful for local runtime visibility because increments are
fast and survive API process restarts while Redis is running.
"""

from typing import Protocol

from redis import Redis

from streamguard.services.repositories import MetricsSnapshot


class RedisMetricsClient(Protocol):
    """Small subset of Redis commands needed by metrics counters."""

    def incr(self, name: str, amount: int = 1) -> object:
        """Increment an integer key."""

    def mget(self, keys: list[str]) -> list[str | bytes | None]:
        """Read multiple string values."""


class RedisMetricsRepository:
    """Store operational counters as Redis integer keys."""

    _COUNTER_NAMES = (
        "processed_total",
        "anomalies_total",
        "duplicates_total",
        "invalid_total",
        "failed_total",
    )

    def __init__(
        self,
        redis_client: RedisMetricsClient,
        *,
        key_prefix: str = "streamguard:metrics",
    ) -> None:
        """Create a metrics repository using a Redis client."""
        self._redis = redis_client
        self._key_prefix = key_prefix

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisMetricsRepository":
        """Create a metrics repository from a Redis URL."""
        return cls(Redis.from_url(redis_url, decode_responses=True))

    def increment_processed(self, *, is_anomaly: bool) -> None:
        """Record one newly processed result and optionally one anomaly."""
        self._redis.incr(self._key("processed_total"))
        if is_anomaly:
            self._redis.incr(self._key("anomalies_total"))

    def increment_duplicate(self) -> None:
        """Record one duplicate event handled through idempotency."""
        self._redis.incr(self._key("duplicates_total"))

    def increment_invalid(self) -> None:
        """Record one invalid event payload."""
        self._redis.incr(self._key("invalid_total"))

    def increment_failed(self) -> None:
        """Record one failed processing attempt."""
        self._redis.incr(self._key("failed_total"))

    def snapshot(self) -> MetricsSnapshot:
        """Return current Redis counter values, treating missing keys as zero."""
        values = self._redis.mget([self._key(name) for name in self._COUNTER_NAMES])
        counters = {
            name: self._parse_counter(value)
            for name, value in zip(self._COUNTER_NAMES, values, strict=True)
        }
        return MetricsSnapshot(**counters)

    def _key(self, name: str) -> str:
        """Build the Redis key for one metrics counter."""
        return f"{self._key_prefix}:{name}"

    @staticmethod
    def _parse_counter(value: str | bytes | None) -> int:
        """Convert Redis string counter values into integers."""
        if value is None:
            return 0
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return int(value)
