"""Background-check tracking with expiry-warning cron."""

from __future__ import annotations

import logging

from odoo import _, api, fields, models

from ..utils.matching import is_background_check_expiring_soon

_logger = logging.getLogger(__name__)


class UsbeaVolunteerBackgroundCheck(models.Model):
    _name = "usbea.volunteer.background_check"
    _description = "Volunteer Background Check"
    _order = "expires_on desc, id desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('usbea_archetype', '=', 'volunteer')]",
    )
    check_type = fields.Selection(
        [
            ("criminal", "Criminal record (Antecedentes Criminais)"),
            ("identity", "Identity verification"),
            ("reference", "Reference check"),
            ("safeguarding", "Safeguarding (work with minors)"),
            ("custom", "Custom"),
        ],
        required=True,
    )
    issued_on = fields.Date()
    expires_on = fields.Date(required=True)
    provider = fields.Char(help="Issuing authority or vendor.")
    document_ref = fields.Char(string="Document reference")
    state = fields.Selection(
        [
            ("active", "Active"),
            ("expiring_soon", "Expiring soon (< 30d)"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        compute="_compute_state",
        store=True,
        index=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("partner_id", "check_type", "expires_on", "state")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s — %s [exp %s]" % (
                rec.partner_id.name or "?",
                rec.check_type or "",
                rec.expires_on or "",
            )

    @api.depends("expires_on")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expires_on:
                rec.state = "active"
                continue
            if rec.expires_on < today:
                rec.state = "expired"
            elif is_background_check_expiring_soon(rec.expires_on, today):
                rec.state = "expiring_soon"
            else:
                rec.state = "active"

    @api.model
    def cron_warn_expiring(self) -> int:
        """Cron: post a message to managers for each expiring_soon record.

        Returns the count of warnings posted. Configured via ir.cron.
        """
        records = self.search([("state", "=", "expiring_soon")])
        for rec in records:
            rec.message_post(
                body=_(
                    "Background check expires on %s — schedule renewal.",
                ) % rec.expires_on,
            )
        return len(records)
