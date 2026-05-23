"""Quantitative outcome indicators per program."""

from __future__ import annotations

from odoo import api, fields, models

from ..utils.progress import compute_progress_pct, compute_status

FREQUENCIES = [
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("biannual", "Biannual"),
    ("annual", "Annual"),
    ("milestone", "Milestone-driven"),
]


class UsbeaImpactIndicator(models.Model):
    _name = "usbea.impact.indicator"
    _description = "USBEA Impact Indicator"
    _order = "program_id, name"
    _rec_name = "name"

    name = fields.Char(required=True)
    program_id = fields.Many2one("usbea.program", required=True, ondelete="restrict")
    unit = fields.Char(help="Unit of measurement (e.g. 'participants', 'hours', 'BRL').", required=True)
    target_value = fields.Float()
    current_value = fields.Float(compute="_compute_current_value", store=True)
    frequency = fields.Selection(FREQUENCIES, default="quarterly", required=True)
    period_start = fields.Date()
    period_end = fields.Date()
    progress_pct = fields.Float(
        compute="_compute_progress",
        store=True,
        help="(current_value / target_value) * 100, clamped at 0 lower bound.",
    )
    status = fields.Selection(
        [
            ("not_started", "Not started"),
            ("on_track", "On track"),
            ("behind", "Behind"),
            ("at_risk", "At risk"),
            ("achieved", "Achieved"),
        ],
        compute="_compute_progress",
        store=True,
    )
    measurement_ids = fields.One2many("usbea.impact.measurement", "indicator_id")
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.depends("measurement_ids", "measurement_ids.value")
    def _compute_current_value(self):
        for rec in self:
            # Latest measurement wins; falls back to the sum if no explicit "latest" flag.
            latest = max(
                rec.measurement_ids,
                key=lambda m: (m.date or fields.Date.from_string("1970-01-01"), m.id),
                default=None,
            )
            rec.current_value = latest.value if latest else 0.0

    @api.depends("current_value", "target_value", "period_start", "period_end")
    def _compute_progress(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.progress_pct = compute_progress_pct(rec.current_value, rec.target_value)
            time_pct = None
            if rec.period_start and rec.period_end and rec.period_end > rec.period_start:
                total_days = (rec.period_end - rec.period_start).days
                elapsed = max(0, min(total_days, (today - rec.period_start).days))
                time_pct = (elapsed / total_days) * 100.0
            rec.status = compute_status(rec.progress_pct, time_pct)
