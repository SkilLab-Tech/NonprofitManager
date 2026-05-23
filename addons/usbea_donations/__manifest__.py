{
    'name': 'USBEA Donations Rail',
    'version': '19.0.1.0.0',
    'category': 'Nonprofit',
    'summary': 'IRPF-compliant donor receipts, recurring giving via PIX Automatico + Mercado Pago, P2P campaigns',
    'description': """
        Pillar 5 — Donations.

        Greenfield (OCA/donation 19.0 is skeleton-only at this writing; we
        mine 18.0 OCA models as reference but ship our own implementation
        tuned for Brazilian fiscal compliance).

        Core models:
        - usbea.donation: single donation record. Reconciles against account.move.
        - usbea.donation.recurring_plan: subscription-style recurring giving.
        - usbea.donation.p2p_campaign: peer-to-peer fundraising pages.
        - usbea.donation.receipt_template: IRPF receipt layout with CNPJ
          (USBEA) + CPF/CNPJ (donor) + OSCIP qualifying article reference.

        Payment rail integration:
        - Doare API client for PIX Automatico recurring donations.
        - Mercado Pago Subscriptions v2 client for credit-card recurring +
          boleto for donors without PIX.
        - Webhook controllers (/usbea_donations/webhook/{doare,mp})
          with HMAC signature verification.

        Cross-pillar wiring:
        - On confirmed donation, write a usbea.engagement.event row of type
          'donation' or 'donation_recurring' to feed CRM engagement scoring.
        - Donor partner must have an active LGPD consent — the CRM gate in
          usbea_crm already enforces this on archetype assignment; donations
          additionally log to the LGPD processing log at install.

        Receipt issuance only when usbea.oscip.status.is_certified AND
        upf_certified — the model raises a UserError otherwise.

        See docs/PRD.md, docs/MODULES.md and docs/COMPLIANCE.md.
    """,
    'author': 'Automation Labs / SkilLab',
    'website': 'https://automation-labs.co',
    'depends': [
        'mail',
        'account',
        'usbea_rbac',
        'usbea_crm',
        'usbea_ai',
        'usbea_compliance_br',
    ],
    'data': [
        'security/donations_security.xml',
        'security/ir.model.access.csv',
        'data/donations_sequence.xml',
        'data/receipt_template_seed.xml',
        'data/processing_log_donations.xml',
        'views/donation_views.xml',
        'views/recurring_plan_views.xml',
        'views/p2p_campaign_views.xml',
        'views/receipt_template_views.xml',
        'views/donations_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
