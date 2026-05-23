"""Inline collaboration comments on grant applications."""

from __future__ import annotations

from odoo import fields, models


class UsbeaGrantApplicationComment(models.Model):
    _name = "usbea.grant_application.comment"
    _description = "Grant Application Comment"
    _order = "create_date desc"

    application_id = fields.Many2one(
        "usbea.grant_application",
        required=True,
        ondelete="cascade",
        index=True,
    )
    body = fields.Text(required=True)
    author_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )
    on_section = fields.Char(
        help="Which application section this comment targets (free-form).",
    )
