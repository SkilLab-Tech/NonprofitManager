"""Moves management — classic fundraising cultivation cycle.

A 'move' is a discrete cultivation action (research call, donor visit,
gift solicitation, thank-you letter). Each move advances or stays at the
same stage and feeds the engagement score.
"""

from __future__ import annotations

from odoo import api, fields, models

MOVE_TYPES = [
    ("research", "Research"),
    ("qualification_call", "Qualification call"),
    ("introduction", "Introduction meeting"),
    ("site_visit", "Site visit / event invite"),
    ("relationship_update", "Relationship update / coffee"),
    ("proposal_discussion", "Proposal discussion"),
    ("solicitation", "Formal solicitation / ask"),
    ("close", "Gift closed"),
    ("thank_you", "Thank-you / stewardship"),
    ("annual_report", "Annual report / impact share"),
    ("other", "Other"),
]


class UsbeaCultivationMove(models.Model):
    _name = "usbea.cultivation.move"
    _description = "Donor / Funder Cultivation Move"
    _order = "occurred_on desc, id desc"
    _inherit = ["mail.thread"]

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_type = fields.Selection(MOVE_TYPES, required=True, tracking=True)
    occurred_on = fields.Date(default=fields.Date.context_today, required=True)
    next_move_due = fields.Date()
    assigned_user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        tracking=True,
    )
    summary = fields.Char(required=True)
    outcome = fields.Text()
    amount_discussed = fields.Monetary(
        currency_field="currency_id",
        help="Amount discussed/asked at this move, if applicable.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    moved_to_stage = fields.Selection(
        [
            ("research", "Research"),
            ("qualification", "Qualification"),
            ("cultivation", "Cultivation"),
            ("solicitation", "Solicitation"),
            ("stewardship", "Stewardship"),
            ("dormant", "Dormant"),
        ],
        help="Cultivation stage after this move. Updates partner.cultivation_stage on save.",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._propagate_stage_to_partner()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "moved_to_stage" in vals:
            self._propagate_stage_to_partner()
        return result

    def _propagate_stage_to_partner(self):
        for rec in self:
            if rec.moved_to_stage and rec.partner_id:
                rec.partner_id.write({"cultivation_stage": rec.moved_to_stage})
