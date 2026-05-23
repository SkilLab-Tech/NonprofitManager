"""Cross-module DSAR aggregator.

A DSAR access/portability request must return ALL data the org holds about
the subject. Each domain module exposes ``_get_lgpd_data_for_partner(partner_id)``
returning a JSON-serializable dict; this aggregator iterates the modules
registered for the current company and merges them.

Adding a new module to DSAR coverage:
1. Implement ``_get_lgpd_data_for_partner(self, partner_id) -> dict`` on
   the module's main AbstractModel (or any model — we accept any with
   that method).
2. Add the model name to ``DSAR_ADAPTERS`` below.
"""

from __future__ import annotations

import json
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


# Registry of model names exposing _get_lgpd_data_for_partner.
# Keep ordered for stable output.
DSAR_ADAPTERS = (
    "usbea.ai",                     # AI suggestions referencing this partner
    "usbea.lgpd.consent",           # consent registry
    "usbea.lgpd.dsar",              # prior DSARs from this subject
    "usbea.mrosc.partnership",      # if subject is a public-funder partner
    # future:
    # 'usbea.crm', 'usbea.donations', etc.
)


class UsbeaLGPDDSARAggregator(models.AbstractModel):
    """Service-style model exposing ``aggregate(partner_id) -> json_text``."""

    _name = "usbea.lgpd.dsar_aggregator"
    _description = "LGPD DSAR cross-module aggregator"

    @api.model
    def aggregate(self, partner_id: int) -> str:
        """Walk registered adapters and produce a single JSON payload."""
        if not partner_id:
            msg = _("partner_id is required")
            raise ValueError(msg)

        out: dict[str, object] = {
            "partner_id": partner_id,
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "modules": {},
        }

        for model_name in DSAR_ADAPTERS:
            if model_name not in self.env:
                _logger.warning("DSAR adapter %s not installed — skipping", model_name)
                continue
            target = self.env[model_name].sudo()
            adapter = getattr(target, "_get_lgpd_data_for_partner", None)
            if not callable(adapter):
                # Fallback: search for rows linked to this partner.
                out["modules"][model_name] = self._generic_partner_dump(target, partner_id)
                continue
            try:
                out["modules"][model_name] = adapter(partner_id)
            except Exception as exc:  # noqa: BLE001 — log + continue, never fail aggregator
                _logger.exception("DSAR adapter %s failed for partner %s", model_name, partner_id)
                out["modules"][model_name] = {"error": str(exc)}

        return json.dumps(out, default=str, ensure_ascii=False, indent=2)

    @staticmethod
    def _generic_partner_dump(target, partner_id: int) -> dict:
        """Best-effort fallback when a model has no explicit adapter."""
        try:
            rows = target.search_read(
                [("partner_id", "=", partner_id)],
                limit=500,
            )
        except Exception:  # noqa: BLE001
            return {"rows": []}
        return {"rows": rows, "count": len(rows)}
