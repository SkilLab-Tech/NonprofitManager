"""Checklist items belonging to a task template."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UsbeaTaskChecklistItem(models.Model):
    _name = "usbea.task.checklist_item"
    _description = "USBEA Task Template Checklist Item"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one(
        "usbea.task.template",
        ondelete="cascade",
        required=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    description = fields.Text()
    due_offset_days = fields.Integer(
        default=0,
        help="Days from instantiation when this checklist item is due.",
    )

    @api.constrains("due_offset_days")
    def _check_offset(self):
        for rec in self:
            if rec.due_offset_days < 0 or rec.due_offset_days > 365:
                msg = _("due_offset_days must be between 0 and 365.")
                raise ValidationError(msg)
