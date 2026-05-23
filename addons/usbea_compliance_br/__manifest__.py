{
    'name': 'USBEA Brazilian Compliance Pack',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'LGPD, MROSC, OSCIP, and Receita Federal compliance for Brazilian nonprofits',
    'description': """
        Brazilian regulatory pack — the differentiator no US-built nonprofit
        suite offers. See docs/COMPLIANCE.md for the full mapping.

        Submodules ship in one bundle to enforce coherent semantics:

        - LGPD (Lei 13.709/2018)
            * Consent registry with scope + lawful basis tracking (Art. 7)
            * DSAR (Data Subject Access Request) workflow with 15-day SLA (Art. 18)
            * Processing log (Art. 37)
            * Cross-module DSAR aggregator — calls per-module
              ``_get_lgpd_data_for_partner(partner_id)`` adapters

        - MROSC (Lei 13.019/2014)
            * Public-sector partnership tracking (termo de colaboração /
              fomento / acordo de cooperação)
            * Prestação de contas state machine

        - OSCIP (Lei 9.790/1999)
            * Certification status + qualifying finalities tracker

        - Receita Federal
            * DIRF prep wizard
            * IRPF-compliant donor receipt template fields

        Extends ``usbea_compliance`` (PDF report templates already live there).
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'base',
        'mail',
        'usbea_rbac',
        'usbea_compliance',
    ],
    'data': [
        'security/compliance_br_security.xml',
        'security/ir.model.access.csv',
        'data/lgpd_processing_log_seed.xml',
        'views/lgpd_consent_views.xml',
        'views/lgpd_dsar_views.xml',
        'views/lgpd_processing_log_views.xml',
        'views/mrosc_partnership_views.xml',
        'views/oscip_status_views.xml',
        'views/compliance_br_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
