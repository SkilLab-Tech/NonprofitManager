{
    'name': 'USBEA AI Layer',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'Shared AI inference layer (Claude API) with LGPD-safe redaction and audit log',
    'description': """
        Cross-cutting AI infrastructure for the USBEA Nonprofit OS:
        - ModelRouter wrapping the Anthropic Claude API (Opus 4.7 / Sonnet 4.6 / Haiku 4.5)
        - Prompt template registry (DB-driven, admin-editable, seeded with 11 templates)
        - Prompt cache (SHA256-keyed, 5-min TTL — leverages Anthropic prompt caching)
        - LGPD-safe Brazilian PII redactor (CPF/CNPJ/PIX keys/phones/CEP/emails)
        - Audit log of every AI call (DSAR-ready, per-partner aggregation)
        - Tenant-level config: API key, default model, cache TTL, redaction policy, budget

        Every pillar module (usbea_tasks, usbea_crm, usbea_grants_seeking, usbea_impact,
        usbea_donations) calls env['usbea.ai'].suggest(template_key, context) — never
        imports the anthropic SDK directly.

        See docs/AI.md for full architecture.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': ['base', 'mail', 'usbea_rbac'],
    'data': [
        'security/ai_security.xml',
        'security/ir.model.access.csv',
        'data/prompt_templates_data.xml',
        'views/ai_prompt_template_views.xml',
        'views/ai_suggestion_views.xml',
        'views/ai_config_views.xml',
        'views/ai_menus.xml',
    ],
    'external_dependencies': {
        'python': ['anthropic'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
