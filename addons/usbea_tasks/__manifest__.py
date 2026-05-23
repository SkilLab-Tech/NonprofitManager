{
    'name': 'USBEA Nonprofit Task Operations',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Nonprofit-native task management with templates, cross-pillar linking, and AI priority',
    'description': """
        Branded task management for USBEA Nonprofit OS — extends stock
        Odoo project/task with nonprofit-specific workflows:

        * Six seeded task templates: program-launch checklist, grant-report
          cadence, board-meeting prep, event-planning, donor-cultivation
          cycle, compliance-deadline tracker.
        * Task linkage to grants (usbea.grant) and programs (usbea.program)
          — time and effort roll up into the receiving-grants module.
        * "My Week" digest view per user.
        * AI-computed priority via usbea_ai (smart prioritization template)
          with explicit accept/reject affordance.
        * Stale-task summary widget on the board portal.

        Pillar 1 deliverable — see docs/PRD.md and docs/MODULES.md.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'project',
        'mail',
        'usbea_rbac',
        'usbea_grants',
        'usbea_programs',
        'usbea_ai',
    ],
    'data': [
        'security/usbea_tasks_security.xml',
        'security/ir.model.access.csv',
        'data/task_templates_data.xml',
        'views/usbea_task_template_views.xml',
        'views/project_task_views.xml',
        'views/usbea_task_dashboard.xml',
        'views/usbea_tasks_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
