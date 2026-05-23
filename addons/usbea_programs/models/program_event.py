from odoo import fields, models


class ProgramEvent(models.Model):
    _name = 'usbea.program.event'
    _description = 'Program Event'
    _inherit = ['mail.thread']
    _order = 'date_start asc'

    name = fields.Char('Event Name', required=True)
    program_id = fields.Many2one(
        'usbea.program', 'Program', required=True, ondelete='cascade',
    )
    event_type = fields.Selection([
        ('orientation', 'Orientation'),
        ('workshop', 'Workshop'),
        ('networking', 'Networking Event'),
        ('ceremony', 'Ceremony'),
        ('field_trip', 'Field Trip'),
        ('meeting', 'Meeting'),
        ('other', 'Other'),
    ], string='Event Type', required=True)
    date_start = fields.Datetime('Start Date/Time', required=True)
    date_end = fields.Datetime('End Date/Time')
    location = fields.Char('Location')
    description = fields.Html('Description')
    attendee_ids = fields.Many2many(
        'usbea.participant', string='Attendees',
    )
    max_attendees = fields.Integer('Max Attendees')
    notes = fields.Text('Notes')

    state = fields.Selection([
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='planned', tracking=True, string='Status')

    def action_confirm(self):
        for event in self:
            event.state = 'confirmed'

    def action_complete(self):
        for event in self:
            event.state = 'completed'

    def action_cancel(self):
        for event in self:
            event.state = 'cancelled'
