"""Append-only measurement log."""

from __future__ import annotations

from odoo import fields, models


class UsbeaImpactMeasurement(models.Model):
    _name = "usbea.impact.measurement"
    _description = "Impact Indicator Measurement"
    _order = "date desc, id desc"

    indicator_id = fields.Many2one(
        "usbea.impact.indicator",
        required=True,
        ondelete="cascade",
        index=True,
    )
    date = fields.Date(required=True, default=fields.Date.context_today)
    value = fields.Float(required=True)
    source = fields.Selection(
        [
            ("manual", "Manual entry"),
            ("survey", "Survey"),
            ("sensor", "Sensor / instrumentation"),
            ("external", "External data source"),
            ("imported", "Imported from CSV"),
        ],
        default="manual",
        required=True,
    )
    notes = fields.Char()
