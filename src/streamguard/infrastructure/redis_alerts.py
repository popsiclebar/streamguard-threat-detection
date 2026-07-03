"""Redis-backed alert repository for StreamGuard.

Redis stores fast operational state rather than long-term history. This adapter
keeps recent detection results available across API requests and process
restarts while using the same repository interface as the in-memory adapter.
"""

from typing import Protocol
from uuid import UUID

from redis import Redis

from streamguard.domain import DetectionResult


class RedisClient(Protocol):
    """Small subset of Redis commands needed by the alert repository."""

    def setex(self, name: str, time: int, value: str) -> object:
        """Store a value with a TTL."""

    def lpush(self, name: str, *values: str) -> object:
        """Push values to the start of a Redis list."""

    def ltrim(self, name: str, start: int, end: int) -> object:
        """Trim a Redis list to the inclusive start/end range."""

    def lrange(self, name: str, start: int, end: int) -> list[str | bytes]:
        """Read values from a Redis list."""

    def get(self, name: str) -> str | bytes | None:
        """Read one Redis string value."""


class RedisAlertRepository:
    """Store and retrieve recent detection results using Redis."""

    def __init__(
        self,
        redis_client: RedisClient,
        *,
        max_results: int = 100,
        ttl_seconds: int = 86_400,
        recent_key: str = "streamguard:alerts:recent",
        detail_key_prefix: str = "streamguard:alerts",
    ) -> None:
        """Create a Redis repository with retention and TTL settings."""
        if max_results < 1:
            raise ValueError("max_results must be at least 1")
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")

        self._redis = redis_client
        self._max_results = max_results
        self._ttl_seconds = ttl_seconds
        self._recent_key = recent_key
        self._detail_key_prefix = detail_key_prefix

    @classmethod
    def from_url(
        cls,
        redis_url: str,
        *,
        max_results: int = 100,
        ttl_seconds: int = 86_400,
    ) -> "RedisAlertRepository":
        """Create a repository from a Redis URL using decoded string responses."""
        return cls(
            Redis.from_url(redis_url, decode_responses=True),
            max_results=max_results,
            ttl_seconds=ttl_seconds,
        )

    def save(self, result: DetectionResult) -> None:
        """Store one detection result and remember it in the recent-alert list."""
        detection_id = str(result.detection_id)
        self._redis.setex(
            self._detail_key(detection_id),
            self._ttl_seconds,
            result.model_dump_json(),
        )
        self._redis.lpush(self._recent_key, detection_id)
        self._redis.ltrim(self._recent_key, 0, self._max_results - 1)

    def list_recent(
        self,
        *,
        limit: int = 100,
        minimum_score: float | None = None,
    ) -> list[DetectionResult]:
        """Return newest recent alerts first, optionally filtered by score."""
        if limit < 1:
            raise ValueError("limit must be at least 1")

        detection_ids = self._redis.lrange(self._recent_key, 0, self._max_results - 1)
        results: list[DetectionResult] = []
        for raw_detection_id in detection_ids:
            detection_id = self._decode(raw_detection_id)
            result = self.get(UUID(detection_id))
            if result is None:
                continue
            if minimum_score is not None and result.anomaly_score < minimum_score:
                continue
            results.append(result)
            if len(results) >= limit:
                break

        return results

    def get(self, detection_id: UUID) -> DetectionResult | None:
        """Return one detection result by detection ID."""
        raw_payload = self._redis.get(self._detail_key(str(detection_id)))
        if raw_payload is None:
            return None
        return DetectionResult.model_validate_json(self._decode(raw_payload))

    def _detail_key(self, detection_id: str) -> str:
        """Build the Redis key for one detection result payload."""
        return f"{self._detail_key_prefix}:{detection_id}"

    @staticmethod
    def _decode(value: str | bytes) -> str:
        """Normalize Redis string values from bytes or decoded clients."""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
