"""Volunteer ↔ opportunity matching score.

Given an opportunity's required skill set and time window, plus a
volunteer's skill set and availability slots, compute a 0-100 fit score.

Pure Python, no Odoo imports — testable in isolation.

Algorithm:
  score = 60% * skill_overlap_pct + 30% * availability_overlap_pct + 10% * background_check_bonus

- skill_overlap_pct: |req ∩ vol| / |req| * 100 (or 100 if req is empty)
- availability_overlap_pct: 100 if any vol slot intersects opp window;
  partial credit (50) if same weekday but disjoint hours; 0 otherwise
- background_check_bonus: 100 if active+valid, 50 if expired, 0 if missing
  (only when opp.requires_background_check is True; else 100 always)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, time


@dataclass(frozen=True)
class VolunteerSlot:
    """A weekly recurring availability window."""

    weekday: int  # 0=Monday … 6=Sunday
    start: time
    end: time


@dataclass(frozen=True)
class OpportunityWindow:
    """When the opportunity needs help."""

    weekday: int
    start: time
    end: time


@dataclass(frozen=True)
class Volunteer:
    skill_ids: frozenset[int]
    slots: tuple[VolunteerSlot, ...] = ()
    background_check_active: bool = False
    background_check_expired: bool = False


@dataclass(frozen=True)
class Opportunity:
    required_skill_ids: frozenset[int]
    windows: tuple[OpportunityWindow, ...] = ()
    requires_background_check: bool = False


@dataclass(frozen=True)
class MatchScore:
    overall: int            # 0..100
    skill_pct: int
    availability_pct: int
    bg_pct: int
    reasons: tuple[str, ...] = field(default_factory=tuple)


def _skill_overlap_pct(req: frozenset[int], vol: frozenset[int]) -> int:
    if not req:
        return 100  # anyone qualifies
    if not vol:
        return 0
    matched = req & vol
    return round(100 * len(matched) / len(req))


def _availability_overlap_pct(
    vol_slots: tuple[VolunteerSlot, ...],
    opp_windows: tuple[OpportunityWindow, ...],
) -> int:
    if not opp_windows:
        return 100  # no constraint
    if not vol_slots:
        return 0
    best = 0
    for w in opp_windows:
        for s in vol_slots:
            if s.weekday != w.weekday:
                continue
            # Same weekday — check time overlap.
            if s.start < w.end and w.start < s.end:
                return 100
            # Same weekday but disjoint hours: partial credit
            best = max(best, 50)
    return best


def _background_check_pct(volunteer: Volunteer, opportunity: Opportunity) -> int:
    if not opportunity.requires_background_check:
        return 100
    if volunteer.background_check_active and not volunteer.background_check_expired:
        return 100
    if volunteer.background_check_active and volunteer.background_check_expired:
        return 50
    return 0


def score_match(volunteer: Volunteer, opportunity: Opportunity) -> MatchScore:
    """Compute a MatchScore for this pair. Always returns a populated result."""
    skill_pct = _skill_overlap_pct(opportunity.required_skill_ids, volunteer.skill_ids)
    avail_pct = _availability_overlap_pct(volunteer.slots, opportunity.windows)
    bg_pct = _background_check_pct(volunteer, opportunity)

    overall = round(0.6 * skill_pct + 0.3 * avail_pct + 0.1 * bg_pct)
    overall = max(0, min(100, overall))

    reasons: list[str] = []
    if skill_pct == 0:
        reasons.append("no required skills met")
    elif skill_pct < 100:
        reasons.append(f"only {skill_pct}% of required skills covered")
    if avail_pct == 0:
        reasons.append("no overlapping availability")
    elif avail_pct == 50:
        reasons.append("same weekday but disjoint hours")
    if bg_pct == 0:
        reasons.append("background check missing")
    elif bg_pct == 50:
        reasons.append("background check expired")

    return MatchScore(
        overall=overall,
        skill_pct=skill_pct,
        availability_pct=avail_pct,
        bg_pct=bg_pct,
        reasons=tuple(reasons),
    )


def rank_matches(volunteers: list[Volunteer], opportunity: Opportunity) -> list[tuple[int, MatchScore]]:
    """Return [(volunteer_index, score), ...] sorted desc by score.overall."""
    scored = [(i, score_match(v, opportunity)) for i, v in enumerate(volunteers)]
    scored.sort(key=lambda x: x[1].overall, reverse=True)
    return scored


def is_background_check_expiring_soon(
    expiry_date: date | None,
    today: date,
    warn_within_days: int = 30,
) -> bool:
    """Cron helper — True if expiry is within warn_within_days from today."""
    if expiry_date is None:
        return False
    delta = (expiry_date - today).days
    return 0 <= delta <= warn_within_days
