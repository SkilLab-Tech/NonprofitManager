from odoo import fields, models


class PlatformRole(models.Model):
    """Custom roles that organization admins can create for their org."""
    _name = 'usbea.platform.role'
    _description = 'Custom Platform Role'
    _order = 'sequence, name'

    name = fields.Char('Role Name', required=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    organization_id = fields.Many2one(
        'res.company', 'Organization', required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean('Active', default=True)

    # Permissions - these define what the role can access within the org
    can_manage_grants = fields.Boolean('Can Manage Grants')
    can_manage_programs = fields.Boolean('Can Manage Programs')
    can_manage_expenses = fields.Boolean('Can Manage Expenses')
    can_approve_expenses = fields.Boolean('Can Approve Expenses')
    can_view_financials = fields.Boolean('Can View Financial Data')
    can_manage_reports = fields.Boolean('Can Manage Reports')
    can_manage_participants = fields.Boolean('Can Manage Participants')
    can_manage_events = fields.Boolean('Can Manage Events')
    can_view_dashboard = fields.Boolean('Can View Dashboard')
    can_export_data = fields.Boolean('Can Export Data')

    # User assignment
    user_ids = fields.Many2many(
        'res.users', 'usbea_user_role_rel',
        'role_id', 'user_id', string='Assigned Users',
    )
    user_count = fields.Integer(
        'Users', compute='_compute_user_count',
    )

    def _compute_user_count(self):
        for role in self:
            role.user_count = len(role.user_ids)
