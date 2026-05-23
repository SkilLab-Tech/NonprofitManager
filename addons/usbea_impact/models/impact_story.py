"""Qualitative beneficiary stories.

A story carries narrative + media. **No beneficiary name** is stored by
default — the narrative is anonymized using deterministic tokens (BENEF_1,
BENEF_2…). If a beneficiary explicitly consents to identification (scope
``media_publication`` on usbea.lgpd.consent), the model flips
``identified_with_consent=True`` and the rendering pipeline includes the
real name in publication outputs.
"""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UsbeaImpactStory(models.Model):
    _name = "usbea.impact.story"
    _description = "Impact Story"
    _order = "create_date desc"
    _rec_name = "title"

    title = fields.Char(required=True)
    program_id = fields.Many2one("usbea.program", ondelete="restrict")
    beneficiary_partner_id = fields.Many2one(
        "res.partner",
        ondelete="restrict",
        help="The beneficiary (kept for internal record). Their name is NOT included "
        "in published outputs unless identified_with_consent is True.",
    )
    consent_id = fields.Many2one(
        "usbea.lgpd.consent",
        domain="[('partner_id', '=', beneficiary_partner_id), ('state', '=', 'active'), ('scope', '=', 'media_publication')]",
        help="Active LGPD consent for media publication. Required to set identified_with_consent.",
    )
    identified_with_consent = fields.Boolean(
        default=False,
        help="Only True when a matching active consent exists. Gated by @api.constrains.",
    )
    narrative = fields.Html(required=True)
    period = fields.Char(help="When the story took place (e.g. 'Q1 2026', 'Jan-Mar 2026').")
    media_attachment_ids = fields.Many2many("ir.attachment", string="Photos / videos")
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.constrains("identified_with_consent", "consent_id", "beneficiary_partner_id")
    def _check_consent_gate(self):
        """Publishing with name requires matching active consent."""
        for rec in self:
            if not rec.identified_with_consent:
                continue
            if not rec.consent_id or rec.consent_id.state != "active":
                msg = _(
                    "Cannot identify beneficiary without an active LGPD consent "
                    "for scope 'media_publication'.",
                )
                raise ValidationError(msg)
            if rec.consent_id.partner_id.id != rec.beneficiary_partner_id.id:
                msg = _(
                    "consent_id partner must match beneficiary_partner_id.",
                )
                raise ValidationError(msg)
