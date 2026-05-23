"""CPF / CNPJ formatting + check-digit validation.

Shared by donor onboarding (receipt requires valid CPF or CNPJ) and the
DIRF wizard in usbea_compliance_br. Pure functions, no Odoo dependency.

We reuse the algorithm logic from usbea_ai.services.lgpd_redactor but
expose it through a stable formatting API distinct from the redactor's
internal helpers — different concern, different module boundary.
"""

from __future__ import annotations

import re

_DIGITS_RE = re.compile(r"\D")


def strip(doc: str | None) -> str:
    """Return the digits-only form of a CPF/CNPJ-shaped string."""
    if not doc:
        return ""
    return _DIGITS_RE.sub("", doc)


def is_valid_cpf(doc: str | None) -> bool:
    """True if doc has 11 digits and passes the Receita Federal check."""
    digits = strip(doc)
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


def is_valid_cnpj(doc: str | None) -> bool:
    """True if doc has 14 digits and passes the Receita Federal check."""
    digits = strip(doc)
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


def format_cpf(doc: str | None) -> str:
    """Return CPF formatted as ``XXX.XXX.XXX-XX``. Returns '' if invalid length."""
    digits = strip(doc)
    if len(digits) != 11:
        return ""
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def format_cnpj(doc: str | None) -> str:
    """Return CNPJ formatted as ``XX.XXX.XXX/XXXX-XX``. Returns '' if invalid length."""
    digits = strip(doc)
    if len(digits) != 14:
        return ""
    return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"


def classify(doc: str | None) -> str:
    """Return ``"cpf" | "cnpj" | ""`` based on length + validity."""
    digits = strip(doc)
    if len(digits) == 11 and is_valid_cpf(digits):
        return "cpf"
    if len(digits) == 14 and is_valid_cnpj(digits):
        return "cnpj"
    return ""


def format_any(doc: str | None) -> str:
    """Format as CPF or CNPJ based on length + validity. Falls back to original."""
    kind = classify(doc)
    if kind == "cpf":
        return format_cpf(doc)
    if kind == "cnpj":
        return format_cnpj(doc)
    return doc or ""
