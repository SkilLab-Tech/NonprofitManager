{
    'name': 'USBEA Board Portal AI Widgets',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'AI-powered board dashboard widgets + tenant theme tokens (Phase 6)',
    'description': """
        Phase 6 polish layer.

        Adds AI-driven dashboard widgets to the board portal:
        - Stale-task summary (consumes the seeded stale_tasks_summary
          prompt template from usbea_ai).
        - Cross-pillar KPI commentary (donations YTD, grants in pipeline,
          stale tasks, LGPD DSAR queue).
        - One-click "weekly briefing" assembling all of the above.

        Hardens multi-tenant white-label readiness via the
        TenantThemeTokens utility — Phase 6 prerequisite to onboarding
        a second tenant. Pure-Python, fully unit-tested.

        Plays cleanly with all preceding USBEA modules — soft-imports
        them and degrades gracefully if any are absent.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'mail',
        'usbea_rbac',
        'usbea_portal',
        'usbea_ai',
    ],
    'data': [
        'security/portal_ai_security.xml',
        'security/ir.model.access.csv',
        'views/board_briefing_views.xml',
        'views/portal_ai_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
