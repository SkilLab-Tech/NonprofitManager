"""Unit tests for tenant theme validation."""

from __future__ import annotations

import pytest

from utils.tenant_theme import (
    ThemeTokens,
    WCAG_AA_NORMAL_TEXT,
    contrast_ratio,
    normalize,
    relative_luminance,
    validate,
)


def build(**overrides) -> ThemeTokens:
    base = {
        "tenant_name": "USBEA Brasil",
        "primary_color": "#0033A0",
        "background_color": "#FFFFFF",
        "text_color": "#1A1A1A",
        "accent_color": "#E20613",
        "logo_url": "https://example.com/logo.png",
        "font_family": "Inter, sans-serif",
    }
    base.update(overrides)
    return ThemeTokens(**base)


class TestRelativeLuminance:
    def test_white_is_1(self):
        assert pytest.approx(relative_luminance("#FFFFFF"), abs=1e-6) == 1.0

    def test_black_is_0(self):
        assert pytest.approx(relative_luminance("#000000"), abs=1e-6) == 0.0

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            relative_luminance("not a color")
        with pytest.raises(ValueError):
            relative_luminance("#GGGGGG")


class TestContrastRatio:
    def test_max_contrast_is_21(self):
        # Black-on-white = 21:1 (the maximum possible)
        assert pytest.approx(contrast_ratio("#000000", "#FFFFFF"), abs=0.01) == 21.0

    def test_same_color_is_1(self):
        # Same color = no contrast (ratio 1:1)
        assert pytest.approx(contrast_ratio("#888888", "#888888"), abs=1e-6) == 1.0

    def test_symmetric(self):
        a = contrast_ratio("#FFFFFF", "#000000")
        b = contrast_ratio("#000000", "#FFFFFF")
        assert a == pytest.approx(b)


class TestValidate:
    def test_canonical_valid(self):
        result = validate(build())
        assert result.ok
        assert not result.errors

    def test_invalid_hex_rejected(self):
        result = validate(build(primary_color="not_a_hex"))
        assert not result.ok
        assert any("primary_color" in e for e in result.errors)

    def test_short_hex_rejected(self):
        # WCAG 3-digit shorthand not accepted — we require full #RRGGBB.
        result = validate(build(primary_color="#FFF"))
        assert not result.ok

    def test_empty_tenant_name(self):
        result = validate(build(tenant_name=""))
        assert any("tenant_name" in e for e in result.errors)

    def test_whitespace_only_tenant_name(self):
        result = validate(build(tenant_name="   "))
        assert any("tenant_name" in e for e in result.errors)

    def test_long_tenant_name_rejected(self):
        result = validate(build(tenant_name="X" * 81))
        assert any("80" in e for e in result.errors)

    def test_logo_must_be_http(self):
        result = validate(build(logo_url="ftp://example.com/logo.png"))
        assert any("logo_url" in e for e in result.errors)

        result = validate(build(logo_url="/local/logo.png"))
        assert any("logo_url" in e for e in result.errors)

    def test_low_contrast_text_fails(self):
        # Light gray on white — usually fails WCAG AA.
        result = validate(build(text_color="#CCCCCC", background_color="#FFFFFF"))
        assert not result.ok
        assert any("contrast ratio" in e for e in result.errors)

    def test_warning_for_low_primary_contrast(self):
        # Slightly low primary/background contrast — warning, not error.
        result = validate(build(primary_color="#AAAAAA", background_color="#FFFFFF"))
        # Errors should NOT include primary/background (that's a warning).
        primary_errors = [e for e in result.errors if "primary/background" in e]
        assert not primary_errors
        # But warnings may include it.
        primary_warnings = [w for w in result.warnings if "primary/background" in w]
        assert primary_warnings

    def test_high_contrast_pair_passes(self):
        # Dark blue on white — contrast > 4.5:1
        result = validate(build(text_color="#0033A0", background_color="#FFFFFF"))
        assert result.ok

    def test_aggregates_multiple_errors(self):
        result = validate(build(
            tenant_name="",
            primary_color="bad",
            logo_url="ftp://x",
            text_color="#FFFFFF",  # white on white = no contrast
        ))
        assert len(result.errors) >= 4

    def test_wcag_aa_threshold_constant(self):
        # If WCAG raises the bar, this test catches the change.
        assert WCAG_AA_NORMAL_TEXT == 4.5


class TestNormalize:
    def test_trims_tenant_name(self):
        t = normalize(build(tenant_name="  USBEA  "))
        assert t.tenant_name == "USBEA"

    def test_lowercases_hex(self):
        t = normalize(build(primary_color="#0033A0"))
        assert t.primary_color == "#0033a0"

    def test_default_font(self):
        t = normalize(build(font_family=""))
        assert t.font_family == "Inter, sans-serif"

    def test_strips_logo_url(self):
        t = normalize(build(logo_url="  https://x.com/logo.png  "))
        assert t.logo_url == "https://x.com/logo.png"
