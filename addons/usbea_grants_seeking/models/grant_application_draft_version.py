"""Immutable draft version snapshots."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UsbeaGrantApplicationDraftVersion(models.Model):
    _name = "usbea.grant_application.draft_version"
    _description = "Grant Application Draft Version"
    _order = "application_id, version_num desc"
    _rec_name = "display_name"

    application_id = fields.Many2one(
        "usbea.grant_application",
        required=True,
        ondelete="cascade",
        index=True,
    )
    version_num = fields.Integer(required=True)
    section = fields.Char(
        help="Which section of the application this draft covers (e.g. 'executive_summary', 'budget', 'theory_of_change').",
    )
    content = fields.Text(required=True)
    created_by = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    ai_assisted = fields.Boolean(
        default=False,
        help="True if this version was generated or edited with help from the AI grant-writing copilot.",
    )
    ai_suggestion_id = fields.Many2one(
        "usbea.ai.suggestion",
        readonly=True,
        help="Link to the AI audit log row that produced this version.",
    )
    display_name = fields.Char(compute="_compute_display_name")

    _sql_constraints = [
        (
            "version_unique_per_application",
            "UNIQUE(application_id, version_num)",
            "Each version_num must be unique within an application.",
        ),
    ]

    @api.depends("application_id", "version_num", "section")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "v%s · %s" % (
                rec.version_num,
                rec.section or "(no section)",
            )

    def write(self, vals):
        """Versions are append-only. Only the section + ai_assisted may be edited."""
        forbidden = {"content", "version_num", "application_id", "created_by"}
        if forbidden.intersection(vals):
            msg = _(
                "Draft versions are append-only — to revise, create a new version.",
            )
            raise UserError(msg)
        return super().write(vals)

    def unlink(self):
        # Allow deletion only by Manager-tier (controlled via ACL).
        # No additional safeguards beyond ACL on this model.
        return super().unlink()
