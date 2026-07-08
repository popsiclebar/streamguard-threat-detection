"""Configuration helpers for StreamGuard.

The project keeps configuration small and environment-variable based for now.
This module centralizes those settings so API dependencies and future workers do
not read environment variables in many different places.
"""

from dataclasses import dataclass
from os import environ
from typing import Literal, Mapping


AlertRepositoryBackend = Literal["memory", "redis"]


@dataclass(frozen=True)
class AppSettings:
    """Runtime settings shared by API dependencies and future worker processes."""

    alert_repository_backend: AlertRepositoryBackend = "memory"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_raw_topic: str = "security-events.raw"
    kafka_detection_topic: str = "security-detections.completed"
    kafka_dead_letter_topic: str = "security-events.dead-letter"
    producer_events_per_second: float = 5.0
    recent_alert_limit: int = 100
    alert_ttl_seconds: int = 86_400
    processed_event_ttl_seconds: int = 86_400


def load_settings(source: Mapping[str, str] | None = None) -> AppSettings:
    """Load StreamGuard settings from environment-like key/value data."""
    values = source or environ
    backend = values.get("ALERT_REPOSITORY_BACKEND", "memory").lower()
    if backend not in {"memory", "redis"}:
        raise ValueError("ALERT_REPOSITORY_BACKEND must be 'memory' or 'redis'")

    return AppSettings(
        alert_repository_backend=backend,
        redis_url=values.get("REDIS_URL", "redis://localhost:6379/0"),
        kafka_bootstrap_servers=values.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_raw_topic=values.get("KAFKA_RAW_TOPIC", "security-events.raw"),
        kafka_detection_topic=values.get(
            "KAFKA_DETECTION_TOPIC",
            "security-detections.completed",
        ),
        kafka_dead_letter_topic=values.get(
            "KAFKA_DEAD_LETTER_TOPIC",
            "security-events.dead-letter",
        ),
        producer_events_per_second=_read_positive_float(
            values,
            "PRODUCER_EVENTS_PER_SECOND",
            5.0,
        ),
        recent_alert_limit=_read_positive_int(values, "RECENT_ALERT_LIMIT", 100),
        alert_ttl_seconds=_read_positive_int(values, "ALERT_TTL_SECONDS", 86_400),
        processed_event_ttl_seconds=_read_positive_int(
            values,
            "PROCESSED_EVENT_TTL_SECONDS",
            86_400,
        ),
    )


def _read_positive_int(values: Mapping[str, str], key: str, default: int) -> int:
    """Read a positive integer setting and fail clearly when it is invalid."""
    raw_value = values.get(key)
    if raw_value is None:
        return default

    parsed_value = int(raw_value)
    if parsed_value < 1:
        raise ValueError(f"{key} must be at least 1")
    return parsed_value


def _read_positive_float(values: Mapping[str, str], key: str, default: float) -> float:
    """Read a positive floating-point setting and fail clearly when invalid."""
    raw_value = values.get(key)
    if raw_value is None:
        return default

    parsed_value = float(raw_value)
    if parsed_value <= 0:
        raise ValueError(f"{key} must be greater than 0")
    return parsed_value
