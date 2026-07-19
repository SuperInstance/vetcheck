"""
Drift module — output drift detection over time (weight monitoring).

Like weighing a dog at every visit, this compares recent model
outputs against an established baseline to detect statistically
significant drift.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

try:
    from statistics import mean, pstdev

    _HAS_STATS = True
except ImportError:
    _HAS_STATS = False


@dataclass
class DriftReport:
    """
    Weight check results — drift report for a model.

    Like a vet's weight log, tracking whether the model's
    outputs have shifted from the baseline.
    """
    model_id: str
    baseline_mean: float
    recent_mean: float
    drift_score: float
    threshold: float
    is_significant: bool
    trend: str  # "stable", "increasing", "decreasing"
    timestamp: float = field(default_factory=time.time)
    sample_size: int = 0

    def summary(self) -> str:
        icon = "✅" if not self.is_significant else "⚖️"
        return (
            f"{icon} Weight Check for {self.model_id}\n"
            f"   Baseline: {self.baseline_mean:.4f}\n"
            f"   Recent:   {self.recent_mean:.4f}\n"
            f"   Drift:    {self.drift_score:.4f} (threshold: {self.threshold:.4f})\n"
            f"   Trend:    {self.trend}\n"
            f"   Verdict:  {'SIGNIFICANT DRIFT' if self.is_significant else 'Within normal range'}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "baseline_mean": self.baseline_mean,
            "recent_mean": self.recent_mean,
            "drift_score": self.drift_score,
            "threshold": self.threshold,
            "is_significant": self.is_significant,
            "trend": self.trend,
            "timestamp": self.timestamp,
            "sample_size": self.sample_size,
        }


def _extract_metric(output: dict[str, Any], key: str = "score") -> float:
    """Extract a numeric metric from an output dict."""
    if key in output:
        return float(output[key])
    # Try common alternatives
    for k in ("value", "metric", "confidence", "loss", "accuracy"):
        if k in output:
            return float(output[k])
    return 0.0


def check_weight_drift(
    model_id: str,
    baseline: list[dict[str, Any]],
    recent: list[dict[str, Any]],
    metric_key: str = "score",
    threshold: float = 0.05,
) -> DriftReport:
    """
    Compare recent outputs to baseline — the weight check.

    Uses a simple statistical comparison: the absolute difference
    of means relative to the baseline standard deviation, similar
    to a Cohen's d effect size.

    Args:
        model_id: The model being weighed.
        baseline: Historical output samples (the established weight).
        recent: Recent output samples (the current weight).
        metric_key: Key to extract the numeric metric from each sample.
        threshold: Drift score above which drift is "significant".

    Returns:
        DriftReport with the assessment.
    """
    baseline_values = [_extract_metric(o, metric_key) for o in baseline] if baseline else [0.0]
    recent_values = [_extract_metric(o, metric_key) for o in recent] if recent else [0.0]

    b_mean = mean(baseline_values) if _HAS_STATS else sum(baseline_values) / len(baseline_values)
    r_mean = mean(recent_values) if _HAS_STATS else sum(recent_values) / len(recent_values)

    b_std = pstdev(baseline_values) if len(baseline_values) > 1 and _HAS_STATS else 0.0001
    b_std = max(b_std, 1e-6)  # avoid division by zero

    # Calculate mean difference
    mean_diff = abs(r_mean - b_mean)

    # Cohen's d-style drift score
    drift_score = mean_diff / b_std

    # Determine significance: use scaled threshold, but ensure minimum sensible threshold
    # When variance is extremely low, don't be overly sensitive to tiny differences
    # The effective threshold is the max of scaled_threshold and a small absolute value
    min_abs_threshold = 0.01  # Minimum 1% absolute difference for significance
    effective_threshold = max(threshold * b_std, min_abs_threshold)
    is_significant = mean_diff > effective_threshold

    # Trend determination: use effective threshold for stability check
    # A trend is "stable" if the mean difference is small
    if mean_diff < effective_threshold * 0.5:
        trend = "stable"
    elif r_mean > b_mean:
        trend = "increasing"
    else:
        trend = "decreasing"

    return DriftReport(
        model_id=model_id,
        baseline_mean=b_mean,
        recent_mean=r_mean,
        drift_score=drift_score,
        threshold=threshold,
        is_significant=is_significant,
        trend=trend,
        sample_size=len(recent_values),
    )
