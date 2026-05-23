"""res.partner extension for volunteers."""

from __future__ import annotations

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    volunteer_skill_ids = fields.Many2many(
        "usbea.volunteer.skill",
        relation="usbea_partner_volunteer_skill_rel",
        column1="partner_id",
        column2="skill_id",
        string="Volunteer skills",
    )
    volunteer_slot_ids = fields.One2many(
        "usbea.volunteer.availability_slot",
        "partner_id",
        string="Availability slots",
    )
    volunteer_bg_check_ids = fields.One2many(
        "usbea.volunteer.background_check",
        "partner_id",
        string="Background checks",
    )
    volunteer_hours_total = fields.Float(
        compute="_compute_volunteer_hours_total",
        help="Sum of all approved hours-log entries.",
    )
    volunteer_latest_bg_state = fields.Selection(
        related="volunteer_bg_check_latest_id.state",
        readonly=True,
    )
    volunteer_bg_check_latest_id = fields.Many2one(
        "usbea.volunteer.background_check",
        compute="_compute_volunteer_latest_bg",
    )

    def _compute_volunteer_hours_total(self):
        HoursLog = self.env["usbea.volunteer.hours_log"].sudo()
        for rec in self:
            rows = HoursLog.search_read(
                [("partner_id", "=", rec.id), ("state", "=", "approved")],
                ["hours"],
            )
            rec.volunteer_hours_total = sum(r["hours"] for r in rows)

    def _compute_volunteer_latest_bg(self):
        BgCheck = self.env["usbea.volunteer.background_check"].sudo()
        for rec in self:
            latest = BgCheck.search(
                [("partner_id", "=", rec.id)],
                order="expires_on desc",
                limit=1,
            )
            rec.volunteer_bg_check_latest_id = latest.id if latest else False

    @api.model
    def _get_lgpd_data_for_partner(self, partner_id: int) -> dict:
        rec = self.sudo().browse(partner_id)
        if not rec.exists():
            return {"exists": False}
        return {
            "volunteer": {
                "skills": rec.volunteer_skill_ids.mapped("complete_name"),
                "slots_count": len(rec.volunteer_slot_ids),
                "bg_checks_count": len(rec.volunteer_bg_check_ids),
                "hours_total": rec.volunteer_hours_total,
            },
        }
