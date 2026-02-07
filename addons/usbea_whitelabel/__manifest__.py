{
    'name': 'USBEA White Label Settings',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Organization branding, profiles, and white-label settings',
    'description': """
        White-label customization for the USBEA platform:
        - Organization logo and branding colors
        - Organization profile and contact information
        - User profile management (bio, picture, social links)
        - Settings page for admins to configure their workspace
        - Theme customization (primary/secondary colors, fonts)
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['base', 'base_setup', 'usbea_rbac'],
    'data': [
        'security/ir.model.access.csv',
        'views/branding_settings_views.xml',
        'views/user_profile_views.xml',
        'views/whitelabel_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
