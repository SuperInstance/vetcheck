# Vetcheck: Model Health Monitoring as Veterinary Care

> Working dogs need regular checkups. So do models.

[![Python](https://img.shields.io/python/required-version-toml?toml=pyproject.toml)](https://python.org)
[![License](https://img.shields.io/github/license/SuperInstance/vetcheck)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)

A model that passed regression tests six months ago might silently degrade over time — distribution drift, fine-tuning side effects, dependency changes. Vetcheck treats model health monitoring like veterinary care because in the Working Animal Architecture paradigm, every model is a working animal that needs ongoing supervision to stay fit for duty. Physical exams catch regressions. Weight monitoring catches output drift. Quarantine isolates failures before they reach production.

## What It Does

Vetcheck provides three core exams and two lifecycle operations. The **physical exam** runs a full regression test suite against the model, checking vital signs: does it still handle edge cases (temperature), are response times within bounds (heart rate), does it handle load without degradation (blood pressure), do function-calling and structured outputs still work (reflexes)? The result is an `ExamResult` with pass/fail per test and an overall `HealthStatus`.

The **weight check** monitors output distribution drift over time. Just as a vet weighs a dog at every visit and flags concerning changes, Vetcheck compares recent output embeddings or distributions to a baseline and flags statistically significant drift. Trends are tracked across checkups — a gradual 5% drift over a month is different from a sudden 20% shift overnight.

When a model fails critically, **quarantine** auto-isolates it: traffic is routed elsewhere, alerts fire, and the model stays isolated until a clean physical exam passes. The **health certificate** is a signed attestation that a model is fit for production — it verifies the last physical exam passed, confirms no active quarantine, checks weight stability, and returns a certificate with an expiry date.

## Install

```bash
pip install vetcheck
```

For development:

```bash
git clone https://github.com/SuperInstance/vetcheck.git
cd vetcheck
pip install -e ".[dev]"
```

## Quick Start

```python
from vetcheck import VetCheck

vet = VetCheck(model_id="llama-3-70b")

# Run a full physical — executes regression suite
report = vet.physical_exam()
print(report.summary())
# ════════════════════════════════════════════
#   PHYSICAL EXAM: llama-3-70b
#   Overall: HEALTHY
#   Tests: 47 passed, 3 failed, 0 skipped
# ════════════════════════════════════════════

# Check for weight drift — compares recent outputs to baseline
drift = vet.weight_check(window=100)
if drift.significant:
    print(f"⚠ Drift detected: {drift.magnitude:.1%} from baseline")
    print(f"  Trend: {drift.trend}")  # "increasing", "decreasing", "stable"
else:
    print("✓ Weight stable")

# Quarantine a sick model
if report.critical_failures > 0:
    vet.quarantine(reason="Critical regression detected")
    print("Model quarantined — traffic routed to backup")

# ... after fixes applied ...

# Run physical again to verify recovery
recovery = vet.physical_exam()
if recovery.passed:
    vet.release()
    print("Model returned to active duty")

# Issue a clean bill of health
cert = vet.health_certificate()
print(f"Health certificate issued, expires: {cert.expires_at}")
print(f"Valid: {cert.is_valid()}")
```

## Architecture

```
src/vetcheck/
├── __init__.py        # VetCheck orchestrator + HealthCertificate
├── exam.py             # Regression test runner (physical exams)
│   ├── run_physical_exam()
│   ├── ExamResult
│   └── TestCase / TestSuite
├── drift.py            # Output drift detection (weight monitoring)
│   ├── check_weight_drift()
│   ├── DriftReport
│   └── BaselineDistribution
└── quarantine.py       # Quarantine and release system
    ├── quarantine_model()
    ├── release_model()
    ├── get_quarantine_status()
    └── QuarantineStatus
```

### Health States

```
HEALTHY ──────▶ UNDER_OBSERVATION ──────▶ QUARANTINED
   ▲                    │                       │
   │                    │                       │
   └────────────────────┘                       │
   release() (clean exam)                       │
   ▲                                            │
   └────────────────────────────────────────────┘
                  release() (clean exam)
```

## API Reference

### `VetCheck`

```python
class VetCheck:
    def __init__(self, model_id: str, baseline_dir: str = "./baselines")

    # Exams
    def physical_exam(self, suite: str = "default") -> ExamResult
    def weight_check(self, window: int = 100) -> DriftReport

    # Lifecycle
    def quarantine(self, reason: str) -> QuarantineStatus
    def release(self) -> bool
    @property
    def is_quarantined(self) -> bool

    # Certification
    def health_certificate(self, validity_days: int = 7) -> HealthCertificate
    @property
    def health_status(self) -> HealthStatus
```

### Result Types

```python
@dataclass
class ExamResult:
    model_id: str
    passed: bool
    overall_status: HealthStatus
    tests_passed: int
    tests_failed: int
    critical_failures: int
    duration_seconds: float
    details: list[TestResult]

@dataclass
class DriftReport:
    model_id: str
    significant: bool        # statistically significant drift
    magnitude: float         # 0.0-1.0
    trend: str               # "increasing", "decreasing", "stable"
    window: int              # samples compared
    p_value: float           # statistical test result

@dataclass
class HealthCertificate:
    model_id: str
    status: HealthStatus
    issued_at: float
    expires_at: float
    last_exam_passed: bool
    weight_stable: bool
    quarantine_active: bool
    notes: str

    def is_valid(self, now: float | None = None) -> bool
    def to_dict(self) -> dict
```

### `HealthStatus`

```python
class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNDER_OBSERVATION = "under_observation"
    QUARANTINED = "quarantined"
    CRITICAL = "critical"
```

## The Analogy

| Veterinary Care | Vetcheck |
|-----------------|----------|
| Physical exam | Regression test suite (`physical_exam`) |
| Weight monitoring | Output drift detection (`weight_check`) |
| Quarantine | Auto-isolation on critical health breach |
| Health certificate | Clearance for production deployment |
| Vaccination schedule | Periodic exam scheduling |
| Breed-specific screening | Model-specific test suites |

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v

# Test exam runner
pytest tests/test_exam.py -v

# Test drift detection
pytest tests/test_drift.py -v

# Test quarantine lifecycle
pytest tests/test_quarantine.py -v
```

## Philosophy

In animal husbandry, preventative medicine is cheaper than emergency treatment. The same applies to AI systems: catching a regression before it reaches production is dramatically cheaper than responding to an outage. Vetcheck brings the discipline of veterinary preventative care to model operations — regular checkups, early detection, isolation of sick individuals, and structured health certificates before deployment.

This is part of [Working Animal Architecture](https://github.com/SuperInstance/AI-Writings) — specifically the health monitoring layer that keeps the kennel (flux registry) populated with animals fit for duty. A model with an expired health certificate shouldn't be in production, just as a working dog that hasn't seen a vet in a year shouldn't be herding sheep.

## Ecosystem

| Repo | Role |
|------|------|
| **[vetcheck](https://github.com/SuperInstance/vetcheck)** | **This repo** — health monitoring |
| [shepherds-console](https://github.com/SuperInstance/shepherds-console) | Dashboard (displays vetcheck health status) |
| [breed-registry](https://github.com/SuperInstance/breed-registry) | Breed selection (uses health certificates) |
| [lineage-tracker](https://github.com/SuperInstance/lineage-tracker) | Lineage (health data enriches lineage records) |
| [baton](https://github.com/SuperInstance/baton) | Generational handoff (health informs sunset decisions) |



## Integration Patterns

### With Breed Registry: Pre-Deployment Health Check

```python
from vetcheck import VetCheck
from breed_registry import select_breed

# Select the best model for a task
recommended = select_breed("code_generation")
print(f"Recommended: {recommended.recommended}")

# Before deploying, verify it's healthy
vet = VetCheck(model_id=recommended.recommended)
cert = vet.health_certificate(validity_days=14)

if cert.is_valid():
    print(f"✓ {recommended.recommended} is certified healthy — deploy")
else:
    print(f"✗ {recommended.recommended} failed health check")
    print(f"  Falling back to alternatives...")
    for alt in recommended.alternatives:
        alt_vet = VetCheck(model_id=alt.breed)
        alt_cert = alt_vet.health_certificate()
        if alt_cert.is_valid():
            print(f"  ✓ {alt.breed} is healthy (score: {alt.score:.1f})")
            break
```

### With Lineage Tracker: Regression Source Detection

```python
from vetcheck import VetCheck
from lineage_tracker import LineageTracker

# Model failed its physical exam
vet = VetCheck(model_id="prod-model-v7")
report = vet.physical_exam()

if not report.passed:
    # Check if this is a known weakness in the lineage
    tracker = LineageTracker("lineage.json")
    lineage = tracker.get_lineage("prod-model-v7")

    print("Failed exam. Checking lineage for inherited weaknesses:")
    for gen in lineage:
        model = gen.model
        failed_areas = [t.name for t in report.details if not t.passed]
        for area in failed_areas:
            trait_key = area.lower().replace(" ", "_")
            if model.traits and trait_key in model.traits:
                print(f"  Gen {gen.generation} {model.name}: {trait_key}={model.traits[trait_key]}")

    # If the weakness is inherited, quarantine and recommend retraining
    vet.quarantine(reason=f"Inherited regression: {failed_areas}")
```

### Continuous Monitoring with Scheduled Exams

```python
from vetcheck import VetCheck
import schedule  # pip install schedule
import time

vet = VetCheck(model_id="prod-model-v7", baseline_dir="./baselines")

# Daily weight check (lightweight — compares output distributions)
schedule.every().day.at("06:00").do(lambda: vet.weight_check(window=500))

# Weekly physical (full regression suite)
schedule.every().monday.at("02:00").do(lambda: vet.physical_exam())

# Monthly health certificate renewal
schedule.every(30).days.do(lambda: vet.health_certificate(validity_days=7))

# Auto-quarantine on critical failure
def full_checkup():
    report = vet.physical_exam()
    if report.critical_failures > 0:
        vet.quarantine(reason=f"Auto-quarantine: {report.critical_failures} critical failures")
        # Alert the team
        print(f"🚨 {vet.model_id} QUARANTINED — {report.critical_failures} critical failures")
    return report

schedule.every().day.at("12:00").do(full_checkup)

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

### Fleet Health Dashboard

```python
from vetcheck import VetCheck
from breed_registry import BreedMatcher

matcher = BreedMatcher()
fleet = ["gpt-4", "claude-3", "llama-3", "glm", "qwen"]

print("FLEET HEALTH REPORT")
print("=" * 60)

for model_id in fleet:
    vet = VetCheck(model_id=model_id)
    status = vet.health_status
    quarantined = "🔒 QUARANTINED" if vet.is_quarantined else "🟢 ACTIVE"

    # Quick weight check
    drift = vet.weight_check(window=100)
    drift_indicator = "📉" if drift.significant else "✓"

    print(f"  {model_id:15s} {status.value:20s} {quarantined} drift:{drift_indicator}")

    # Recommend breed-specific action
    aptitude = matcher.assess(model_id, "reasoning")
    if status.value == "quarantined":
        alternatives = matcher.select("reasoning").alternatives[:2]
        print(f"    → Failover to: {[a.breed for a in alternatives]}")
```

## Monitoring Philosophy

The veterinary metaphor runs deeper than naming. In real animal husbandry:

- **Preventative care is cheaper than emergency treatment.** A daily weight check catches drift before it becomes a regression. A weekly physical catches regressions before they reach users.
- **Quarantine is not punishment.** It's protection — for the model (no traffic to handle while recovering) and for the system (no degraded output reaching users). The quarantine is lifted the moment a clean physical passes.
- **Health certificates expire.** A model that was healthy last month might not be healthy today. Certificate expiry isn't bureaucracy — it's the acknowledgment that model health is dynamic, not static.
- **Breed-specific screening matters.** A Thoroughbred (GPT-4) needs different tests than a Mustang (Llama-3). Custom test suites per breed catch breed-specific failure modes that generic tests miss.
- **The vet's authority overrides the registry.** A model with the best breed score should not be in production if its health certificate has expired. The registry says what's best on paper; the vet says what's fit for duty right now.

## License

MIT — see [LICENSE](LICENSE).
