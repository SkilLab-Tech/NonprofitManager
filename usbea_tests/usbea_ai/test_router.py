"""Unit tests for ModelRouter.

We mock the Anthropic SDK shape rather than importing it so tests run with
no external dependency. The router's contract is:
- Call client.messages.create() exactly once on success
- Retry up to N times on failure, then raise AIProviderError
- Pass redacted prompt to the API (never raw PII)
- Write a cache entry on success, hit it on second identical call
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from services.cache import PromptCache
from services.lgpd_redactor import LGPDRedactor
from services.router import (
    AIConfigurationError,
    AIProviderError,
    ModelRouter,
    RouterResponse,
)


@dataclass
class FakeBlock:
    text: str


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


class FakeResponse:
    def __init__(self, text: str, tokens_in: int = 10, tokens_out: int = 20):
        self.content = [FakeBlock(text=text)]
        self.usage = FakeUsage(input_tokens=tokens_in, output_tokens=tokens_out)


class FakeAnthropic:
    """Minimal Anthropic client surface that ModelRouter needs."""

    def __init__(self, response_text: str = "ok", fail_times: int = 0):
        self._response_text = response_text
        self._fail_times = fail_times
        self._calls = 0
        self.messages = self  # so .messages.create works

    def create(self, **kwargs):
        self._calls += 1
        if self._fail_times > 0:
            self._fail_times -= 1
            msg = "transient provider error"
            raise RuntimeError(msg)
        return FakeResponse(self._response_text)


class TestModelRouterConstruction:
    def test_requires_client(self):
        with pytest.raises(AIConfigurationError):
            ModelRouter(
                anthropic_client=None,
                cache=PromptCache(),
                redactor=LGPDRedactor(),
            )

    def test_resolve_model_uses_tier_default(self):
        router = ModelRouter(
            anthropic_client=FakeAnthropic(),
            cache=PromptCache(),
            redactor=LGPDRedactor(),
        )
        assert router._resolve_model("quick", None) == "claude-haiku-4-5-20251001"
        assert router._resolve_model("standard", None) == "claude-sonnet-4-6"
        assert router._resolve_model("deep", None) == "claude-opus-4-7"

    def test_resolve_model_honors_default_override(self):
        router = ModelRouter(
            anthropic_client=FakeAnthropic(),
            cache=PromptCache(),
            redactor=LGPDRedactor(),
            default_model="some-custom-model",
        )
        # Default model wins over tier
        assert router._resolve_model("quick", None) == "some-custom-model"

    def test_resolve_model_honors_per_call_override(self):
        router = ModelRouter(
            anthropic_client=FakeAnthropic(),
            cache=PromptCache(),
            redactor=LGPDRedactor(),
        )
        assert router._resolve_model("standard", "claude-opus-4-7") == "claude-opus-4-7"


class TestModelRouterCall:
    def test_successful_call_returns_response(self):
        router = ModelRouter(
            anthropic_client=FakeAnthropic(response_text="hello world"),
            cache=PromptCache(),
            redactor=LGPDRedactor(),
        )
        resp = router.call(
            system_prompt="You are helpful.",
            user_prompt="Say hi.",
        )
        assert isinstance(resp, RouterResponse)
        assert resp.response == "hello world"
        assert resp.cache_hit is False
        assert resp.tokens_in == 10
        assert resp.tokens_out == 20

    def test_empty_user_prompt_raises(self):
        router = ModelRouter(
            anthropic_client=FakeAnthropic(),
            cache=PromptCache(),
            redactor=LGPDRedactor(),
        )
        with pytest.raises(ValueError):
            router.call(system_prompt="sys", user_prompt="")

    def test_retry_then_success(self):
        client = FakeAnthropic(response_text="recovered", fail_times=2)
        router = ModelRouter(
            anthropic_client=client,
            cache=PromptCache(),
            redactor=LGPDRedactor(),
            retry_attempts=3,
            retry_backoff_seconds=0.0,
        )
        resp = router.call(system_prompt="s", user_prompt="u")
        assert resp.response == "recovered"
        assert client._calls == 3  # 2 failures + 1 success

    def test_retry_exhausted_raises_provider_error(self):
        client = FakeAnthropic(response_text="never", fail_times=5)
        router = ModelRouter(
            anthropic_client=client,
            cache=PromptCache(),
            redactor=LGPDRedactor(),
            retry_attempts=3,
            retry_backoff_seconds=0.0,
        )
        with pytest.raises(AIProviderError):
            router.call(system_prompt="s", user_prompt="u")
        assert client._calls == 3  # exhausted

    def test_cache_hit_on_second_identical_call(self):
        client = FakeAnthropic(response_text="cached me")
        cache = PromptCache(ttl_seconds=300)
        router = ModelRouter(
            anthropic_client=client,
            cache=cache,
            redactor=LGPDRedactor(),
        )
        r1 = router.call(system_prompt="s", user_prompt="u")
        r2 = router.call(system_prompt="s", user_prompt="u")
        assert r1.cache_hit is False
        assert r2.cache_hit is True
        assert r2.response == "cached me"
        # Provider called only on first call.
        assert client._calls == 1

    def test_redactor_strips_pii_before_provider_call(self):
        client = MagicMock()
        # Set up the mock to return a FakeResponse
        client.messages.create.return_value = FakeResponse("scrubbed", 5, 5)
        router = ModelRouter(
            anthropic_client=client,
            cache=PromptCache(),
            redactor=LGPDRedactor(),
        )
        # Pass a user prompt with a valid CPF
        resp = router.call(
            system_prompt="s",
            user_prompt="O CPF do doador é 529.982.247-25, ligue para (11) 99876-5432.",
        )
        # Inspect the actual messages payload sent to the provider
        call_args = client.messages.create.call_args
        sent_user = call_args.kwargs["messages"][0]["content"]
        assert "529.982.247-25" not in sent_user
        assert "99876-5432" not in sent_user
        assert "<CPF_1>" in sent_user
        assert "<PHONE_1>" in sent_user
        # Router reports the redaction in the response
        assert resp.lgpd_redacted is True
        assert "CPF" in resp.redaction_types
        assert "PHONE" in resp.redaction_types

    def test_redactor_skipped_when_redact_false(self):
        client = MagicMock()
        client.messages.create.return_value = FakeResponse("ok")
        router = ModelRouter(
            anthropic_client=client,
            cache=PromptCache(),
            redactor=LGPDRedactor(),
        )
        router.call(
            system_prompt="s",
            user_prompt="O CPF é 529.982.247-25.",
            redact=False,
        )
        sent_user = client.messages.create.call_args.kwargs["messages"][0]["content"]
        # PII preserved when explicitly told not to redact
        assert "529.982.247-25" in sent_user


class TestExtractText:
    def test_extracts_from_content_blocks(self):
        resp = FakeResponse("hello world")
        assert ModelRouter._extract_text(resp) == "hello world"

    def test_extracts_from_text_attribute(self):
        class FlatResp:
            text = "flat response"
        assert ModelRouter._extract_text(FlatResp()) == "flat response"

    def test_raises_on_empty(self):
        class Empty:
            content: list[Any] = []
        with pytest.raises(AIProviderError):
            ModelRouter._extract_text(Empty())

    def test_concatenates_multiple_blocks(self):
        class MultiResp:
            content = [FakeBlock(text="Hello "), FakeBlock(text="world!")]
        assert ModelRouter._extract_text(MultiResp()) == "Hello world!"


class TestExtractTokenCounts:
    def test_extracts_when_usage_present(self):
        resp = FakeResponse("ok", tokens_in=42, tokens_out=17)
        assert ModelRouter._extract_token_counts(resp) == (42, 17)

    def test_returns_zero_when_usage_missing(self):
        class NoUsage:
            content: list[Any] = []
        assert ModelRouter._extract_token_counts(NoUsage()) == (0, 0)
