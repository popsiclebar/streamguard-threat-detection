"""Transparent baseline anomaly scoring for StreamGuard.

This module intentionally avoids claiming to be a trained machine-learning
model. It provides a readable heuristic scorer so the project can exercise the
full detection flow before adding scikit-learn or PyTorch.
"""

from dataclasses import dataclass

from streamguard.features import FEATURE_NAMES, EventFeatureVector


DEFAULT_BASELINE_THRESHOLD = 0.7


@dataclass(frozen=True)
class BaselineAnomalyScore:
    """Result returned by the rule-based baseline scorer.

    The score follows one application convention: higher means more suspicious.
    `reasons` keeps the baseline explainable, which is useful while learning and
    while demoing the system before real model artifacts exist.
    """

    anomaly_score: float
    is_anomaly: bool
    threshold: float
    reasons: tuple[str, ...]


class BaselineAnomalyScorer:
    """Rule-based scorer that turns extracted features into an anomaly score.

    Each rule contributes a small amount to the final score. This is not meant
    to detect real attacks reliably; it is a software-engineering baseline that
    makes suspicious-looking test events score higher than normal-looking ones.
    """

    def __init__(self, threshold: float = DEFAULT_BASELINE_THRESHOLD) -> None:
        """Create a scorer with the threshold used to classify anomalies."""
        if threshold < 0 or threshold > 1:
            raise ValueError("threshold must be between 0 and 1")
        self.threshold = threshold

    def score(self, features: EventFeatureVector) -> BaselineAnomalyScore:
        """Score one event feature vector using transparent heuristic rules."""
        if features.names != FEATURE_NAMES:
            raise ValueError("feature vector does not match StreamGuard feature contract")

        feature_map = features.as_dict()
        score = 0.0
        reasons: list[str] = []

        score = self._add_if(
            score=score,
            reasons=reasons,
            condition=feature_map["failed_connections"] >= 5,
            contribution=0.25,
            reason="many_failed_connections",
        )
        score = self._add_if(
            score=score,
            reasons=reasons,
            condition=feature_map["failed_connection_ratio"] >= 0.25,
            contribution=0.25,
            reason="high_failed_connection_ratio",
        )
        score = self._add_if(
            score=score,
            reasons=reasons,
            condition=feature_map["bytes_per_packet"] >= 10_000,
            contribution=0.2,
            reason="large_bytes_per_packet",
        )
        score = self._add_if(
            score=score,
            reasons=reasons,
            condition=feature_map["tcp_flag_count"] >= 10,
            contribution=0.15,
            reason="many_tcp_flags",
        )
        score = self._add_if(
            score=score,
            reasons=reasons,
            condition=self._targets_sensitive_service(feature_map),
            contribution=0.2,
            reason="sensitive_destination_service_with_failures",
        )

        normalized_score = min(score, 1.0)
        return BaselineAnomalyScore(
            anomaly_score=normalized_score,
            is_anomaly=normalized_score >= self.threshold,
            threshold=self.threshold,
            reasons=tuple(reasons),
        )

    @staticmethod
    def _add_if(
        *,
        score: float,
        reasons: list[str],
        condition: bool,
        contribution: float,
        reason: str,
    ) -> float:
        """Add a score contribution and reason when one heuristic rule matches."""
        if not condition:
            return score

        reasons.append(reason)
        return score + contribution

    @staticmethod
    def _targets_sensitive_service(feature_map: dict[str, float]) -> bool:
        """Identify failures against common admin or file-sharing service ports."""
        sensitive_ports = {22.0, 445.0, 3389.0}
        return (
            feature_map["destination_port"] in sensitive_ports
            and feature_map["failed_connections"] > 0
        )
