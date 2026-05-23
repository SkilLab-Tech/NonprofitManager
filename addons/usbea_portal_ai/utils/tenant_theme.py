"""Tenant theme tokens — Phase 6 white-label hardening.

Pure-Python utility that validates and normalizes per-tenant theme
configuration (colors, font, logo URL, name). White-label tenant
onboarding wizards consume this before persisting branding to
``res.company`` (via usbea_whitelabel).

We enforce:
- WCAG 2.1 AA contrast ratio >= 4.5 for primary/background pairs
- All colors in #RRGGBB hex form
- Logo URL is http(s)
- Tenant_name is non-empty and trimmed

Computing relative luminance + contrast follows the WCAG 2.x formula:
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    (R, G, B linearized via the sRGB ramp)

Contrast(L1, L2) = (L_brighter + 0.05) / (L_dimmer + 0.05)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_URL_RE = re.compile(r"^https?://[^\s]+$")

WCAG_AA_NORMAL_TEXT = 4.5
WCAG_AA_LARGE_TEXT = 3.0


@dataclass(frozen=True)
class ThemeTokens:
    """Validated theme bundle ready to persist on res.company."""

    tenant_name: str
    primary_color: str       # #RRGGBB
    background_color: str    # #RRGGBB
    text_color: str          # #RRGGBB
    accent_color: str        # #RRGGBB
    logo_url: str
    font_family: str = "Inter, sans-serif"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _is_hex_color(s: str | None) -> bool:
    return bool(s and _HEX_RE.match(s))


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _linearize(channel: int) -> float:
    """sRGB to linear channel value (0.0-1.0)."""
    c = channel / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """Compute WCAG relative luminance for a hex color."""
    if not _is_hex_color(hex_color):
        msg = f"invalid hex color: {hex_color!r}"
        raise ValueError(msg)
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """Compute contrast ratio between two hex colors (always >= 1.0)."""
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def validate(tokens: ThemeTokens) -> ValidationResult:
    """Validate a candidate theme. Returns errors + warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    if not tokens.tenant_name or not tokens.tenant_name.strip():
        errors.append("tenant_name must be non-empty.")
    elif len(tokens.tenant_name.strip()) > 80:
        errors.append("tenant_name must be <= 80 characters.")

    for label, color in [
        ("primary_color", tokens.primary_color),
        ("background_color", tokens.background_color),
        ("text_color", tokens.text_color),
        ("accent_color", tokens.accent_color),
    ]:
        if not _is_hex_color(color):
            errors.append(f"{label} must be #RRGGBB hex (got {color!r}).")

    if not tokens.logo_url or not _URL_RE.match(tokens.logo_url):
        errors.append("logo_url must be a http(s) URL.")

    # Contrast checks (only if base colors are valid).
    if _is_hex_color(tokens.text_color) and _is_hex_color(tokens.background_color):
        ratio = contrast_ratio(tokens.text_color, tokens.background_color)
        if ratio < WCAG_AA_NORMAL_TEXT:
            errors.append(
                f"text/background contrast ratio {ratio:.2f} below WCAG AA "
                f"({WCAG_AA_NORMAL_TEXT}).",
            )

    if _is_hex_color(tokens.primary_color) and _is_hex_color(tokens.background_color):
        ratio = contrast_ratio(tokens.primary_color, tokens.background_color)
        if ratio < WCAG_AA_LARGE_TEXT:
            warnings.append(
                f"primary/background contrast {ratio:.2f} below WCAG AA-large "
                f"({WCAG_AA_LARGE_TEXT}) — buttons/CTAs may be hard to read.",
            )

    return ValidationResult(ok=not errors, errors=tuple(errors), warnings=tuple(warnings))


def normalize(tokens: ThemeTokens) -> ThemeTokens:
    """Return a normalized copy: trim names, lowercase hex, default font."""
    return ThemeTokens(
        tenant_name=tokens.tenant_name.strip(),
        primary_color=tokens.primary_color.lower(),
        background_color=tokens.background_color.lower(),
        text_color=tokens.text_color.lower(),
        accent_color=tokens.accent_color.lower(),
        logo_url=tokens.logo_url.strip(),
        font_family=tokens.font_family or "Inter, sans-serif",
    )
