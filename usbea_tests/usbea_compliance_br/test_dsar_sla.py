"""Unit tests for the DSAR SLA helpers — pure date arithmetic, no Odoo."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from utils.dsar_sla import (
    DSAR_RED_REMAINING,
    DSAR_YELLOW_REMAINING,
    LGPD_DSAR_SLA_DAYS,
    compute_sla_deadline,
    days_remaining,
    sla_status,
)


class TestSLAConstants:
    def test_lgpd_sla_is_15_days(self):
        # Per Lei 13.709/2018 Art. 19 §1 — must be 15 calendar days.
        # If a future amendment changes this, this test catches it.
        assert LGPD_DSAR_SLA_DAYS == 15


class TestComputeSLADeadline:
    def test_deadline_is_15_days_after_receipt(self):
        received = date(2026, 5, 1)
        assert compute_sla_deadline(received) == date(2026, 5, 16)

    def test_crosses_month_boundary(self):
        received = date(2026, 5, 25)
        # +15 days → 2026-06-09
        assert compute_sla_deadline(received) == date(2026, 6, 9)

    def test_none_raises(self):
        with pytest.raises(ValueError):
            compute_sla_deadline(None)


class TestDaysRemaining:
    def test_on_receipt_day(self):
        received = date(2026, 5, 1)
        assert days_remaining(received, received) == LGPD_DSAR_SLA_DAYS

    def test_one_day_later(self):
        received = date(2026, 5, 1)
        assert days_remaining(received, date(2026, 5, 2)) == 14

    def test_on_deadline(self):
        received = date(2026, 5, 1)
        deadline = received + timedelta(days=LGPD_DSAR_SLA_DAYS)
        assert days_remaining(received, deadline) == 0

    def test_overdue(self):
        received = date(2026, 5, 1)
        assert days_remaining(received, date(2026, 5, 20)) == -4


class TestSLAStatus:
    def test_green_when_far_from_deadline(self):
        received = date(2026, 5, 1)
        today = date(2026, 5, 2)  # 14 days remaining
        assert sla_status(received, today) == "green"

    def test_yellow_at_threshold(self):
        received = date(2026, 5, 1)
        today = received + timedelta(days=LGPD_DSAR_SLA_DAYS - DSAR_YELLOW_REMAINING)
        # remaining == DSAR_YELLOW_REMAINING (5) → yellow
        assert sla_status(received, today) == "yellow"

    def test_red_at_threshold(self):
        received = date(2026, 5, 1)
        today = received + timedelta(days=LGPD_DSAR_SLA_DAYS - DSAR_RED_REMAINING)
        # remaining == DSAR_RED_REMAINING (2) → red
        assert sla_status(received, today) == "red"

    def test_overdue(self):
        received = date(2026, 5, 1)
        today = received + timedelta(days=LGPD_DSAR_SLA_DAYS + 1)
        assert sla_status(received, today) == "overdue"

    def test_fulfilled_overrides_all_states(self):
        received = date(2026, 5, 1)
        today = received + timedelta(days=LGPD_DSAR_SLA_DAYS + 100)
        # Even if overdue, fulfilled wins
        assert sla_status(received, today, fulfilled=True) == "fulfilled"

    def test_boundary_red_below_yellow(self):
        # red threshold (2) is lower than yellow threshold (5) — proves order.
        assert DSAR_RED_REMAINING < DSAR_YELLOW_REMAINING
