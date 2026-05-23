"""Mercado Pago Subscriptions v2 client.

Same shape as the Doare client: thin wrapper over HTTP, session-injectable,
config from ir.config_parameter.

- ``usbea_donations.mp_api_base`` (default https://api.mercadopago.com)
- ``usbea_donations.mp_access_token``
- ``usbea_donations.mp_webhook_secret``
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MercadoPagoConfig:
    api_base: str
    access_token: str
    webhook_secret: str


class MercadoPagoError(Exception):
    pass


class MercadoPagoClient:
    """Minimal Mercado Pago Preapproval (subscriptions) client."""

    def __init__(self, config: MercadoPagoConfig, session: Any | None = None):
        if not config.access_token:
            msg = "Mercado Pago access token is required"
            raise MercadoPagoError(msg)
        self._config = config
        self._session = session

    def _ensure_session(self):
        if self._session is None:
            import requests  # noqa: PLC0415 — soft dep

            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {self._config.access_token}",
                    "Accept": "application/json",
                    "User-Agent": "USBEA-NonprofitOS/1.0",
                },
            )
        return self._session

    def create_preapproval(
        self,
        *,
        payer_email: str,
        amount_brl: float,
        frequency_months: int,
        reason: str,
        back_url: str,
    ) -> dict:
        """POST /preapproval and return the parsed JSON.

        Mercado Pago's Preapproval requires the payer to confirm on their
        site — the response carries an ``init_point`` URL we redirect the
        donor to.
        """
        if amount_brl <= 0:
            msg = "amount_brl must be > 0"
            raise MercadoPagoError(msg)
        if frequency_months not in (1, 3, 6, 12):
            msg = "frequency_months must be 1, 3, 6, or 12"
            raise MercadoPagoError(msg)
        payload = {
            "reason": reason,
            "external_reference": "",
            "payer_email": payer_email,
            "back_url": back_url,
            "auto_recurring": {
                "frequency": frequency_months,
                "frequency_type": "months",
                "transaction_amount": amount_brl,
                "currency_id": "BRL",
            },
        }
        return self._post("/preapproval", payload)

    def cancel_preapproval(self, preapproval_id: str) -> bool:
        if not preapproval_id:
            return False
        try:
            self._put(f"/preapproval/{preapproval_id}", {"status": "cancelled"})
        except MercadoPagoError as exc:
            _logger.warning("MP cancel failed for %s: %s", preapproval_id, exc)
            return False
        return True

    def get_preapproval(self, preapproval_id: str) -> dict:
        return self._get(f"/preapproval/{preapproval_id}")

    # ---- HTTP helpers ----

    def _full_url(self, path: str) -> str:
        return f"{self._config.api_base.rstrip('/')}{path}"

    def _post(self, path: str, payload: dict) -> dict:
        session = self._ensure_session()
        resp = session.post(self._full_url(path), json=payload, timeout=20)
        return self._handle(resp)

    def _put(self, path: str, payload: dict) -> dict:
        session = self._ensure_session()
        resp = session.put(self._full_url(path), json=payload, timeout=20)
        return self._handle(resp)

    def _get(self, path: str) -> dict:
        session = self._ensure_session()
        resp = session.get(self._full_url(path), timeout=20)
        return self._handle(resp)

    @staticmethod
    def _handle(resp: Any) -> dict:
        status = getattr(resp, "status_code", 0)
        if status >= 400:
            body = getattr(resp, "text", "") or ""
            msg = f"Mercado Pago API returned {status}: {body[:200]}"
            raise MercadoPagoError(msg)
        try:
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            msg = f"MP response was not JSON: {exc}"
            raise MercadoPagoError(msg) from exc
