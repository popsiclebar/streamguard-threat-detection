"""PostgreSQL infrastructure adapters for durable StreamGuard history.

PostgreSQL is used for long-lived records that should survive application and
Redis restarts. The first adapter stores detection results; later adapters can
store raw events, dead letters, model metadata, and audit records.
"""

from streamguard.infrastructure.postgres.detections import PostgresDetectionHistoryRepository

__all__ = ["PostgresDetectionHistoryRepository"]
