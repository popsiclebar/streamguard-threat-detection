"""Tests for StreamGuard environment-based configuration loading.

Configuration tests keep startup behavior predictable: invalid environment
values should fail early, while omitted values should use safe local defaults.
"""

import pytest

from streamguard.config import AppSettings, load_settings


def test_load_settings_uses_local_defaults() -> None:
    """Default settings should keep StreamGuard runnable without external services."""
    assert load_settings({}) == AppSettings()


def test_load_settings_accepts_redis_backend() -> None:
    """Redis settings should be loaded when the operator enables Redis storage."""
    settings = load_settings(
        {
            "ALERT_REPOSITORY_BACKEND": "redis",
            "REDIS_URL": "redis://redis.example.test:6379/1",
            "KAFKA_BOOTSTRAP_SERVERS": "broker.example.test:9092",
            "KAFKA_RAW_TOPIC": "custom.raw",
            "KAFKA_DETECTION_TOPIC": "custom.completed",
            "KAFKA_DEAD_LETTER_TOPIC": "custom.dead-letter",
            "PRODUCER_EVENTS_PER_SECOND": "12.5",
            "RECENT_ALERT_LIMIT": "50",
            "ALERT_TTL_SECONDS": "60",
            "PROCESSED_EVENT_TTL_SECONDS": "120",
        }
    )

    assert settings.alert_repository_backend == "redis"
    assert settings.redis_url == "redis://redis.example.test:6379/1"
    assert settings.kafka_bootstrap_servers == "broker.example.test:9092"
    assert settings.kafka_raw_topic == "custom.raw"
    assert settings.kafka_detection_topic == "custom.completed"
    assert settings.kafka_dead_letter_topic == "custom.dead-letter"
    assert settings.producer_events_per_second == 12.5
    assert settings.recent_alert_limit == 50
    assert settings.alert_ttl_seconds == 60
    assert settings.processed_event_ttl_seconds == 120


def test_load_settings_accepts_postgres_detection_history() -> None:
    """PostgreSQL history settings should be opt-in and separately configured."""
    settings = load_settings(
        {
            "DETECTION_HISTORY_BACKEND": "postgres",
            "POSTGRES_URL": "postgresql://user:pass@db.example.test:5432/streamguard",
        }
    )

    assert settings.detection_history_backend == "postgres"
    assert settings.postgres_url == "postgresql://user:pass@db.example.test:5432/streamguard"


def test_load_settings_rejects_unknown_repository_backend() -> None:
    """Unknown repository backends should fail before the API starts."""
    with pytest.raises(ValueError, match="ALERT_REPOSITORY_BACKEND"):
        load_settings({"ALERT_REPOSITORY_BACKEND": "postgres"})


def test_load_settings_rejects_unknown_detection_history_backend() -> None:
    """Unknown durable history backends should fail before startup."""
    with pytest.raises(ValueError, match="DETECTION_HISTORY_BACKEND"):
        load_settings({"DETECTION_HISTORY_BACKEND": "redis"})


def test_load_settings_rejects_non_positive_numbers() -> None:
    """Retention and TTL settings must be positive integers."""
    with pytest.raises(ValueError, match="RECENT_ALERT_LIMIT"):
        load_settings({"RECENT_ALERT_LIMIT": "0"})

    with pytest.raises(ValueError, match="ALERT_TTL_SECONDS"):
        load_settings({"ALERT_TTL_SECONDS": "0"})

    with pytest.raises(ValueError, match="PROCESSED_EVENT_TTL_SECONDS"):
        load_settings({"PROCESSED_EVENT_TTL_SECONDS": "0"})

    with pytest.raises(ValueError, match="PRODUCER_EVENTS_PER_SECOND"):
        load_settings({"PRODUCER_EVENTS_PER_SECOND": "0"})
