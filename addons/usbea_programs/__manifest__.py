{
    'name': 'USBEA Program Management',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Exchange program management for USBEA Brasil',
    'description': """
        Manage USBEA exchange programs:
        - Program lifecycle management
        - Participant tracking
        - Visa coordination
        - Event scheduling
        - Integration with grant funding
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['base', 'mail', 'usbea_grants'],
    'data': [
        'security/program_security.xml',
        'security/ir.model.access.csv',
        'data/program_sequence.xml',
        'views/program_views.xml',
        'views/participant_views.xml',
        'views/program_event_views.xml',
        'views/program_menus.xml',
    ],
    'demo': [
        'demo/program_demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
