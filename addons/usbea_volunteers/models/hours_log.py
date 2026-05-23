"""Append-only volunteer hours log with manager approval workflow."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UsbeaVolunteerHoursLog(models.Model):
    _name = "usbea.volunteer.hours_log"
    _description = "Volunteer Hours Log"
    _order = "served_on desc, id desc"
    _inherit = ["mail.thread"]

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="restrict",
        domain="[('usbea_archetype', '=', 'volunteer')]",
        index=True,
    )
    program_id = fields.Many2one("usbea.program", ondelete="set null", index=True)
    opportunity_id = fields.Many2one("usbea.volunteer.opportunity", ondelete="set null")
    served_on = fields.Date(default=fields.Date.context_today, required=True)
    hours = fields.Float(required=True)
    description = fields.Char()
    state = fields.Selection(
        [
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="submitted",
        required=True,
        tracking=True,
        index=True,
    )
    approved_by = fields.Many2one("res.users", readonly=True)
    approved_at = fields.Datetime(readonly=True)
    rejection_reason = fields.Char()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.constrains("hours")
    def _check_hours(self):
        for rec in self:
            if rec.hours is None or rec.hours <= 0:
                msg = _("Hours must be > 0.")
                raise UserError(msg)
            if rec.hours > 24:
                msg = _("Hours cannot exceed 24 per single log entry.")
                raise UserError(msg)

    def action_approve(self):
        for rec in self:
            if rec.state == "approved":
                continue
            rec.write(
                {
                    "state": "approved",
                    "approved_by": self.env.user.id,
                    "approved_at": fields.Datetime.now(),
                },
            )
            # Post an engagement event so volunteer activity feeds CRM scoring.
            Event = self.env.get("usbea.engagement.event")
            if Event is not None:
                Event.sudo().create(
                    {
                        "partner_id": rec.partner_id.id,
                        "event_type": "event_attendance",
                        "when": rec.served_on,
                        "source": f"volunteer_hours:{rec.id}",
                        "notes": f"Approved {rec.hours}h on {rec.served_on}",
                    },
                )

    def action_reject(self):
        for rec in self:
            if not rec.rejection_reason:
                msg = _("Provide a reason before rejecting.")
                raise UserError(msg)
            rec.write({"state": "rejected"})

    def write(self, vals):
        """Once approved, only rejection_reason and state can be edited."""
        frozen_fields = {"hours", "served_on", "partner_id", "program_id", "opportunity_id"}
        for rec in self:
            if rec.state == "approved" and frozen_fields.intersection(vals):
                msg = _("Approved hours-log entries are append-only; reject + new entry to revise.")
                raise UserError(msg)
        return super().write(vals)
