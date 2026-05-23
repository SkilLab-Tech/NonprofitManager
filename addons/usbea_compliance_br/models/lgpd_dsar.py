"""Data Subject Access Request workflow (LGPD Art. 18).

State machine: received → processing → fulfilled | denied
SLA: 15 calendar days from received_at to fulfilled_at (LGPD Art. 19 §1).
"""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..utils.dsar_sla import compute_sla_deadline, days_remaining, sla_status

REQUEST_TYPES = [
    ("access", "Access / confirmation"),
    ("portability", "Data portability"),
    ("correction", "Correction"),
    ("deletion", "Deletion / erasure"),
    ("anonymization", "Anonymization"),
    ("processing_info", "Information about processing"),
    ("revoke_consent", "Consent revocation"),
]


class UsbeaLGPDDSAR(models.Model):
    _name = "usbea.lgpd.dsar"
    _description = "LGPD Data Subject Access Request"
    _order = "received_at desc"
    _rec_name = "display_name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    request_type = fields.Selection(REQUEST_TYPES, required=True, tracking=True)
    received_at = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    received_via = fields.Selection(
        [
            ("email", "Email"),
            ("form", "Web form"),
            ("phone", "Phone"),
            ("letter", "Letter / written"),
            ("in_person", "In-person"),
            ("anpd_referral", "ANPD referral"),
        ],
        default="email",
        required=True,
    )
    state = fields.Selection(
        [
            ("received", "Received"),
            ("processing", "Processing"),
            ("fulfilled", "Fulfilled"),
            ("denied", "Denied"),
            ("withdrawn", "Withdrawn"),
        ],
        default="received",
        required=True,
        tracking=True,
        index=True,
    )
    sla_deadline = fields.Date(
        compute="_compute_sla",
        store=True,
        help="Legal deadline (15 days from received_at per LGPD Art. 19 §1).",
    )
    sla_days_remaining = fields.Integer(compute="_compute_sla")
    sla_status_indicator = fields.Selection(
        [
            ("green", "Green — on track"),
            ("yellow", "Yellow — approaching deadline"),
            ("red", "Red — imminent breach"),
            ("overdue", "Overdue"),
            ("fulfilled", "Fulfilled"),
        ],
        compute="_compute_sla",
        store=True,
    )
    fulfilled_at = fields.Date(tracking=True)
    denied_reason = fields.Text()
    notes = fields.Html()
    assigned_user_id = fields.Many2one("res.users", tracking=True)
    aggregated_data = fields.Text(
        help="JSON snapshot of partner data aggregated at fulfillment time.",
    )

    display_name = fields.Char(compute="_compute_display_name")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.depends("name", "partner_id", "request_type")
    def _compute_display_name(self):
        type_labels = dict(REQUEST_TYPES)
        for rec in self:
            rec.display_name = "%s — %s — %s" % (
                rec.name or "",
                rec.partner_id.name or "?",
                type_labels.get(rec.request_type, rec.request_type or ""),
            )

    @api.depends("received_at", "fulfilled_at", "state")
    def _compute_sla(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.received_at:
                rec.sla_deadline = False
                rec.sla_days_remaining = 0
                rec.sla_status_indicator = "green"
                continue
            rec.sla_deadline = compute_sla_deadline(rec.received_at)
            rec.sla_days_remaining = days_remaining(rec.received_at, today)
            rec.sla_status_indicator = sla_status(
                rec.received_at, today, fulfilled=rec.state == "fulfilled",
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("usbea.lgpd.dsar") or "DSAR/000"
        return super().create(vals_list)

    # ----- State transitions -----

    def action_start_processing(self):
        for rec in self:
            if rec.state != "received":
                msg = _("Only received DSARs can transition to processing.")
                raise UserError(msg)
            rec.state = "processing"

    def action_fulfill(self):
        for rec in self:
            if rec.state not in ("received", "processing"):
                msg = _("Only received or processing DSARs can be fulfilled.")
                raise UserError(msg)
            # Aggregate partner data right before fulfillment (snapshot).
            aggregate = self.env["usbea.lgpd.dsar_aggregator"].aggregate(rec.partner_id.id)
            rec.write(
                {
                    "state": "fulfilled",
                    "fulfilled_at": fields.Date.context_today(self),
                    "aggregated_data": aggregate,
                },
            )

    def action_deny(self):
        for rec in self:
            if not rec.denied_reason:
                msg = _("Provide a reason before denying a DSAR.")
                raise UserError(msg)
            rec.state = "denied"

    def action_withdraw(self):
        for rec in self:
            rec.state = "withdrawn"
