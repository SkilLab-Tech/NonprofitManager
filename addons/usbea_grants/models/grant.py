from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class Grant(models.Model):
    _name = 'usbea.grant'
    _description = 'Grant Application and Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_date desc, id desc'

    # Basic Info
    name = fields.Char('Grant Name', required=True, tracking=True)
    grant_number = fields.Char(
        'Grant Number', readonly=True, copy=False, default='New',
    )
    description = fields.Html('Description')
    funding_source = fields.Many2one(
        'res.partner', 'Funding Organization', tracking=True,
    )
    grant_type = fields.Selection([
        ('government', 'Government'),
        ('foundation', 'Foundation'),
        ('corporate', 'Corporate'),
        ('individual', 'Individual Donor'),
    ], string='Grant Type', required=True, tracking=True)
    responsible_id = fields.Many2one(
        'res.users', 'Grant Manager', default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        required=True,
    )

    # Financial
    requested_amount = fields.Monetary(
        'Requested Amount', currency_field='currency_id', tracking=True,
    )
    approved_amount = fields.Monetary(
        'Approved Amount', currency_field='currency_id', tracking=True,
    )
    disbursed_amount = fields.Monetary(
        'Disbursed Amount', currency_field='currency_id',
        compute='_compute_disbursed', store=True,
    )
    spent_amount = fields.Monetary(
        'Spent Amount', currency_field='currency_id',
        compute='_compute_spent', store=True,
    )
    remaining_amount = fields.Monetary(
        'Remaining', currency_field='currency_id',
        compute='_compute_remaining', store=True,
    )
    utilization_rate = fields.Float(
        'Utilization %', compute='_compute_utilization', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # Dates
    application_date = fields.Date('Application Date', tracking=True)
    approval_date = fields.Date('Approval Date', tracking=True)
    start_date = fields.Date('Project Start Date', tracking=True)
    end_date = fields.Date('Project End Date', tracking=True)
    reporting_deadline = fields.Date('Next Report Due', tracking=True)

    # Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('active', 'Active/Disbursed'),
        ('reporting', 'Reporting Phase'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, string='Status')

    # Relationships
    expense_ids = fields.One2many(
        'usbea.grant.expense', 'grant_id', 'Expenses',
    )
    report_ids = fields.One2many(
        'usbea.grant.report', 'grant_id', 'Reports',
    )
    disbursement_ids = fields.One2many(
        'usbea.grant.disbursement', 'grant_id', 'Disbursements',
    )
    budget_ids = fields.One2many(
        'usbea.grant.budget', 'grant_id', 'Budget Lines',
    )

    # Compliance
    compliance_requirements = fields.Html('Compliance Requirements')
    reporting_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('biannual', 'Bi-Annual'),
        ('annual', 'Annual'),
    ], string='Reporting Frequency')

    # Counts for smart buttons
    expense_count = fields.Integer(
        compute='_compute_expense_count', string='Expenses',
    )
    report_count = fields.Integer(
        compute='_compute_report_count', string='Reports',
    )
    disbursement_count = fields.Integer(
        compute='_compute_disbursement_count', string='Disbursements',
    )

    # Notes
    notes = fields.Html('Internal Notes')

    # --- Computed fields ---

    @api.depends('disbursement_ids.amount')
    def _compute_disbursed(self):
        for grant in self:
            grant.disbursed_amount = sum(
                grant.disbursement_ids.filtered(
                    lambda d: d.state == 'confirmed'
                ).mapped('amount')
            )

    @api.depends('expense_ids.amount', 'expense_ids.state')
    def _compute_spent(self):
        for grant in self:
            grant.spent_amount = sum(
                grant.expense_ids.filtered(
                    lambda e: e.state == 'approved'
                ).mapped('amount')
            )

    @api.depends('approved_amount', 'spent_amount')
    def _compute_remaining(self):
        for grant in self:
            grant.remaining_amount = grant.approved_amount - grant.spent_amount

    @api.depends('approved_amount', 'spent_amount')
    def _compute_utilization(self):
        for grant in self:
            if grant.approved_amount:
                grant.utilization_rate = (
                    grant.spent_amount / grant.approved_amount
                ) * 100
            else:
                grant.utilization_rate = 0.0

    def _compute_expense_count(self):
        for grant in self:
            grant.expense_count = len(grant.expense_ids)

    def _compute_report_count(self):
        for grant in self:
            grant.report_count = len(grant.report_ids)

    def _compute_disbursement_count(self):
        for grant in self:
            grant.disbursement_count = len(grant.disbursement_ids)

    # --- CRUD overrides ---

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('grant_number', 'New') == 'New':
                vals['grant_number'] = self.env['ir.sequence'].next_by_code(
                    'usbea.grant'
                ) or 'New'
        return super().create(vals_list)

    # --- Workflow actions ---

    def action_submit(self):
        """Submit grant application for review."""
        for grant in self:
            if grant.state != 'draft':
                raise UserError(_("Only draft grants can be submitted."))
            grant.state = 'submitted'

    def action_review(self):
        """Move grant to under review."""
        for grant in self:
            if grant.state != 'submitted':
                raise UserError(
                    _("Only submitted grants can be moved to review.")
                )
            grant.state = 'under_review'

    def action_approve(self):
        """Approve the grant."""
        for grant in self:
            if grant.state != 'under_review':
                raise UserError(
                    _("Only grants under review can be approved.")
                )
            if not grant.approved_amount:
                raise UserError(
                    _("Please set the approved amount before approving.")
                )
            grant.state = 'approved'
            grant.approval_date = fields.Date.today()

    def action_activate(self):
        """Activate the grant (first disbursement received)."""
        for grant in self:
            if grant.state != 'approved':
                raise UserError(
                    _("Only approved grants can be activated.")
                )
            grant.state = 'active'

    def action_reporting(self):
        """Move grant to reporting phase."""
        for grant in self:
            if grant.state != 'active':
                raise UserError(
                    _("Only active grants can move to reporting phase.")
                )
            grant.state = 'reporting'

    def action_complete(self):
        """Mark grant as completed."""
        for grant in self:
            if grant.state not in ('active', 'reporting'):
                raise UserError(
                    _("Only active or reporting grants can be completed.")
                )
            grant.state = 'completed'

    def action_reject(self):
        """Reject the grant application."""
        for grant in self:
            if grant.state not in ('submitted', 'under_review'):
                raise UserError(
                    _("Only submitted or under-review grants can be rejected.")
                )
            grant.state = 'rejected'

    def action_cancel(self):
        """Cancel the grant."""
        for grant in self:
            if grant.state in ('completed',):
                raise UserError(
                    _("Completed grants cannot be cancelled.")
                )
            grant.state = 'cancelled'

    def action_reset_draft(self):
        """Reset to draft state."""
        for grant in self:
            if grant.state not in ('rejected', 'cancelled'):
                raise UserError(
                    _("Only rejected or cancelled grants can be reset.")
                )
            grant.state = 'draft'

    # --- Smart button actions ---

    def action_view_expenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Grant Expenses'),
            'res_model': 'usbea.grant.expense',
            'view_mode': 'list,form',
            'domain': [('grant_id', '=', self.id)],
            'context': {'default_grant_id': self.id},
        }

    def action_view_disbursements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Disbursements'),
            'res_model': 'usbea.grant.disbursement',
            'view_mode': 'list,form',
            'domain': [('grant_id', '=', self.id)],
            'context': {'default_grant_id': self.id},
        }

    def action_view_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compliance Reports'),
            'res_model': 'usbea.grant.report',
            'view_mode': 'list,form',
            'domain': [('grant_id', '=', self.id)],
            'context': {'default_grant_id': self.id},
        }

    # --- Constraints ---

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for grant in self:
            if grant.start_date and grant.end_date:
                if grant.start_date > grant.end_date:
                    raise ValidationError(
                        _("End date must be after start date.")
                    )

    @api.constrains('approved_amount')
    def _check_approved_amount(self):
        for grant in self:
            if grant.approved_amount < 0:
                raise ValidationError(
                    _("Approved amount cannot be negative.")
                )
