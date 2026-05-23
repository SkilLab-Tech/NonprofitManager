"""Doare API client — PIX Automatico recurring donations.

This is a thin wrapper. We expose a tiny surface that matches what
``usbea.donation.recurring_plan`` needs:

- create_subscription(donor_cpf, amount, frequency, callback_url) -> external_id
- cancel_subscription(external_id) -> bool
- get_subscription(external_id) -> dict

The actual HTTP client is built lazily so unit tests can inject a fake
session. No keys are baked in — they live in ``ir.config_parameter``:
- ``usbea_donations.doare_api_base`` (default https://doare.org/api/v1)
- ``usbea_donations.doare_api_key``
- ``usbea_donations.doare_webhook_secret``
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DoareConfig:
    api_base: str
    api_key: str
    webhook_secret: str


class DoareError(Exception):
    """Base error raised by the Doare client."""


class DoareClient:
    """Minimal Doare API client.

    Constructed by the recurring-plan model with a config snapshot. Real
    HTTP transport is delegated to a session-like object so tests pass
    a stub.
    """

    def __init__(self, config: DoareConfig, session: Any | None = None):
        if not config.api_key:
            msg = "Doare API key is required"
            raise DoareError(msg)
        self._config = config
        self._session = session  # if None, late-init via _ensure_session

    def _ensure_session(self):
        if self._session is None:
            import requests  # noqa: PLC0415 — soft dep

            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Accept": "application/json",
                    "User-Agent": "USBEA-NonprofitOS/1.0",
                },
            )
        return self._session

    def create_subscription(
        self,
        *,
        donor_cpf: str,
        amount_brl: float,
        frequency: str,
        callback_url: str,
        external_ref: str | None = None,
    ) -> dict:
        """POST /subscriptions and return the parsed JSON response."""
        if amount_brl <= 0:
            msg = "amount_brl must be > 0"
            raise DoareError(msg)
        if frequency not in ("monthly", "quarterly", "annual"):
            msg = f"unsupported frequency: {frequency}"
            raise DoareError(msg)
        payload = {
            "donor_cpf": donor_cpf,
            "amount_brl": amount_brl,
            "frequency": frequency,
            "callback_url": callback_url,
            "external_ref": external_ref or "",
        }
        return self._post("/subscriptions", payload)

    def cancel_subscription(self, external_id: str) -> bool:
        """DELETE /subscriptions/{id}. Returns True if accepted."""
        if not external_id:
            return False
        url = f"/subscriptions/{external_id}"
        try:
            self._delete(url)
        except DoareError as exc:
            _logger.warning("Doare cancel failed for %s: %s", external_id, exc)
            return False
        return True

    def get_subscription(self, external_id: str) -> dict:
        return self._get(f"/subscriptions/{external_id}")

    # ---- HTTP helpers ----

    def _full_url(self, path: str) -> str:
        return f"{self._config.api_base.rstrip('/')}{path}"

    def _post(self, path: str, payload: dict) -> dict:
        session = self._ensure_session()
        resp = session.post(self._full_url(path), json=payload, timeout=20)
        return self._handle(resp)

    def _delete(self, path: str) -> dict:
        session = self._ensure_session()
        resp = session.delete(self._full_url(path), timeout=20)
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
            msg = f"Doare API returned {status}: {body[:200]}"
            raise DoareError(msg)
        try:
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            msg = f"Doare response was not JSON: {exc}"
            raise DoareError(msg) from exc
