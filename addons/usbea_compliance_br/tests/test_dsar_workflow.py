"""Integration tests for the LGPD DSAR workflow + cross-module aggregator."""

from __future__ import annotations

import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "usbea_compliance_br")
class TestDSARStateMachine(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.DSAR = self.env["usbea.lgpd.dsar"]
        self.partner = self.Partner.create({"name": "Test Subject"})

    def test_create_assigns_sequence_number(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
        })
        self.assertTrue(dsar.name)
        self.assertNotEqual(dsar.name, "New")

    def test_sla_deadline_is_15_days_after_received(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
            "received_at": fields.Date.from_string("2026-05-01"),
        })
        self.assertEqual(
            fields.Date.to_string(dsar.sla_deadline), "2026-05-16",
        )

    def test_initial_state_is_received(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
        })
        self.assertEqual(dsar.state, "received")

    def test_start_processing_only_from_received(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
        })
        dsar.action_start_processing()
        self.assertEqual(dsar.state, "processing")
        # Cannot transition again from processing.
        with self.assertRaises(UserError):
            dsar.action_start_processing()

    def test_fulfill_aggregates_data(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
        })
        dsar.action_fulfill()
        self.assertEqual(dsar.state, "fulfilled")
        self.assertTrue(dsar.fulfilled_at)
        # aggregated_data should be valid JSON.
        parsed = json.loads(dsar.aggregated_data or "{}")
        self.assertIn("partner_id", parsed)
        self.assertIn("modules", parsed)

    def test_deny_requires_reason(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
        })
        with self.assertRaises(UserError):
            dsar.action_deny()
        dsar.denied_reason = "Out of scope"
        dsar.action_deny()
        self.assertEqual(dsar.state, "denied")

    def test_sla_status_green_when_far_from_deadline(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
            "received_at": fields.Date.context_today(self.DSAR),
        })
        self.assertEqual(dsar.sla_status_indicator, "green")

    def test_sla_status_overdue_when_past(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
            "received_at": fields.Date.context_today(self.DSAR) - timedelta(days=30),
        })
        self.assertEqual(dsar.sla_status_indicator, "overdue")

    def test_fulfilled_status_overrides_overdue(self):
        dsar = self.DSAR.create({
            "partner_id": self.partner.id,
            "request_type": "access",
            "received_at": fields.Date.context_today(self.DSAR) - timedelta(days=30),
        })
        dsar.action_fulfill()
        self.assertEqual(dsar.sla_status_indicator, "fulfilled")


@tagged("post_install", "-at_install", "usbea_compliance_br")
class TestDSARAggregator(TransactionCase):

    def test_aggregator_returns_json(self):
        partner = self.env["res.partner"].create({"name": "Test Subject"})
        result = self.env["usbea.lgpd.dsar_aggregator"].aggregate(partner.id)
        parsed = json.loads(result)
        self.assertEqual(parsed["partner_id"], partner.id)
        self.assertIn("modules", parsed)
        self.assertIn("generated_at", parsed)

    def test_aggregator_requires_partner_id(self):
        with self.assertRaises(ValueError):
            self.env["usbea.lgpd.dsar_aggregator"].aggregate(0)

    def test_aggregator_includes_ai_module(self):
        partner = self.env["res.partner"].create({"name": "Test Subject"})
        result = self.env["usbea.lgpd.dsar_aggregator"].aggregate(partner.id)
        parsed = json.loads(result)
        # usbea.ai is installed (depends chain) so it MUST appear.
        self.assertIn("usbea.ai", parsed["modules"])


@tagged("post_install", "-at_install", "usbea_compliance_br")
class TestLGPDConsent(TransactionCase):

    def test_consent_state_active_by_default(self):
        partner = self.env["res.partner"].create({"name": "Test"})
        consent = self.env["usbea.lgpd.consent"].create({
            "partner_id": partner.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        self.assertEqual(consent.state, "active")

    def test_consent_revoke_changes_state(self):
        partner = self.env["res.partner"].create({"name": "Test"})
        consent = self.env["usbea.lgpd.consent"].create({
            "partner_id": partner.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        consent.action_revoke("data subject request")
        self.assertEqual(consent.state, "revoked")
        self.assertEqual(consent.revoked_reason, "data subject request")

    def test_has_active_consent_helper(self):
        partner = self.env["res.partner"].create({"name": "Test"})
        Consent = self.env["usbea.lgpd.consent"]
        self.assertFalse(Consent.has_active_consent(partner.id, "newsletter"))
        Consent.create({
            "partner_id": partner.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        self.assertTrue(Consent.has_active_consent(partner.id, "newsletter"))
