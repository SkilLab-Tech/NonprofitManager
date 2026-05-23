"""Pure-Python progress arithmetic for indicators."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressSnapshot:
    """Outcome of progress computation for one indicator."""

    progress_pct: float          # 0.0 .. 100.0 (or beyond if exceeded target)
    on_track: bool                # heuristic: progress_pct >= time_pct - 10
    status: str                  # 'not_started' | 'on_track' | 'behind' | 'at_risk' | 'achieved'


def compute_progress_pct(current: float | None, target: float | None) -> float:
    """Return progress as a percentage 0..100+.

    Handles edge cases:
    - target <= 0 → return 0 (we can't measure progress against non-positive target)
    - current is None → return 0
    """
    if current is None or target is None or target <= 0:
        return 0.0
    return max(0.0, (current / target) * 100.0)


def compute_status(
    progress_pct: float,
    time_pct: float | None = None,
    achieved_threshold: float = 100.0,
) -> str:
    """Bucketize progress vs time-elapsed into a status label.

    - progress_pct == 0: not_started
    - progress_pct >= achieved_threshold: achieved
    - if time_pct is None (no end date known): on_track if any progress
    - if progress_pct >= time_pct - 10: on_track
    - if progress_pct >= time_pct - 25: behind
    - else: at_risk
    """
    if progress_pct <= 0:
        return "not_started"
    if progress_pct >= achieved_threshold:
        return "achieved"
    if time_pct is None:
        return "on_track"
    if progress_pct >= time_pct - 10:
        return "on_track"
    if progress_pct >= time_pct - 25:
        return "behind"
    return "at_risk"


def snapshot(current: float | None, target: float | None, time_pct: float | None = None) -> ProgressSnapshot:
    """Convenience: compute both progress_pct and status in one call."""
    pct = compute_progress_pct(current, target)
    status = compute_status(pct, time_pct)
    on_track = status in ("on_track", "achieved")
    return ProgressSnapshot(progress_pct=pct, on_track=on_track, status=status)
