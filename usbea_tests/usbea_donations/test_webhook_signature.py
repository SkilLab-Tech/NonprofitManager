"""Unit tests for webhook_signature utility.

A signature-verification bug would let attackers forge confirmed donations
and trigger receipt issuance + accounting entries. Test thoroughly:
- happy paths (real sig passes)
- tampered body fails
- tampered signature fails
- missing inputs fail closed
- algorithm prefix ('sha256=') stripped correctly
"""

from __future__ import annotations

from utils.webhook_signature import (
    sign_for_testing,
    verify_doare,
    verify_mercado_pago,
)


SECRET = "test_secret_abc_123"
BODY = b'{"event_type":"donation.confirmed","amount_brl":150.0}'


class TestVerifyDoare:
    def test_valid_signature_passes(self):
        sig = sign_for_testing(SECRET, BODY)
        assert verify_doare(SECRET, BODY, sig)

    def test_signature_with_algorithm_prefix_passes(self):
        sig = sign_for_testing(SECRET, BODY)
        prefixed = f"sha256={sig}"
        assert verify_doare(SECRET, BODY, prefixed)

    def test_tampered_body_fails(self):
        sig = sign_for_testing(SECRET, BODY)
        tampered = BODY + b" extra"
        assert not verify_doare(SECRET, tampered, sig)

    def test_tampered_signature_fails(self):
        sig = sign_for_testing(SECRET, BODY)
        bad_sig = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        assert not verify_doare(SECRET, BODY, bad_sig)

    def test_empty_signature_fails(self):
        assert not verify_doare(SECRET, BODY, None)
        assert not verify_doare(SECRET, BODY, "")

    def test_empty_secret_fails_closed(self):
        sig = sign_for_testing(SECRET, BODY)
        assert not verify_doare("", BODY, sig)

    def test_wrong_secret_fails(self):
        sig = sign_for_testing(SECRET, BODY)
        assert not verify_doare("other_secret", BODY, sig)

    def test_case_insensitive_hex(self):
        sig = sign_for_testing(SECRET, BODY).upper()
        assert verify_doare(SECRET, BODY, sig)


class TestVerifyMercadoPago:
    REQUEST_ID = "req-abc-123"

    def test_valid_signature_passes(self):
        sig = sign_for_testing(SECRET, BODY)
        assert verify_mercado_pago(SECRET, BODY, sig, self.REQUEST_ID)

    def test_missing_request_id_fails(self):
        sig = sign_for_testing(SECRET, BODY)
        assert not verify_mercado_pago(SECRET, BODY, sig, "")
        assert not verify_mercado_pago(SECRET, BODY, sig, None)

    def test_missing_secret_fails(self):
        sig = sign_for_testing(SECRET, BODY)
        assert not verify_mercado_pago("", BODY, sig, self.REQUEST_ID)

    def test_tampered_body_fails(self):
        sig = sign_for_testing(SECRET, BODY)
        assert not verify_mercado_pago(SECRET, BODY + b"!", sig, self.REQUEST_ID)

    def test_empty_signature_fails(self):
        assert not verify_mercado_pago(SECRET, BODY, None, self.REQUEST_ID)
        assert not verify_mercado_pago(SECRET, BODY, "", self.REQUEST_ID)


class TestSignHelper:
    def test_deterministic(self):
        # Same inputs → same output.
        a = sign_for_testing(SECRET, BODY)
        b = sign_for_testing(SECRET, BODY)
        assert a == b

    def test_different_secret_different_signature(self):
        a = sign_for_testing(SECRET, BODY)
        b = sign_for_testing("different_secret", BODY)
        assert a != b

    def test_different_body_different_signature(self):
        a = sign_for_testing(SECRET, BODY)
        b = sign_for_testing(SECRET, BODY + b" diff")
        assert a != b
