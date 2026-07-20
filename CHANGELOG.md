# Changelog

All notable changes to `vetcheck` are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.1.3 — 2026-07-20

### Fixed
- **Documented CRITICAL state reachability.** The `CRITICAL` health state is now provably reachable through proper weight degradation chains. Previously the documentation implied `CRITICAL` was a theoretical state that couldn't be arrived at through normal monitoring rules. Added explicit documentation of the transition path and updated docstrings to reflect actual model behavior.

## v0.1.2 — 2026-07-20

### Fixed
- **`weight_check` now requires `recent_outputs`.** The weight monitoring function silently succeeded when `recent_outputs` was empty, producing a false sense of health for untracked models. Now raises `ValueError` if no output history is available.
- **`is_valid` had an off-by-one error.** The validity check for health records used an exclusive upper bound where inclusive was intended, causing edge-case records (exactly at the boundary) to be incorrectly flagged as invalid. Bounds corrected to inclusive.

## v0.1.1 — 2026-07-19

### Fixed
- **Audit fixes from code review.** Physical exam input validation strengthened; drift thresholds now handle edge cases robustly. Added regression tests for boundary conditions in health state transitions.

## v0.1.0 — 2026-07-18

### Initial Release
- Package: vetcheck — model health monitoring as veterinary care
- Threshold alerts, weight checks, physical exam validation
- Tests passing
