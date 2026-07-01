"""Dependency providers used by StreamGuard API routes.

FastAPI dependencies are small functions that supply shared objects to route
handlers. Keeping them here makes route modules easy to test and keeps object
creation separate from request-handling code.
"""

from functools import lru_cache

from streamguard.services import DetectionService


@lru_cache
def get_detection_service() -> DetectionService:
    """Return the reusable detection service used by API requests.

    `lru_cache` makes this function behave like a tiny singleton factory: the
    first call creates the service, and later calls reuse the same instance.
    """
    return DetectionService()
