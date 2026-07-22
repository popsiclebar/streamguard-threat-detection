"""Tests for the PostgreSQL durable detection history repository.

These tests use a fake connection instead of a real PostgreSQL server. That
keeps the unit suite fast while still documenting the SQL adapter behavior.
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from streamguard.domain import DetectionResult
from streamguard.infrastructure.postgres.detections import (
    CREATE_DETECTION_RESULTS_TABLE_SQL,
    GET_DETECTION_RESULT_SQL,
    LIST_DETECTION_RESULTS_SQL,
    LIST_DETECTION_RESULTS_WITH_SCORE_SQL,
    UPSERT_DETECTION_RESULT_SQL,
    PostgresDetectionHistoryRepository,
)


class FakeCursor:
    """Minimal cursor for fake PostgreSQL SELECT results."""

    def __init__(self, rows: list[tuple[object, ...]] | None = None) -> None:
        """Create a cursor with preloaded rows."""
        self._rows = rows or []

    def fetchone(self) -> tuple[object, ...] | None:
        """Return the first fake row when one exists."""
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        """Return all fake rows."""
        return self._rows


class FakePostgresConnection:
    """Small fake connection that records executed SQL and stores payload rows."""

    def __init__(self) -> None:
        """Create an empty fake PostgreSQL connection."""
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []
        self.payloads_by_detection_id: dict[str, object] = {}
        self.commits = 0

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> FakeCursor:
        """Record SQL and simulate the repository's small query set."""
        normalized_query = query.strip()
        self.calls.append((normalized_query, params))

        if normalized_query == UPSERT_DETECTION_RESULT_SQL.strip() and params is not None:
            self.payloads_by_detection_id[str(params[0])] = params[5]
            return FakeCursor()

        if normalized_query == GET_DETECTION_RESULT_SQL.strip() and params is not None:
            payload = self.payloads_by_detection_id.get(str(params[0]))
            return FakeCursor([] if payload is None else [(payload,)])

        if normalized_query in {
            LIST_DETECTION_RESULTS_SQL.strip(),
            LIST_DETECTION_RESULTS_WITH_SCORE_SQL.strip(),
        }:
            return FakeCursor([(payload,) for payload in self.payloads_by_detection_id.values()])

        return FakeCursor()

    def commit(self) -> None:
        """Count commits requested by the repository."""
        self.commits += 1


def detection_result(**overrides: object) -> DetectionResult:
    """Build a valid detection result for PostgreSQL repository tests."""
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "detection_id": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
        "event_id": "50e7935d-8c80-49ef-9613-a846c88b1220",
        "processed_at": datetime(2026, 6, 22, 8, 30, tzinfo=UTC),
        "model_name": "baseline_rules",
        "model_version": "0.1.0",
        "feature_version": "1.0.0",
        "anomaly_score": 0.7,
        "is_anomaly": True,
        "threshold": 0.7,
        "inference_time_ms": 1.5,
        "device": "cpu",
        "status": "completed",
        "error_code": None,
    }
    payload.update(overrides)
    return DetectionResult.model_validate(payload)


def test_postgres_repository_ensures_schema_on_startup() -> None:
    """Repository construction should create the table when requested."""
    fake_connection = FakePostgresConnection()

    PostgresDetectionHistoryRepository(fake_connection)

    assert fake_connection.calls[0][0] == CREATE_DETECTION_RESULTS_TABLE_SQL.strip()
    assert fake_connection.commits == 1


def test_postgres_repository_saves_and_gets_detection_payload() -> None:
    """Saved detection results should round-trip through JSON payload storage."""
    fake_connection = FakePostgresConnection()
    repository = PostgresDetectionHistoryRepository(fake_connection, ensure_schema=False)
    result = detection_result()

    repository.save_detection(result)

    assert fake_connection.calls[0][0] == UPSERT_DETECTION_RESULT_SQL.strip()
    assert repository.get_detection(result.detection_id) == result


def test_postgres_repository_lists_detections_with_optional_score_filter() -> None:
    """List queries should support newest-first limits and score filtering."""
    fake_connection = FakePostgresConnection()
    repository = PostgresDetectionHistoryRepository(fake_connection, ensure_schema=False)
    result = detection_result()
    repository.save_detection(result)

    assert repository.list_detections(limit=10) == [result]
    assert repository.list_detections(limit=10, minimum_score=0.7) == [result]
    assert fake_connection.calls[-2] == (LIST_DETECTION_RESULTS_SQL.strip(), (10,))
    assert fake_connection.calls[-1] == (
        LIST_DETECTION_RESULTS_WITH_SCORE_SQL.strip(),
        (0.7, 10),
    )


def test_postgres_repository_validates_limit_and_missing_results() -> None:
    """Invalid list limits should fail and missing rows should return None."""
    repository = PostgresDetectionHistoryRepository(
        FakePostgresConnection(),
        ensure_schema=False,
    )

    assert repository.get_detection(UUID("00000000-0000-0000-0000-000000000001")) is None
    with pytest.raises(ValueError, match="limit"):
        repository.list_detections(limit=0)
