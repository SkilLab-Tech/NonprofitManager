"""Weekly recurring availability slots for volunteers."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

WEEKDAYS = [
    ("0", "Monday"),
    ("1", "Tuesday"),
    ("2", "Wednesday"),
    ("3", "Thursday"),
    ("4", "Friday"),
    ("5", "Saturday"),
    ("6", "Sunday"),
]


class UsbeaVolunteerAvailabilitySlot(models.Model):
    _name = "usbea.volunteer.availability_slot"
    _description = "Volunteer Availability Slot"
    _order = "partner_id, weekday, start_hour"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('usbea_archetype', '=', 'volunteer')]",
    )
    weekday = fields.Selection(WEEKDAYS, required=True)
    start_hour = fields.Float(
        required=True,
        help="Local-time start hour (0.0-24.0). Decimal: 9.5 = 09:30.",
    )
    end_hour = fields.Float(required=True)
    timezone = fields.Char(default="America/Sao_Paulo")
    notes = fields.Char()

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for rec in self:
            if not (0.0 <= rec.start_hour < 24.0):
                msg = _("start_hour must be in [0.0, 24.0).")
                raise ValidationError(msg)
            if not (0.0 < rec.end_hour <= 24.0):
                msg = _("end_hour must be in (0.0, 24.0].")
                raise ValidationError(msg)
            if rec.start_hour >= rec.end_hour:
                msg = _("start_hour must be < end_hour.")
                raise ValidationError(msg)
