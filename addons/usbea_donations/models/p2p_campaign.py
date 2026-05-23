"""Peer-to-peer fundraising campaign — alumni/supporters run their own pages."""

from __future__ import annotations

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,50}")


class UsbeaDonationP2PCampaign(models.Model):
    _name = "usbea.donation.p2p_campaign"
    _description = "P2P Fundraising Campaign"
    _order = "create_date desc"
    _rec_name = "name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    host_partner_id = fields.Many2one(
        "res.partner",
        required=True,
        help="The supporter hosting this campaign (typically an alumnus).",
        tracking=True,
    )
    slug = fields.Char(
        required=True,
        copy=False,
        help="URL-safe identifier used in the public page URL.",
    )
    target_amount = fields.Monetary(currency_field="currency_id")
    current_amount = fields.Monetary(
        compute="_compute_current_amount",
        currency_field="currency_id",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("closed", "Closed")],
        default="draft",
        required=True,
        tracking=True,
    )
    start_date = fields.Date()
    end_date = fields.Date()
    description_html = fields.Html()
    donation_ids = fields.One2many("usbea.donation", "p2p_campaign_id")
    progress_pct = fields.Float(compute="_compute_progress")
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    _sql_constraints = [
        ("slug_unique", "UNIQUE(slug)", "P2P campaign slug must be unique."),
    ]

    @api.constrains("slug")
    def _check_slug(self):
        for rec in self:
            if not _SLUG_RE.fullmatch(rec.slug or ""):
                msg = _("Slug must be lowercase alphanumerics + hyphens (2-51 chars).")
                raise ValidationError(msg)

    @api.depends("donation_ids", "donation_ids.amount", "donation_ids.state")
    def _compute_current_amount(self):
        for rec in self:
            rec.current_amount = sum(
                d.amount or 0.0 for d in rec.donation_ids if d.state == "confirmed"
            )

    @api.depends("current_amount", "target_amount")
    def _compute_progress(self):
        for rec in self:
            if rec.target_amount and rec.target_amount > 0:
                rec.progress_pct = (rec.current_amount / rec.target_amount) * 100.0
            else:
                rec.progress_pct = 0.0
