"""Audit log of every AI inference — one row per ``env['usbea.ai'].suggest()`` call.

This is the DSAR substrate: every AI call referencing a partner writes that
partner_id into ``partner_ids`` so an LGPD access request can show "here is
exactly what AI knew about you, when, and whether anything left Brazil".
"""

from __future__ import annotations

from odoo import _, api, fields, models


class UsbeaAISuggestion(models.Model):
    _name = "usbea.ai.suggestion"
    _description = "USBEA AI Suggestion (audit log)"
    _order = "create_date desc"
    _rec_name = "template_id"

    template_id = fields.Many2one(
        "usbea.ai.prompt_template",
        string="Prompt template",
        ondelete="restrict",
        required=True,
        index=True,
    )
    model_used = fields.Char(help="Exact Anthropic model ID returned by the API.")
    prompt_hash = fields.Char(
        index=True,
        help="SHA256 of (model + system + user) prompt — for cache lookup and dedup.",
    )
    response = fields.Text()
    error = fields.Char(help="If the AI call failed, the user-facing error string.")

    # Accept/reject signal — drives per-template quality metrics.
    accepted = fields.Boolean(default=False)
    accepted_by = fields.Many2one("res.users", readonly=True)
    accepted_at = fields.Datetime(readonly=True)
    rejected = fields.Boolean(default=False)

    # Cost + perf
    tokens_in = fields.Integer(default=0)
    tokens_out = fields.Integer(default=0)
    cache_hit = fields.Boolean(default=False)
    latency_ms = fields.Integer(default=0)

    # LGPD audit
    lgpd_redacted = fields.Boolean(
        default=False,
        help="True if any Brazilian PII pattern matched and was replaced before the API call.",
    )
    redaction_types = fields.Char(
        help="Comma-separated list of PII types redacted (e.g. 'CPF,EMAIL').",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Partners referenced",
        help="Partners whose data appeared in this prompt — used to aggregate "
        "AI activity for LGPD DSAR responses.",
    )

    # Source tracking (which pillar+record called us)
    source_module = fields.Char(index=True)
    source_model = fields.Char(index=True)
    source_record_id = fields.Integer(index=True)

    # Bounded snapshot of context (for debugging — capped to 8000 chars in code)
    context_json = fields.Text()

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )

    def action_accept(self):
        """User accepted the AI suggestion."""
        self.ensure_one()
        self.write(
            {
                "accepted": True,
                "rejected": False,
                "accepted_by": self.env.user.id,
                "accepted_at": fields.Datetime.now(),
            },
        )

    def action_reject(self):
        """User rejected the AI suggestion."""
        self.ensure_one()
        self.write(
            {"accepted": False, "rejected": True, "accepted_by": False, "accepted_at": False},
        )

    @api.model
    def gc_expired(self) -> int:
        """Cron entry-point: delete suggestions older than retention_days.

        Returns the count of removed rows. Triggered nightly by an ir.cron
        (see data/ai_cron.xml — added in Phase 1.1).
        """
        retention = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("usbea_ai.audit_retention_days", default="365")
        )
        try:
            days = int(retention)
        except (TypeError, ValueError):
            days = 365
        if days <= 0:
            return 0
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        expired = self.search([("create_date", "<", cutoff)])
        count = len(expired)
        expired.unlink()
        return count

    def name_get(self):
        result = []
        for rec in self:
            label = "%s · %s" % (
                rec.template_id.name or _("(no template)"),
                fields.Datetime.to_string(rec.create_date) if rec.create_date else "",
            )
            result.append((rec.id, label))
        return result
