"""Funder extension on res.partner.

A funder is a partner archetype that USBEA pursues for grant funding —
foundations, government agencies, embassies, corporate donors, major
individual donors who write grant-sized checks.
"""

from __future__ import annotations

from odoo import fields, models

FUNDER_TYPES = [
    ("foundation", "Foundation"),
    ("government", "Government agency"),
    ("embassy", "Embassy / consulate"),
    ("corporate", "Corporate"),
    ("major_individual", "Major individual donor"),
    ("multilateral", "Multilateral (UN, World Bank, etc.)"),
    ("other", "Other"),
]


class UsbeaFunder(models.Model):
    """One row per funder. Stored as extension to res.partner."""

    _inherit = "res.partner"

    funder_type = fields.Selection(
        FUNDER_TYPES,
        help="Used by AI fit scoring and pipeline filters.",
    )
    funder_focus_areas = fields.Char(
        help="Comma-separated focus areas (e.g. 'education,leadership,US-Brazil relations').",
    )
    funder_typical_min_brl = fields.Monetary(
        currency_field="company_currency_id",
        string="Typical min grant (BRL)",
    )
    funder_typical_max_brl = fields.Monetary(
        currency_field="company_currency_id",
        string="Typical max grant (BRL)",
    )
    funder_application_seasons = fields.Char(
        help="When this funder accepts applications (e.g. 'Q1, Q3', 'rolling', 'annual: Sep-Oct').",
    )
    funder_application_url = fields.Char(string="Application portal URL")
    funder_notes = fields.Text(string="Funder notes (internal)")
    funder_application_count = fields.Integer(
        compute="_compute_funder_application_count",
    )

    def _compute_funder_application_count(self):
        Application = self.env["usbea.grant_application"].sudo()
        for rec in self:
            rec.funder_application_count = Application.search_count(
                [("funder_id", "=", rec.id)],
            )
