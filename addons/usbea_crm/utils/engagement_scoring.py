"""Pure-Python engagement scoring — no Odoo dependencies, fully testable.

Engagement is a function of recency, frequency, and weighted signal types
(donation > meeting > event > email_open). Score is clamped to [0, 100].

The score is computed deterministically from a list of event dicts. The
Odoo model passes the events; the algorithm is here in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import exp

# Half-life in days for the recency decay. An event from 30 days ago counts
# half as much as one from today.
RECENCY_HALF_LIFE_DAYS = 30

# Per-event-type weights — sum of unbounded contributions before decay.
EVENT_TYPE_WEIGHTS = {
    "donation": 20,
    "donation_recurring": 25,
    "meeting": 15,
    "event_attendance": 10,
    "email_reply": 8,
    "email_open": 2,
    "manual": 10,
    "p2p_share": 12,
    "no_show": -8,
}


@dataclass(frozen=True)
class EngagementEvent:
    """A single engagement signal."""

    event_type: str
    when: date
    score_delta_override: float | None = None  # if set, overrides the weight


def compute_engagement_score(
    events: list[EngagementEvent],
    today: date,
    horizon_days: int = 365,
) -> int:
    """Score a partner's engagement based on their events.

    Returns an integer 0-100. ``events`` outside the ``horizon_days`` window
    are ignored. Newer events dominate via exponential decay tied to the
    recency half-life. If no events contribute (empty list, all out of
    horizon, all in the future, or all unrecognized types), returns 0.
    """
    if not events:
        return 0
    cutoff = today - timedelta(days=horizon_days)
    raw = 0.0
    contributed = False
    for ev in events:
        if ev.when is None or ev.when < cutoff or ev.when > today:
            continue
        weight = (
            ev.score_delta_override
            if ev.score_delta_override is not None
            else EVENT_TYPE_WEIGHTS.get(ev.event_type, 0)
        )
        if weight == 0:
            continue
        age = (today - ev.when).days
        decay = 0.5 ** (age / RECENCY_HALF_LIFE_DAYS)
        raw += weight * decay
        contributed = True
    if not contributed:
        return 0
    # Smooth the raw signal into [0, 100] via a logistic curve. Calibrated so
    # ~3 recent donations + meetings put a donor at ~70-80.
    score = 100.0 / (1.0 + exp(-(raw - 25) / 12))
    return max(0, min(100, round(score)))
