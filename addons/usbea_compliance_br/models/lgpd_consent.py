"""LGPD consent registry.

Per LGPD Art. 7-8, every personal-data processing requires a lawful basis.
Consent is one of several bases (also: legitimate interest, contract execution,
legal obligation, protection of life, etc.). This model tracks consent
granted by data subjects, scoped to specific purposes.

A revoked consent does NOT erase historical processing under that consent —
it stops future processing. Revocation is event-sourced (revoked_at, reason).
"""

from __future__ import annotations

from odoo import api, fields, models

LAWFUL_BASES = [
    ("consent", "Consent (Art. 7, I)"),
    ("legal_obligation", "Legal obligation (Art. 7, II)"),
    ("public_policy", "Public policy execution (Art. 7, III)"),
    ("research", "Research by research org (Art. 7, IV)"),
    ("contract", "Contract execution (Art. 7, V)"),
    ("legal_process", "Legal process (Art. 7, VI)"),
    ("life_protection", "Life protection (Art. 7, VII)"),
    ("health_protection", "Health protection (Art. 7, VIII)"),
    ("legitimate_interest", "Legitimate interest (Art. 7, IX)"),
    ("credit_protection", "Credit protection (Art. 7, X)"),
]

CONSENT_SCOPES = [
    ("marketing", "Marketing communications"),
    ("newsletter", "Newsletter"),
    ("events", "Event invitations"),
    ("research", "Research and surveys"),
    ("sharing_with_partners", "Sharing with partners/funders"),
    ("media_publication", "Media publication (photos, videos, stories)"),
    ("alumni_directory", "Alumni directory listing"),
]


class UsbeaLGPDConsent(models.Model):
    _name = "usbea.lgpd.consent"
    _description = "LGPD Consent Record"
    _order = "granted_at desc, id desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    scope = fields.Selection(CONSENT_SCOPES, required=True, index=True)
    lawful_basis = fields.Selection(
        LAWFUL_BASES,
        required=True,
        default="consent",
        help="LGPD Art. 7 lawful basis. 'Consent' requires affirmative action; "
        "other bases do not require explicit consent but still must be documented.",
    )
    granted_at = fields.Datetime(required=True, default=fields.Datetime.now)
    granted_via = fields.Selection(
        [
            ("in_person", "In-person"),
            ("email", "Email"),
            ("form", "Online form"),
            ("contract", "Contract clause"),
            ("verbal", "Verbal (witnessed)"),
            ("legacy", "Legacy / pre-LGPD (best-effort)"),
        ],
        default="form",
        required=True,
    )
    granted_by = fields.Many2one(
        "res.users",
        string="Recorded by",
        default=lambda self: self.env.user,
    )
    expires_at = fields.Datetime(
        help="Optional expiry date — after which this consent must be re-obtained.",
    )
    revoked_at = fields.Datetime()
    revoked_reason = fields.Char()
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("active", "Active"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        compute="_compute_state",
        store=True,
        index=True,
    )

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("partner_id", "scope", "state")
    def _compute_display_name(self):
        scope_labels = dict(CONSENT_SCOPES)
        for rec in self:
            scope_label = scope_labels.get(rec.scope, rec.scope or "")
            partner_name = rec.partner_id.name or "?"
            rec.display_name = "%s — %s [%s]" % (partner_name, scope_label, rec.state or "active")

    @api.depends("revoked_at", "expires_at")
    def _compute_state(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.revoked_at:
                rec.state = "revoked"
            elif rec.expires_at and rec.expires_at < now:
                rec.state = "expired"
            else:
                rec.state = "active"

    def action_revoke(self, reason: str = ""):
        """Revoke this consent. Cannot be un-revoked — must create a new consent."""
        for rec in self:
            if rec.revoked_at:
                continue
            rec.write(
                {
                    "revoked_at": fields.Datetime.now(),
                    "revoked_reason": reason or "(no reason provided)",
                },
            )

    @api.model
    def has_active_consent(self, partner_id: int, scope: str) -> bool:
        """Helper: True if partner has at least one active consent for scope."""
        return bool(
            self.search_count(
                [
                    ("partner_id", "=", partner_id),
                    ("scope", "=", scope),
                    ("state", "=", "active"),
                ],
            ),
        )
