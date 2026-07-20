"""
Vetcheck: Model health monitoring as veterinary care.

In the working dog paradigm, dogs need regular checkups.
This does the same for models.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from vetcheck.exam import ExamResult, run_physical_exam
from vetcheck.drift import DriftReport, check_weight_drift
from vetcheck.quarantine import QuarantineStatus, quarantine_model, release_model, get_quarantine_status

__version__ = "0.1.0"
__all__ = [
    "VetCheck",
    "ExamResult",
    "DriftReport",
    "QuarantineStatus",
    "HealthStatus",
    "HealthCertificate",
]


class HealthStatus(str, Enum):
    """Overall health status of a model — like a vet's diagnosis."""
    HEALTHY = "healthy"
    UNDER_OBSERVATION = "under_observation"
    QUARANTINED = "quarantined"
    CRITICAL = "critical"


@dataclass
class HealthCertificate:
    """A clean bill of health — like a health certificate from the vet."""
    model_id: str
    status: HealthStatus
    issued_at: float
    expires_at: float
    last_exam_passed: bool
    weight_stable: bool
    quarantine_active: bool
    notes: str = ""

    def is_valid(self, now: float | None = None) -> bool:
        """Check if this certificate is still within its expiry."""
        now = now or time.time()
        return now <= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "status": self.status.value,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "last_exam_passed": self.last_exam_passed,
            "weight_stable": self.weight_stable,
            "quarantine_active": self.quarantine_active,
            "notes": self.notes,
        }

    def __repr__(self) -> str:
        return (
            f"HealthCertificate(model={self.model_id!r}, status={self.status.value}, "
            f"valid_until={time.strftime('%Y-%m-%d %H:%M', time.gmtime(self.expires_at))} UTC)"
        )


class VetCheck:
    """
    The veterinarian for your models.

    Usage:
        vet = VetCheck(model_id="llama-3-70b")
        report = vet.physical_exam()
        drift = vet.weight_check()
    """

    def __init__(
        self,
        model_id: str,
        baseline: list[dict[str, Any]] | None = None,
        registry: dict[str, Any] | None = None,
        exam_suite: list[dict[str, Any]] | None = None,
        certificate_ttl: float = 86400.0,  # 24 hours
    ):
        self.model_id = model_id
        self._baseline = baseline or []
        self._registry = registry or {}
        self._exam_suite = exam_suite or _default_exam_suite()
        self._certificate_ttl = certificate_ttl
        self._last_exam: ExamResult | None = None
        self._last_drift: DriftReport | None = None

    def physical_exam(self, suite: list[dict[str, Any]] | None = None) -> ExamResult:
        """
        Run a full physical exam — the regression test suite.

        Each test is a vital sign check. Returns a full ExamResult
        with pass/fail per test and an overall health assessment.
        """
        suite = suite or self._exam_suite
        result = run_physical_exam(self.model_id, suite)
        self._last_exam = result

        # Auto-quarantine on critical failures
        if result.critical_failures > 0:
            self.quarantine(reason=f"Critical failures in physical exam: {result.critical_failures}")

        return result

    def weight_check(
        self,
        recent_outputs: list[dict[str, Any]] | None = None,
        window: int = 100,
        threshold: float = 0.05,
    ) -> DriftReport:
        """
        Check for weight drift — output distribution shift over time.

        Like weighing a dog at every visit, this compares recent
        outputs against the baseline to detect statistically
        significant drift.
        """
        if recent_outputs is None:
            raise ValueError("recent_outputs is required — cannot compare baseline against itself")
        recent = recent_outputs
        baseline = self._baseline[:window] if len(self._baseline) > window else self._baseline
        report = check_weight_drift(self.model_id, baseline, recent, threshold=threshold)
        self._last_drift = report
        return report

    def quarantine(self, reason: str) -> QuarantineStatus:
        """
        Quarantine a sick model — isolate it from production traffic.

        The model stays in quarantine until a clean physical exam
        passes and release() is explicitly called.
        """
        return quarantine_model(self.model_id, reason, registry=self._registry)

    def release(self) -> QuarantineStatus:
        """
        Release a model from quarantine back to active duty.

        Requires a recent, passing physical exam.
        """
        if self._last_exam and not self._last_exam.passed:
            raise ValueError(
                f"Cannot release {self.model_id}: last physical exam did not pass. "
                "Run physical_exam() and ensure it passes before releasing."
            )
        return release_model(self.model_id, registry=self._registry)

    @property
    def status(self) -> HealthStatus:
        """Current health status of the model."""
        q = get_quarantine_status(self.model_id, registry=self._registry)
        if q.is_quarantined:
            return HealthStatus.QUARANTINED

        if self._last_exam and not self._last_exam.passed:
            return HealthStatus.CRITICAL

        if self._last_drift and self._last_drift.is_significant:
            return HealthStatus.UNDER_OBSERVATION

        return HealthStatus.HEALTHY

    def health_certificate(self, force: bool = False) -> HealthCertificate:
        """
        Issue a health certificate — a clean bill of health.

        Verifies:
        - Last physical exam passed
        - No active quarantine
        - Weight (drift) is stable

        Raises ValueError if the model is not healthy unless force=True.
        """
        last_passed = self._last_exam is not None and self._last_exam.passed
        weight_stable = self._last_drift is None or not self._last_drift.is_significant
        q = get_quarantine_status(self.model_id, registry=self._registry)
        quarantined = q.is_quarantined

        if not force:
            issues = []
            if not last_passed:
                issues.append("last physical exam did not pass (or no exam on record)")
            if quarantined:
                issues.append("model is under quarantine")
            if not weight_stable:
                issues.append("weight drift detected")
            if issues:
                raise ValueError(
                    f"Cannot issue health certificate for {self.model_id}: "
                    + "; ".join(issues)
                )

        now = time.time()
        return HealthCertificate(
            model_id=self.model_id,
            status=self.status,
            issued_at=now,
            expires_at=now + self._certificate_ttl,
            last_exam_passed=last_passed,
            weight_stable=weight_stable,
            quarantine_active=quarantined,
            notes="Issued by Vetcheck" if last_passed and not quarantined and not (self._last_drift and self._last_drift.is_significant) else "Force-issued",
        )


def _default_exam_suite() -> list[dict[str, Any]]:
    """Default vital signs checked during a physical exam."""
    return [
        {"name": "temperature", "description": "Edge case handling", "critical": True},
        {"name": "heart_rate", "description": "Response latency within bounds", "critical": True},
        {"name": "blood_pressure", "description": "Load handling without degradation", "critical": False},
        {"name": "reflexes", "description": "Function calling and structured output", "critical": True},
        {"name": "vision", "description": "Context window utilization", "critical": False},
    ]
