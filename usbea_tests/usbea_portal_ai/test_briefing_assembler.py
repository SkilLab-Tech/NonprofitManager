"""Unit tests for briefing assembler utilities."""

from __future__ import annotations

import json
from datetime import date, timedelta

from utils.briefing_assembler import (
    compact_tasks_for_prompt,
    filter_stale_tasks,
    kpi_summary,
    truncate_text,
)


TODAY = date(2026, 5, 23)


class TestTruncateText:
    def test_empty_returns_empty(self):
        assert truncate_text("") == ""
        assert truncate_text(None) == ""

    def test_short_text_unchanged(self):
        assert truncate_text("hello") == "hello"

    def test_long_text_truncated_with_ellipsis(self):
        text = "x" * 300
        result = truncate_text(text, limit=100)
        assert len(result) <= 100
        assert result.endswith("…")

    def test_non_string_input(self):
        # Defensive — should coerce to string
        assert truncate_text(123) == "123"


class TestFilterStaleTasks:
    def test_no_tasks(self):
        assert filter_stale_tasks([], TODAY) == []

    def test_recent_task_not_stale(self):
        tasks = [{"name": "T1", "last_activity": TODAY - timedelta(days=2)}]
        assert filter_stale_tasks(tasks, TODAY) == []

    def test_old_task_is_stale(self):
        tasks = [{"name": "T1", "last_activity": TODAY - timedelta(days=10)}]
        assert len(filter_stale_tasks(tasks, TODAY)) == 1

    def test_no_activity_with_past_deadline_is_stale(self):
        tasks = [
            {"name": "T1", "last_activity": None, "date_deadline": TODAY - timedelta(days=3)},
        ]
        assert len(filter_stale_tasks(tasks, TODAY)) == 1

    def test_no_activity_with_future_deadline_not_stale(self):
        tasks = [
            {"name": "T1", "last_activity": None, "date_deadline": TODAY + timedelta(days=3)},
        ]
        assert filter_stale_tasks(tasks, TODAY) == []

    def test_no_activity_and_no_deadline_not_stale(self):
        tasks = [{"name": "T1", "last_activity": None, "date_deadline": None}]
        assert filter_stale_tasks(tasks, TODAY) == []

    def test_custom_stale_days(self):
        tasks = [{"name": "T1", "last_activity": TODAY - timedelta(days=10)}]
        assert filter_stale_tasks(tasks, TODAY, stale_days=14) == []
        assert len(filter_stale_tasks(tasks, TODAY, stale_days=7)) == 1


class TestCompactTasksForPrompt:
    def test_serializes_valid_json(self):
        tasks = [{"name": "T1", "date_deadline": TODAY, "priority": "1"}]
        result = compact_tasks_for_prompt(tasks)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["name"] == "T1"

    def test_caps_at_30(self):
        tasks = [{"name": f"T{i}"} for i in range(100)]
        result = compact_tasks_for_prompt(tasks)
        parsed = json.loads(result)
        assert len(parsed) == 30

    def test_truncates_long_names(self):
        tasks = [{"name": "x" * 500}]
        result = compact_tasks_for_prompt(tasks)
        parsed = json.loads(result)
        # Name truncated to <= 80 + ellipsis
        assert len(parsed[0]["name"]) <= 80

    def test_handles_missing_fields(self):
        result = compact_tasks_for_prompt([{"name": "T1"}])
        parsed = json.loads(result)
        assert parsed[0]["name"] == "T1"
        assert "deadline" in parsed[0]


class TestKPISummary:
    def test_defaults_are_zero(self):
        kpis = kpi_summary()
        assert kpis["donations"]["ytd_total_brl"] == 0
        assert kpis["donations"]["ytd_count"] == 0
        assert kpis["grants"]["pipeline_count"] == 0
        assert kpis["compliance"]["open_dsars"] == 0
        assert kpis["ops"]["stale_tasks"] == 0

    def test_rounded_donations(self):
        kpis = kpi_summary(confirmed_donations_ytd=12345.6789)
        assert kpis["donations"]["ytd_total_brl"] == 12345.68

    def test_full_kpi_population(self):
        kpis = kpi_summary(
            confirmed_donations_ytd=50000.0,
            confirmed_donations_count=120,
            active_recurring_plans=15,
            grants_pipeline_count=8,
            grants_awarded_ytd=3,
            open_dsar_count=2,
            dsar_overdue_count=1,
            stale_task_count=5,
        )
        assert kpis["donations"]["ytd_count"] == 120
        assert kpis["grants"]["awarded_ytd"] == 3
        assert kpis["compliance"]["overdue_dsars"] == 1
        assert kpis["ops"]["stale_tasks"] == 5

    def test_structure_keys_present(self):
        kpis = kpi_summary()
        assert set(kpis.keys()) == {"donations", "grants", "compliance", "ops"}
