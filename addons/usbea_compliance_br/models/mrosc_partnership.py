"""MROSC partnership tracking (Lei 13.019/2014).

USBEA's public-sector partnerships fall under MROSC. Each instrumento jurídico
(termo de colaboração / fomento / acordo de cooperação) carries its own
prestação de contas state machine.
"""

from __future__ import annotations

from odoo import fields, models

PARTNERSHIP_TYPES = [
    ("termo_colaboracao", "Termo de Colaboração"),
    ("termo_fomento", "Termo de Fomento"),
    ("acordo_cooperacao", "Acordo de Cooperação (sem repasse financeiro)"),
]

PRESTACAO_STATES = [
    ("not_due", "Not due yet"),
    ("preparing", "Preparing"),
    ("under_review", "Under internal review"),
    ("submitted", "Submitted to public administration"),
    ("approved", "Approved"),
    ("returned_for_correction", "Returned for correction"),
    ("rejected", "Rejected"),
]


class UsbeaMROSCPartnership(models.Model):
    _name = "usbea.mrosc.partnership"
    _description = "MROSC Public-Sector Partnership"
    _order = "start_date desc, id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    partner_id = fields.Many2one(
        "res.partner",
        domain="[('is_company', '=', True)]",
        required=True,
        help="Public administration entity (funder).",
    )
    partnership_type = fields.Selection(PARTNERSHIP_TYPES, required=True)
    instrumento_juridico_ref = fields.Char(
        string="Instrumento jurídico ref.",
        required=True,
        copy=False,
    )
    chamamento_publico_ref = fields.Char(
        string="Chamamento público ref.",
        help="If applicable — chamamento público process reference.",
    )
    start_date = fields.Date(required=True, tracking=True)
    end_date = fields.Date(tracking=True)
    total_value_brl = fields.Monetary(
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    object_description = fields.Text(string="Objeto da parceria")
    prestacao_contas_state = fields.Selection(
        PRESTACAO_STATES,
        default="not_due",
        tracking=True,
    )
    prestacao_contas_due_date = fields.Date(tracking=True)
    transparency_published = fields.Boolean(
        help="Whether this instrumento is published on USBEA's transparency portal "
        "as required by Lei 13.019 Art. 11.",
    )
    notes = fields.Html()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    is_active_now = fields.Boolean(compute="_compute_is_active_now", search="_search_is_active_now")

    def _compute_is_active_now(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_active_now = bool(
                rec.start_date and rec.start_date <= today
                and (not rec.end_date or rec.end_date >= today),
            )

    @staticmethod
    def _search_is_active_now(operator, value):
        today = fields.Date.context_today(self=None)  # placeholder; Odoo passes self at runtime
        # We delegate to a domain expression on start/end.
        match = [
            ("start_date", "<=", today),
            "|",
            ("end_date", "=", False),
            ("end_date", ">=", today),
        ]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return match
        return ["!", "&", "&", *match]
