"""Hierarchical volunteer skill taxonomy."""

from __future__ import annotations

from odoo import api, fields, models


class UsbeaVolunteerSkill(models.Model):
    _name = "usbea.volunteer.skill"
    _description = "Volunteer Skill"
    _parent_store = True
    _parent_name = "parent_id"
    _order = "complete_name"
    _rec_name = "complete_name"

    name = fields.Char(required=True)
    technical_key = fields.Char(required=True, copy=False)
    parent_id = fields.Many2one("usbea.volunteer.skill", ondelete="cascade")
    parent_path = fields.Char(index=True)
    complete_name = fields.Char(compute="_compute_complete_name", store=True, recursive=True)
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("technical_key_unique", "UNIQUE(technical_key)", "Skill technical_key must be unique."),
    ]

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name or ""
