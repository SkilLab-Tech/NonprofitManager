"""Pure-Python state-machine helpers for the grant application pipeline.

Isolated from Odoo so the transition rules are unit-testable. The Odoo model
delegates to ``validate_transition`` before any state change.
"""

from __future__ import annotations

from dataclasses import dataclass

# Pipeline states with the legal transitions out of each.
# A state mapping to () is terminal (no outgoing transitions).
STATE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "prospect": ("researching", "withdrawn"),
    "researching": ("drafting", "withdrawn"),
    "drafting": ("researching", "submitted", "withdrawn"),
    "submitted": ("under_review", "withdrawn"),
    "under_review": ("awarded", "declined", "withdrawn"),
    "awarded": (),       # terminal — handed off to usbea.grant
    "declined": (),      # terminal
    "withdrawn": (),     # terminal
}

PIPELINE_STATES = tuple(STATE_TRANSITIONS.keys())
TERMINAL_STATES = tuple(s for s, outs in STATE_TRANSITIONS.items() if not outs)
ACTIVE_STATES = tuple(s for s in PIPELINE_STATES if s not in TERMINAL_STATES)


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of an attempted state transition."""

    ok: bool
    reason: str = ""


def validate_transition(from_state: str, to_state: str) -> TransitionResult:
    """Return ok=True if from_state → to_state is a legal pipeline transition.

    Same-state transitions (no-ops) return ok=False with a descriptive reason,
    so callers can either short-circuit or surface a clear error.
    """
    if from_state == to_state:
        return TransitionResult(
            ok=False, reason=f"already in state '{from_state}'",
        )
    if from_state not in STATE_TRANSITIONS:
        return TransitionResult(ok=False, reason=f"unknown source state '{from_state}'")
    if to_state not in STATE_TRANSITIONS:
        return TransitionResult(ok=False, reason=f"unknown target state '{to_state}'")
    allowed = STATE_TRANSITIONS[from_state]
    if to_state in allowed:
        return TransitionResult(ok=True)
    return TransitionResult(
        ok=False,
        reason=(
            f"illegal transition '{from_state}' → '{to_state}'. "
            f"Allowed: {allowed or '(terminal)'}."
        ),
    )


def is_terminal(state: str) -> bool:
    """True if the state has no outgoing transitions."""
    return state in TERMINAL_STATES


def is_active(state: str) -> bool:
    """True if the state is in the active pipeline (not terminal)."""
    return state in ACTIVE_STATES
