from odoo import api, fields, models


class HrExpenseUSBEA(models.Model):
    _inherit = 'hr.expense'

    grant_id = fields.Many2one(
        'usbea.grant', 'Charged to Grant',
        help='Select the grant this expense should be charged to.',
    )
    program_id = fields.Many2one(
        'usbea.program', 'Related Program',
        help='Select the program this expense is related to.',
    )
    expense_category = fields.Selection([
        ('travel', 'Travel'),
        ('accommodation', 'Accommodation'),
        ('meals', 'Meals & Per Diem'),
        ('materials', 'Program Materials'),
        ('staff', 'Staff Costs'),
        ('technology', 'Technology/Infrastructure'),
        ('marketing', 'Marketing'),
        ('admin', 'Administrative'),
        ('other', 'Other'),
    ], string='USBEA Category')
    grant_budget_line_id = fields.Many2one(
        'usbea.grant.budget', 'Grant Budget Line',
        domain="[('grant_id', '=', grant_id)]",
    )
    requires_grant_approval = fields.Boolean(
        'Requires Grant Approval',
        compute='_compute_grant_approval', store=True,
    )

    @api.depends('grant_id', 'total_amount_currency')
    def _compute_grant_approval(self):
        for expense in self:
            expense.requires_grant_approval = bool(
                expense.grant_id and expense.total_amount_currency > 1000
            )
