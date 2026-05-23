{
    'name': 'USBEA Grant Seeking',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Grant application pipeline with AI grant-writing copilot (flagship Pillar 3 feature)',
    'description': """
        Pillar 3 — distinct from usbea_grants (grant **receiving** lifecycle).
        This module is the **seeking** side: pursuing funding from foundations,
        government, corporate, and major donors.

        Pipeline kanban:
            prospect → researching → drafting → submitted → under_review
                     → awarded | declined | withdrawn

        Key features:
        - usbea.funder — extends res.partner archetype=funder with focus areas,
          typical grant size, application seasons, funder type.
        - usbea.grant_application — pipeline kanban entity with state machine,
          deadline tracker, requested amount in any currency, assigned writer.
        - usbea.grant_application.draft_version — immutable version history
          of the draft narrative. Each version captures who edited what, when,
          and whether AI was used.
        - usbea.grant_application.comment — inline collaboration on drafts.
        - **AI grant-writing copilot** (flagship): calls usbea_ai with the
          'grant_writing' template, conditioned on funder profile + program
          context + draft-so-far. Output goes into a new draft version.
        - AI fit scoring (grant_fit_score) on application creation.
        - AI EN↔PT-BR translation (grant_translate) for funder-language drafts.
        - Award handoff: transitioning to 'awarded' state creates a
          usbea.grant record automatically (linked back via application_id).

        See docs/PRD.md §Pillar 3 and docs/MODULES.md §usbea_grants_seeking.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'mail',
        'usbea_rbac',
        'usbea_ai',
        'usbea_grants',
        'usbea_crm',
    ],
    'data': [
        'security/grants_seeking_security.xml',
        'security/ir.model.access.csv',
        'data/grants_seeking_sequence.xml',
        'views/funder_views.xml',
        'views/grant_application_views.xml',
        'views/grant_application_draft_views.xml',
        'views/grants_seeking_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
