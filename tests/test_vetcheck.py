"""
Tests for Vetcheck — model health monitoring as veterinary care.
"""

import pytest
import time

from vetcheck import VetCheck, HealthStatus, HealthCertificate
from vetcheck.exam import run_physical_exam, ExamResult, VitalSign
from vetcheck.drift import check_weight_drift, DriftReport
from vetcheck.quarantine import (
    quarantine_model,
    release_model,
    get_quarantine_status,
    QuarantineState,
    QuarantineStatus,
)


# ─── Physical Exam Tests ────────────────────────────────────────────


class TestPhysicalExam:
    def test_all_pass(self):
        """A suite where all critical vitals pass → overall pass."""
        suite = [
            {"name": "temperature", "description": "Edge cases", "critical": True, "check": lambda: True},
            {"name": "heart_rate", "description": "Latency", "critical": True, "check": lambda: True},
            {"name": "reflexes", "description": "Function calling", "critical": True, "check": lambda: True},
        ]
        result = run_physical_exam("test-model", suite)
        assert result.passed
        assert result.all_passed
        assert result.critical_failures == 0
        assert result.warnings == 0

    def test_critical_failure(self):
        """A critical vital sign failing → overall fail."""
        suite = [
            {"name": "temperature", "description": "Edge cases", "critical": True, "check": lambda: True},
            {"name": "heart_rate", "description": "Latency", "critical": True, "check": lambda: False},
        ]
        result = run_physical_exam("test-model", suite)
        assert not result.passed
        assert result.critical_failures == 1

    def test_non_critical_warning(self):
        """Non-critical failures produce warnings but don't fail the exam."""
        suite = [
            {"name": "temperature", "description": "Edge cases", "critical": True, "check": lambda: True},
            {"name": "vision", "description": "Context window", "critical": False, "check": lambda: False},
        ]
        result = run_physical_exam("test-model", suite)
        assert result.passed  # Critical vitals passed
        assert not result.all_passed  # But not everything passed
        assert result.warnings == 1
        assert result.critical_failures == 0

    def test_exception_handling(self):
        """Exceptions in checks are caught and recorded as failures."""
        def bomb():
            raise RuntimeError("Vital sign machine broke")

        suite = [
            {"name": "temperature", "description": "Edge cases", "critical": True, "check": bomb},
        ]
        result = run_physical_exam("test-model", suite)
        assert not result.passed
        vital = result.vitals[0]
        assert not vital.passed
        assert "Vital sign machine broke" in (vital.error or "")

    def test_summary_output(self):
        """Summary produces human-readable text."""
        suite = [
            {"name": "temperature", "description": "Edge cases", "critical": True, "check": lambda: True},
        ]
        result = run_physical_exam("test-model", suite)
        summary = result.summary()
        assert "Physical Exam Report" in summary
        assert "PASSED" in summary

    def test_no_check_defaults_pass(self):
        """Tests without a check function default to pass."""
        suite = [{"name": "resting", "description": "Passive check", "critical": True}]
        result = run_physical_exam("test-model", suite)
        assert result.passed


# ─── Drift Detection Tests ──────────────────────────────────────────


class TestWeightCheck:
    def test_no_drift(self):
        """Identical distributions → no significant drift."""
        baseline = [{"score": 0.5} for _ in range(50)]
        recent = [{"score": 0.5} for _ in range(50)]
        report = check_weight_drift("model", baseline, recent)
        assert not report.is_significant
        assert report.trend == "stable"
        assert report.drift_score < 0.05

    def test_significant_drift(self):
        """Large shift → significant drift detected."""
        baseline = [{"score": 0.5 + i * 0.001} for i in range(50)]
        recent = [{"score": 0.9 + i * 0.001} for i in range(50)]
        report = check_weight_drift("model", baseline, recent, threshold=0.5)
        assert report.is_significant
        assert report.trend == "increasing"

    def test_decreasing_trend(self):
        """Scores going down → decreasing trend."""
        baseline = [{"score": 0.9} for _ in range(30)]
        recent = [{"score": 0.2} for _ in range(30)]
        report = check_weight_drift("model", baseline, recent, threshold=0.5)
        assert report.is_significant
        assert report.trend == "decreasing"

    def test_summary_output(self):
        """Summary is human-readable."""
        baseline = [{"score": 0.5} for _ in range(10)]
        recent = [{"score": 0.5} for _ in range(10)]
        report = check_weight_drift("model", baseline, recent)
        assert "Weight Check" in report.summary()

    def test_empty_inputs(self):
        """Empty inputs don't crash — return defaults."""
        report = check_weight_drift("model", [], [])
        assert report.model_id == "model"


# ─── Quarantine Tests ───────────────────────────────────────────────


