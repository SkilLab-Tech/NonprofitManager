"""Validate that a receipt is IRPF-deductible per Lei 9.249/95 art. 13.

For a donor to deduct, the issuing organization must hold both OSCIP
qualification (Lei 9.790/99) AND Utilidade Publica Federal (UPF) status.
The receipt must carry: organization CNPJ, donor CPF or CNPJ (validated),
donation amount, donation date, and a reference to the OSCIP qualifying
article.

This validator returns a list of human-readable error strings — empty
list means the receipt is issuable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .cpf_formatter import is_valid_cnpj, is_valid_cpf


@dataclass(frozen=True)
class ReceiptCandidate:
    """Bundle of fields needed to issue an IRPF-compliant receipt."""

    org_cnpj: str
    org_name: str
    donor_doc: str            # CPF or CNPJ
    donor_name: str
    amount_brl: float
    donation_date: date
    oscip_active: bool
    upf_active: bool
    oscip_article_ref: str    # e.g. "Lei 9.790/99 Art. 3, IV — Educacao"


def validate(candidate: ReceiptCandidate) -> list[str]:
    """Return a list of validation errors. Empty list means issuable."""
    errors: list[str] = []

    if not candidate.org_cnpj or not is_valid_cnpj(candidate.org_cnpj):
        errors.append("Organization CNPJ is missing or fails Receita check.")

    if not candidate.org_name:
        errors.append("Organization name is required on the receipt.")

    if not candidate.donor_doc:
        errors.append("Donor document (CPF or CNPJ) is required.")
    elif not (is_valid_cpf(candidate.donor_doc) or is_valid_cnpj(candidate.donor_doc)):
        errors.append("Donor document fails CPF/CNPJ check-digit validation.")

    if not candidate.donor_name:
        errors.append("Donor name is required on the receipt.")

    if candidate.amount_brl is None or candidate.amount_brl <= 0:
        errors.append("Donation amount must be a positive BRL value.")

    if candidate.donation_date is None:
        errors.append("Donation date is required.")
    elif candidate.donation_date > date.today():
        errors.append("Donation date cannot be in the future.")

    if not candidate.oscip_active:
        errors.append(
            "OSCIP certification is not active for the issuing company — "
            "tax-deductible receipt cannot be issued (Lei 9.249/95 art. 13).",
        )

    if not candidate.upf_active:
        errors.append(
            "Utilidade Publica Federal (UPF) status is not active — "
            "required in addition to OSCIP for IRPF deduction.",
        )

    if not candidate.oscip_article_ref:
        errors.append(
            "OSCIP qualifying article reference is missing — required on receipt.",
        )

    return errors


def is_issuable(candidate: ReceiptCandidate) -> bool:
    """Convenience: True iff validate() returns empty."""
    return not validate(candidate)
