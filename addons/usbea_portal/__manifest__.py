{
    'name': 'USBEA Board Portal',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Board member and donor dashboard for USBEA',
    'description': """
        Board and donor portal for USBEA Brasil:
        - Grant portfolio dashboard with KPIs
        - Financial health indicators
        - Program impact metrics
        - Compliance deadline tracking
        - Read-only access for board members
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['base', 'usbea_rbac', 'usbea_grants', 'usbea_programs'],
    'data': [
        'security/ir.model.access.csv',
        'views/portal_dashboard_views.xml',
        'views/portal_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
