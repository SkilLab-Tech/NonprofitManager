from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class GrantBudget(models.Model):
    _name = 'usbea.grant.budget'
    _description = 'Grant Budget Line'
    _order = 'sequence, id'

    name = fields.Char('Budget Category', required=True)
    grant_id = fields.Many2one(
        'usbea.grant', 'Grant', required=True, ondelete='cascade',
    )
    sequence = fields.Integer('Sequence', default=10)
    planned_amount = fields.Monetary(
        'Planned Amount', currency_field='currency_id', required=True,
    )
    actual_amount = fields.Monetary(
        'Actual Spent', currency_field='currency_id',
        compute='_compute_actual_amount', store=True,
    )
    variance = fields.Monetary(
        'Variance', currency_field='currency_id',
        compute='_compute_variance', store=True,
    )
    variance_pct = fields.Float(
        'Variance %', compute='_compute_variance', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='grant_id.currency_id', store=True,
    )
    expense_ids = fields.One2many(
        'usbea.grant.expense', 'budget_line_id', 'Expenses',
    )
    notes = fields.Text('Notes')

    @api.depends('expense_ids.amount', 'expense_ids.state')
    def _compute_actual_amount(self):
        for line in self:
            line.actual_amount = sum(
                line.expense_ids.filtered(
                    lambda e: e.state == 'approved'
                ).mapped('amount')
            )

    @api.depends('planned_amount', 'actual_amount')
    def _compute_variance(self):
        for line in self:
            line.variance = line.planned_amount - line.actual_amount
            if line.planned_amount:
                line.variance_pct = (
                    (line.planned_amount - line.actual_amount)
                    / line.planned_amount
                ) * 100
            else:
                line.variance_pct = 0.0

    @api.constrains('planned_amount')
    def _check_planned_amount(self):
        for line in self:
            if line.planned_amount < 0:
                raise ValidationError(
                    _("Planned amount cannot be negative.")
                )
