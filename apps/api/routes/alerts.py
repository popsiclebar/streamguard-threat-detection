"""Alert retrieval routes for StreamGuard's API.

The first alert API reads recent detection results from an in-memory repository.
Later, the same route behavior can be backed by Redis without changing the API
contract.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.dependencies import get_alert_repository
from streamguard.domain import DetectionResult
from streamguard.services.repositories import AlertRepository


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[DetectionResult])
def list_alerts(
    alert_repository: Annotated[AlertRepository, Depends(get_alert_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    minimum_score: Annotated[float | None, Query(ge=0)] = None,
) -> list[DetectionResult]:
    """Return recent detection results, newest first."""
    return alert_repository.list_recent(limit=limit, minimum_score=minimum_score)


@router.get("/{detection_id}", response_model=DetectionResult)
def get_alert(
    detection_id: UUID,
    alert_repository: Annotated[AlertRepository, Depends(get_alert_repository)],
) -> DetectionResult:
    """Return one detection result by detection ID."""
    result = alert_repository.get(detection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return result
