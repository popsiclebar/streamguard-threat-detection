"""Feature extraction utilities for StreamGuard's detection pipeline.

Feature code converts validated domain events into stable numeric values that
simple scorers and future machine-learning models can consume.
"""

from streamguard.features.feature_contract import FEATURE_NAMES, FEATURE_VERSION, EventFeatureVector
from streamguard.features.preprocessing import extract_event_features

__all__ = [
    "FEATURE_NAMES",
    "FEATURE_VERSION",
    "EventFeatureVector",
    "extract_event_features",
]
