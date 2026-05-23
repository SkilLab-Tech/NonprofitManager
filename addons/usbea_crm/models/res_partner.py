"""Extensions to res.partner for USBEA archetypes + engagement + LGPD gate."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..utils.engagement_scoring import EngagementEvent, compute_engagement_score

ARCHETYPES = [
    ("donor", "Donor (individual/corporate)"),
    ("funder", "Funder (foundation/agency)"),
    ("staff", "Staff/Diretoria"),
    ("grantee", "Grantee (alumni/entity)"),
    ("volunteer", "Volunteer"),
]

CULTIVATION_STAGES = [
    ("research", "Research"),
    ("qualification", "Qualification"),
    ("cultivation", "Cultivation"),
    ("solicitation", "Solicitation"),
    ("stewardship", "Stewardship"),
    ("dormant", "Dormant"),
]

# Archetypes that require an active LGPD consent record to be saved.
# Staff records are governed by their employment contract (contract lawful basis).
ARCHETYPES_REQUIRING_CONSENT = ("donor", "volunteer", "grantee")


class ResPartner(models.Model):
    _inherit = "res.partner"

    usbea_archetype = fields.Selection(
        ARCHETYPES,
        string="USBEA archetype",
        index=True,
    )
    cultivation_stage = fields.Selection(
        CULTIVATION_STAGES,
        default="research",
        tracking=True,
    )
    engagement_score = fields.Integer(
        compute="_compute_engagement_score",
        store=True,
        help="Computed 0-100 engagement score over the past 365 days. "
        "Higher = more engaged.",
    )
    engagement_score_updated_at = fields.Datetime(readonly=True)
    soft_credit_partner_ids = fields.Many2many(
        "res.partner",
        relation="usbea_partner_softcredit_rel",
        column1="partner_id",
        column2="credited_partner_id",
        string="Soft-credit partners",
        help="Other partners who share credit for this partner's giving "
        "(e.g. spouse, parent company, joint funder).",
    )
    cultivation_move_ids = fields.One2many(
        "usbea.cultivation.move",
        "partner_id",
        string="Cultivation moves",
    )
    engagement_event_ids = fields.One2many(
        "usbea.engagement.event",
        "partner_id",
        string="Engagement events",
    )
    has_active_lgpd_consent = fields.Boolean(
        compute="_compute_has_active_lgpd_consent",
        help="True if at least one active consent exists for this partner.",
    )

    @api.depends("engagement_event_ids", "engagement_event_ids.event_type", "engagement_event_ids.when")
    def _compute_engagement_score(self):
        today = fields.Date.context_today(self)
        for rec in self:
            events = [
                EngagementEvent(
                    event_type=e.event_type,
                    when=e.when,
                    score_delta_override=(
                        e.score_delta_override if e.score_delta_override else None
                    ),
                )
                for e in rec.engagement_event_ids
            ]
            rec.engagement_score = compute_engagement_score(events, today)
            rec.engagement_score_updated_at = fields.Datetime.now()

    def _compute_has_active_lgpd_consent(self):
        Consent = self.env["usbea.lgpd.consent"].sudo()
        for rec in self:
            rec.has_active_lgpd_consent = bool(
                Consent.search_count(
                    [("partner_id", "=", rec.id), ("state", "=", "active")],
                    limit=1,
                ),
            )

    @api.constrains("usbea_archetype")
    def _check_lgpd_consent_gate(self):
        """For archetypes requiring consent, refuse the write if none exists.

        This is the LGPD Art. 7-I gate: we cannot label someone a donor (and
        process their data on the basis of consent) without recording that
        consent. The error guides the user to create the consent first.
        """
        Consent = self.env["usbea.lgpd.consent"].sudo()
        for rec in self:
            if rec.usbea_archetype in ARCHETYPES_REQUIRING_CONSENT:
                has_consent = Consent.search_count(
                    [("partner_id", "=", rec.id), ("state", "=", "active")],
                    limit=1,
                )
                if not has_consent:
                    msg = _(
                        "LGPD gate: cannot set %(partner)s as %(archetype)s without an "
                        "active consent record. Create an usbea.lgpd.consent first "
                        "(e.g. for scope 'newsletter' or 'sharing_with_partners') and "
                        "then re-apply the archetype.",
                        partner=rec.display_name,
                        archetype=dict(ARCHETYPES).get(rec.usbea_archetype),
                    )
                    raise ValidationError(msg)

    @api.model
    def _get_lgpd_data_for_partner(self, partner_id: int) -> dict:
        """DSAR adapter — used by usbea.lgpd.dsar_aggregator."""
        rec = self.sudo().browse(partner_id)
        if not rec.exists():
            return {"exists": False}
        return {
            "exists": True,
            "name": rec.display_name,
            "archetype": rec.usbea_archetype,
            "cultivation_stage": rec.cultivation_stage,
            "engagement_score": rec.engagement_score,
            "engagement_events_count": len(rec.engagement_event_ids),
            "cultivation_moves_count": len(rec.cultivation_move_ids),
            "soft_credit_partner_ids": rec.soft_credit_partner_ids.ids,
        }

    def action_open_create_consent(self):
        """Convenience action: pre-fill an LGPD consent form for this partner."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "usbea.lgpd.consent",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "default_granted_at": fields.Datetime.now(),
            },
        }
