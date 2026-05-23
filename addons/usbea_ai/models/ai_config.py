"""Singleton config + the public service interface for the AI layer.

Pillar modules call:

    self.env['usbea.ai'].suggest('task_priority', context={...})

This indirection means callers never import the anthropic SDK and never
construct router/cache/redactor instances themselves. All state lives on
``ir.config_parameter`` so changes don't require a module reload.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.cache import PromptCache
from ..services.lgpd_redactor import LGPDRedactor
from ..services.router import (
    TIER_MODEL_DEFAULTS,
    AIBudgetExceededError,
    AIConfigurationError,
    AIError,
    ModelRouter,
    RouterResponse,
)

_logger = logging.getLogger(__name__)


CONFIG_KEYS = {
    "api_key": "usbea_ai.anthropic_api_key",
    "default_model": "usbea_ai.default_model",
    "cache_ttl": "usbea_ai.cache_ttl_seconds",
    "cache_max_entries": "usbea_ai.cache_max_entries",
    "redaction_enabled": "usbea_ai.redaction_enabled",
    "audit_retention_days": "usbea_ai.audit_retention_days",
    "monthly_token_budget": "usbea_ai.monthly_token_budget",
    "retry_attempts": "usbea_ai.retry_attempts",
}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).lower() in ("1", "true", "yes", "on")


class UsbeaAI(models.AbstractModel):
    """Public service surface — every pillar module calls ``env['usbea.ai']``."""

    _name = "usbea.ai"
    _description = "USBEA AI service entry point"

    # Per-thread router cache so we don't rebuild the Anthropic client on every
    # call. Recreated when config changes (see ``_invalidate_router_cache``).
    _router_cache: threading.local = threading.local()

    # ----- Configuration accessors -----

    @api.model
    def _get_param(self, key: str) -> str | None:
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(CONFIG_KEYS[key])
        )

    @api.model
    def _get_config_snapshot(self) -> dict[str, Any]:
        get = self._get_param
        return {
            "api_key": get("api_key") or "",
            "default_model": get("default_model") or "",
            "cache_ttl": _as_int(get("cache_ttl"), 300),
            "cache_max_entries": _as_int(get("cache_max_entries"), 256),
            "redaction_enabled": _as_bool(get("redaction_enabled"), True),
            "audit_retention_days": _as_int(get("audit_retention_days"), 365),
            "monthly_token_budget": _as_int(get("monthly_token_budget"), 0),
            "retry_attempts": _as_int(get("retry_attempts"), 3),
        }

    # ----- Router construction -----

    @api.model
    def _build_router(self) -> ModelRouter:
        cfg = self._get_config_snapshot()
        if not cfg["api_key"]:
            msg = _(
                "USBEA AI is not configured: missing Anthropic API key. "
                "Set usbea_ai.anthropic_api_key in Settings.",
            )
            raise AIConfigurationError(msg)
        try:
            import anthropic  # noqa: PLC0415 — soft dependency, graceful fallback message
        except ImportError as exc:
            msg = _(
                "anthropic Python SDK not installed. Add 'anthropic' to "
                "the Python environment serving Odoo.",
            )
            raise AIConfigurationError(msg) from exc

        client = anthropic.Anthropic(api_key=cfg["api_key"])
        cache = PromptCache(
            ttl_seconds=cfg["cache_ttl"],
            max_entries=cfg["cache_max_entries"],
        )
        redactor = LGPDRedactor() if cfg["redaction_enabled"] else None
        return ModelRouter(
            anthropic_client=client,
            cache=cache,
            redactor=redactor,
            default_model=cfg["default_model"] or None,
            retry_attempts=cfg["retry_attempts"],
        )

    @api.model
    def _get_router(self) -> ModelRouter:
        existing = getattr(self._router_cache, "router", None)
        if existing is not None:
            return existing
        router = self._build_router()
        self._router_cache.router = router
        return router

    @api.model
    def _invalidate_router_cache(self) -> None:
        """Called after config changes so the next call rebuilds the client."""
        if hasattr(self._router_cache, "router"):
            del self._router_cache.router

    # ----- Budget enforcement -----

    @api.model
    def _check_budget(self, company_id: int) -> None:
        """Hard cap: raise if this company exceeded monthly token budget."""
        budget = _as_int(self._get_param("monthly_token_budget"), 0)
        if budget <= 0:
            return
        Suggestion = self.env["usbea.ai.suggestion"].sudo()
        start = fields.Datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        used = Suggestion.search_read(
            [
                ("company_id", "=", company_id),
                ("create_date", ">=", fields.Datetime.to_string(start)),
            ],
            ["tokens_in", "tokens_out"],
        )
        total = sum((r.get("tokens_in") or 0) + (r.get("tokens_out") or 0) for r in used)
        if total >= budget:
            msg = _(
                "USBEA AI monthly token budget exceeded for this company "
                "(used %(used)s of %(budget)s).",
                used=total,
                budget=budget,
            )
            raise AIBudgetExceededError(msg)

    # ----- Public suggest() -----

    @api.model
    def suggest(
        self,
        template_key: str,
        *,
        context: dict[str, Any] | None = None,
        source_module: str = "",
        source_model: str = "",
        source_record_id: int | None = None,
        partner_ids: list[int] | None = None,
        max_tokens_override: int | None = None,
        model_override: str | None = None,
    ):
        """Run a prompt template against the configured model.

        Returns the persisted ``usbea.ai.suggestion`` record. Callers can read
        ``record.response`` and present an Accept/Reject UI affordance.

        Errors raised from the router (``AIError`` subclasses) are wrapped in a
        suggestion record with ``error`` set rather than re-raised, so the caller
        can render an inline 'AI unavailable' state without crashing.
        """
        context = context or {}
        Template = self.env["usbea.ai.prompt_template"].sudo()
        tmpl = Template.search([("technical_key", "=", template_key)], limit=1)
        if not tmpl:
            msg = _("Unknown AI prompt template: %s", template_key)
            raise UserError(msg)

        Suggestion = self.env["usbea.ai.suggestion"].sudo()
        company = self.env.company

        # Budget gate — write a failed suggestion if hit, then surface to user.
        try:
            self._check_budget(company.id)
        except AIBudgetExceededError as exc:
            return Suggestion.create(
                {
                    "template_id": tmpl.id,
                    "model_used": "",
                    "prompt_hash": "",
                    "response": "",
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cache_hit": False,
                    "latency_ms": 0,
                    "lgpd_redacted": False,
                    "redaction_types": "",
                    "source_module": source_module,
                    "source_model": source_model,
                    "source_record_id": source_record_id or 0,
                    "partner_ids": [(6, 0, partner_ids or [])],
                    "error": str(exc),
                    "company_id": company.id,
                },
            )

        # Render prompt — Jinja-light using str.format_map for safety
        try:
            rendered = tmpl.render(context)
        except Exception as exc:  # noqa: BLE001
            msg = _("Failed to render template %s: %s", template_key, exc)
            raise UserError(msg) from exc

        try:
            router = self._get_router()
            resp: RouterResponse = router.call(
                system_prompt=rendered["system"],
                user_prompt=rendered["user"],
                tier=tmpl.tier,
                model_override=model_override or tmpl.model_preference or None,
                max_tokens=max_tokens_override or tmpl.max_tokens,
                temperature=tmpl.temperature,
                redact=True,
            )
        except AIError as exc:
            return Suggestion.create(
                {
                    "template_id": tmpl.id,
                    "model_used": "",
                    "prompt_hash": "",
                    "response": "",
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cache_hit": False,
                    "latency_ms": 0,
                    "lgpd_redacted": False,
                    "redaction_types": "",
                    "source_module": source_module,
                    "source_model": source_model,
                    "source_record_id": source_record_id or 0,
                    "partner_ids": [(6, 0, partner_ids or [])],
                    "error": str(exc),
                    "company_id": company.id,
                },
            )

        prompt_hash = PromptCache.make_key(
            rendered["system"], rendered["user"], resp.model_used,
        )

        return Suggestion.create(
            {
                "template_id": tmpl.id,
                "model_used": resp.model_used,
                "prompt_hash": prompt_hash,
                "response": resp.response,
                "tokens_in": resp.tokens_in,
                "tokens_out": resp.tokens_out,
                "cache_hit": resp.cache_hit,
                "latency_ms": resp.latency_ms,
                "lgpd_redacted": resp.lgpd_redacted,
                "redaction_types": ",".join(resp.redaction_types),
                "source_module": source_module,
                "source_model": source_model,
                "source_record_id": source_record_id or 0,
                "partner_ids": [(6, 0, partner_ids or [])],
                "context_json": json.dumps(context, default=str)[:8000],
                "company_id": company.id,
            },
        )

    # ----- DSAR adapter -----

    @api.model
    def _get_lgpd_data_for_partner(self, partner_id: int) -> dict[str, Any]:
        """Expose AI suggestions referencing this partner for DSAR export."""
        rows = self.env["usbea.ai.suggestion"].sudo().search_read(
            [("partner_ids", "in", [partner_id])],
            ["id", "template_id", "model_used", "create_date", "lgpd_redacted",
             "redaction_types", "source_module", "source_model", "source_record_id"],
        )
        return {"usbea.ai.suggestion": rows}


class ResConfigSettings(models.TransientModel):
    """Admin UI for USBEA AI config — writes to ir.config_parameter."""

    _inherit = "res.config.settings"

    usbea_ai_api_key = fields.Char(
        string="Anthropic API Key",
        config_parameter=CONFIG_KEYS["api_key"],
    )
    usbea_ai_default_model = fields.Char(
        string="Default Model (override per-template tier)",
        config_parameter=CONFIG_KEYS["default_model"],
        help="If empty, model is resolved from template tier (quick/standard/deep).",
    )
    usbea_ai_cache_ttl_seconds = fields.Integer(
        string="Prompt cache TTL (seconds)",
        config_parameter=CONFIG_KEYS["cache_ttl"],
        default=300,
    )
    usbea_ai_cache_max_entries = fields.Integer(
        string="Prompt cache max entries",
        config_parameter=CONFIG_KEYS["cache_max_entries"],
        default=256,
    )
    usbea_ai_redaction_enabled = fields.Boolean(
        string="LGPD redaction (mandatory in BR — leave on)",
        config_parameter=CONFIG_KEYS["redaction_enabled"],
        default=True,
    )
    usbea_ai_audit_retention_days = fields.Integer(
        string="Audit log retention (days)",
        config_parameter=CONFIG_KEYS["audit_retention_days"],
        default=365,
    )
    usbea_ai_monthly_token_budget = fields.Integer(
        string="Monthly token budget (0 = unlimited)",
        config_parameter=CONFIG_KEYS["monthly_token_budget"],
        default=0,
    )
    usbea_ai_retry_attempts = fields.Integer(
        string="Retry attempts on provider error",
        config_parameter=CONFIG_KEYS["retry_attempts"],
        default=3,
    )

    def set_values(self):
        super().set_values()
        # Force a router rebuild on next call so config changes take effect.
        self.env["usbea.ai"]._invalidate_router_cache()

    @api.model
    def get_values(self):
        res = super().get_values()
        # Show available tiers for documentation purposes.
        res["usbea_ai_tier_defaults"] = json.dumps(TIER_MODEL_DEFAULTS)
        return res
