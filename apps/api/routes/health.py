"""Health-check routes for StreamGuard's API.

Health endpoints let local developers and future container orchestration check
whether the API process is alive and whether the minimal detection path is ready.
"""

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a simple compatibility health check for local development."""
    return {"status": "alive"}


@router.get("/health/live")
def live() -> dict[str, str]:
    """Report that the FastAPI process is running."""
    return {"status": "alive"}


@router.get("/health/ready")
def ready() -> dict[str, object]:
    """Report readiness for the current Milestone 1 local detection path."""
    return {
        "status": "ready",
        "components": {
            "api": "healthy",
            "model": "baseline_ready",
        },
    }


@router.get("/health/test")
def test() -> dict[str, str]:
    """Return a lightweight learning endpoint used while testing reload behavior."""
    return {"status": "you hit the test endpoint"}
