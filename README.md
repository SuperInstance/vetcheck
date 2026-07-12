# Vetcheck: Model Health Monitoring as Veterinary Care

> Working dogs need regular checkups. So do models.

Vetcheck treats model health monitoring like veterinary care — because in the SuperInstance working-dog paradigm, every model is a working animal that needs ongoing supervision to stay fit for duty.

## The Analogy

| Veterinary Care | Vetcheck |
|---|---|
| Physical exam | Regression test suite (`physical_exam`) |
| Weight monitoring | Output drift detection (`weight_check`) |
| Quarantine | Auto-isolation on critical health breach (`quarantine`) |
| Health certificate | Clearance for production deployment (`health_certificate`) |

## Quick Start

```bash
pip install vetcheck
```

```python
from vetcheck import VetCheck

vet = VetCheck(model_id="llama-3-70b")

# Run a full physical — executes regression suite
report = vet.physical_exam()
print(report.summary())

# Check for weight drift — compares recent outputs to baseline
drift = vet.weight_check(window=100)

# Quarantine a sick model
if report.critical_failures > 0:
    vet.quarantine(reason="Critical regression detected")

# Issue a clean bill of health
cert = vet.health_certificate()
```

## Core Exams

### Physical Exam (`physical_exam`)

Runs the full regression test suite against the model. Each test is like checking a vital sign:

- **Temperature** — does the model still handle edge cases?
- **Heart rate** — are response times within bounds?
- **Blood pressure** — does it handle load without degradation?
- **Reflexes** — do function-calling and structured outputs still work?

### Weight Check (`weight_check`)

Monitors output distribution drift over time, like weighing a dog at every visit:

- Compares recent output embeddings/distributions to a baseline
- Flags statistically significant drift
- Tracks trends across checkups

### Quarantine (`quarantine` / `release`)

When a model fails critically, it gets isolated:

- Model is marked `quarantined` — traffic routed elsewhere
- Alerts are triggered
- Stays isolated until a clean physical exam passes
- `release()` returns the model to active duty

### Health Certificate (`health_certificate`)

A signed attestation that a model is fit for production:

- Verifies last physical exam passed
- Confirms no active quarantine
- Checks weight is stable
- Returns a certificate with expiry

## Architecture

```
src/vetcheck/
├── __init__.py      # VetCheck orchestrator class
├── exam.py           # Regression test runner (physical exams)
├── drift.py          # Output drift detection (weight monitoring)
└── quarantine.py     # Quarantine and release system
```

## License

MIT
