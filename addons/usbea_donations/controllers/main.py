"""Webhook controllers for Doare and Mercado Pago."""

from __future__ import annotations

import json
import logging

from odoo import http
from odoo.http import request

from ..utils.webhook_signature import verify_doare, verify_mercado_pago

_logger = logging.getLogger(__name__)


class UsbeaDonationsWebhook(http.Controller):

    @http.route(
        "/usbea_donations/webhook/doare",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def doare_webhook(self, **kwargs):
        raw = request.httprequest.get_data() or b""
        signature = request.httprequest.headers.get("X-Doare-Signature", "")
        secret = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("usbea_donations.doare_webhook_secret", default="")
        )
        if not verify_doare(secret, raw, signature):
            _logger.warning("Doare webhook signature verification failed")
            return request.make_response(
                json.dumps({"ok": False, "error": "invalid signature"}),
                headers=[("Content-Type", "application/json")],
                status=401,
            )
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            return request.make_response(
                json.dumps({"ok": False, "error": "invalid json"}),
                headers=[("Content-Type", "application/json")],
                status=400,
            )
        self._process_doare(body)
        return request.make_response(
            json.dumps({"ok": True}),
            headers=[("Content-Type", "application/json")],
            status=200,
        )

    @http.route(
        "/usbea_donations/webhook/mercado_pago",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def mp_webhook(self, **kwargs):
        raw = request.httprequest.get_data() or b""
        signature = request.httprequest.headers.get("X-Signature", "")
        request_id = request.httprequest.headers.get("X-Request-Id", "")
        secret = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("usbea_donations.mp_webhook_secret", default="")
        )
        if not verify_mercado_pago(secret, raw, signature, request_id):
            _logger.warning("Mercado Pago webhook signature verification failed")
            return request.make_response(
                json.dumps({"ok": False, "error": "invalid signature"}),
                headers=[("Content-Type", "application/json")],
                status=401,
            )
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            return request.make_response(
                json.dumps({"ok": False, "error": "invalid json"}),
                headers=[("Content-Type", "application/json")],
                status=400,
            )
        self._process_mp(body)
        return request.make_response(
            json.dumps({"ok": True}),
            headers=[("Content-Type", "application/json")],
            status=200,
        )

    # ---- Processing helpers ----

    @staticmethod
    def _process_doare(body: dict) -> None:
        """Process a verified Doare webhook payload (idempotent)."""
        if body.get("event_type") != "donation.confirmed":
            return
        Donation = request.env["usbea.donation"].sudo()
        partner = request.env["res.partner"].sudo().search(
            [("vat", "=", body.get("donor_cpf"))], limit=1,
        )
        if not partner:
            _logger.warning(
                "Doare webhook: no partner found for donor CPF %s — skipping",
                body.get("donor_cpf"),
            )
            return
        Donation.upsert_from_webhook(
            rail="doare",
            external_ref=body.get("donation_id"),
            donor_partner=partner,
            amount=float(body.get("amount_brl", 0)),
            donation_date=body.get("donation_date"),
            payment_method="pix_recurring" if body.get("recurring") else "pix_one_off",
            state="confirmed",
        )

    @staticmethod
    def _process_mp(body: dict) -> None:
        """Process a verified Mercado Pago webhook payload (idempotent)."""
        if body.get("type") != "payment":
            return
        payment_data = body.get("data") or {}
        Donation = request.env["usbea.donation"].sudo()
        partner = request.env["res.partner"].sudo().search(
            [("email", "=", payment_data.get("payer_email"))], limit=1,
        )
        if not partner:
            _logger.warning(
                "MP webhook: no partner found for payer %s — skipping",
                payment_data.get("payer_email"),
            )
            return
        Donation.upsert_from_webhook(
            rail="mercado_pago",
            external_ref=str(payment_data.get("id")),
            donor_partner=partner,
            amount=float(payment_data.get("amount", 0)),
            donation_date=payment_data.get("date_approved"),
            payment_method="cc_recurring" if payment_data.get("preapproval_id") else "cc_one_off",
            state="confirmed",
        )
