"""Detection model interfaces and implementations for StreamGuard.

The first implementation is a transparent baseline scorer. Later milestones can
add scikit-learn and PyTorch models behind the same application-level concepts.
"""

from streamguard.models.baseline import BaselineAnomalyScore, BaselineAnomalyScorer

__all__ = ["BaselineAnomalyScore", "BaselineAnomalyScorer"]
