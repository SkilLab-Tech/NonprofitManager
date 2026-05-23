"""IRPF-compliant receipt templates."""

from __future__ import annotations

from odoo import fields, models


class UsbeaDonationReceiptTemplate(models.Model):
    _name = "usbea.donation.receipt_template"
    _description = "Donation Receipt Template (IRPF-compliant)"
    _order = "active desc, name"

    name = fields.Char(required=True)
    technical_key = fields.Char(required=True, copy=False)
    org_cnpj_field = fields.Char(
        default="vat",
        help="Field on res.company to read the issuing CNPJ from (default: vat).",
    )
    oscip_article_ref = fields.Char(
        required=True,
        help="OSCIP qualifying article reference (e.g. 'Lei 9.790/99 Art. 3, IV — Educacao').",
    )
    irpf_article_ref = fields.Char(
        default="Lei 9.249/95 art. 13, §2°, II",
        help="Tax-deduction legal article reference cited on the receipt.",
    )
    footer_text = fields.Text(
        help="Footer note printed on the receipt (e.g. 'Sua doacao pode ser deduzida no IRPF...').",
    )
    locale = fields.Selection(
        [("pt_BR", "Portuguese"), ("en_US", "English")],
        default="pt_BR",
        required=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("technical_key_unique", "UNIQUE(technical_key)", "Template key must be unique."),
    ]
