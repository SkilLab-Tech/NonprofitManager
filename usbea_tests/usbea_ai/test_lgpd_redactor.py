"""Unit tests for the LGPD redactor.

These tests are critical: a redactor false-negative leaks Brazilian PII to
Anthropic — an LGPD Article 33 violation. A false-positive blocks legitimate
content but is recoverable. We bias the test suite hard against false negatives.
"""

from __future__ import annotations

import pytest

from services.lgpd_redactor import LGPDRedactor, _cnpj_is_valid, _cpf_is_valid


# A small set of real-shape valid CPFs (check-digit valid; not actual people).
# Generated via the standard CPF algorithm with arbitrary base digits.
VALID_CPFS = [
    "529.982.247-25",
    "11144477735",
    "12345678909",
    "390.533.447-05",
]

# Real-shape invalid CPFs — bad check digits OR all-same-digit edge case.
INVALID_CPFS = [
    "123.456.789-00",  # bad check digit
    "111.111.111-11",  # repeated digit (rejected by algorithm)
    "000.000.000-00",
    "98765432101",     # bad check digit
]

# Real-shape valid CNPJs.
VALID_CNPJS = [
    "11.222.333/0001-81",
    "04.252.011/0001-10",
    "27865757000102",
]

INVALID_CNPJS = [
    "11.222.333/0001-99",  # bad check digit
    "00.000.000/0000-00",
    "12345678901234",
]


class TestCPFValidator:
    @pytest.mark.parametrize("cpf", VALID_CPFS)
    def test_valid_cpfs_pass(self, cpf):
        assert _cpf_is_valid(cpf) is True

    @pytest.mark.parametrize("cpf", INVALID_CPFS)
    def test_invalid_cpfs_rejected(self, cpf):
        assert _cpf_is_valid(cpf) is False

    def test_empty_and_short_rejected(self):
        assert _cpf_is_valid("") is False
        assert _cpf_is_valid("123") is False
        assert _cpf_is_valid("12345678901234") is False  # too long


class TestCNPJValidator:
    @pytest.mark.parametrize("cnpj", VALID_CNPJS)
    def test_valid_cnpjs_pass(self, cnpj):
        assert _cnpj_is_valid(cnpj) is True

    @pytest.mark.parametrize("cnpj", INVALID_CNPJS)
    def test_invalid_cnpjs_rejected(self, cnpj):
        assert _cnpj_is_valid(cnpj) is False


