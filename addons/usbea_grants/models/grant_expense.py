from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class GrantExpense(models.Model):
    _name = 'usbea.grant.expense'
    _description = 'Grant Expense'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Description', required=True)
    grant_id = fields.Many2one(
        'usbea.grant', 'Grant', required=True, ondelete='cascade',
    )
    date = fields.Date('Expense Date', required=True, default=fields.Date.today)
    amount = fields.Monetary('Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', related='grant_id.currency_id', store=True,
    )
    category = fields.Selection([
        ('travel', 'Travel'),
        ('accommodation', 'Accommodation'),
        ('meals', 'Meals & Per Diem'),
        ('materials', 'Program Materials'),
        ('staff', 'Staff Costs'),
        ('technology', 'Technology/Infrastructure'),
        ('marketing', 'Marketing'),
        ('admin', 'Administrative'),
        ('other', 'Other'),
    ], string='Category', required=True)
    budget_line_id = fields.Many2one(
        'usbea.grant.budget', 'Budget Line',
        domain="[('grant_id', '=', grant_id)]",
    )
    vendor = fields.Char('Vendor/Payee')
    reference = fields.Char('Reference/Invoice #')
    receipt = fields.Binary('Receipt', attachment=True)
    receipt_filename = fields.Char('Receipt Filename')
    notes = fields.Text('Notes')
    employee_id = fields.Many2one('res.users', 'Submitted By',
                                  default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', 'Approved By', readonly=True)
    approval_date = fields.Date('Approval Date', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True, string='Status')

    requires_extra_approval = fields.Boolean(
        'Requires Extra Approval',
        compute='_compute_requires_extra_approval', store=True,
    )

    @api.depends('amount')
    def _compute_requires_extra_approval(self):
        for expense in self:
            expense.requires_extra_approval = expense.amount > 1000

    def action_submit(self):
        for expense in self:
            if expense.state != 'draft':
                raise UserError(_("Only draft expenses can be submitted."))
            expense.state = 'submitted'

    def action_approve(self):
        for expense in self:
            if expense.state != 'submitted':
                raise UserError(_("Only submitted expenses can be approved."))
            # Check if expense would exceed grant budget
            grant = expense.grant_id
            total_after = grant.spent_amount + expense.amount
            if total_after > grant.approved_amount and grant.approved_amount > 0:
                raise UserError(
                    _("This expense would exceed the grant's approved amount. "
                      "Approved: %s, Already spent: %s, This expense: %s")
                    % (grant.approved_amount, grant.spent_amount, expense.amount)
                )
            expense.state = 'approved'
            expense.approved_by = self.env.user
            expense.approval_date = fields.Date.today()

    def action_reject(self):
        for expense in self:
            if expense.state != 'submitted':
                raise UserError(_("Only submitted expenses can be rejected."))
            expense.state = 'rejected'

    def action_reset_draft(self):
        for expense in self:
            if expense.state not in ('rejected',):
                raise UserError(
                    _("Only rejected expenses can be reset to draft.")
                )
            expense.state = 'draft'

    @api.constrains('amount')
    def _check_amount(self):
        for expense in self:
            if expense.amount <= 0:
                raise ValidationError(_("Expense amount must be positive."))
