"""Receita Federal DIRF preparation.

Annual DIRF filing summarizes IR withheld on payments to beneficiaries.
This model is a working table — actual TXT generation in the Receita
Federal layout is a wizard (added in Phase 5 when payment rails land).
"""

from __future__ import annotations

from odoo import fields, models


class UsbeaReceitaDirfLine(models.Model):
    _name = "usbea.receita.dirf_line"
    _description = "DIRF preparation line"
    _order = "calendar_year desc, beneficiary_id"

    calendar_year = fields.Integer(required=True, index=True)
    beneficiary_id = fields.Many2one("res.partner", required=True)
    beneficiary_cpf_cnpj = fields.Char(
        help="CPF or CNPJ of the beneficiary — snapshot at filing time.",
    )
    gross_amount = fields.Monetary(currency_field="currency_id", required=True)
    ir_withheld = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    code_natureza = fields.Char(
        string="Natureza do rendimento",
        help="Código de natureza per Receita Federal IN updated annually.",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
