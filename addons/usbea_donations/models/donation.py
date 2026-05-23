"""Single donation entity. Reconciles against account.move."""

from __future__ import annotations

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..utils.cpf_formatter import classify, format_any
from ..utils.receipt_validator import ReceiptCandidate
from ..utils.receipt_validator import validate as validate_receipt

_logger = logging.getLogger(__name__)


PAYMENT_METHODS = [
    ("pix_one_off", "PIX (one-off)"),
    ("pix_recurring", "PIX (recurring)"),
    ("cc_one_off", "Credit card (one-off)"),
    ("cc_recurring", "Credit card (recurring)"),
    ("boleto", "Boleto"),
    ("cash", "Cash"),
    ("in_kind", "In-kind"),
    ("other", "Other"),
]

RAILS = [
    ("doare", "Doare"),
    ("mercado_pago", "Mercado Pago"),
    ("manual", "Manual entry"),
    ("other", "Other"),
]


class UsbeaDonation(models.Model):
    _name = "usbea.donation"
    _description = "USBEA Donation"
    _order = "donation_date desc, id desc"
    _rec_name = "display_name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, copy=False, default=lambda self: _("New"))
    donor_partner_id = fields.Many2one(
        "res.partner",
        string="Donor",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    donor_doc = fields.Char(
        string="Donor CPF/CNPJ",
        compute="_compute_donor_doc",
        store=True,
        readonly=False,
        help="Snapshot at donation time so historical receipts remain valid if the partner's vat changes.",
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    donation_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    payment_method = fields.Selection(PAYMENT_METHODS, required=True, default="pix_one_off")
    rail = fields.Selection(RAILS, default="manual", required=True)
    external_ref = fields.Char(
        copy=False,
        help="Provider-side ID for reconciliation and idempotency.",
    )
    recurring_plan_id = fields.Many2one(
        "usbea.donation.recurring_plan",
        help="Parent recurring plan if this donation is one of its charges.",
        ondelete="set null",
        index=True,
    )
    p2p_campaign_id = fields.Many2one(
        "usbea.donation.p2p_campaign",
        ondelete="set null",
        index=True,
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="pending",
        required=True,
        tracking=True,
        index=True,
    )
    account_move_id = fields.Many2one(
        "account.move",
        readonly=True,
        copy=False,
        help="Accounting entry created on confirmation.",
    )
    receipt_template_id = fields.Many2one("usbea.donation.receipt_template")
    receipt_issued = fields.Boolean(default=False)
    receipt_pdf = fields.Binary(attachment=True, readonly=True)
    receipt_pdf_name = fields.Char(default="receipt.pdf")
    receipt_issued_at = fields.Datetime(readonly=True)
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    display_name = fields.Char(compute="_compute_display_name")

    _sql_constraints = [
        (
            "external_ref_unique",
            "UNIQUE(rail, external_ref)",
            "external_ref must be unique per rail (webhook idempotency).",
        ),
    ]

    @api.depends("name", "donor_partner_id", "amount", "currency_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s — %s — %s %s" % (
                rec.name or "?",
                rec.donor_partner_id.name or "?",
                rec.currency_id.symbol if rec.currency_id else "",
                rec.amount or 0.0,
            )

    @api.depends("donor_partner_id", "donor_partner_id.vat")
    def _compute_donor_doc(self):
        for rec in self:
            if not rec.donor_doc and rec.donor_partner_id:
                rec.donor_doc = format_any(rec.donor_partner_id.vat or "")

    @api.constrains("donor_doc", "state")
    def _check_donor_doc_for_confirmed(self):
        for rec in self:
            if rec.state == "confirmed" and rec.donor_doc:
                kind = classify(rec.donor_doc)
                if not kind:
                    msg = _(
                        "Confirmed donations require a valid CPF or CNPJ — "
                        "check-digit validation failed for '%s'.",
                    ) % rec.donor_doc
                    raise ValidationError(msg)

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount is not None and rec.amount <= 0:
                msg = _("Donation amount must be > 0.")
                raise ValidationError(msg)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("usbea.donation") or "DON/000"
                )
        return super().create(vals_list)

    # ----- State transitions -----

    def action_confirm(self):
        for rec in self:
            if rec.state != "pending":
                continue
            rec.write({"state": "confirmed"})
            rec._post_engagement_event()

    def action_fail(self):
        for rec in self:
            rec.write({"state": "failed"})

    def action_refund(self):
        for rec in self:
            if rec.state != "confirmed":
                msg = _("Only confirmed donations can be refunded.")
                raise UserError(msg)
            rec.write({"state": "refunded"})

    # ----- Receipt issuance (IRPF) -----

    def action_issue_receipt(self):
        for rec in self:
            rec._issue_receipt()

    def _issue_receipt(self):
        self.ensure_one()
        if self.state != "confirmed":
            msg = _("Receipts are only issued on confirmed donations.")
            raise UserError(msg)
        if self.receipt_issued:
            return
        company = self.company_id or self.env.company
        oscip = self.env["usbea.oscip.status"].sudo().search(
            [("company_id", "=", company.id)], limit=1,
        )
        candidate = ReceiptCandidate(
            org_cnpj=company.vat or "",
            org_name=company.name or "",
            donor_doc=self.donor_doc or "",
            donor_name=self.donor_partner_id.name or "",
            amount_brl=float(self.amount or 0.0),
            donation_date=self.donation_date,
            oscip_active=bool(oscip and oscip.is_certified),
            upf_active=bool(oscip and oscip.upf_certified),
            oscip_article_ref=(self.receipt_template_id.oscip_article_ref or "")
            if self.receipt_template_id
            else "",
        )
        errors = validate_receipt(candidate)
        if errors:
            msg = _("Cannot issue IRPF receipt:\n- %s") % "\n- ".join(errors)
            raise UserError(msg)
        # Receipt PDF generation is delegated to a future report — for now
        # we mark the receipt as issued and record the moment.
        self.write(
            {
                "receipt_issued": True,
                "receipt_issued_at": fields.Datetime.now(),
            },
        )

    # ----- Engagement event hook into CRM -----

    def _post_engagement_event(self):
        self.ensure_one()
        EngagementEvent = self.env.get("usbea.engagement.event")
        if EngagementEvent is None:
            return
        event_type = "donation_recurring" if self.recurring_plan_id else "donation"
        EngagementEvent.sudo().create(
            {
                "partner_id": self.donor_partner_id.id,
                "event_type": event_type,
                "when": self.donation_date,
                "source": f"donation:{self.name}",
                "notes": f"Confirmed donation via {self.rail}",
            },
        )

    @api.model
    def _get_lgpd_data_for_partner(self, partner_id: int) -> dict:
        rows = self.sudo().search_read(
            [("donor_partner_id", "=", partner_id)],
            ["name", "donation_date", "amount", "state", "rail", "payment_method"],
        )
        return {"donations": rows, "count": len(rows)}

    # ----- Helpers used by webhook controllers -----

    @api.model
    def upsert_from_webhook(
        self,
        *,
        rail: str,
        external_ref: str,
        donor_partner: object,
        amount: float,
        donation_date,
        payment_method: str,
        state: str = "confirmed",
        recurring_plan: object = None,
    ):
        """Idempotent webhook handler. Returns the donation record."""
        existing = self.sudo().search(
            [("rail", "=", rail), ("external_ref", "=", external_ref)], limit=1,
        )
        if existing:
            return existing
        rec = self.sudo().create(
            {
                "donor_partner_id": donor_partner.id if donor_partner else False,
                "amount": amount,
                "donation_date": donation_date,
                "payment_method": payment_method,
                "rail": rail,
                "external_ref": external_ref,
                "state": "pending",
                "recurring_plan_id": recurring_plan.id if recurring_plan else False,
            },
        )
        if state == "confirmed":
            rec.action_confirm()
        return rec
