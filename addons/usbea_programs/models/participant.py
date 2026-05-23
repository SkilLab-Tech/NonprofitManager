from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class Participant(models.Model):
    _name = 'usbea.participant'
    _description = 'Program Participant'
    _inherit = ['mail.thread']
    _order = 'name asc'

    name = fields.Char('Full Name', required=True)
    partner_id = fields.Many2one('res.partner', 'Contact Record')
    program_id = fields.Many2one(
        'usbea.program', 'Program', required=True, ondelete='cascade',
    )
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    date_of_birth = fields.Date('Date of Birth')
    nationality = fields.Many2one('res.country', 'Nationality')
    city = fields.Char('City')

    # Program participation
    role = fields.Selection([
        ('participant', 'Participant'),
        ('mentor', 'Mentor'),
        ('facilitator', 'Facilitator'),
        ('coordinator', 'Coordinator'),
    ], default='participant', string='Role')

    # Visa tracking
    visa_status = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending Application'),
        ('applied', 'Applied'),
        ('interview', 'Interview Scheduled'),
        ('approved', 'Approved'),
        ('issued', 'Issued'),
        ('denied', 'Denied'),
    ], default='not_required', string='Visa Status', tracking=True)
    visa_number = fields.Char('Visa Number')
    visa_expiry = fields.Date('Visa Expiry Date')
    passport_number = fields.Char('Passport Number')
    ds2019_number = fields.Char('DS-2019 Number')

    # Dates
    arrival_date = fields.Date('Arrival Date')
    departure_date = fields.Date('Departure Date')

    # Status
    state = fields.Selection([
        ('applied', 'Applied'),
        ('accepted', 'Accepted'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('withdrawn', 'Withdrawn'),
    ], default='applied', tracking=True, string='Status')

    # Emergency contact
    emergency_contact = fields.Char('Emergency Contact Name')
    emergency_phone = fields.Char('Emergency Contact Phone')

    notes = fields.Text('Notes')

    def action_accept(self):
        for participant in self:
            participant.state = 'accepted'

    def action_activate(self):
        for participant in self:
            participant.state = 'active'

    def action_complete(self):
        for participant in self:
            participant.state = 'completed'

    def action_withdraw(self):
        for participant in self:
            participant.state = 'withdrawn'
