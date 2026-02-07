from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ---- Organization Profile ----
    organization_type = fields.Selection(
        related='company_id.organization_type', readonly=False,
    )
    organization_size = fields.Selection(
        related='company_id.organization_size', readonly=False,
    )
    organization_description = fields.Html(
        related='company_id.organization_description', readonly=False,
    )
    mission_statement = fields.Text(
        related='company_id.mission_statement', readonly=False,
    )
    founded_year = fields.Char(
        related='company_id.founded_year', readonly=False,
    )
    tax_id_number = fields.Char(
        related='company_id.tax_id_number', readonly=False,
    )
    registration_number = fields.Char(
        related='company_id.registration_number', readonly=False,
    )

    # ---- Contact Info ----
    support_email = fields.Char(
        related='company_id.support_email', readonly=False,
    )
    public_phone = fields.Char(
        related='company_id.public_phone', readonly=False,
    )
    public_website = fields.Char(
        related='company_id.public_website', readonly=False,
    )
    contact_email_public = fields.Char(
        related='company_id.contact_email_public', readonly=False,
    )
    contact_phone_public = fields.Char(
        related='company_id.contact_phone_public', readonly=False,
    )
    address_display = fields.Text(
        related='company_id.address_display', readonly=False,
    )

    # ---- Social Media ----
    social_facebook = fields.Char(
        related='company_id.social_facebook', readonly=False,
    )
    social_instagram = fields.Char(
        related='company_id.social_instagram', readonly=False,
    )
    social_linkedin = fields.Char(
        related='company_id.social_linkedin', readonly=False,
    )
    social_twitter = fields.Char(
        related='company_id.social_twitter', readonly=False,
    )
    social_youtube = fields.Char(
        related='company_id.social_youtube', readonly=False,
    )

    # ---- Branding ----
    favicon = fields.Binary(
        related='company_id.favicon', readonly=False,
    )
    brand_primary_color = fields.Char(
        related='company_id.brand_primary_color', readonly=False,
    )
    brand_secondary_color = fields.Char(
        related='company_id.brand_secondary_color', readonly=False,
    )
    brand_accent_color = fields.Char(
        related='company_id.brand_accent_color', readonly=False,
    )
    brand_font = fields.Selection(
        related='company_id.brand_font', readonly=False,
    )

    # ---- Legal / Display ----
    legal_name = fields.Char(
        related='company_id.legal_name', readonly=False,
    )
    report_footer_text = fields.Text(
        related='company_id.report_footer_text', readonly=False,
    )
    portal_welcome_message = fields.Html(
        related='company_id.portal_welcome_message', readonly=False,
    )

    # ---- Feature Toggles ----
    show_grants_module = fields.Boolean(
        related='company_id.show_grants_module', readonly=False,
    )
    show_programs_module = fields.Boolean(
        related='company_id.show_programs_module', readonly=False,
    )
    show_expenses_module = fields.Boolean(
        related='company_id.show_expenses_module', readonly=False,
    )
    show_compliance_module = fields.Boolean(
        related='company_id.show_compliance_module', readonly=False,
    )
    show_board_portal = fields.Boolean(
        related='company_id.show_board_portal', readonly=False,
    )
