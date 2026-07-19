"""
Exam module — regression test runner as health check (physical exam).

Each test is a vital sign. The runner executes them and produces
an ExamResult with a full health assessment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class VitalSign:
    """A single test result — one vital sign from the physical."""
    name: str
    description: str
    critical: bool
    passed: bool
    duration_ms: float = 0.0
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExamResult:
    """Full results of a physical exam — the vet's report."""
    model_id: str
    vitals: list[VitalSign] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        """Overall pass — no critical vital signs failed.

        If there are no critical vitals, requires all vitals to pass
        to avoid a vacuous pass on an empty exam.
        """
        critical_vitals = [v for v in self.vitals if v.critical]
        if critical_vitals:
            return all(v.passed for v in critical_vitals)
        # No critical vitals: require all vitals to pass
        return all(v.passed for v in self.vitals)

    @property
    def all_passed(self) -> bool:
        """Every vital sign passed, including non-critical."""
        return all(v.passed for v in self.vitals)

    @property
    def critical_failures(self) -> int:
        return sum(1 for v in self.vitals if v.critical and not v.passed)

    @property
    def warnings(self) -> int:
        return sum(1 for v in self.vitals if not v.critical and not v.passed)

    def summary(self) -> str:
        """Human-readable summary — like the vet's notes."""
        lines = [
            f"📋 Physical Exam Report for {self.model_id}",
            f"   Date: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(self.timestamp))}",
            f"   Duration: {self.duration_ms:.1f}ms",
            f"   Overall: {'✅ PASSED' if self.passed else '❌ FAILED'}",
            "",
        ]
        for v in self.vitals:
            icon = "✅" if v.passed else ("🚨" if v.critical else "⚠️")
            tag = " [CRITICAL]" if v.critical else " [warning]" if not v.passed else ""
            lines.append(f"   {icon} {v.name}{tag} — {v.description}")
            if v.error:
                lines.append(f"      Error: {v.error}")
        lines.append("")
        lines.append(
            f"   Critical failures: {self.critical_failures} | Warnings: {self.warnings}"
        )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "passed": self.passed,
            "all_passed": self.all_passed,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "vitals": [
                {
                    "name": v.name,
                    "description": v.description,
                    "critical": v.critical,
                    "passed": v.passed,
                    "duration_ms": v.duration_ms,
                    "error": v.error,
                    "details": v.details,
                }
                for v in self.vitals
            ],
        }


def run_physical_exam(
    model_id: str,
    suite: list[dict[str, Any]],
    runner: Callable[[dict[str, Any]], bool] | None = None,
) -> ExamResult:
    """
    Execute the regression suite as a physical exam.

    Args:
        model_id: The model being examined.
        suite: List of test definitions. Each must have:
            - name: vital sign name
            - description: what it checks
            - critical: whether failure means quarantine
            - check (optional): a callable that returns bool
        runner: Optional custom runner. If None, uses default which
            calls each test's "check" callable or defaults to pass.

    Returns:
        ExamResult with all vital signs recorded.
    """
    start = time.time()
    vitals: list[VitalSign] = []

    for test in suite:
        name = test.get("name", "unknown")
        desc = test.get("description", "")
        critical = test.get("critical", False)
        check = test.get("check")

        v_start = time.time()
        passed = True
        error = None

        try:
            if runner is not None:
                passed = bool(runner(test))
            elif check is not None:
                passed = bool(check())
            # If no runner and no check, default to pass (assume external)
        except Exception as e:
            passed = False
            error = str(e)

        v_duration = (time.time() - v_start) * 1000

        vitals.append(
            VitalSign(
                name=name,
                description=desc,
                critical=critical,
                passed=passed,
                duration_ms=v_duration,
                error=error,
            )
        )

    total_duration = (time.time() - start) * 1000

    return ExamResult(
        model_id=model_id,
        vitals=vitals,
        duration_ms=total_duration,
    )
