"""Recurring giving plans — PIX Automatico (Doare) and Mercado Pago."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError

FREQUENCIES = [
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("biannual", "Biannual"),
    ("annual", "Annual"),
]

# Mapping to frequency_months for Mercado Pago + month-step for next_charge_date.
FREQUENCY_MONTHS = {
    "monthly": 1,
    "quarterly": 3,
    "biannual": 6,
    "annual": 12,
}


class UsbeaDonationRecurringPlan(models.Model):
    _name = "usbea.donation.recurring_plan"
    _description = "USBEA Donation Recurring Plan"
    _order = "next_charge_date asc, id desc"
    _rec_name = "display_name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, copy=False, default=lambda self: _("New"))
    donor_partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    amount = fields.Monetary(currency_field="currency_id", required=True, tracking=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    frequency = fields.Selection(FREQUENCIES, default="monthly", required=True, tracking=True)
    rail = fields.Selection(
        [("doare", "Doare PIX Automatico"), ("mercado_pago", "Mercado Pago Subscriptions v2")],
        required=True,
        tracking=True,
    )
    external_subscription_id = fields.Char(
        copy=False,
        readonly=True,
        help="Provider-side subscription ID.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_confirmation", "Pending donor confirmation"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("cancelled", "Cancelled"),
            ("failed", "Failed"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    started_at = fields.Date(tracking=True)
    cancelled_at = fields.Date(tracking=True)
    next_charge_date = fields.Date(tracking=True)
    notes = fields.Text()
    donation_ids = fields.One2many("usbea.donation", "recurring_plan_id")
    donation_count = fields.Integer(compute="_compute_donation_count")
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("name", "donor_partner_id", "amount", "frequency", "rail")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s — %s — %s/%s [%s]" % (
                rec.name or "?",
                rec.donor_partner_id.name or "?",
                rec.amount or 0.0,
                rec.frequency or "",
                rec.rail or "",
            )

    @api.depends("donation_ids")
    def _compute_donation_count(self):
        for rec in self:
            rec.donation_count = len(rec.donation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("usbea.donation.recurring_plan")
                    or "RP/000"
                )
        return super().create(vals_list)

    def action_activate(self):
        for rec in self:
            if rec.state in ("active",):
                continue
            rec.write(
                {
                    "state": "active",
                    "started_at": rec.started_at or fields.Date.context_today(rec),
                },
            )

    def action_pause(self):
        for rec in self:
            if rec.state != "active":
                msg = _("Only active plans can be paused.")
                raise UserError(msg)
            rec.write({"state": "paused"})

    def action_resume(self):
        for rec in self:
            if rec.state != "paused":
                msg = _("Only paused plans can be resumed.")
                raise UserError(msg)
            rec.write({"state": "active"})

    def action_cancel(self):
        for rec in self:
            if rec.state == "cancelled":
                continue
            rec.write(
                {"state": "cancelled", "cancelled_at": fields.Date.context_today(rec)},
            )
