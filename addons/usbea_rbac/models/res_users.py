from odoo import api, fields, models
from odoo.tools.translate import _


class ResUsers(models.Model):
    """Extend res.users with platform-level role management."""
    _inherit = 'res.users'

    # Platform role
    platform_role = fields.Selection([
        ('super_admin', 'Super Admin'),
        ('org_admin', 'Organization Admin'),
        ('org_manager', 'Organization Manager'),
        ('org_member', 'Organization Member'),
        ('org_viewer', 'Viewer (Read-Only)'),
    ], string='Platform Role', default='org_member')
    is_super_admin = fields.Boolean(
        'Is Super Admin', compute='_compute_is_super_admin', store=True,
    )

    # Custom roles
    role_ids = fields.Many2many(
        'usbea.platform.role', 'usbea_user_role_rel',
        'user_id', 'role_id', string='Custom Roles',
    )

    # Profile fields
    bio = fields.Text('Bio / About')
    job_title_custom = fields.Char('Job Title')
    department_custom = fields.Char('Department')
    profile_website = fields.Char('Personal Website')
    social_linkedin = fields.Char('LinkedIn Profile')
    social_twitter = fields.Char('Twitter/X Profile')
    social_github = fields.Char('GitHub Profile')
    timezone_display = fields.Char(
        'Timezone', related='tz', readonly=True,
    )

    # Invitation tracking
    invited_by = fields.Many2one('res.users', 'Invited By', readonly=True)
    invitation_date = fields.Datetime('Invitation Date', readonly=True)

    # Last activity
    last_active_organization = fields.Many2one(
        'res.company', 'Last Active Organization',
    )

    @api.depends('platform_role')
    def _compute_is_super_admin(self):
        for user in self:
            user.is_super_admin = user.platform_role == 'super_admin'

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'platform_role', 'is_super_admin', 'bio', 'job_title_custom',
            'department_custom', 'profile_website', 'social_linkedin',
            'social_twitter', 'social_github', 'role_ids',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'bio', 'job_title_custom', 'department_custom',
            'profile_website', 'social_linkedin', 'social_twitter',
            'social_github',
        ]

    def action_grant_super_admin(self):
        """Grant super admin privileges to selected users."""
        self.ensure_one()
        self.sudo().write({
            'platform_role': 'super_admin',
            'groups_id': [(4, self.env.ref('usbea_rbac.group_platform_super_admin').id)],
        })

    def action_revoke_super_admin(self):
        """Revoke super admin privileges."""
        self.ensure_one()
        self.sudo().write({
            'platform_role': 'org_admin',
            'groups_id': [(3, self.env.ref('usbea_rbac.group_platform_super_admin').id)],
        })

    def action_set_org_admin(self):
        for user in self:
            user.sudo().write({
                'platform_role': 'org_admin',
                'groups_id': [
                    (4, self.env.ref('usbea_rbac.group_platform_org_admin').id),
                ],
            })

    def action_set_org_manager(self):
        for user in self:
            user.sudo().write({
                'platform_role': 'org_manager',
                'groups_id': [
                    (4, self.env.ref('usbea_rbac.group_platform_org_manager').id),
                ],
            })

    def action_set_org_member(self):
        for user in self:
            user.sudo().write({
                'platform_role': 'org_member',
                'groups_id': [
                    (4, self.env.ref('usbea_rbac.group_platform_org_member').id),
                ],
            })

    def action_set_org_viewer(self):
        for user in self:
            user.sudo().write({
                'platform_role': 'org_viewer',
                'groups_id': [
                    (4, self.env.ref('usbea_rbac.group_platform_org_viewer').id),
                ],
            })
