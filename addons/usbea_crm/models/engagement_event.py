"""Engagement event log — raw signals that feed the partner's engagement score.

Sources: donations, event attendance, email opens/replies, manual notes,
meeting attendance, no-shows. Events are append-only; deletion only for
LGPD DSAR fulfillment.
"""

from __future__ import annotations

from odoo import fields, models

from ..utils.engagement_scoring import EVENT_TYPE_WEIGHTS


class UsbeaEngagementEvent(models.Model):
    _name = "usbea.engagement.event"
    _description = "USBEA Engagement Event"
    _order = "when desc, id desc"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    event_type = fields.Selection(
        [(k, k.replace("_", " ").title()) for k in EVENT_TYPE_WEIGHTS],
        required=True,
        index=True,
    )
    when = fields.Date(default=fields.Date.context_today, required=True, index=True)
    source = fields.Char(
        help="Origin of the event (e.g. 'donation:#1234', 'event:bsb_meetup_2026', 'manual').",
    )
    notes = fields.Char()
    score_delta_override = fields.Float(
        help="If set, overrides the default weight for this event type.",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
