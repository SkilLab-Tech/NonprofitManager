from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResCompany(models.Model):
    """Extend res.company to act as an Organization/Workspace for the platform."""
    _inherit = 'res.company'

    # Organization metadata
    organization_type = fields.Selection([
        ('nonprofit', 'Nonprofit Organization'),
        ('company', 'Company'),
        ('government', 'Government Agency'),
        ('educational', 'Educational Institution'),
        ('other', 'Other'),
    ], string='Organization Type', default='nonprofit')
    organization_size = fields.Selection([
        ('small', '1-10 employees'),
        ('medium', '11-50 employees'),
        ('large', '51-200 employees'),
        ('enterprise', '200+ employees'),
    ], string='Organization Size')

    # Platform subscription
    subscription_status = fields.Selection([
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ], string='Subscription Status', default='trial')
    subscription_plan = fields.Selection([
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ], string='Plan', default='free')
    trial_end_date = fields.Date('Trial End Date')

    # Organization profile
    organization_description = fields.Html('About the Organization')
    mission_statement = fields.Text('Mission Statement')
    founded_year = fields.Char('Year Founded')
    tax_id_number = fields.Char('Tax ID / EIN')
    registration_number = fields.Char('Registration Number')

    # Contact details
    support_email = fields.Char('Support Email')
    public_phone = fields.Char('Public Phone')
    public_website = fields.Char('Public Website')

    # Social media
    social_facebook = fields.Char('Facebook URL')
    social_instagram = fields.Char('Instagram URL')
    social_linkedin = fields.Char('LinkedIn URL')
    social_twitter = fields.Char('Twitter/X URL')
    social_youtube = fields.Char('YouTube URL')

    # Platform admin reference
    created_by_super_admin = fields.Many2one(
        'res.users', 'Created By (Super Admin)', readonly=True,
    )
    is_platform_root = fields.Boolean(
        'Is Platform Root Organization', default=False,
        help='The root organization is managed by the platform super admin.',
    )

    # Member counts
    member_count = fields.Integer(
        'Active Members', compute='_compute_member_count',
    )
    invitation_count = fields.Integer(
        'Pending Invitations', compute='_compute_invitation_count',
    )

    def _compute_member_count(self):
        for company in self:
            company.member_count = self.env['res.users'].sudo().search_count([
                ('company_ids', 'in', company.id),
                ('active', '=', True),
            ])

    def _compute_invitation_count(self):
        for company in self:
            company.invitation_count = self.env['usbea.user.invitation'].sudo().search_count([
                ('organization_id', '=', company.id),
                ('state', '=', 'pending'),
            ])

    @api.constrains('subscription_status')
    def _check_root_subscription(self):
        for company in self:
            if company.is_platform_root and company.subscription_status == 'cancelled':
                raise ValidationError(
                    _("The root platform organization cannot be cancelled.")
                )

    def action_view_members(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members'),
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'domain': [('company_ids', 'in', self.id)],
            'context': {'default_company_id': self.id},
        }

    def action_view_invitations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invitations'),
            'res_model': 'usbea.user.invitation',
            'view_mode': 'list,form',
            'domain': [('organization_id', '=', self.id)],
            'context': {'default_organization_id': self.id},
        }
