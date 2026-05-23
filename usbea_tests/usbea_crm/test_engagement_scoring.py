"""Unit tests for the engagement scoring algorithm."""

from __future__ import annotations

from datetime import date, timedelta

from utils.engagement_scoring import (
    EVENT_TYPE_WEIGHTS,
    EngagementEvent,
    compute_engagement_score,
)


TODAY = date(2026, 5, 23)


def evs(*specs):
    """Helper: build EngagementEvents from (event_type, days_ago) tuples."""
    return [
        EngagementEvent(event_type=t, when=TODAY - timedelta(days=d))
        for (t, d) in specs
    ]


class TestComputeEngagementScore:
    def test_no_events_returns_zero(self):
        assert compute_engagement_score([], TODAY) == 0

    def test_score_in_range(self):
        score = compute_engagement_score(evs(("donation", 1)), TODAY)
        assert 0 <= score <= 100

    def test_donation_today_higher_than_email_open_today(self):
        donation = compute_engagement_score(evs(("donation", 0)), TODAY)
        open_only = compute_engagement_score(evs(("email_open", 0)), TODAY)
        assert donation > open_only

    def test_recent_events_dominate(self):
        recent_donation = compute_engagement_score(evs(("donation", 1)), TODAY)
        old_donation = compute_engagement_score(evs(("donation", 300)), TODAY)
        assert recent_donation > old_donation

    def test_multiple_signals_compound(self):
        single = compute_engagement_score(evs(("donation", 0)), TODAY)
        multi = compute_engagement_score(
            evs(("donation", 0), ("meeting", 5), ("event_attendance", 10)),
            TODAY,
        )
        assert multi > single

    def test_recurring_donation_higher_than_one_off(self):
        one_off = compute_engagement_score(evs(("donation", 0)), TODAY)
        recurring = compute_engagement_score(evs(("donation_recurring", 0)), TODAY)
        # Per EVENT_TYPE_WEIGHTS table.
        assert recurring > one_off

    def test_no_show_reduces_score(self):
        baseline = compute_engagement_score(evs(("donation", 0), ("meeting", 0)), TODAY)
        with_no_show = compute_engagement_score(
            evs(("donation", 0), ("meeting", 0), ("no_show", 0)),
            TODAY,
        )
        assert with_no_show < baseline

    def test_events_outside_horizon_ignored(self):
        score = compute_engagement_score(
            evs(("donation", 400)),  # > 365 days
            TODAY,
            horizon_days=365,
        )
        assert score == 0

    def test_future_events_ignored(self):
        future = [EngagementEvent("donation", TODAY + timedelta(days=10))]
        assert compute_engagement_score(future, TODAY) == 0

    def test_score_capped_at_100(self):
        # 50 recent donations
        many = evs(*[("donation", i) for i in range(50)])
        score = compute_engagement_score(many, TODAY)
        assert score <= 100

    def test_override_takes_precedence(self):
        # Manual event with override > 0 outweighs an open-only baseline
        baseline = compute_engagement_score(evs(("email_open", 0)), TODAY)
        with_override = compute_engagement_score(
            [
                EngagementEvent("manual", TODAY, score_delta_override=100),
                EngagementEvent("email_open", TODAY),
            ],
            TODAY,
        )
        assert with_override > baseline

    def test_unknown_event_type_contributes_zero(self):
        score = compute_engagement_score(evs(("unknown_signal", 0)), TODAY)
        assert score == compute_engagement_score([], TODAY)

    def test_all_weights_documented(self):
        # If anyone adds an event_type to the model selection without adding
        # a weight here, this test will catch it (assuming the test suite is
        # kept aligned with the model).
        expected = {
            "donation", "donation_recurring", "meeting", "event_attendance",
            "email_reply", "email_open", "manual", "p2p_share", "no_show",
        }
        assert set(EVENT_TYPE_WEIGHTS) == expected
