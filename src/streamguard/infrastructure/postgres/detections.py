"""PostgreSQL-backed detection history repository for StreamGuard.

This adapter stores completed detection results as durable rows. A few important
fields are kept as normal columns for filtering and sorting, while the full
Pydantic result is stored as JSONB so the exact API/worker output can be
reconstructed later.
"""

from __future__ import annotations

from json import dumps
from typing import Any, Protocol
from uuid import UUID

from streamguard.domain import DetectionResult


CREATE_DETECTION_RESULTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS detection_results (
    detection_id uuid PRIMARY KEY,
    event_id uuid NOT NULL,
    processed_at timestamptz NOT NULL,
    anomaly_score double precision NOT NULL,
    is_anomaly boolean NOT NULL,
    payload jsonb NOT NULL
)
"""

UPSERT_DETECTION_RESULT_SQL = """
INSERT INTO detection_results (
    detection_id,
    event_id,
    processed_at,
    anomaly_score,
    is_anomaly,
    payload
) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
ON CONFLICT (detection_id) DO UPDATE SET
    event_id = EXCLUDED.event_id,
    processed_at = EXCLUDED.processed_at,
    anomaly_score = EXCLUDED.anomaly_score,
    is_anomaly = EXCLUDED.is_anomaly,
    payload = EXCLUDED.payload
"""

GET_DETECTION_RESULT_SQL = """
SELECT payload
FROM detection_results
WHERE detection_id = %s
"""

LIST_DETECTION_RESULTS_SQL = """
SELECT payload
FROM detection_results
ORDER BY processed_at DESC
LIMIT %s
"""

LIST_DETECTION_RESULTS_WITH_SCORE_SQL = """
SELECT payload
FROM detection_results
WHERE anomaly_score >= %s
ORDER BY processed_at DESC
LIMIT %s
"""


class PostgresCursor(Protocol):
    """Small subset of cursor behavior used by the repository."""

    def fetchone(self) -> tuple[Any, ...] | None:
        """Fetch one row from a SELECT query."""

    def fetchall(self) -> list[tuple[Any, ...]]:
        """Fetch all rows from a SELECT query."""


class PostgresConnection(Protocol):
    """Small subset of psycopg connection behavior used by the repository."""

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> PostgresCursor:
        """Execute one SQL statement and return a cursor-like object."""


class PostgresDetectionHistoryRepository:
    """Store and query durable detection-result history in PostgreSQL."""

    def __init__(self, connection: PostgresConnection, *, ensure_schema: bool = True) -> None:
        """Create the repository with an existing PostgreSQL connection."""
        self._connection = connection
        if ensure_schema:
            self.ensure_schema()

    @classmethod
    def from_url(cls, postgres_url: str) -> "PostgresDetectionHistoryRepository":
        """Create a repository from a PostgreSQL connection URL."""
        import psycopg

        connection = psycopg.connect(postgres_url, autocommit=True)
        return cls(connection)

    def ensure_schema(self) -> None:
        """Create the detection history table if it does not already exist."""
        self._connection.execute(CREATE_DETECTION_RESULTS_TABLE_SQL)
        self._commit_if_supported()

    def save_detection(self, result: DetectionResult) -> None:
        """Persist one detection result as queryable columns plus JSONB payload."""
        self._connection.execute(
            UPSERT_DETECTION_RESULT_SQL,
            (
                str(result.detection_id),
                str(result.event_id),
                result.processed_at,
                result.anomaly_score,
                result.is_anomaly,
                dumps(result.model_dump(mode="json")),
            ),
        )
        self._commit_if_supported()

    def get_detection(self, detection_id: UUID) -> DetectionResult | None:
        """Return one persisted detection result by detection ID."""
        cursor = self._connection.execute(GET_DETECTION_RESULT_SQL, (str(detection_id),))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._result_from_payload(row[0])

    def list_detections(
        self,
        *,
        limit: int = 100,
        minimum_score: float | None = None,
    ) -> list[DetectionResult]:
        """Return persisted detection results, newest first."""
        if limit < 1:
            raise ValueError("limit must be at least 1")

        if minimum_score is None:
            cursor = self._connection.execute(LIST_DETECTION_RESULTS_SQL, (limit,))
        else:
            cursor = self._connection.execute(
                LIST_DETECTION_RESULTS_WITH_SCORE_SQL,
                (minimum_score, limit),
            )
        return [self._result_from_payload(row[0]) for row in cursor.fetchall()]

    def _commit_if_supported(self) -> None:
        """Commit changes when the injected connection exposes manual commits."""
        commit = getattr(self._connection, "commit", None)
        if commit is not None:
            commit()

    @staticmethod
    def _result_from_payload(payload: object) -> DetectionResult:
        """Build a DetectionResult from PostgreSQL JSONB or fake-test payloads."""
        if isinstance(payload, str):
            return DetectionResult.model_validate_json(payload)
        return DetectionResult.model_validate(payload)
