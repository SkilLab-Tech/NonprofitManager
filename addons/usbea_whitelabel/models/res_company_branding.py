from odoo import fields, models


class ResCompanyBranding(models.Model):
    """Extend res.company with white-label branding fields."""
    _inherit = 'res.company'

    # Branding - visual identity
    # Note: logo is already on res.company (related to partner_id.image_1920)
    # We add additional branding fields here
    favicon = fields.Binary('Favicon', help='Upload a 32x32 favicon for the browser tab.')
    brand_primary_color = fields.Char(
        'Primary Color', default='#007bff',
        help='Primary brand color (hex). Used for buttons, links, and accents.',
    )
    brand_secondary_color = fields.Char(
        'Secondary Color', default='#6c757d',
        help='Secondary brand color (hex). Used for secondary elements.',
    )
    brand_accent_color = fields.Char(
        'Accent Color', default='#28a745',
        help='Accent color (hex). Used for success states and highlights.',
    )
    brand_font = fields.Selection([
        ('Lato', 'Lato'),
        ('Roboto', 'Roboto'),
        ('Open Sans', 'Open Sans'),
        ('Montserrat', 'Montserrat'),
        ('Poppins', 'Poppins'),
        ('Inter', 'Inter'),
    ], string='Brand Font', default='Roboto')

    # Extended contact details for public display
    address_display = fields.Text(
        'Display Address',
        help='Full address as you want it displayed on reports and portal.',
    )
    contact_email_public = fields.Char(
        'Public Contact Email',
        help='General contact email shown on public-facing pages.',
    )
    contact_phone_public = fields.Char(
        'Public Contact Phone',
    )

    # Legal / footer
    legal_name = fields.Char(
        'Legal Entity Name',
        help='Full legal name for contracts and official documents.',
    )
    report_footer_text = fields.Text(
        'Report Footer Text',
        help='Custom text displayed at the bottom of PDF reports.',
    )
    portal_welcome_message = fields.Html(
        'Portal Welcome Message',
        help='Custom welcome message shown to users when they log in.',
    )

    # Feature toggles for the organization
    show_grants_module = fields.Boolean('Enable Grant Management', default=True)
    show_programs_module = fields.Boolean('Enable Program Management', default=True)
    show_expenses_module = fields.Boolean('Enable Expense Tracking', default=True)
    show_compliance_module = fields.Boolean('Enable Compliance Reporting', default=True)
    show_board_portal = fields.Boolean('Enable Board Portal', default=True)
