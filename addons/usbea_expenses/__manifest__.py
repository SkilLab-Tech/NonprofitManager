{
    'name': 'USBEA Expense Management',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Extended expense tracking with grant allocation',
    'description': """
        Extended expense management for USBEA Brasil:
        - Grant allocation on expenses
        - Program-linked expenses
        - Multi-currency support
        - Enhanced approval workflow for grant-funded expenses
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['hr_expense', 'usbea_grants', 'usbea_programs'],
    'data': [
        'security/ir.model.access.csv',
        'views/expense_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
