from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class InviteUserWizard(models.TransientModel):
    _name = 'usbea.invite.user.wizard'
    _description = 'Invite User to Organization'

    email = fields.Char('Email Address', required=True)
    name = fields.Char('Full Name')
    organization_id = fields.Many2one(
        'res.company', 'Organization', required=True,
        default=lambda self: self.env.company,
    )
    platform_role = fields.Selection([
        ('org_admin', 'Organization Admin'),
        ('org_manager', 'Organization Manager'),
        ('org_member', 'Organization Member'),
        ('org_viewer', 'Viewer (Read-Only)'),
    ], string='Role', default='org_member', required=True)
    role_ids = fields.Many2many(
        'usbea.platform.role', string='Custom Roles',
        domain="[('organization_id', '=', organization_id)]",
    )
    message = fields.Text(
        'Personal Message',
        default="You've been invited to join our organization on the USBEA platform.",
    )

    @api.constrains('email')
    def _check_email(self):
        for wizard in self:
            if wizard.email and '@' not in wizard.email:
                raise ValidationError(_("Please enter a valid email address."))

    def action_send_invitation(self):
        self.ensure_one()
        invitation = self.env['usbea.user.invitation'].create({
            'email': self.email,
            'name': self.name,
            'organization_id': self.organization_id.id,
            'platform_role': self.platform_role,
            'role_ids': [(6, 0, self.role_ids.ids)],
            'message': self.message,
        })
        invitation.action_send()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invitation Sent'),
                'message': _('Invitation sent to %s') % self.email,
                'type': 'success',
                'sticky': False,
            },
        }
