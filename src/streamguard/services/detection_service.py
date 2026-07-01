"""Detection use-case service for StreamGuard.

The service coordinates the first complete local detection flow: take a
validated security event, extract stable features, score those features with the
baseline scorer, and return a versioned detection result.
"""

from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from streamguard.domain import DetectionResult, SecurityEvent
from streamguard.features import extract_event_features
from streamguard.models import BaselineAnomalyScorer


BASELINE_MODEL_NAME = "baseline_rules"
BASELINE_MODEL_VERSION = "0.1.0"


class DetectionService:
    """Coordinate feature extraction, scoring, and detection-result creation.

    FastAPI routes and future Kafka consumers should call this service instead
    of reimplementing detection workflow steps themselves. That keeps one
    consistent path for direct API detection and streaming detection.
    """

    def __init__(self, scorer: BaselineAnomalyScorer | None = None) -> None:
        """Create a detection service with an optional injected scorer.

        Dependency injection means the caller can provide a different scorer in
        tests or future configuration while the service keeps the same workflow.
        """
        self._scorer = scorer or BaselineAnomalyScorer()

    def detect(self, event: SecurityEvent) -> DetectionResult:
        """Run the baseline detection workflow for one validated security event."""
        started_at = perf_counter()

        features = extract_event_features(event)
        score = self._scorer.score(features)

        inference_time_ms = (perf_counter() - started_at) * 1000
        return DetectionResult(
            schema_version="1.0",
            detection_id=uuid4(),
            event_id=event.event_id,
            processed_at=datetime.now(UTC),
            model_name=BASELINE_MODEL_NAME,
            model_version=BASELINE_MODEL_VERSION,
            feature_version=features.version,
            anomaly_score=score.anomaly_score,
            is_anomaly=score.is_anomaly,
            threshold=score.threshold,
            inference_time_ms=inference_time_ms,
            device="cpu",
            status="completed",
            error_code=None,
        )
