{
    'name': 'USBEA Platform RBAC',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Role-based access control, super admin, and organization management',
    'description': """
        Platform-level access control for the USBEA white-label platform:
        - Super Admin role for platform management
        - Organization (workspace) management
        - Custom roles per organization
        - User invitation workflow
        - Multi-tenant data isolation via Odoo multi-company
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['base', 'mail'],
    'data': [
        'security/rbac_security.xml',
        'security/ir.model.access.csv',
        'data/rbac_data.xml',
        'wizard/invite_user_views.xml',
        'views/organization_views.xml',
        'views/platform_role_views.xml',
        'views/user_management_views.xml',
        'views/rbac_menus.xml',
    ],
    'demo': [
        'demo/rbac_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