class TestQuarantine:
    def test_quarantine_and_release(self):
        """Full quarantine → release cycle."""
        reg = {}
        status = quarantine_model("sick-model", "Failed vitals", registry=reg)
        assert status.is_quarantined
        assert status.state == QuarantineState.ACTIVE
        assert status.reason == "Failed vitals"

        released = release_model("sick-model", registry=reg)
        assert not released.is_quarantined
        assert released.state == QuarantineState.RELEASED
        assert released.released_at is not None

    def test_release_not_quarantined_fails(self):
        """Can't release a model that isn't quarantined."""
        reg = {}
        with pytest.raises(ValueError, match="not in quarantine"):
            release_model("healthy-model", registry=reg)

    def test_quarantine_history(self):
        """Quarantine events are recorded in history."""
        reg = {}
        quarantine_model("model", "Sick", registry=reg)
        release_model("model", registry=reg)
        quarantine_model("model", "Sick again", registry=reg)

        status = get_quarantine_status("model", registry=reg)
        assert len(status.history) >= 2
        assert status.is_quarantined

    def test_never_quarantined(self):
        """Fresh model has never_quarantined status."""
        status = get_quarantine_status("fresh-model")
        assert status.state == QuarantineState.NEVER_QUARANTINED
        assert not status.is_quarantined
        assert status.duration is None


# ─── VetCheck Integration Tests ─────────────────────────────────────


class TestVetCheck:
    def _make_vet(self, **kwargs):
        """Create a VetCheck with a passing default suite."""
        defaults = {
            "model_id": "test-model",
            "baseline": [{"score": 0.5} for _ in range(20)],
            "exam_suite": [
                {"name": "temperature", "description": "Edge cases", "critical": True, "check": lambda: True},
                {"name": "heart_rate", "description": "Latency", "critical": True, "check": lambda: True},
            ],
        }
        defaults.update(kwargs)
        return VetCheck(**defaults)

    def test_healthy_model(self):
        """A model that passes everything is healthy."""
        vet = self._make_vet()
        exam = vet.physical_exam()
        assert exam.passed
        assert vet.status == HealthStatus.HEALTHY

    def test_auto_quarantine_on_critical(self):
        """Critical failures auto-trigger quarantine."""
        vet = self._make_vet(
            exam_suite=[
                {"name": "heart", "description": "Critical", "critical": True, "check": lambda: False},
            ]
        )
        vet.physical_exam()
        assert vet.status == HealthStatus.QUARANTINED

    def test_health_certificate_when_healthy(self):
        """Healthy model gets a valid certificate."""
        vet = self._make_vet()
        vet.physical_exam()
        cert = vet.health_certificate()
        assert cert.last_exam_passed
        assert cert.status == HealthStatus.HEALTHY
        assert cert.is_valid()
        assert "force" not in cert.notes.lower()

    def test_health_certificate_denied_when_sick(self):
        """Sick model can't get a certificate without force."""
        vet = self._make_vet(
            exam_suite=[
                {"name": "heart", "description": "Critical", "critical": True, "check": lambda: False},
            ]
        )
        vet.physical_exam()
        with pytest.raises(ValueError, match="Cannot issue health certificate"):
            vet.health_certificate()

    def test_health_certificate_forced(self):
        """Force-issued certificate works even for sick models."""
        vet = self._make_vet(
            exam_suite=[
                {"name": "heart", "description": "Critical", "critical": True, "check": lambda: False},
            ]
        )
        vet.physical_exam()
        cert = vet.health_certificate(force=True)
        assert cert is not None

    def test_release_requires_passing_exam(self):
        """Can't release without a passing exam."""
        vet = self._make_vet(
            exam_suite=[
                {"name": "heart", "description": "Critical", "critical": True, "check": lambda: False},
            ]
        )
        vet.physical_exam()  # Fails and auto-quarantines
        with pytest.raises(ValueError, match="last physical exam did not pass"):
            vet.release()

    def test_drift_detection(self):
        """Weight check detects drift."""
        baseline = [{"score": 0.5} for _ in range(30)]
        vet = VetCheck(model_id="drifty", baseline=baseline)
        recent = [{"score": 0.9} for _ in range(30)]
        drift = vet.weight_check(recent_outputs=recent, threshold=0.5)
        assert drift.is_significant

    def test_under_observation_from_drift(self):
        """Significant drift → under observation status."""
        baseline = [{"score": 0.5} for _ in range(30)]
        vet = VetCheck(model_id="drifty", baseline=baseline)
        vet.physical_exam()  # Pass
        recent = [{"score": 0.95} for _ in range(30)]
        vet.weight_check(recent_outputs=recent, threshold=0.5)
        assert vet.status == HealthStatus.UNDER_OBSERVATION
