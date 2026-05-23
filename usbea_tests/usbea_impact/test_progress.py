"""Unit tests for impact progress arithmetic."""

from __future__ import annotations

import pytest

from utils.progress import (
    ProgressSnapshot,
    compute_progress_pct,
    compute_status,
    snapshot,
)


class TestComputeProgressPct:
    def test_zero_progress(self):
        assert compute_progress_pct(0, 100) == 0.0

    def test_half_progress(self):
        assert compute_progress_pct(50, 100) == 50.0

    def test_full_progress(self):
        assert compute_progress_pct(100, 100) == 100.0

    def test_exceeded_target(self):
        # We allow >100 so callers can see overdelivery.
        assert compute_progress_pct(150, 100) == 150.0

    def test_negative_current_clamped_to_zero(self):
        assert compute_progress_pct(-10, 100) == 0.0

    def test_none_inputs(self):
        assert compute_progress_pct(None, 100) == 0.0
        assert compute_progress_pct(50, None) == 0.0
        assert compute_progress_pct(None, None) == 0.0

    def test_zero_target(self):
        # Cannot measure progress against zero target — return 0.
        assert compute_progress_pct(50, 0) == 0.0
        assert compute_progress_pct(50, -1) == 0.0


class TestComputeStatus:
    def test_not_started(self):
        assert compute_status(0.0) == "not_started"
        assert compute_status(0.0, time_pct=50.0) == "not_started"

    def test_achieved(self):
        assert compute_status(100.0) == "achieved"
        assert compute_status(150.0) == "achieved"

    def test_on_track_no_time_known(self):
        assert compute_status(10.0) == "on_track"

    def test_on_track_with_time(self):
        # Progress within 10pp of time_pct → on track.
        assert compute_status(45.0, time_pct=50.0) == "on_track"
        assert compute_status(50.0, time_pct=50.0) == "on_track"
        assert compute_status(70.0, time_pct=50.0) == "on_track"

    def test_behind(self):
        # 10-25pp behind time → "behind".
        assert compute_status(30.0, time_pct=50.0) == "behind"
        assert compute_status(25.0, time_pct=50.0) == "behind"

    def test_at_risk(self):
        # >25pp behind time → at_risk.
        assert compute_status(10.0, time_pct=50.0) == "at_risk"

    def test_threshold_boundary(self):
        # Right at 100 → achieved (inclusive boundary).
        assert compute_status(99.99) == "on_track"
        assert compute_status(100.0) == "achieved"


class TestSnapshot:
    def test_snapshot_returns_dataclass(self):
        s = snapshot(50, 100)
        assert isinstance(s, ProgressSnapshot)

    def test_on_track_flag_alignment(self):
        s = snapshot(50, 100, time_pct=50.0)
        assert s.status == "on_track"
        assert s.on_track is True

    def test_achieved_marks_on_track(self):
        s = snapshot(120, 100)
        assert s.status == "achieved"
        assert s.on_track is True

    def test_at_risk_marks_off_track(self):
        s = snapshot(10, 100, time_pct=80.0)
        assert s.status == "at_risk"
        assert s.on_track is False