class TestLGPDRedactor:
    def setup_method(self):
        self.r = LGPDRedactor()

    def test_empty_input(self):
        result = self.r.scrub("")
        assert result.text == ""
        assert result.matched is False

    def test_none_input(self):
        result = self.r.scrub(None)
        assert result.text == ""
        assert result.matched is False

    def test_text_without_pii_unchanged(self):
        text = "USBEA Brasil empowers 60,000 alumni across Brazil through educational exchange."
        result = self.r.scrub(text)
        assert result.text == text
        assert result.matched is False
        assert not result.types_matched

    @pytest.mark.parametrize("cpf", VALID_CPFS)
    def test_valid_cpf_redacted(self, cpf):
        text = f"O doador tem CPF {cpf} e contribui mensalmente."
        result = self.r.scrub(text)
        assert cpf not in result.text
        assert "<CPF_1>" in result.text
        assert "CPF" in result.types_matched
        assert result.matched is True

    @pytest.mark.parametrize("cpf", INVALID_CPFS)
    def test_invalid_cpf_not_redacted(self, cpf):
        # Invalid CPFs (bad check digits) should pass through — they're noise.
        text = f"Random number {cpf} here."
        result = self.r.scrub(text)
        # The pattern matches but validator rejects; the original digits remain.
        # We just assert no CPF placeholder appeared.
        assert "<CPF_" not in result.text
        assert "CPF" not in result.types_matched

    def test_multiple_distinct_cpfs_get_distinct_tokens(self):
        cpf_a, cpf_b = VALID_CPFS[0], VALID_CPFS[1]
        text = f"Doadores: {cpf_a} e {cpf_b}."
        result = self.r.scrub(text)
        assert "<CPF_1>" in result.text
        assert "<CPF_2>" in result.text
        assert cpf_a not in result.text
        assert cpf_b not in result.text

    def test_same_cpf_twice_gets_same_token(self):
        cpf = VALID_CPFS[0]
        text = f"O CPF {cpf} aparece de novo: {cpf}."
        result = self.r.scrub(text)
        # Deterministic: same input → same placeholder
        assert result.text.count("<CPF_1>") == 2
        assert "<CPF_2>" not in result.text

    @pytest.mark.parametrize("cnpj", VALID_CNPJS)
    def test_valid_cnpj_redacted(self, cnpj):
        text = f"A fundação tem CNPJ {cnpj}, com sede em SP."
        result = self.r.scrub(text)
        assert cnpj not in result.text
        assert "<CNPJ_1>" in result.text

    def test_cnpj_matched_before_cpf(self):
        # If a CNPJ string is also matched by CPF regex, CNPJ must win.
        cnpj = "11.222.333/0001-81"
        result = self.r.scrub(f"CNPJ: {cnpj}")
        assert "<CNPJ_1>" in result.text
        assert "<CPF_" not in result.text

    def test_email_redacted(self):
        text = "Contact me at jorge.silva@example.com.br for details."
        result = self.r.scrub(text)
        assert "jorge.silva@example.com.br" not in result.text
        assert "<EMAIL_1>" in result.text
        assert "EMAIL" in result.types_matched

    def test_phone_br_redacted(self):
        # Mobile with area code: (11) 99876-5432
        text = "Ligue para (11) 99876-5432 entre 9h e 18h."
        result = self.r.scrub(text)
        assert "99876-5432" not in result.text
        assert "PHONE" in result.types_matched

    def test_phone_br_with_country_code(self):
        text = "Contato internacional: +55 11 99876-5432."
        result = self.r.scrub(text)
        assert "<PHONE_1>" in result.text

    def test_cep_redacted(self):
        text = "Sede em São Paulo, CEP 01310-100, próximo à Av. Paulista."
        result = self.r.scrub(text)
        assert "01310-100" not in result.text
        assert "<CEP_1>" in result.text

    def test_pix_uuid_redacted(self):
        # PIX random key (UUID v4)
        text = "Chave PIX: 550e8400-e29b-41d4-a716-446655440000"
        result = self.r.scrub(text)
        assert "550e8400" not in result.text
        assert "<PIX_UUID_1>" in result.text

    def test_bank_account_redacted(self):
        text = "Conta bancária — Agência 1234 Conta 56789-0"
        result = self.r.scrub(text)
        assert "<BANK_ACCT_1>" in result.text
        assert "BANK_ACCT" in result.types_matched

    def test_mixed_pii_all_redacted(self):
        cpf = VALID_CPFS[0]
        cnpj = VALID_CNPJS[0]
        text = (
            f"Beneficiário: João Silva, CPF {cpf}, email joao@ong.org, "
            f"telefone (11) 99876-5432. Empresa parceira: CNPJ {cnpj}, "
            f"sede em CEP 04567-890."
        )
        result = self.r.scrub(text)
        assert result.matched is True
        # All five PII types should be redacted
        expected_types = {"CPF", "CNPJ", "EMAIL", "PHONE", "CEP"}
        assert expected_types.issubset(result.types_matched)
        # Raw PII must not appear in output
        for raw in (cpf, cnpj, "joao@ong.org", "04567-890"):
            assert raw not in result.text

    def test_unicode_names_preserved(self):
        # Names with diacritics must pass through (no PII).
        text = "João, Maria, Conceição e André participam do programa."
        result = self.r.scrub(text)
        assert "João" in result.text
        assert "Conceição" in result.text
        # No false-positive matches expected for plain names.
        assert not result.matched

    def test_scrub_many(self):
        texts = ["No PII here.", "CPF: 529.982.247-25"]
        results = self.r.scrub_many(texts)
        assert len(results) == 2
        assert results[0].matched is False
        assert results[1].matched is True

    def test_no_false_positive_on_arbitrary_long_numbers(self):
        # 11 random digits that fail CPF check should NOT be redacted.
        text = "Order ID: 99999999999"
        result = self.r.scrub(text)
        # CPF validation rejects all-same digits, so this should remain.
        assert "<CPF_" not in result.text
