{
    'name': 'USBEA Impact Measurement',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Outcome indicators, theory-of-change, impact narratives, AI-generated reports',
    'description': """
        Pillar 4 — Impact measurement.

        Models:
        - usbea.impact.indicator — quantitative outcome indicators per program
          (target_value, current_value, frequency).
        - usbea.impact.measurement — append-only measurement log feeding indicators.
        - usbea.impact.story — qualitative beneficiary narratives, with media
          attachments and explicit consent_id linkage (LGPD-safe).
        - usbea.impact.report — period × programs report assembly with
          AI-generated narrative.

        AI hooks:
        - impact_narrative template — assembles factual report from indicators
          and (consent-cleared) story tokens.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'mail',
        'usbea_rbac',
        'usbea_programs',
        'usbea_ai',
        'usbea_compliance_br',
    ],
    'data': [
        'security/impact_security.xml',
        'security/ir.model.access.csv',
        'views/indicator_views.xml',
        'views/measurement_views.xml',
        'views/story_views.xml',
        'views/report_views.xml',
        'views/impact_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
