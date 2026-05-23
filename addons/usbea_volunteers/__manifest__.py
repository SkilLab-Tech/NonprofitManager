{
    'name': 'USBEA Volunteer Management',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Volunteer profiles, skills, availability, hours tracking, opportunity matching',
    'description': """
        Phase 4 expansion — extends usbea_programs with proper volunteer
        management. Separate module so adopters who don't need volunteer
        workflows can skip the extra complexity.

        Models:
        - usbea.volunteer.skill: hierarchical skill taxonomy (mentoring,
          translation, event ops, marketing, legal, etc.).
        - usbea.volunteer.availability_slot: when a volunteer can serve
          (weekday + hour window + timezone).
        - usbea.volunteer.opportunity: a specific need posted by a program.
        - usbea.volunteer.hours_log: append-only hours ledger with manager
          approval workflow.
        - usbea.volunteer.background_check: status + expiry tracking with
          cron-driven expiry warnings.

        Extends res.partner with archetype='volunteer' from usbea_crm — the
        CRM LGPD consent gate already covers volunteer onboarding.

        Pure-Python skill matching algorithm in utils/matching.py — scores
        opportunity↔volunteer fit and returns a ranked list.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'mail',
        'usbea_rbac',
        'usbea_programs',
        'usbea_crm',
    ],
    'data': [
        'security/volunteers_security.xml',
        'security/ir.model.access.csv',
        'data/volunteer_skill_seed.xml',
        'views/volunteer_skill_views.xml',
        'views/volunteer_views.xml',
        'views/availability_slot_views.xml',
        'views/opportunity_views.xml',
        'views/hours_log_views.xml',
        'views/background_check_views.xml',
        'views/volunteers_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
