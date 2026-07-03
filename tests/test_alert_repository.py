"""Tests for StreamGuard's in-memory alert repository.

The repository stores recent detection results behind the same interface that a
future Redis adapter will implement. These tests document ordering, filtering,
lookup, and retention behavior.
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from streamguard.domain import DetectionResult
from streamguard.infrastructure.memory import InMemoryAlertRepository


def detection_result(
    *,
    detection_id: str,
    anomaly_score: float,
) -> DetectionResult:
    """Build a valid detection result for repository tests."""
    return DetectionResult(
        schema_version="1.0",
        detection_id=UUID(detection_id),
        event_id=UUID("50e7935d-8c80-49ef-9613-a846c88b1220"),
        processed_at=datetime(2026, 6, 22, 8, 30, tzinfo=UTC),
        model_name="baseline_rules",
        model_version="0.1.0",
        feature_version="1.0.0",
        anomaly_score=anomaly_score,
        is_anomaly=anomaly_score >= 0.7,
        threshold=0.7,
        inference_time_ms=1.0,
        device="cpu",
        status="completed",
        error_code=None,
    )


def test_repository_returns_recent_results_newest_first() -> None:
    """Saved results should be listed with the newest result first."""
    repository = InMemoryAlertRepository()
    first = detection_result(
        detection_id="00000000-0000-0000-0000-000000000001",
        anomaly_score=0.2,
    )
    second = detection_result(
        detection_id="00000000-0000-0000-0000-000000000002",
        anomaly_score=0.8,
    )

    repository.save(first)
    repository.save(second)

    assert repository.list_recent() == [second, first]


def test_repository_filters_by_minimum_score() -> None:
    """Minimum score filtering supports recent-alert investigation views."""
    repository = InMemoryAlertRepository()
    repository.save(
        detection_result(
            detection_id="00000000-0000-0000-0000-000000000001",
            anomaly_score=0.2,
        )
    )
    anomaly = detection_result(
        detection_id="00000000-0000-0000-0000-000000000002",
        anomaly_score=0.8,
    )
    repository.save(anomaly)

    assert repository.list_recent(minimum_score=0.7) == [anomaly]


def test_repository_gets_result_by_detection_id() -> None:
    """A stored detection result should be retrievable by its stable ID."""
    repository = InMemoryAlertRepository()
    result = detection_result(
        detection_id="00000000-0000-0000-0000-000000000001",
        anomaly_score=0.8,
    )
    repository.save(result)

    assert repository.get(result.detection_id) == result


def test_repository_enforces_retention_limit() -> None:
    """The repository should trim old results beyond its configured capacity."""
    repository = InMemoryAlertRepository(max_results=1)
    first = detection_result(
        detection_id="00000000-0000-0000-0000-000000000001",
        anomaly_score=0.2,
    )
    second = detection_result(
        detection_id="00000000-0000-0000-0000-000000000002",
        anomaly_score=0.8,
    )

    repository.save(first)
    repository.save(second)

    assert repository.list_recent() == [second]
    assert repository.get(first.detection_id) is None


def test_repository_rejects_invalid_limits() -> None:
    """Invalid repository limits should fail clearly close to configuration time."""
    with pytest.raises(ValueError, match="max_results"):
        InMemoryAlertRepository(max_results=0)

    repository = InMemoryAlertRepository()
    with pytest.raises(ValueError, match="limit"):
        repository.list_recent(limit=0)
