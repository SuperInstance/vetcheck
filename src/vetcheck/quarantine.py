"""
Quarantine module — isolation and release for sick models.

When a model fails a critical exam, it gets quarantined.
Traffic is routed elsewhere until it passes a clean physical
and is explicitly released.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QuarantineState(str, Enum):
    """State of a model in the quarantine system."""
    ACTIVE = "active"          # In quarantine
    RELEASED = "released"      # Released back to duty
    NEVER_QUARANTINED = "never_quarantined"


@dataclass
class QuarantineStatus:
    """
    Current quarantine status of a model — like a kennel record.

    Tracks when and why a model was isolated, and whether it's
    been released.
    """
    model_id: str
    state: QuarantineState = QuarantineState.NEVER_QUARANTINED
    quarantined_at: float | None = None
    released_at: float | None = None
    reason: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_quarantined(self) -> bool:
        """Is this model currently in quarantine?"""
        return self.state == QuarantineState.ACTIVE

    @property
    def duration(self) -> float | None:
        """How long has this model been in quarantine (seconds)?"""
        if self.quarantined_at is None:
            return None
        end = self.released_at or time.time()
        return end - self.quarantined_at

    def summary(self) -> str:
        icon = "🔒" if self.is_quarantined else "🟢"
        lines = [f"{icon} Quarantine Status for {self.model_id}"]
        lines.append(f"   State: {self.state.value}")

        if self.quarantined_at:
            lines.append(
                f"   Quarantined: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(self.quarantined_at))}"
            )
            lines.append(f"   Reason: {self.reason}")
            if self.is_quarantined and self.duration is not None:
                lines.append(f"   Duration: {self.duration:.0f}s")

        if self.released_at:
            lines.append(
                f"   Released: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(self.released_at))}"
            )

        if self.history:
            lines.append(f"   History: {len(self.history)} previous event(s)")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "state": self.state.value,
            "quarantined_at": self.quarantined_at,
            "released_at": self.released_at,
            "reason": self.reason,
            "duration": self.duration,
            "history": self.history,
        }


# In-memory registry (shared across VetCheck instances in same process)
_registry: dict[str, QuarantineStatus] = {}


def _get_or_create(model_id: str, registry: dict[str, Any] | None = None) -> QuarantineStatus:
    """Get existing status or create a fresh one."""
    reg = registry if registry is not None else _registry
    if model_id not in reg:
        reg[model_id] = QuarantineStatus(model_id=model_id)
    return reg[model_id]


def quarantine_model(
    model_id: str,
    reason: str,
    registry: dict[str, Any] | None = None,
) -> QuarantineStatus:
    """
    Put a model into quarantine — isolate it from production.

    Records the reason and timestamp. If already quarantined,
    updates the reason but doesn't create a new record.

    Args:
        model_id: The model to quarantine.
        reason: Why it's being quarantined.
        registry: Optional custom registry (for testing/isolation).

    Returns:
        Updated QuarantineStatus.
    """
    status = _get_or_create(model_id, registry)

    now = time.time()

    # Record history if re-quarantining or state changes
    if status.state != QuarantineState.ACTIVE:
        status.history.append({
            "event": "quarantined",
            "timestamp": now,
            "reason": reason,
            "previous_state": status.state.value,
        })

    status.state = QuarantineState.ACTIVE
    status.quarantined_at = now
    status.released_at = None
    status.reason = reason

    return status


def release_model(
    model_id: str,
    registry: dict[str, Any] | None = None,
) -> QuarantineStatus:
    """
    Release a model from quarantine — return it to active duty.

    The model must be in quarantine. Records the release timestamp.

    Args:
        model_id: The model to release.
        registry: Optional custom registry.

    Returns:
        Updated QuarantineStatus.

    Raises:
        ValueError: If the model is not currently quarantined.
    """
    status = _get_or_create(model_id, registry)

    if status.state != QuarantineState.ACTIVE:
        raise ValueError(
            f"Cannot release {model_id}: not in quarantine (state={status.state.value})"
        )

    now = time.time()
    status.history.append({
        "event": "released",
        "timestamp": now,
        "duration": status.duration,
    })

    status.state = QuarantineState.RELEASED
    status.released_at = now

    return status


def get_quarantine_status(
    model_id: str,
    registry: dict[str, Any] | None = None,
) -> QuarantineStatus:
    """
    Check the quarantine status of a model.

    Returns the current status, creating a fresh "never quarantined"
    record if the model has never been seen.
    """
    return _get_or_create(model_id, registry)
