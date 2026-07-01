"""Direct detection routes for StreamGuard's API.

The detection endpoint accepts one validated security event and returns the
baseline detection result produced by the shared detection service.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.api.dependencies import get_detection_service
from streamguard.domain import DetectionResult, SecurityEvent
from streamguard.services import DetectionService


router = APIRouter(tags=["detections"])


@router.post("/detections", response_model=DetectionResult)
def detect_event(
    event: SecurityEvent,
    detection_service: Annotated[DetectionService, Depends(get_detection_service)],
) -> DetectionResult:
    """Score one event submitted through the direct detection API."""
    return detection_service.detect(event)
