"""Pure-Python helpers that assemble compact context payloads for AI prompts.

Keeps the Odoo model thin and the formatting logic testable. Each function
takes raw record dicts (from search_read) and returns a string/JSON-ish
structure suitable for a prompt template.
"""

from __future__ import annotations

import json
from datetime import date, timedelta


def truncate_text(value: str | None, limit: int = 240) -> str:
    """Defensive truncation for free-form text fields before going into a prompt."""
    if not value:
        return ""
    value = str(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def filter_stale_tasks(tasks: list[dict], today: date, stale_days: int = 7) -> list[dict]:
    """Return the subset of tasks whose last-activity date is > stale_days ago.

    Each task dict should carry ``last_activity`` (date or None). Tasks with
    no last_activity are considered stale if their date_deadline is in the past.
    """
    cutoff = today - timedelta(days=stale_days)
    stale = []
    for t in tasks:
        last = t.get("last_activity")
        deadline = t.get("date_deadline")
        if last is None:
            if deadline and deadline < today:
                stale.append(t)
            continue
        if last < cutoff:
            stale.append(t)
    return stale


def compact_tasks_for_prompt(tasks: list[dict]) -> str:
    """JSON-serialize a stripped-down task list — no PII, ≤ 30 tasks."""
    stripped = []
    for t in tasks[:30]:
        stripped.append(
            {
                "name": truncate_text(t.get("name"), 80),
                "deadline": str(t.get("date_deadline") or ""),
                "priority": t.get("priority"),
                "last_activity": str(t.get("last_activity") or ""),
                "category": t.get("usbea_template_category"),
            },
        )
    return json.dumps(stripped, default=str, ensure_ascii=False)


def kpi_summary(
    *,
    confirmed_donations_ytd: float = 0.0,
    confirmed_donations_count: int = 0,
    active_recurring_plans: int = 0,
    grants_pipeline_count: int = 0,
    grants_awarded_ytd: int = 0,
    open_dsar_count: int = 0,
    dsar_overdue_count: int = 0,
    stale_task_count: int = 0,
) -> dict:
    """Bundle KPIs into the dict shape consumed by the AI briefing template."""
    return {
        "donations": {
            "ytd_total_brl": round(confirmed_donations_ytd, 2),
            "ytd_count": confirmed_donations_count,
            "active_recurring": active_recurring_plans,
        },
        "grants": {
            "pipeline_count": grants_pipeline_count,
            "awarded_ytd": grants_awarded_ytd,
        },
        "compliance": {
            "open_dsars": open_dsar_count,
            "overdue_dsars": dsar_overdue_count,
        },
        "ops": {
            "stale_tasks": stale_task_count,
        },
    }
