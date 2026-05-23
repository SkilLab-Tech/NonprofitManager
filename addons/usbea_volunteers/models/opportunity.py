"""Volunteer opportunity — a specific need posted by a program."""

from __future__ import annotations

from datetime import time

from odoo import _, api, fields, models

from ..utils.matching import (
    Opportunity,
    OpportunityWindow,
    Volunteer,
    VolunteerSlot,
    rank_matches,
)


class UsbeaVolunteerOpportunity(models.Model):
    _name = "usbea.volunteer.opportunity"
    _description = "Volunteer Opportunity"
    _order = "starts_on, name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    program_id = fields.Many2one("usbea.program", required=True, ondelete="restrict")
    required_skill_ids = fields.Many2many(
        "usbea.volunteer.skill",
        string="Required skills",
    )
    weekday = fields.Selection(
        [
            ("0", "Monday"), ("1", "Tuesday"), ("2", "Wednesday"),
            ("3", "Thursday"), ("4", "Friday"), ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        required=True,
    )
    start_hour = fields.Float(required=True)
    end_hour = fields.Float(required=True)
    starts_on = fields.Date()
    ends_on = fields.Date()
    requires_background_check = fields.Boolean(default=False)
    description = fields.Text()
    state = fields.Selection(
        [("open", "Open"), ("filled", "Filled"), ("closed", "Closed")],
        default="open",
        required=True,
        tracking=True,
    )
    assigned_volunteer_ids = fields.Many2many(
        "res.partner",
        domain="[('usbea_archetype', '=', 'volunteer')]",
        string="Assigned volunteers",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    def action_rank_volunteers(self) -> list[dict]:
        """Run the matching algorithm against all volunteers and return ranked results.

        Returns a list of dicts ``[{partner_id, score, skill_pct, availability_pct,
        bg_pct, reasons}]`` ordered by score desc. Does NOT mutate state.
        """
        self.ensure_one()
        Partner = self.env["res.partner"].sudo()
        volunteers = Partner.search([("usbea_archetype", "=", "volunteer")])

        opp = Opportunity(
            required_skill_ids=frozenset(self.required_skill_ids.ids),
            windows=(
                OpportunityWindow(
                    weekday=int(self.weekday),
                    start=_float_to_time(self.start_hour),
                    end=_float_to_time(self.end_hour),
                ),
            ),
            requires_background_check=self.requires_background_check,
        )

        vol_list: list[Volunteer] = []
        order: list[int] = []  # parallel array of partner ids
        Slot = self.env["usbea.volunteer.availability_slot"].sudo()
        BgCheck = self.env["usbea.volunteer.background_check"].sudo()
        for v in volunteers:
            slots_rs = Slot.search([("partner_id", "=", v.id)])
            slot_tuples = tuple(
                VolunteerSlot(
                    weekday=int(s.weekday),
                    start=_float_to_time(s.start_hour),
                    end=_float_to_time(s.end_hour),
                )
                for s in slots_rs
            )
            bg = BgCheck.search([("partner_id", "=", v.id)], limit=1, order="expires_on desc")
            vol_list.append(
                Volunteer(
                    skill_ids=frozenset(v.volunteer_skill_ids.ids),
                    slots=slot_tuples,
                    background_check_active=bool(bg and bg.state in ("active", "expiring_soon", "expired")),
                    background_check_expired=bool(bg and bg.state in ("expired",)),
                ),
            )
            order.append(v.id)

        ranked = rank_matches(vol_list, opp)
        return [
            {
                "partner_id": order[idx],
                "score": ms.overall,
                "skill_pct": ms.skill_pct,
                "availability_pct": ms.availability_pct,
                "bg_pct": ms.bg_pct,
                "reasons": list(ms.reasons),
            }
            for idx, ms in ranked
        ]

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for rec in self:
            if not (0.0 <= rec.start_hour < rec.end_hour <= 24.0):
                msg = _("Opportunity hours must satisfy 0 <= start < end <= 24.")
                raise ValueError(msg)


def _float_to_time(value: float) -> time:
    """Convert 9.5 -> time(9, 30)."""
    if value is None:
        return time(0, 0)
    h = int(value)
    m = round((value - h) * 60)
    if m == 60:
        h += 1
        m = 0
    h = max(0, min(23, h))
    m = max(0, min(59, m))
    return time(h, m)
