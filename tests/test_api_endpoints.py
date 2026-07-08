"""API tests for StreamGuard's health and direct detection endpoints.

These tests exercise FastAPI as an HTTP boundary while still using the same
schema, feature extraction, scoring, and service code as the internal tests.
"""

from fastapi.testclient import TestClient

from apps.api.dependencies import (
    get_alert_repository,
    get_detection_service,
    get_metrics_repository,
    get_processed_event_repository,
)
from apps.api.main import create_app


def api_client() -> TestClient:
    """Create a test client with fresh cached dependencies for isolation."""
    get_detection_service.cache_clear()
    get_alert_repository.cache_clear()
    get_processed_event_repository.cache_clear()
    get_metrics_repository.cache_clear()
    return TestClient(create_app())


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
    client = api_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready_endpoint_reports_baseline_model_ready() -> None:
    """Readiness should describe the current local dependencies honestly."""
    client = api_client()

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
    client = api_client()

    response = client.get("/health/test")

    assert response.status_code == 200
    assert response.json() == {"status": "you hit the test endpoint"}


def test_detection_endpoint_scores_valid_event() -> None:
    """A valid event request should return the service's detection result."""
    client = api_client()

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
    client = api_client()

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
    client = api_client()

    response = client.post(
        "/api/v1/detections",
        json=event_payload(destination_port=70000),
    )

    assert response.status_code == 422


def test_alerts_endpoint_lists_detections_saved_by_api() -> None:
    """The API should expose recent detection results saved by DetectionService."""
    client = api_client()
    detection_response = client.post("/api/v1/detections", json=event_payload())

    response = client.get("/api/v1/alerts")

    assert detection_response.status_code == 200
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    assert alerts[0]["detection_id"] == detection_response.json()["detection_id"]


def test_alerts_endpoint_filters_by_minimum_score() -> None:
    """Recent alerts can be filtered to show only higher-scoring detections."""
    client = api_client()
    client.post("/api/v1/detections", json=event_payload())
    client.post(
        "/api/v1/detections",
        json=event_payload(
            event_id="11111111-1111-1111-1111-111111111111",
            destination_port=22,
            failed_connections=12,
            packet_count=20,
        ),
    )

    response = client.get("/api/v1/alerts?minimum_score=0.7")

    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    assert alerts[0]["is_anomaly"] is True


def test_alert_by_id_endpoint_returns_detection() -> None:
    """A saved detection should be retrievable through the alert detail endpoint."""
    client = api_client()
    detection_response = client.post("/api/v1/detections", json=event_payload())
    detection_id = detection_response.json()["detection_id"]

    response = client.get(f"/api/v1/alerts/{detection_id}")

    assert response.status_code == 200
    assert response.json()["detection_id"] == detection_id


def test_alert_by_id_endpoint_returns_404_for_missing_detection() -> None:
    """Missing alert IDs should produce an HTTP 404 response."""
    client = api_client()

    response = client.get("/api/v1/alerts/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404


def test_detection_endpoint_is_idempotent_for_repeated_event_id() -> None:
    """Posting the same event twice should return the original detection result."""
    client = api_client()

    first_response = client.post("/api/v1/detections", json=event_payload())
    second_response = client.post("/api/v1/detections", json=event_payload())
    alerts_response = client.get("/api/v1/alerts")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["detection_id"] == first_response.json()["detection_id"]
    assert len(alerts_response.json()) == 1


def test_metrics_endpoint_reports_detection_activity() -> None:
    """The metrics endpoint should expose counters from detection activity."""
    client = api_client()

    before_response = client.get("/api/v1/metrics")
    client.post(
        "/api/v1/detections",
        json=event_payload(destination_port=22, failed_connections=12, packet_count=20),
    )
    client.post(
        "/api/v1/detections",
        json=event_payload(destination_port=22, failed_connections=12, packet_count=20),
    )
    after_response = client.get("/api/v1/metrics")

    assert before_response.status_code == 200
    assert before_response.json() == {
        "processed_total": 0,
        "anomalies_total": 0,
        "duplicates_total": 0,
        "invalid_total": 0,
        "failed_total": 0,
    }
    assert after_response.status_code == 200
    assert after_response.json() == {
        "processed_total": 1,
        "anomalies_total": 1,
        "duplicates_total": 1,
        "invalid_total": 0,
        "failed_total": 0,
    }
