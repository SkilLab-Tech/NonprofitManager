import secrets

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class UserInvitation(models.Model):
    _name = 'usbea.user.invitation'
    _description = 'User Invitation'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    email = fields.Char('Email Address', required=True, tracking=True)
    name = fields.Char('Recipient Name')
    organization_id = fields.Many2one(
        'res.company', 'Organization', required=True,
        default=lambda self: self.env.company,
    )
    invited_by = fields.Many2one(
        'res.users', 'Invited By', required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    platform_role = fields.Selection([
        ('org_admin', 'Organization Admin'),
        ('org_manager', 'Organization Manager'),
        ('org_member', 'Organization Member'),
        ('org_viewer', 'Viewer (Read-Only)'),
    ], string='Assigned Role', default='org_member', required=True)
    role_ids = fields.Many2many(
        'usbea.platform.role', string='Custom Roles',
        domain="[('organization_id', '=', organization_id)]",
    )
    message = fields.Text('Personal Message')
    token = fields.Char(
        'Invitation Token', readonly=True, copy=False,
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], default='pending', tracking=True, string='Status')
    expiry_date = fields.Datetime('Expiry Date')
    accepted_date = fields.Datetime('Accepted Date', readonly=True)
    user_id = fields.Many2one(
        'res.users', 'Created User', readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = secrets.token_urlsafe(32)
            if not vals.get('expiry_date'):
                vals['expiry_date'] = fields.Datetime.add(
                    fields.Datetime.now(), days=7,
                )
        return super().create(vals_list)

    def action_send(self):
        """Send the invitation email."""
        for invitation in self:
            if invitation.state != 'pending':
                raise UserError(
                    _("Only pending invitations can be sent.")
                )
            # In production, this would send an email via mail.template
            # For now, mark as sent
            invitation.state = 'sent'
            invitation.message_post(
                body=_("Invitation sent to %s for role: %s") % (
                    invitation.email,
                    dict(invitation._fields['platform_role'].selection).get(
                        invitation.platform_role
                    ),
                ),
            )

    def action_accept(self):
        """Accept the invitation and create/link user."""
        for invitation in self:
            if invitation.state not in ('pending', 'sent'):
                raise UserError(
                    _("This invitation cannot be accepted.")
                )
            if invitation.expiry_date and invitation.expiry_date < fields.Datetime.now():
                invitation.state = 'expired'
                raise UserError(_("This invitation has expired."))

            # Check if user already exists
            existing_user = self.env['res.users'].sudo().search([
                ('login', '=', invitation.email),
            ], limit=1)

            if existing_user:
                # Add to organization
                existing_user.sudo().write({
                    'company_ids': [(4, invitation.organization_id.id)],
                    'platform_role': invitation.platform_role,
                    'invited_by': invitation.invited_by.id,
                    'invitation_date': fields.Datetime.now(),
                })
                if invitation.role_ids:
                    existing_user.sudo().write({
                        'role_ids': [(4, r.id) for r in invitation.role_ids],
                    })
                invitation.user_id = existing_user
            else:
                # Create new user
                new_user = self.env['res.users'].sudo().create({
                    'name': invitation.name or invitation.email.split('@')[0],
                    'login': invitation.email,
                    'email': invitation.email,
                    'company_id': invitation.organization_id.id,
                    'company_ids': [(4, invitation.organization_id.id)],
                    'platform_role': invitation.platform_role,
                    'invited_by': invitation.invited_by.id,
                    'invitation_date': fields.Datetime.now(),
                    'role_ids': [(4, r.id) for r in invitation.role_ids] if invitation.role_ids else [],
                })
                invitation.user_id = new_user

            invitation.accepted_date = fields.Datetime.now()
            invitation.state = 'accepted'

    def action_cancel(self):
        for invitation in self:
            if invitation.state in ('accepted',):
                raise UserError(
                    _("Accepted invitations cannot be cancelled.")
                )
            invitation.state = 'cancelled'

    def action_resend(self):
        for invitation in self:
            if invitation.state not in ('sent', 'expired'):
                raise UserError(
                    _("Only sent or expired invitations can be resent.")
                )
            invitation.token = secrets.token_urlsafe(32)
            invitation.expiry_date = fields.Datetime.add(
                fields.Datetime.now(), days=7,
            )
            invitation.state = 'pending'
            invitation.action_send()

    @api.constrains('email')
    def _check_email(self):
        for invitation in self:
            if invitation.email and '@' not in invitation.email:
                raise ValidationError(_("Please enter a valid email address."))

    @api.constrains('email', 'organization_id', 'state')
    def _check_duplicate(self):
        for invitation in self:
            if invitation.state in ('pending', 'sent'):
                existing = self.search([
                    ('email', '=', invitation.email),
                    ('organization_id', '=', invitation.organization_id.id),
                    ('state', 'in', ('pending', 'sent')),
                    ('id', '!=', invitation.id),
                ])
                if existing:
                    raise ValidationError(
                        _("An active invitation for %s already exists in this organization.")
                        % invitation.email
                    )
