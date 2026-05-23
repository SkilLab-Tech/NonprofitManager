"""Pure-Python SLA helpers for LGPD DSAR fulfillment.

Isolated here so we can unit-test the business-day arithmetic without
loading Odoo. The 15-day SLA in LGPD Art. 19 §1 is calendar days, but
internal escalation thresholds (yellow/red) are configured here.
"""

from __future__ import annotations

from datetime import date, timedelta

# LGPD Art. 19 §1: 15 calendar days from request to response.
LGPD_DSAR_SLA_DAYS = 15

# Internal escalation thresholds (days remaining).
DSAR_YELLOW_REMAINING = 5
DSAR_RED_REMAINING = 2


def compute_sla_deadline(received_on: date) -> date:
    """Return the legal deadline for a DSAR received on *received_on*."""
    if received_on is None:
        msg = "received_on is required"
        raise ValueError(msg)
    return received_on + timedelta(days=LGPD_DSAR_SLA_DAYS)


def days_remaining(received_on: date, today: date) -> int:
    """Days remaining until the SLA deadline. Negative if overdue."""
    deadline = compute_sla_deadline(received_on)
    return (deadline - today).days


def sla_status(received_on: date, today: date, fulfilled: bool = False) -> str:
    """Return one of: ``"fulfilled" | "overdue" | "red" | "yellow" | "green"``.

    The status is used by the kanban view to color cards and by reports to
    flag risk before the legal deadline hits.
    """
    if fulfilled:
        return "fulfilled"
    remaining = days_remaining(received_on, today)
    if remaining < 0:
        return "overdue"
    if remaining <= DSAR_RED_REMAINING:
        return "red"
    if remaining <= DSAR_YELLOW_REMAINING:
        return "yellow"
    return "green"
