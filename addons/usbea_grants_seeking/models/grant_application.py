"""The pipeline entity. One row per opportunity USBEA is pursuing."""

from __future__ import annotations

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..utils.pipeline import (
    is_terminal,
    validate_transition,
)

_logger = logging.getLogger(__name__)


PIPELINE_STATE_SELECTION = [
    ("prospect", "Prospect"),
    ("researching", "Researching"),
    ("drafting", "Drafting"),
    ("submitted", "Submitted"),
    ("under_review", "Under review"),
    ("awarded", "Awarded"),
    ("declined", "Declined"),
    ("withdrawn", "Withdrawn"),
]


class UsbeaGrantApplication(models.Model):
    _name = "usbea.grant_application"
    _description = "USBEA Grant Application (seeking side)"
    _order = "deadline asc, id desc"
    _rec_name = "display_name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, copy=False, default=lambda self: _("New"))
    funder_id = fields.Many2one(
        "res.partner",
        string="Funder",
        required=True,
        ondelete="restrict",
        domain="[('funder_type', '!=', False)]",
        tracking=True,
    )
    program_id = fields.Many2one(
        "usbea.program",
        help="USBEA program(s) the funding will support.",
        tracking=True,
    )
    state = fields.Selection(
        PIPELINE_STATE_SELECTION,
        default="prospect",
        required=True,
        tracking=True,
        index=True,
    )
    assigned_writer_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        tracking=True,
    )
    requested_amount = fields.Monetary(
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    deadline = fields.Date(tracking=True, index=True)
    submitted_at = fields.Date(tracking=True)
    decision_at = fields.Date(tracking=True)
    decision_notes = fields.Text()

    # AI-computed fit
    fit_score_ai = fields.Integer(
        string="Fit score (AI)",
        readonly=True,
        help="0-100 score from grant_fit_score template. Higher = better funder/program fit.",
    )
    fit_score_suggestion_id = fields.Many2one(
        "usbea.ai.suggestion",
        readonly=True,
    )

    # Draft versions + comments
    draft_version_ids = fields.One2many(
        "usbea.grant_application.draft_version",
        "application_id",
    )
    latest_draft_text = fields.Text(
        compute="_compute_latest_draft",
        store=True,
        help="Latest draft narrative text — for quick reference in list/kanban views.",
    )
    latest_draft_version_num = fields.Integer(
        compute="_compute_latest_draft",
        store=True,
    )
    comment_ids = fields.One2many("usbea.grant_application.comment", "application_id")

    # Award handoff
    awarded_grant_id = fields.Many2one(
        "usbea.grant",
        readonly=True,
        help="If awarded, the receiving-grant record created from this application.",
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("name", "funder_id", "state")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s — %s [%s]" % (
                rec.name or "?",
                rec.funder_id.name or "?",
                rec.state or "",
            )

    @api.depends("draft_version_ids.version_num", "draft_version_ids.content")
    def _compute_latest_draft(self):
        for rec in self:
            latest = max(rec.draft_version_ids, key=lambda v: v.version_num, default=None)
            rec.latest_draft_text = latest.content if latest else ""
            rec.latest_draft_version_num = latest.version_num if latest else 0

    @api.constrains("requested_amount")
    def _check_requested_amount(self):
        for rec in self:
            if rec.requested_amount and rec.requested_amount < 0:
                msg = _("requested_amount cannot be negative.")
                raise ValidationError(msg)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("usbea.grant_application")
                    or "GA/000"
                )
        records = super().create(vals_list)
        # Compute fit score asynchronously? For now, eager + best-effort.
        for rec in records:
            rec._refresh_fit_score_silent()
        return records

    # ----- State machine transitions -----

    def _transition(self, target_state: str):
        for rec in self:
            check = validate_transition(rec.state, target_state)
            if not check.ok:
                msg = _("Cannot move application: %s", check.reason)
                raise UserError(msg)
            update = {"state": target_state}
            if target_state == "submitted":
                update["submitted_at"] = fields.Date.context_today(rec)
            elif target_state in ("awarded", "declined"):
                update["decision_at"] = fields.Date.context_today(rec)
            rec.write(update)
            if target_state == "awarded":
                rec._handoff_to_grants()

    def action_research(self):
        self._transition("researching")

    def action_draft(self):
        self._transition("drafting")

    def action_submit(self):
        self._transition("submitted")

    def action_under_review(self):
        self._transition("under_review")

    def action_award(self):
        self._transition("awarded")

    def action_decline(self):
        self._transition("declined")

    def action_withdraw(self):
        for rec in self:
            if is_terminal(rec.state) and rec.state != "withdrawn":
                msg = _("Cannot withdraw an application already in a terminal state.")
                raise UserError(msg)
            rec.write({"state": "withdrawn"})

    # ----- Award handoff -----

    def _handoff_to_grants(self):
        """Create a usbea.grant record from this application.

        Best-effort: if the receiving-grants model rejects our payload (e.g.
        missing required fields), we surface the error to the user so they can
        complete the record manually rather than silently losing the link.
        """
        for rec in self:
            if rec.awarded_grant_id:
                continue
            Grant = self.env["usbea.grant"].sudo()
            vals = {
                "name": rec.name,
                "partner_id": rec.funder_id.id,
                "amount": rec.requested_amount,
                "currency_id": rec.currency_id.id,
            }
            # We don't pre-empt usbea_grants required fields beyond the
            # essentials; the user will complete them in the new record.
            try:
                grant = Grant.create(vals)
                rec.awarded_grant_id = grant.id
            except Exception as exc:  # noqa: BLE001
                _logger.exception("Grant handoff failed for application %s", rec.name)
                rec.message_post(
                    body=_("Award handoff failed: %s") % exc,
                )

    # ----- AI hooks -----

    def action_generate_draft(self, section: str = "executive_summary", word_count: int = 400):
        """Call the AI grant-writing copilot to produce a new draft version."""
        self.ensure_one()
        AI = self.env["usbea.ai"]
        context = {
            "funder_name": self.funder_id.name or "",
            "funder_profile": self._render_funder_profile(),
            "section": section,
            "programs": (self.program_id.name or ""),
            "program_context": self._render_program_context(),
            "draft_so_far": self.latest_draft_text or "(no draft yet)",
            "word_count": str(word_count),
        }
        suggestion = AI.suggest(
            "grant_writing",
            context=context,
            source_module="usbea_grants_seeking",
            source_model="usbea.grant_application",
            source_record_id=self.id,
            partner_ids=[self.funder_id.id] if self.funder_id else [],
        )
        if suggestion.response and not suggestion.error:
            self.env["usbea.grant_application.draft_version"].create(
                {
                    "application_id": self.id,
                    "version_num": self.latest_draft_version_num + 1,
                    "content": suggestion.response,
                    "ai_assisted": True,
                    "ai_suggestion_id": suggestion.id,
                    "section": section,
                },
            )
        return suggestion

    def action_refresh_fit_score(self):
        for rec in self:
            rec._refresh_fit_score_silent()

    def _refresh_fit_score_silent(self):
        """Run grant_fit_score against this application. Best-effort, never raises."""
        self.ensure_one()
        AI = self.env["usbea.ai"]
        if not self.funder_id or not self.program_id:
            return False
        try:
            suggestion = AI.suggest(
                "grant_fit_score",
                context={
                    "funder_profile": self._render_funder_profile(),
                    "focus_areas": self.funder_id.funder_focus_areas or "",
                    "typical_size": "%s - %s" % (
                        self.funder_id.funder_typical_min_brl or 0,
                        self.funder_id.funder_typical_max_brl or 0,
                    ),
                    "program_name": self.program_id.name or "",
                    "program_goals": "(see program description)",
                },
                source_module="usbea_grants_seeking",
                source_model="usbea.grant_application",
                source_record_id=self.id,
                partner_ids=[self.funder_id.id],
            )
        except Exception:  # noqa: BLE001
            _logger.warning("Fit score AI call failed for application %s", self.name)
            return False
        score = self._parse_fit_score(suggestion.response)
        self.write(
            {
                "fit_score_ai": score or 0,
                "fit_score_suggestion_id": suggestion.id,
            },
        )
        return True

    @staticmethod
    def _parse_fit_score(response: str | None) -> int | None:
        """Extract score 0-100 from the grant_fit_score JSON response."""
        if not response:
            return None
        try:
            data = json.loads(response)
        except (TypeError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        score = data.get("score")
        try:
            score = int(score) if score is not None else None
        except (TypeError, ValueError):
            return None
        if score is None:
            return None
        return max(0, min(100, score))

    def _render_funder_profile(self) -> str:
        """Compact profile string for AI prompt context."""
        self.ensure_one()
        p = self.funder_id
        if not p:
            return ""
        parts = [
            f"Name: {p.name}",
            f"Type: {p.funder_type or 'unknown'}",
            f"Focus areas: {p.funder_focus_areas or 'unknown'}",
            f"Typical range BRL: {p.funder_typical_min_brl or '?'} - {p.funder_typical_max_brl or '?'}",
            f"Application seasons: {p.funder_application_seasons or 'unknown'}",
        ]
        return " | ".join(parts)

    def _render_program_context(self) -> str:
        """Compact program context for AI prompt."""
        self.ensure_one()
        if not self.program_id:
            return "(no program linked)"
        return self.program_id.name or ""

    # ----- DSAR adapter (funder may be a partner the AI prompts referenced) -----

    @api.model
    def _get_lgpd_data_for_partner(self, partner_id: int) -> dict:
        rows = self.sudo().search_read(
            [("funder_id", "=", partner_id)],
            ["id", "name", "state", "deadline", "requested_amount"],
        )
        return {"applications_as_funder": rows, "count": len(rows)}
