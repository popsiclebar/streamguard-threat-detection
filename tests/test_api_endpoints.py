"""API tests for StreamGuard's health and direct detection endpoints.

These tests exercise FastAPI as an HTTP boundary while still using the same
schema, feature extraction, scoring, and service code as the internal tests.
"""

from fastapi.testclient import TestClient

from apps.api.main import create_app


def event_payload(**overrides: object) -> dict[str, object]:
    """Build a valid API request payload and allow individual tests to vary fields."""
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "event_id": "50e7935d-8c80-49ef-9613-a846c88b1220",
        "timestamp": "2026-06-22T08:30:00Z",
        "source_ip": "10.10.1.12",
        "destination_ip": "172.16.0.20",
        "source_port": 52311,
        "destination_port": 443,
        "protocol": "TCP",
        "duration_ms": 192.4,
        "source_bytes": 1450,
        "destination_bytes": 8300,
        "packet_count": 41,
        "failed_connections": 0,
        "tcp_flag_count": 4,
    }
    payload.update(overrides)
    return payload


def test_health_endpoint_reports_alive() -> None:
    """The simple health endpoint should be available for local smoke checks."""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready_endpoint_reports_baseline_model_ready() -> None:
    """Readiness should describe the current local dependencies honestly."""
    client = TestClient(create_app())

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "components": {
            "api": "healthy",
            "model": "baseline_ready",
        },
    }


def test_learning_health_test_endpoint_reports_message() -> None:
    """The temporary learning endpoint should confirm reload experiments work."""
    client = TestClient(create_app())

    response = client.get("/health/test")

    assert response.status_code == 200
    assert response.json() == {"status": "you hit the test endpoint"}


def test_detection_endpoint_scores_valid_event() -> None:
    """A valid event request should return the service's detection result."""
    client = TestClient(create_app())

    response = client.post("/api/v1/detections", json=event_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["event_id"] == "50e7935d-8c80-49ef-9613-a846c88b1220"
    assert body["model_name"] == "baseline_rules"
    assert body["device"] == "cpu"
    assert body["status"] == "completed"
    assert body["is_anomaly"] is False


def test_detection_endpoint_scores_suspicious_event_as_anomaly() -> None:
    """Suspicious input should cross the baseline threshold through the API path."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/detections",
        json=event_payload(destination_port=22, failed_connections=12, packet_count=20),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_anomaly"] is True
    assert body["anomaly_score"] == 0.7
    assert body["threshold"] == 0.7


def test_detection_endpoint_rejects_invalid_event() -> None:
    """FastAPI should use the Pydantic schema to reject malformed requests."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/detections",
        json=event_payload(destination_port=70000),
    )

    assert response.status_code == 422
