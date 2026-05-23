"""ModelRouter — single chokepoint for all LLM calls.

Every pillar module calls `env['usbea.ai'].suggest(template_key, context)`,
which in turn calls a router instance. The router:
1. Resolves model from template tier + tenant overrides
2. Builds final prompt (Jinja-style {{context}} interpolation)
3. Runs LGPD redaction on prompt body
4. Checks the prompt cache
5. Calls the Anthropic API (or other provider in future) with retry
6. Writes an `usbea.ai.suggestion` audit row
7. Returns the response (or raises a typed error)

The router is provider-agnostic at the public surface. Today it wraps
the Anthropic SDK; tomorrow it can wrap an Ollama local fallback or
OpenAI without changing callers.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)


# Model identifiers per `/root/CLAUDE.md` (Claude 4.X family — Jan 2026 cutoff).
TIER_MODEL_DEFAULTS: dict[str, str] = {
    "quick": "claude-haiku-4-5-20251001",
    "standard": "claude-sonnet-4-6",
    "deep": "claude-opus-4-7",
}


class AIError(Exception):
    """Base class for all router-raised errors. Callers should not auto-fallback;
    they MUST surface to user with a clear 'AI unavailable' affordance."""


class AIConfigurationError(AIError):
    """Configuration missing (e.g., no API key) — fail loudly at startup."""


class AIProviderError(AIError):
    """The downstream provider returned an error after retries."""


class AIBudgetExceededError(AIError):
    """Tenant exceeded monthly token budget — hard cap reached."""


@dataclass
class RouterResponse:
    """Return value of a router call. Models map closely to the audit row."""

    response: str
    model_used: str
    tokens_in: int
    tokens_out: int
    cache_hit: bool
    latency_ms: int
    lgpd_redacted: bool
    redaction_types: list[str]


class ModelRouter:
    """Provider-agnostic LLM router.

    Constructed lazily by the `usbea.ai.config` Odoo singleton, which passes in
    a configured Anthropic client. Pure-Python; no Odoo imports here so the
    services layer remains independently testable.
    """

    def __init__(
        self,
        anthropic_client: Any,
        cache: Any,
        redactor: Any,
        default_model: str | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 1.0,
    ):
        if anthropic_client is None:
            msg = "anthropic client is required"
            raise AIConfigurationError(msg)
        self._client = anthropic_client
        self._cache = cache
        self._redactor = redactor
        self._default_model = default_model
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = max(0.0, retry_backoff_seconds)

    def _resolve_model(self, tier: str, override: str | None) -> str:
        if override:
            return override
        if self._default_model:
            return self._default_model
        return TIER_MODEL_DEFAULTS.get(tier, TIER_MODEL_DEFAULTS["standard"])

    def call(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tier: str = "standard",
        model_override: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        redact: bool = True,
    ) -> RouterResponse:
        """Make a single inference call.

        Raises AIProviderError on failure after retries; never silently falls
        back to cache.
        """
        if not user_prompt:
            msg = "user_prompt is required"
            raise ValueError(msg)

        # Step 1: redact PII before anything else touches the prompt.
        redaction_types: list[str] = []
        lgpd_redacted = False
        if redact and self._redactor is not None:
            result = self._redactor.scrub(user_prompt)
            user_prompt = result.text
            lgpd_redacted = result.matched
            redaction_types = sorted(result.types_matched)
            if result.matched:
                _logger.debug(
                    "LGPD redactor matched %s",
                    redaction_types,
                )

        model = self._resolve_model(tier, model_override)

        # Step 2: cache lookup.
        cache_key = None
        if self._cache is not None:
            cache_key = self._cache.make_key(system_prompt, user_prompt, model)
            cached = self._cache.get(cache_key)
            if cached is not None:
                return RouterResponse(
                    response=cached,
                    model_used=model,
                    tokens_in=0,
                    tokens_out=0,
                    cache_hit=True,
                    latency_ms=0,
                    lgpd_redacted=lgpd_redacted,
                    redaction_types=redaction_types,
                )

        # Step 3: provider call with retry.
        last_error: Exception | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:  # noqa: PLW0717 — retry body needs to wrap the full request cycle
                start = time.monotonic()
                resp = self._client.messages.create(
                    model=model,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                text = self._extract_text(resp)
                tokens_in, tokens_out = self._extract_token_counts(resp)

                if cache_key is not None and self._cache is not None:
                    self._cache.set(cache_key, text)

                return RouterResponse(
                    response=text,
                    model_used=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cache_hit=False,
                    latency_ms=latency_ms,
                    lgpd_redacted=lgpd_redacted,
                    redaction_types=redaction_types,
                )
            except Exception as exc:  # noqa: BLE001 — re-raise as typed error after retries
                last_error = exc
                _logger.warning(
                    "AI provider call failed (attempt %s/%s): %s",
                    attempt,
                    self._retry_attempts,
                    exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff * attempt)

        msg = f"AI provider failed after {self._retry_attempts} attempts"
        raise AIProviderError(msg) from last_error

    @staticmethod
    def _extract_text(resp: Any) -> str:
        """Pull plain-text content out of an Anthropic Messages response.

        Defensive against SDK shape changes — supports the documented
        content blocks list as well as a flat .text attribute.
        """
        text_attr = getattr(resp, "text", None)
        if isinstance(text_attr, str):
            return text_attr
        content = getattr(resp, "content", None)
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                block_text = getattr(block, "text", None)
                if isinstance(block_text, str):
                    parts.append(block_text)
            if parts:
                return "".join(parts)
        msg = "Anthropic response did not contain text content"
        raise AIProviderError(msg)

    @staticmethod
    def _extract_token_counts(resp: Any) -> tuple[int, int]:
        usage = getattr(resp, "usage", None)
        if usage is None:
            return 0, 0
        return (
            int(getattr(usage, "input_tokens", 0) or 0),
            int(getattr(usage, "output_tokens", 0) or 0),
        )
