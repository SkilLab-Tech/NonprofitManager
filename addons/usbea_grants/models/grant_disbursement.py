from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class GrantDisbursement(models.Model):
    _name = 'usbea.grant.disbursement'
    _description = 'Grant Disbursement'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Description', required=True)
    grant_id = fields.Many2one(
        'usbea.grant', 'Grant', required=True, ondelete='cascade',
    )
    date = fields.Date('Disbursement Date', required=True, default=fields.Date.today)
    amount = fields.Monetary('Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', related='grant_id.currency_id', store=True,
    )
    tranche_number = fields.Integer('Tranche #')
    payment_method = fields.Selection([
        ('wire', 'Wire Transfer'),
        ('check', 'Check'),
        ('ach', 'ACH Transfer'),
        ('other', 'Other'),
    ], string='Payment Method')
    payment_reference = fields.Char('Payment Reference')
    notes = fields.Text('Notes')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], default='pending', tracking=True, string='Status')

    def action_confirm(self):
        for disbursement in self:
            disbursement.state = 'confirmed'

    def action_cancel(self):
        for disbursement in self:
            disbursement.state = 'cancelled'

    @api.constrains('amount')
    def _check_amount(self):
        for disbursement in self:
            if disbursement.amount <= 0:
                raise ValidationError(
                    _("Disbursement amount must be positive.")
                )
