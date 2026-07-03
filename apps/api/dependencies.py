"""Dependency providers used by StreamGuard API routes.

FastAPI dependencies are small functions that supply shared objects to route
handlers. Keeping them here makes route modules easy to test and keeps object
creation separate from request-handling code.
"""

from functools import lru_cache

from streamguard.config import AppSettings, load_settings
from streamguard.infrastructure.memory import (
    InMemoryAlertRepository,
    InMemoryProcessedEventRepository,
)
from streamguard.infrastructure.redis_alerts import RedisAlertRepository
from streamguard.infrastructure.redis_state import RedisProcessedEventRepository
from streamguard.services import DetectionService
from streamguard.services.repositories import AlertRepository, ProcessedEventRepository


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings loaded from environment variables."""
    return load_settings()


@lru_cache
def get_alert_repository() -> AlertRepository:
    """Return the configured alert repository used by the API.

    Memory remains the default for simple local runs. Redis can be enabled with
    `ALERT_REPOSITORY_BACKEND=redis` once the Redis service is running.
    """
    settings = get_settings()
    if settings.alert_repository_backend == "redis":
        return RedisAlertRepository.from_url(
            settings.redis_url,
            max_results=settings.recent_alert_limit,
            ttl_seconds=settings.alert_ttl_seconds,
        )

    return InMemoryAlertRepository(max_results=settings.recent_alert_limit)


@lru_cache
def get_processed_event_repository() -> ProcessedEventRepository:
    """Return the configured processed-event marker repository."""
    settings = get_settings()
    if settings.alert_repository_backend == "redis":
        return RedisProcessedEventRepository.from_url(
            settings.redis_url,
            ttl_seconds=settings.processed_event_ttl_seconds,
        )

    return InMemoryProcessedEventRepository()


@lru_cache
def get_detection_service() -> DetectionService:
    """Return the reusable detection service used by API requests.

    `lru_cache` makes this function behave like a tiny singleton factory: the
    first call creates the service, and later calls reuse the same instance.
    """
    return DetectionService(
        alert_repository=get_alert_repository(),
        processed_event_repository=get_processed_event_repository(),
    )
