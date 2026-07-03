"""Redis-backed operational state repositories for StreamGuard.

This module stores short-lived processing state, such as event idempotency
markers. These keys help workers and APIs avoid duplicate processing without
turning Redis into the long-term source of truth.
"""

from typing import Protocol
from uuid import UUID

from redis import Redis


class RedisStateClient(Protocol):
    """Small subset of Redis commands needed for operational state."""

    def setex(self, name: str, time: int, value: str) -> object:
        """Store a value with a TTL."""

    def get(self, name: str) -> str | bytes | None:
        """Read one Redis string value."""


class RedisProcessedEventRepository:
    """Store event-id to detection-id markers in Redis."""

    def __init__(
        self,
        redis_client: RedisStateClient,
        *,
        ttl_seconds: int = 86_400,
        key_prefix: str = "streamguard:event",
    ) -> None:
        """Create a Redis processed-event repository with a TTL."""
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix

    @classmethod
    def from_url(
        cls,
        redis_url: str,
        *,
        ttl_seconds: int = 86_400,
    ) -> "RedisProcessedEventRepository":
        """Create a processed-event repository from a Redis URL."""
        return cls(Redis.from_url(redis_url, decode_responses=True), ttl_seconds=ttl_seconds)

    def get_detection_id(self, event_id: UUID) -> UUID | None:
        """Return the detection ID previously produced for an event ID."""
        raw_detection_id = self._redis.get(self._key(event_id))
        if raw_detection_id is None:
            return None
        return UUID(self._decode(raw_detection_id))

    def mark_processed(self, event_id: UUID, detection_id: UUID) -> None:
        """Remember which detection ID was produced for one event ID."""
        self._redis.setex(self._key(event_id), self._ttl_seconds, str(detection_id))

    def _key(self, event_id: UUID) -> str:
        """Build the Redis key for one processed event marker."""
        return f"{self._key_prefix}:{event_id}:processed"

    @staticmethod
    def _decode(value: str | bytes) -> str:
        """Normalize Redis string values from bytes or decoded clients."""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
