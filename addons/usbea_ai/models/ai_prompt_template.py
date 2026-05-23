"""Reusable AI prompt templates — DB-driven so admins can tune without code deploy."""

from __future__ import annotations

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Allow {{variable}} placeholders only — refuses arbitrary code expressions.
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class UsbeaAIPromptTemplate(models.Model):
    _name = "usbea.ai.prompt_template"
    _description = "USBEA AI Prompt Template"
    _order = "tier, name"
    _rec_name = "name"

    name = fields.Char(required=True)
    technical_key = fields.Char(
        required=True,
        copy=False,
        help="Stable identifier referenced from code (e.g. 'task_priority'). "
        "Snake_case, no spaces.",
    )
    description = fields.Text()
    tier = fields.Selection(
        [("quick", "Quick (haiku)"), ("standard", "Standard (sonnet)"), ("deep", "Deep (opus)")],
        default="standard",
        required=True,
    )
    model_preference = fields.Char(
        help="Override the tier default — set the exact Anthropic model ID. "
        "Leave empty to use tier default.",
    )
    system_prompt = fields.Text(required=True)
    user_prompt_template = fields.Text(
        required=True,
        help="User-side prompt body. Use {{variable}} placeholders interpolated from the "
        "context dict at call time. No code execution — placeholders are simple substitution.",
    )
    max_tokens = fields.Integer(default=1024, required=True)
    temperature = fields.Float(default=0.7, required=True)
    locale = fields.Selection(
        [("pt_BR", "Portuguese (Brazil)"), ("en_US", "English (US)"), ("multi", "Multilingual")],
        default="pt_BR",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "technical_key_unique",
            "UNIQUE(technical_key)",
            "Prompt template technical_key must be unique.",
        ),
    ]

    @api.constrains("temperature")
    def _check_temperature(self):
        for rec in self:
            if not 0.0 <= rec.temperature <= 2.0:
                msg = _("Temperature must be between 0.0 and 2.0 (got %s).") % rec.temperature
                raise ValidationError(msg)

    @api.constrains("max_tokens")
    def _check_max_tokens(self):
        for rec in self:
            if rec.max_tokens < 16 or rec.max_tokens > 64000:
                msg = _("max_tokens must be between 16 and 64000 (got %s).") % rec.max_tokens
                raise ValidationError(msg)

    @api.constrains("technical_key")
    def _check_technical_key(self):
        for rec in self:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", rec.technical_key or ""):
                msg = _(
                    "technical_key must be snake_case (got %s).",
                ) % rec.technical_key
                raise ValidationError(msg)

    def render(self, context: dict) -> dict:
        """Interpolate {{vars}} into system+user prompt.

        Returns ``{"system": "...", "user": "..."}``. Missing variables raise
        ValidationError so we never silently send a half-rendered prompt.
        """
        self.ensure_one()
        context = context or {}

        def _substitute(template: str) -> str:
            def _repl(match: re.Match[str]) -> str:
                key = match.group(1)
                if key not in context:
                    msg = _(
                        "Template %(tpl)s requires context variable %(var)s",
                        tpl=self.technical_key,
                        var=key,
                    )
                    raise ValidationError(msg)
                value = context[key]
                # Coerce to string, but DON'T re-redact here — that happens in the router.
                return str(value)

            return _PLACEHOLDER_RE.sub(_repl, template)

        return {
            "system": _substitute(self.system_prompt or ""),
            "user": _substitute(self.user_prompt_template or ""),
        }

    @api.model
    def accept_rate(self, technical_key: str) -> float:
        """Return the accept-rate (0.0-1.0) for a template across all suggestions.

        Used in admin dashboards to flag underperforming prompts.
        """
        Suggestion = self.env["usbea.ai.suggestion"].sudo()
        total = Suggestion.search_count(
            [("template_id.technical_key", "=", technical_key), ("error", "=", False)],
        )
        if total == 0:
            return 0.0
        accepted = Suggestion.search_count(
            [
                ("template_id.technical_key", "=", technical_key),
                ("error", "=", False),
                ("accepted", "=", True),
            ],
        )
        return accepted / total
