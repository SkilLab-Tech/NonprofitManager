"""Processing log (LGPD Art. 37).

Records WHAT personal data is processed, WHY, on WHAT lawful basis, for HOW
long, and WHO it's shared with. Seeded with default entries at install time
(see data/lgpd_processing_log_seed.xml); modules touching new data classes
add entries to keep the log current.
"""

from __future__ import annotations

from odoo import fields, models

from .lgpd_consent import LAWFUL_BASES


class UsbeaLGPDProcessingLog(models.Model):
    _name = "usbea.lgpd.processing_log"
    _description = "LGPD Processing Activity Record (Art. 37)"
    _order = "data_class, purpose"

    name = fields.Char(required=True)
    data_class = fields.Char(
        required=True,
        help="The category of personal data processed (e.g. 'donor contact info').",
    )
    purpose = fields.Text(required=True, help="Why this data is processed.")
    lawful_basis = fields.Selection(LAWFUL_BASES, required=True)
    retention_period = fields.Char(
        help="How long the data is retained (e.g. '5 years post last donation').",
    )
    sharing_recipients = fields.Char(
        help="Whether the data is shared and with whom (e.g. 'Mailchimp; Anthropic via usbea_ai with PII redaction').",
    )
    international_transfer = fields.Boolean(
        help="True if data crosses Brazilian borders. Triggers Art. 33 compliance review.",
    )
    transfer_safeguards = fields.Text(
        help="If international_transfer is True, what safeguards apply (SCCs, redaction, anonymization).",
    )
    module_origin = fields.Char(
        help="Which custom module owns this data class (e.g. 'usbea_crm').",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
