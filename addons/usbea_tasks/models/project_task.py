"""Extensions to stock ``project.task`` for nonprofit workflows.

Adds:
- Template linkage (usbea.task.template) + button to expand checklist
- Grant + program many-to-one (cross-pillar linking)
- AI priority (computed via usbea_ai, with accept/reject affordance)
- "My Week" filter via date_deadline + assignee
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from odoo import api, fields, models

from ..utils.ai_parsing import parse_ai_priority_response

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = "project.task"

    # ----- Template linkage -----

    usbea_template_id = fields.Many2one(
        "usbea.task.template",
        string="USBEA template",
        help="Apply a nonprofit-native template to populate fields and checklist.",
    )
    usbea_template_category = fields.Selection(
        related="usbea_template_id.category",
        store=True,
        index=True,
    )

    # ----- Cross-pillar linking -----

    grant_id = fields.Many2one(
        "usbea.grant",
        string="Grant",
        help="Grant this task contributes to (receiving side).",
        index=True,
    )
    program_id = fields.Many2one(
        "usbea.program",
        string="Program",
        help="Program this task belongs to.",
        index=True,
    )

    # ----- AI-computed priority -----

    usbea_priority_ai = fields.Integer(
        string="AI priority score",
        readonly=True,
        help="0-100 score from the smart-prioritization template. Higher = more urgent.",
    )
    usbea_priority_ai_reason = fields.Char(
        string="AI priority reason",
        readonly=True,
    )
    usbea_priority_ai_suggestion_id = fields.Many2one(
        "usbea.ai.suggestion",
        string="AI suggestion",
        readonly=True,
        help="Link to the audit log row for the computation.",
    )

    # ----- 'My Week' helper -----

    is_in_my_week = fields.Boolean(
        compute="_compute_is_in_my_week",
        search="_search_is_in_my_week",
    )

    @api.depends("date_deadline", "user_ids")
    def _compute_is_in_my_week(self):
        """True for tasks assigned to current user with deadline within 7 days."""
        uid = self.env.uid
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=7)
        for rec in self:
            rec.is_in_my_week = bool(
                rec.user_ids and uid in rec.user_ids.ids
                and rec.date_deadline
                and today <= rec.date_deadline <= horizon,
            )

    @api.model
    def _search_is_in_my_week(self, operator, value):
        # Allows the filter to be used in search views.
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return [("id", "=", False)]
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=7)
        match_domain = [
            ("user_ids", "in", self.env.uid),
            ("date_deadline", ">=", today),
            ("date_deadline", "<=", horizon),
        ]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return match_domain
        # Negated: build the inverse using OR-of-NOTs would balloon — easier:
        return ["!", "&", "&", *match_domain]

    # ----- Actions -----

    def action_apply_template(self):
        """Re-apply the linked template (idempotent over already-created subtasks)."""
        self.ensure_one()
        if not self.usbea_template_id:
            return False
        self.usbea_template_id.instantiate_on_task(self)
        return True

    def action_compute_ai_priority(self):
        """Call usbea_ai to compute a smart priority score.

        Safe to call when usbea_ai isn't configured — the suggestion record
        will carry an ``error`` field and we leave the existing priority intact.
        """
        self.ensure_one()
        AI = self.env["usbea.ai"]
        # Build a compact context that DOES NOT include free-form description
        # PII — the redactor would scrub it but we minimize anyway.
        tasks_payload = [
            {
                "id": self.id,
                "name": self.name,
                "deadline": fields.Date.to_string(self.date_deadline) if self.date_deadline else None,
                "current_priority": self.priority,
                "grant": self.grant_id.name or None,
                "program": self.program_id.name or None,
                "category": self.usbea_template_category or None,
                "open_subtasks": self.env["project.task"].search_count(
                    [("parent_id", "=", self.id), ("state", "!=", "done")],
                ),
            },
        ]
        suggestion = AI.suggest(
            "task_priority",
            context={
                "tasks_json": json.dumps(tasks_payload, ensure_ascii=False),
                "context_notes": "single-task priority refresh",
            },
            source_module="usbea_tasks",
            source_model="project.task",
            source_record_id=self.id,
        )

        # Parse the response (template asks for JSON with ranking[0])
        score, reason = parse_ai_priority_response(suggestion.response)
        self.write(
            {
                "usbea_priority_ai": score or 0,
                "usbea_priority_ai_reason": reason or "",
                "usbea_priority_ai_suggestion_id": suggestion.id,
            },
        )
        return suggestion

    # ----- CRUD hooks -----

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # If template_id was passed at create time, auto-instantiate.
        for rec in records:
            if rec.usbea_template_id and not rec.child_ids:
                rec.usbea_template_id.instantiate_on_task(rec)
        return records
