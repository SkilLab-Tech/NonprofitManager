"""Board briefing model — assembles cross-module KPIs and runs AI commentary."""

from __future__ import annotations

import json
import logging

from odoo import _, fields, models

from ..utils.briefing_assembler import (
    compact_tasks_for_prompt,
    filter_stale_tasks,
    kpi_summary,
)

_logger = logging.getLogger(__name__)


class UsbeaPortalBoardBriefing(models.Model):
    _name = "usbea.portal.board_briefing"
    _description = "Board Briefing (AI-assembled)"
    _order = "generated_at desc"
    _rec_name = "name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, default=lambda self: _("New briefing"))
    generated_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    period_start = fields.Date()
    period_end = fields.Date(default=fields.Date.context_today)
    kpis_json = fields.Text(readonly=True)
    stale_tasks_summary = fields.Text(readonly=True)
    stale_tasks_suggestion_id = fields.Many2one("usbea.ai.suggestion", readonly=True)
    commentary = fields.Html(readonly=True)
    commentary_suggestion_id = fields.Many2one("usbea.ai.suggestion", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    def action_assemble(self):
        """Compute KPIs + run AI commentary. Idempotent — overwrites prior values."""
        for rec in self:
            rec._assemble_kpis()
            rec._run_stale_tasks_ai()
            rec._run_commentary_ai()

    # ----- KPIs -----

    def _assemble_kpis(self):
        self.ensure_one()
        kpis = kpi_summary(
            confirmed_donations_ytd=self._count_donations_ytd_total(),
            confirmed_donations_count=self._count_donations_ytd_count(),
            active_recurring_plans=self._count_active_recurring_plans(),
            grants_pipeline_count=self._count_grant_applications_pipeline(),
            grants_awarded_ytd=self._count_grants_awarded_ytd(),
            open_dsar_count=self._count_dsars_open(),
            dsar_overdue_count=self._count_dsars_overdue(),
            stale_task_count=len(self._collect_stale_tasks()),
        )
        self.kpis_json = json.dumps(kpis, default=str, ensure_ascii=False)

    def _count_donations_ytd_total(self) -> float:
        Don = self.env.get("usbea.donation")
        if Don is None:
            return 0.0
        today = fields.Date.context_today(self)
        yr_start = today.replace(month=1, day=1)
        rows = Don.sudo().search_read(
            [("state", "=", "confirmed"), ("donation_date", ">=", yr_start)],
            ["amount"],
        )
        return sum(r["amount"] for r in rows)

    def _count_donations_ytd_count(self) -> int:
        Don = self.env.get("usbea.donation")
        if Don is None:
            return 0
        today = fields.Date.context_today(self)
        yr_start = today.replace(month=1, day=1)
        return Don.sudo().search_count(
            [("state", "=", "confirmed"), ("donation_date", ">=", yr_start)],
        )

    def _count_active_recurring_plans(self) -> int:
        Plan = self.env.get("usbea.donation.recurring_plan")
        if Plan is None:
            return 0
        return Plan.sudo().search_count([("state", "=", "active")])

    def _count_grant_applications_pipeline(self) -> int:
        App = self.env.get("usbea.grant_application")
        if App is None:
            return 0
        return App.sudo().search_count(
            [("state", "in", ["prospect", "researching", "drafting", "submitted", "under_review"])],
        )

    def _count_grants_awarded_ytd(self) -> int:
        App = self.env.get("usbea.grant_application")
        if App is None:
            return 0
        today = fields.Date.context_today(self)
        yr_start = today.replace(month=1, day=1)
        return App.sudo().search_count(
            [("state", "=", "awarded"), ("decision_at", ">=", yr_start)],
        )

    def _count_dsars_open(self) -> int:
        DSAR = self.env.get("usbea.lgpd.dsar")
        if DSAR is None:
            return 0
        return DSAR.sudo().search_count(
            [("state", "in", ["received", "processing"])],
        )

    def _count_dsars_overdue(self) -> int:
        DSAR = self.env.get("usbea.lgpd.dsar")
        if DSAR is None:
            return 0
        return DSAR.sudo().search_count([("sla_status_indicator", "=", "overdue")])

    # ----- Stale tasks -----

    def _collect_stale_tasks(self) -> list[dict]:
        Task = self.env.get("project.task")
        if Task is None:
            return []
        today = fields.Date.context_today(self)
        # We accept any open task; the filter narrows to stale.
        rows = Task.sudo().search_read(
            [("state", "!=", "1_done"), ("state", "!=", "1_canceled")],
            ["name", "date_deadline", "priority", "usbea_template_category", "write_date"],
            limit=200,
        )
        # Project tasks expose write_date — treat as "last_activity".
        for r in rows:
            wd = r.pop("write_date", None)
            r["last_activity"] = wd.date() if hasattr(wd, "date") else None
        return filter_stale_tasks(rows, today)

    def _run_stale_tasks_ai(self):
        self.ensure_one()
        stale = self._collect_stale_tasks()
        if not stale:
            self.stale_tasks_summary = ""
            return
        AI = self.env["usbea.ai"]
        suggestion = AI.suggest(
            "stale_tasks_summary",
            context={"stale_tasks_json": compact_tasks_for_prompt(stale)},
            source_module="usbea_portal_ai",
            source_model="usbea.portal.board_briefing",
            source_record_id=self.id,
        )
        self.write(
            {
                "stale_tasks_summary": suggestion.response or "",
                "stale_tasks_suggestion_id": suggestion.id,
            },
        )

    # ----- Commentary on KPIs -----

    def _run_commentary_ai(self):
        """Use the impact_narrative template (Pillar 4) for executive commentary.

        Falls back gracefully if no narrative template is configured.
        """
        self.ensure_one()
        AI = self.env["usbea.ai"]
        period = "%s to %s" % (
            self.period_start or "year start",
            self.period_end or fields.Date.context_today(self),
        )
        suggestion = AI.suggest(
            "impact_narrative",
            context={
                "period": period,
                "programs": "Cross-pillar (donations, grants, compliance, ops)",
                "indicators_json": self.kpis_json or "{}",
                "stories": "[]",
                "audience": "Board of directors",
            },
            source_module="usbea_portal_ai",
            source_model="usbea.portal.board_briefing",
            source_record_id=self.id,
        )
        self.write(
            {
                "commentary": suggestion.response or "",
                "commentary_suggestion_id": suggestion.id,
            },
        )
