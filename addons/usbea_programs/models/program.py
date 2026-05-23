from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class Program(models.Model):
    _name = 'usbea.program'
    _description = 'Exchange Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char('Program Name', required=True, tracking=True)
    program_code = fields.Char(
        'Code', readonly=True, copy=False, default='New',
    )
    program_type = fields.Selection([
        ('cultural_exchange', 'Cultural Exchange'),
        ('academic', 'Academic Exchange'),
        ('professional', 'Professional Training'),
        ('leadership', 'Leadership Program'),
    ], string='Program Type', required=True, tracking=True)
    description = fields.Html('Description')
    responsible_id = fields.Many2one(
        'res.users', 'Program Coordinator',
        default=lambda self: self.env.user, tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        required=True,
    )

    # Participants
    participant_ids = fields.One2many(
        'usbea.participant', 'program_id', 'Participants',
    )
    participant_count = fields.Integer(
        compute='_compute_participant_count', string='Participants',
    )
    max_participants = fields.Integer('Max Participants')

    # Financials
    grant_ids = fields.Many2many('usbea.grant', string='Funding Grants')
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id,
    )
    budget = fields.Monetary('Total Budget', currency_field='currency_id')
    spent_amount = fields.Monetary(
        'Amount Spent', currency_field='currency_id',
        compute='_compute_spent_amount', store=True,
    )

    # Timeline
    start_date = fields.Date('Start Date', tracking=True)
    end_date = fields.Date('End Date', tracking=True)

    # Visa/Immigration
    visa_type = fields.Selection([
        ('j1', 'J-1 Visa'),
        ('f1', 'F-1 Visa'),
        ('b1', 'B-1 Visa'),
        ('other', 'Other'),
        ('none', 'No Visa Required'),
    ], string='Visa Type')
    visa_sponsor = fields.Char('Visa Sponsor Organization')

    # Location
    country_ids = fields.Many2many(
        'res.country', string='Countries Involved',
    )
    location = fields.Char('Primary Location')

    # Events
    event_ids = fields.One2many(
        'usbea.program.event', 'program_id', 'Events',
    )
    event_count = fields.Integer(
        compute='_compute_event_count', string='Events',
    )

    # Workflow
    state = fields.Selection([
        ('planning', 'Planning'),
        ('recruiting', 'Recruiting'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='planning', tracking=True, string='Status')

    notes = fields.Html('Internal Notes')

    def _compute_participant_count(self):
        for program in self:
            program.participant_count = len(program.participant_ids)

    def _compute_event_count(self):
        for program in self:
            program.event_count = len(program.event_ids)

    @api.depends('grant_ids.expense_ids.amount', 'grant_ids.expense_ids.state')
    def _compute_spent_amount(self):
        for program in self:
            program.spent_amount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('program_code', 'New') == 'New':
                vals['program_code'] = self.env['ir.sequence'].next_by_code(
                    'usbea.program'
                ) or 'New'
        return super().create(vals_list)

    def action_start_recruiting(self):
        for program in self:
            program.state = 'recruiting'

    def action_activate(self):
        for program in self:
            program.state = 'active'

    def action_complete(self):
        for program in self:
            program.state = 'completed'

    def action_cancel(self):
        for program in self:
            program.state = 'cancelled'

    def action_reset_planning(self):
        for program in self:
            program.state = 'planning'

    def action_view_participants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Participants'),
            'res_model': 'usbea.participant',
            'view_mode': 'list,form',
            'domain': [('program_id', '=', self.id)],
            'context': {'default_program_id': self.id},
        }

    def action_view_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Events'),
            'res_model': 'usbea.program.event',
            'view_mode': 'list,form,calendar',
            'domain': [('program_id', '=', self.id)],
            'context': {'default_program_id': self.id},
        }

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for program in self:
            if program.start_date and program.end_date:
                if program.start_date > program.end_date:
                    raise ValidationError(
                        _("End date must be after start date.")
                    )
