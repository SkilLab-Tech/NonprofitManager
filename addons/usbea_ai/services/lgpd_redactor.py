"""LGPD-safe PII redactor for Brazilian personal data.

Used before any prompt is sent to an external LLM API (Anthropic, OpenAI, etc.).
Replaces PII with deterministic placeholder tokens so the model can still reason
about distinct entities without exposing raw personal data outside Brazil.

All redaction is logged via `usbea.ai.suggestion.lgpd_redacted` so DSAR
responses can show "no PII was sent" or "the following placeholders were used".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from re import Pattern

# CPF: 11 digits, formatted XXX.XXX.XXX-XX or plain.
# Use word boundaries to avoid matching inside longer numbers (e.g., a phone).
_CPF_RE: Pattern[str] = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

# CNPJ: 14 digits, formatted XX.XXX.XXX/XXXX-XX or plain.
_CNPJ_RE: Pattern[str] = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")

# Brazilian phone (mobile or landline) — flexible formats with +55 country code optional,
# area code 2 digits, mobile prefix 9, then 8 digits. Allow common separators.
# We deliberately keep this conservative to limit false positives.
_PHONE_BR_RE: Pattern[str] = re.compile(
    r"(?:\+?55\s?)?"                # optional country code
    r"(?:\(?\d{2}\)?[\s.-]?)"       # area code
    r"9?\d{4}[\s.-]?\d{4}\b",        # 8 or 9-digit subscriber number
)

# CEP: 8 digits, formatted XXXXX-XXX or plain.
_CEP_RE: Pattern[str] = re.compile(r"\b\d{5}-?\d{3}\b")

# Email — standard. We strip but keep the domain hash for context.
_EMAIL_RE: Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)

# Brazilian bank account hint: "agência ... conta ..." — heuristic, conservative.
_BANK_ACCT_RE: Pattern[str] = re.compile(
    r"ag(?:ê|e)ncia\s*[:#]?\s*\d{3,5}[\s.-]*(?:conta|c/c|cc)\s*[:#]?\s*[\d\-x]{5,}",
    re.IGNORECASE,
)

# PIX random key (UUID v4 format)
_PIX_UUID_RE: Pattern[str] = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def _cpf_is_valid(cpf: str) -> bool:
    """Validate a CPF using the Receita Federal check-digit algorithm.

    Reduces false positives when matching CPFs in free text — random 11-digit
    sequences will fail check-digit validation and be left alone.
    """
    digits = [c for c in cpf if c.isdigit()]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    nums = [int(d) for d in digits]
    for i in range(9, 11):
        weight = i + 1
        s = sum(nums[j] * (weight - j) for j in range(i))
        expected = (s * 10) % 11 % 10
        if nums[i] != expected:
            return False
    return True


def _cnpj_is_valid(cnpj: str) -> bool:
    """Validate a CNPJ using the Receita Federal check-digit algorithm."""
    digits = [c for c in cnpj if c.isdigit()]
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    nums = [int(d) for d in digits]
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s1 = sum(nums[i] * weights1[i] for i in range(12))
    d1 = 0 if (s1 % 11) < 2 else 11 - (s1 % 11)
    if nums[12] != d1:
        return False
    s2 = sum(nums[i] * weights2[i] for i in range(13))
    d2 = 0 if (s2 % 11) < 2 else 11 - (s2 % 11)
    return nums[13] == d2


@dataclass
class RedactionResult:
    """Outcome of a redactor pass over text.

    Attributes:
        text: redacted text (PII replaced with placeholder tokens)
        tokens: mapping placeholder_token -> count (never stores original PII)
        matched: True if any redaction occurred
        types_matched: set of PII type names that matched
    """

    text: str
    tokens: dict[str, int] = field(default_factory=dict)
    matched: bool = False
    types_matched: set[str] = field(default_factory=set)


class LGPDRedactor:
    """Brazilian PII redactor.

    Replaces detected PII with deterministic placeholder tokens of the form
    `<TYPE_N>` where N is the 1-based sequence number within the input string.
    Tokens are stable for repeated occurrences (same value → same token), so
    the model can reason about distinct entities.

    Usage:

        redactor = LGPDRedactor()
        result = redactor.scrub("Email me at jorge@example.com or (11) 99999-1234")
        # result.text == "Email me at <EMAIL_1> or <PHONE_1>"
        # result.matched is True
        # result.types_matched == {"EMAIL", "PHONE"}

    Validation: CPF and CNPJ matches are check-digit-validated before redaction
    to reduce false positives on random number sequences.
    """

    # (type_name, compiled_regex, validator | None) — order matters: longer
    # patterns first to avoid CNPJ being partially consumed as CPF.
    _PATTERNS: list[tuple[str, Pattern[str], callable | None]] = [
        ("CNPJ", _CNPJ_RE, _cnpj_is_valid),
        ("CPF", _CPF_RE, _cpf_is_valid),
        ("PIX_UUID", _PIX_UUID_RE, None),
        ("BANK_ACCT", _BANK_ACCT_RE, None),
        ("EMAIL", _EMAIL_RE, None),
        ("PHONE", _PHONE_BR_RE, None),
        ("CEP", _CEP_RE, None),
    ]

    def scrub(self, text: str | None) -> RedactionResult:
        """Replace PII in *text* with placeholder tokens.

        Returns RedactionResult. Safe to call with None (returns empty result).
        """
        if not text:
            return RedactionResult(text=text or "")

        result_text = text
        tokens: dict[str, int] = {}
        types_matched: set[str] = set()

        for type_name, regex, validator in self._PATTERNS:
            seen: dict[str, str] = {}
            counter = 0

            def _replace(match: re.Match[str]) -> str:
                nonlocal counter
                raw = match.group(0)
                if validator is not None and not validator(raw):
                    return raw
                if raw in seen:
                    return seen[raw]
                counter += 1
                placeholder = f"<{type_name}_{counter}>"
                seen[raw] = placeholder
                return placeholder

            new_text = regex.sub(_replace, result_text)
            if new_text != result_text:
                types_matched.add(type_name)
                tokens[type_name] = counter
                result_text = new_text

        return RedactionResult(
            text=result_text,
            tokens=tokens,
            matched=bool(types_matched),
            types_matched=types_matched,
        )

    def scrub_many(self, texts: list[str | None]) -> list[RedactionResult]:
        """Convenience: redact multiple strings independently."""
        return [self.scrub(t) for t in texts]
