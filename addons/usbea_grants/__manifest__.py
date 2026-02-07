{
    'name': 'USBEA Grant Management',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Grant tracking and compliance for nonprofits',
    'description': """
        Complete grant lifecycle management for USBEA Brasil:
        - Application tracking
        - Budget monitoring
        - Expense allocation
        - Disbursement tracking
        - Compliance reporting
        - Multi-currency support (USD/BRL)
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/grant_security.xml',
        'security/ir.model.access.csv',
        'data/grant_sequence.xml',
        'views/grant_views.xml',
        'views/grant_expense_views.xml',
        'views/grant_disbursement_views.xml',
        'views/grant_report_views.xml',
        'views/grant_budget_views.xml',
        'views/grant_menus.xml',
        'reports/grant_report_template.xml',
    ],
    'demo': [
        'demo/grant_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
