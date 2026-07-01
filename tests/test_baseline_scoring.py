"""Tests for the transparent baseline anomaly scorer.

The baseline scorer is intentionally simple and deterministic. These tests
document what kinds of extracted features should look normal or suspicious
before the project introduces trained ML models.
"""

import pytest

from streamguard.domain import SecurityEvent
from streamguard.features import FEATURE_NAMES, EventFeatureVector, extract_event_features
from streamguard.models import BaselineAnomalyScorer


def event_payload(**overrides: object) -> dict[str, object]:
    """Build a valid event payload and let tests override suspicious fields."""
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


def extract_features_from_payload(**overrides: object) -> EventFeatureVector:
    """Create a feature vector through the real schema and preprocessing path."""
    event = SecurityEvent.model_validate(event_payload(**overrides))
    return extract_event_features(event)


def test_baseline_scores_normal_event_below_threshold() -> None:
    """A boring HTTPS-looking event should not be classified as anomalous."""
    features = extract_features_from_payload()

    result = BaselineAnomalyScorer().score(features)

    assert result.anomaly_score == 0.0
    assert result.is_anomaly is False
    assert result.reasons == ()


def test_baseline_scores_failed_admin_service_activity_as_anomaly() -> None:
    """Repeated failures against SSH should cross the default anomaly threshold."""
    features = extract_features_from_payload(
        destination_port=22,
        failed_connections=12,
        packet_count=20,
    )

    result = BaselineAnomalyScorer().score(features)

    assert result.is_anomaly is True
    assert result.anomaly_score == pytest.approx(0.7)
    assert result.reasons == (
        "many_failed_connections",
        "high_failed_connection_ratio",
        "sensitive_destination_service_with_failures",
    )


def test_baseline_caps_score_at_one() -> None:
    """Many matching rules should never produce a score above the documented range."""
    features = extract_features_from_payload(
        destination_port=3389,
        source_bytes=1_000_000,
        destination_bytes=1_000_000,
        packet_count=10,
        failed_connections=10,
        tcp_flag_count=20,
    )

    result = BaselineAnomalyScorer().score(features)

    assert result.anomaly_score == 1.0
    assert result.is_anomaly is True


def test_baseline_threshold_is_configurable() -> None:
    """Changing the threshold changes classification without changing the score."""
    features = extract_features_from_payload(failed_connections=5, packet_count=10)

    strict_result = BaselineAnomalyScorer(threshold=0.9).score(features)
    relaxed_result = BaselineAnomalyScorer(threshold=0.4).score(features)

    assert strict_result.anomaly_score == relaxed_result.anomaly_score
    assert strict_result.is_anomaly is False
    assert relaxed_result.is_anomaly is True


def test_baseline_rejects_unknown_feature_order() -> None:
    """The scorer should fail loudly if feature extraction contract drift occurs."""
    features = EventFeatureVector(
        names=FEATURE_NAMES[:-1],
        values=(0.0,) * (len(FEATURE_NAMES) - 1),
        version="broken",
    )

    with pytest.raises(ValueError, match="feature contract"):
        BaselineAnomalyScorer().score(features)


def test_baseline_rejects_invalid_threshold() -> None:
    """Threshold validation catches configuration mistakes close to startup."""
    with pytest.raises(ValueError, match="threshold"):
        BaselineAnomalyScorer(threshold=1.5)
