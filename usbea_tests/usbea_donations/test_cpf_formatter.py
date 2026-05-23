"""Unit tests for cpf_formatter utility."""

from __future__ import annotations

import pytest

from utils.cpf_formatter import (
    classify,
    format_any,
    format_cnpj,
    format_cpf,
    is_valid_cnpj,
    is_valid_cpf,
    strip,
)


# Real-shape valid samples (check-digit valid; not real people/orgs).
VALID_CPFS = ["52998224725", "11144477735", "12345678909", "39053344705"]
VALID_CNPJS = ["11222333000181", "04252011000110", "27865757000102"]


class TestStrip:
    def test_strip_punctuation(self):
        assert strip("529.982.247-25") == "52998224725"
        assert strip("11.222.333/0001-81") == "11222333000181"

    def test_strip_none_empty(self):
        assert strip(None) == ""
        assert strip("") == ""

    def test_strip_letters_removed(self):
        assert strip("CPF: 529.982.247-25 (joao)") == "52998224725"


class TestValidators:
    @pytest.mark.parametrize("cpf", VALID_CPFS)
    def test_valid_cpfs_pass(self, cpf):
        assert is_valid_cpf(cpf)
        assert is_valid_cpf(format_cpf(cpf))  # formatted form also passes

    @pytest.mark.parametrize("bad", ["12345678900", "11111111111", "529.982.247-26", "", None, "abc"])
    def test_invalid_cpfs_rejected(self, bad):
        assert not is_valid_cpf(bad)

    @pytest.mark.parametrize("cnpj", VALID_CNPJS)
    def test_valid_cnpjs_pass(self, cnpj):
        assert is_valid_cnpj(cnpj)
        assert is_valid_cnpj(format_cnpj(cnpj))

    @pytest.mark.parametrize("bad", ["11222333000182", "00000000000000", "", None])
    def test_invalid_cnpjs_rejected(self, bad):
        assert not is_valid_cnpj(bad)


class TestFormatters:
    def test_format_cpf_punctuation(self):
        assert format_cpf("52998224725") == "529.982.247-25"
        assert format_cpf("529.982.247-25") == "529.982.247-25"

    def test_format_cpf_wrong_length(self):
        assert format_cpf("123") == ""
        assert format_cpf(None) == ""

    def test_format_cnpj_punctuation(self):
        assert format_cnpj("11222333000181") == "11.222.333/0001-81"

    def test_format_cnpj_wrong_length(self):
        assert format_cnpj("11222333") == ""


class TestClassifyAndFormatAny:
    @pytest.mark.parametrize("cpf", VALID_CPFS)
    def test_classify_cpf(self, cpf):
        assert classify(cpf) == "cpf"

    @pytest.mark.parametrize("cnpj", VALID_CNPJS)
    def test_classify_cnpj(self, cnpj):
        assert classify(cnpj) == "cnpj"

    def test_classify_invalid(self):
        assert classify("12345") == ""
        assert classify("11111111111") == ""  # 11-digit but fails check
        assert classify(None) == ""

    def test_format_any_dispatch(self):
        assert format_any(VALID_CPFS[0]) == "529.982.247-25"
        assert format_any(VALID_CNPJS[0]) == "11.222.333/0001-81"

    def test_format_any_fallback_returns_original(self):
        # An invalid doc is returned as-is so the caller can show it back to the user.
        assert format_any("invalid") == "invalid"
        assert format_any(None) == ""
