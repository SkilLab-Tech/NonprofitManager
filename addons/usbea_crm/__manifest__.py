{
    'name': 'USBEA Alumni / Donor / Funder CRM',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Nonprofit-native CRM with archetypes, moves management, engagement scoring, LGPD consent gate',
    'description': """
        Pillar 2 — CRM tailored to alumni-driven Brazilian nonprofits.

        Adds three contact archetypes on top of res.partner:
        - donor (individuals + corporate)
        - funder (foundations, embassies, agencies)
        - grantee (alumni or entities receiving USBEA grants)

        Workflows:
        - Moves management: research → qualification → cultivation →
          solicitation → stewardship.
        - Engagement scoring: aggregated signals over a configurable window.
        - Soft-credit tracking: m2m between donors for joint giving credit.
        - LGPD consent gate: archetype contacts cannot be saved without an
          active consent record covering the relevant scope.
        - AI hooks: ``donor_segmentation``, ``donor_next_move``, ``donor_thanks_draft``
          via env['usbea.ai'].suggest().

        Extends OCA/partner-contact where ≥70% coverage exists; otherwise
        greenfield. See docs/MODULES.md §usbea_crm.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'crm',
        'mail',
        'usbea_rbac',
        'usbea_ai',
        'usbea_compliance_br',
    ],
    'data': [
        'security/usbea_crm_security.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/cultivation_move_views.xml',
        'views/engagement_event_views.xml',
        'views/usbea_crm_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
