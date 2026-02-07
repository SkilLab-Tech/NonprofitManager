{
    'name': 'USBEA Compliance & Reporting',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Compliance report templates and automated generation',
    'description': """
        Compliance reporting for USBEA Brasil:
        - Quarterly narrative report template
        - Financial expenditure report
        - Participant impact report
        - Final grant closeout report
        - PDF export with USBEA branding
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['base', 'usbea_grants', 'usbea_programs'],
    'data': [
        'security/ir.model.access.csv',
        'reports/compliance_report_templates.xml',
        'views/compliance_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
