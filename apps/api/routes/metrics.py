"""Operational metrics routes for StreamGuard's API.

The metrics endpoint exposes simple counters for local debugging and learning.
It is not a full observability stack, but it gives the project a clean place to
report processing activity.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.api.dependencies import get_metrics_repository
from streamguard.services import MetricsRepository, MetricsSnapshot


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsSnapshot)
def get_metrics(
    metrics_repository: Annotated[MetricsRepository, Depends(get_metrics_repository)],
) -> MetricsSnapshot:
    """Return current operational counters."""
    return metrics_repository.snapshot()
