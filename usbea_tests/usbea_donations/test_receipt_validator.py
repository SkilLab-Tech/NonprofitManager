"""Unit tests for receipt_validator utility.

Validates that an IRPF-compliant receipt can or cannot be issued.
Critical for Receita Federal compliance — failure to validate would
issue invalid receipts and put the org at audit risk.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from utils.receipt_validator import ReceiptCandidate, is_issuable, validate


def make_valid(**overrides) -> ReceiptCandidate:
    """Helper: build a canonical valid candidate, overriding any fields."""
    base = {
        "org_cnpj": "11.222.333/0001-81",
        "org_name": "USBEA Brasil",
        "donor_doc": "529.982.247-25",
        "donor_name": "Jorge Silva",
        "amount_brl": 100.0,
        "donation_date": date(2026, 5, 1),
        "oscip_active": True,
        "upf_active": True,
        "oscip_article_ref": "Lei 9.790/99 Art. 3, IV",
    }
    base.update(overrides)
    return ReceiptCandidate(**base)


class TestValidate:
    def test_canonical_valid_returns_empty(self):
        assert validate(make_valid()) == []
        assert is_issuable(make_valid())

    def test_missing_org_cnpj(self):
        errors = validate(make_valid(org_cnpj=""))
        assert any("CNPJ" in e for e in errors)

    def test_invalid_org_cnpj(self):
        errors = validate(make_valid(org_cnpj="11.222.333/0001-99"))
        assert any("Receita check" in e for e in errors)

    def test_missing_org_name(self):
        errors = validate(make_valid(org_name=""))
        assert any("Organization name" in e for e in errors)

    def test_missing_donor_doc(self):
        errors = validate(make_valid(donor_doc=""))
        assert any("Donor document" in e for e in errors)

    def test_invalid_donor_doc(self):
        errors = validate(make_valid(donor_doc="12345678900"))
        assert any("check-digit" in e for e in errors)

    def test_missing_donor_name(self):
        errors = validate(make_valid(donor_name=""))
        assert any("Donor name" in e for e in errors)

    def test_zero_amount(self):
        errors = validate(make_valid(amount_brl=0.0))
        assert any("amount" in e.lower() for e in errors)

    def test_negative_amount(self):
        errors = validate(make_valid(amount_brl=-50.0))
        assert any("amount" in e.lower() for e in errors)

    def test_missing_date(self):
        errors = validate(make_valid(donation_date=None))
        assert any("date is required" in e.lower() for e in errors)

    def test_future_date(self):
        errors = validate(make_valid(donation_date=date.today() + timedelta(days=10)))
        assert any("future" in e.lower() for e in errors)

    def test_no_oscip(self):
        errors = validate(make_valid(oscip_active=False))
        assert any("OSCIP" in e for e in errors)

    def test_no_upf(self):
        errors = validate(make_valid(upf_active=False))
        assert any("UPF" in e for e in errors)

    def test_no_oscip_article_ref(self):
        errors = validate(make_valid(oscip_article_ref=""))
        assert any("qualifying article" in e.lower() for e in errors)

    def test_multiple_errors_aggregated(self):
        bad = make_valid(
            org_cnpj="", donor_doc="abc", amount_brl=-1, oscip_active=False, upf_active=False,
        )
        errors = validate(bad)
        # We get one error per failed check (at least 5).
        assert len(errors) >= 5

    @pytest.mark.parametrize("donor_doc", [
        "529.982.247-25",  # CPF formatted
        "52998224725",     # CPF stripped
        "11.222.333/0001-81",  # CNPJ formatted
        "11222333000181",  # CNPJ stripped
    ])
    def test_both_cpf_and_cnpj_accepted_as_donor(self, donor_doc):
        # Donors can be individuals OR corporate.
        errors = validate(make_valid(donor_doc=donor_doc))
        # No errors related to donor_doc
        assert not any("donor" in e.lower() and "document" in e.lower() for e in errors)
