"""FastAPI application entry point for StreamGuard.

This module builds the HTTP application used by `uvicorn apps.api.main:app`.
Routes stay thin and call StreamGuard services so the same business logic can be
reused later by streaming workers.
"""

from fastapi import FastAPI

from apps.api.routes import alerts, detections, health, metrics


def create_app() -> FastAPI:
    """Create and configure the StreamGuard FastAPI application."""
    app = FastAPI(
        title="StreamGuard",
        description="Local-first threat-detection API for learning AI engineering.",
        version="0.1.0",
    )
    app.include_router(health.router)
    app.include_router(alerts.router, prefix="/api/v1")
    app.include_router(detections.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")
    return app


app = create_app()
