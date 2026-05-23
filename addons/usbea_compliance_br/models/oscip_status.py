"""OSCIP (Lei 9.790/1999) certification status tracker — singleton per company."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

QUALIFYING_FINALITIES = [
    ("social_assistance", "Promoção de assistência social"),
    ("culture", "Promoção da cultura"),
    ("education", "Promoção gratuita da educação"),
    ("health", "Promoção gratuita da saúde"),
    ("environment", "Defesa do meio ambiente"),
    ("volunteer", "Promoção do voluntariado"),
    ("economic_dev", "Promoção do desenvolvimento econômico e social"),
    ("citizenship", "Promoção da ética, paz, cidadania, direitos humanos"),
    ("research", "Estudos, pesquisas, desenvolvimento de tecnologias alternativas"),
]


class UsbeaOSCIPStatus(models.Model):
    _name = "usbea.oscip.status"
    _description = "OSCIP Certification Status"
    _order = "company_id"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    is_certified = fields.Boolean(string="OSCIP certified", tracking=True)
    granted_at = fields.Date()
    granted_by = fields.Char(default="Ministério da Justiça")
    renewed_until = fields.Date()
    upf_certified = fields.Boolean(
        string="Utilidade Pública Federal",
        help="Cumulative status with OSCIP — required for donor IRPF deduction.",
    )
    qualifying_finalities = fields.Many2many(
        "usbea.oscip.finality",
        string="Qualifying finalities (Art. 3)",
    )
    notes = fields.Html()

    _sql_constraints = [
        ("one_per_company", "UNIQUE(company_id)", "There can be only one OSCIP status per company."),
    ]

    @api.constrains("granted_at", "renewed_until")
    def _check_dates(self):
        for rec in self:
            if rec.granted_at and rec.renewed_until and rec.renewed_until < rec.granted_at:
                msg = _("renewed_until cannot be before granted_at.")
                raise ValidationError(msg)


class UsbeaOSCIPFinality(models.Model):
    _name = "usbea.oscip.finality"
    _description = "OSCIP Qualifying Finality (Lei 9.790/99 Art. 3)"

    code = fields.Selection(QUALIFYING_FINALITIES, required=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("code")
    def _compute_name(self):
        labels = dict(QUALIFYING_FINALITIES)
        for rec in self:
            rec.name = labels.get(rec.code, rec.code or "")
