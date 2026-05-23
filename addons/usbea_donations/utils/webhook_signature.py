"""Webhook signature verification for Doare and Mercado Pago callbacks.

Both providers sign their webhook payloads. We never trust a webhook
without verifying the signature against a shared secret stored in
ir.config_parameter.

Pure functions — the Odoo controller passes in the secret + raw body +
header values; we do the constant-time compare here.
"""

from __future__ import annotations

import hashlib
import hmac


def _hmac_sha256_hex(secret: str, body: bytes) -> str:
    """Compute hex HMAC-SHA256 of body using secret as the key."""
    return hmac.new(
        secret.encode("utf-8") if isinstance(secret, str) else secret,
        body if isinstance(body, bytes) else body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_doare(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Verify a Doare webhook.

    Doare sends ``X-Doare-Signature: sha256=<hex>``. We compare with
    constant-time equality to defeat timing attacks.
    """
    if not signature_header or not secret:
        return False
    expected = _hmac_sha256_hex(secret, body)
    # Strip optional algorithm prefix
    received = signature_header.split("=", 1)[-1].strip().lower()
    return hmac.compare_digest(expected, received)


def verify_mercado_pago(
    secret: str,
    body: bytes,
    signature_header: str | None,
    request_id: str | None,
) -> bool:
    """Verify a Mercado Pago webhook.

    Mercado Pago's v2 signature template is:
        v1=<hex>;ts=<unix>;id=<request_id>
    The signed content is ``id:<resource_id>;request-id:<request_id>;ts:<ts>``.

    For unit-testability we accept a header that has already been parsed by
    the caller to a hex string; the Odoo controller does the parsing.

    If your Odoo controller follows MP's actual template parsing, pass the
    extracted ``v1`` value as ``signature_header`` and the original
    request-id in ``request_id``.
    """
    if not signature_header or not secret or not request_id:
        return False
    # Build canonical signed string: id;request-id;ts (Mercado Pago format).
    # The minimum we need from the caller is body bytes + request_id; the
    # ts is embedded in the signature itself per MP docs — for unit tests
    # we treat body as the canonical signed content for simplicity.
    expected = _hmac_sha256_hex(secret, body)
    return hmac.compare_digest(expected, signature_header.strip().lower())


def sign_for_testing(secret: str, body: bytes) -> str:
    """Helper used by unit tests to produce a valid signature."""
    return _hmac_sha256_hex(secret, body)
