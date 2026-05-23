"""Integration tests for the LGPD consent gate on res.partner.

The gate is the critical compliance feature: a partner cannot become a
donor/volunteer/grantee without an active consent record. We test the
exact behaviors the COMPLIANCE.md spec relies on.
"""

from __future__ import annotations

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "usbea_crm")
class TestLGPDConsentGate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.Consent = self.env["usbea.lgpd.consent"]

    def test_donor_without_consent_blocked(self):
        partner = self.Partner.create({"name": "Test Donor"})
        with self.assertRaises(ValidationError):
            partner.usbea_archetype = "donor"

    def test_volunteer_without_consent_blocked(self):
        partner = self.Partner.create({"name": "Test Volunteer"})
        with self.assertRaises(ValidationError):
            partner.usbea_archetype = "volunteer"

    def test_grantee_without_consent_blocked(self):
        partner = self.Partner.create({"name": "Test Grantee"})
        with self.assertRaises(ValidationError):
            partner.usbea_archetype = "grantee"

    def test_funder_archetype_does_not_require_consent(self):
        # Funder archetype is processed under contract / legitimate-interest,
        # not consent — should NOT trigger the gate.
        partner = self.Partner.create({"name": "Test Funder", "is_company": True})
        partner.usbea_archetype = "funder"
        self.assertEqual(partner.usbea_archetype, "funder")

    def test_staff_archetype_does_not_require_consent(self):
        partner = self.Partner.create({"name": "Test Staff"})
        partner.usbea_archetype = "staff"
        self.assertEqual(partner.usbea_archetype, "staff")

    def test_donor_with_consent_passes(self):
        partner = self.Partner.create({"name": "Test Donor With Consent"})
        self.Consent.create({
            "partner_id": partner.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        partner.usbea_archetype = "donor"
        self.assertEqual(partner.usbea_archetype, "donor")
        self.assertTrue(partner.has_active_lgpd_consent)

    def test_revoked_consent_blocks_archetype(self):
        partner = self.Partner.create({"name": "Test Revoked"})
        consent = self.Consent.create({
            "partner_id": partner.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        consent.action_revoke("test")
        self.assertEqual(consent.state, "revoked")
        # Active consent is now gone → archetype assignment must fail
        partner_no_archetype = self.Partner.create({"name": "Test No Archetype"})
        with self.assertRaises(ValidationError):
            partner_no_archetype.usbea_archetype = "donor"

    def test_engagement_score_zero_when_no_events(self):
        partner = self.Partner.create({"name": "Test No Events"})
        self.assertEqual(partner.engagement_score, 0)

    def test_engagement_score_increases_with_donation_event(self):
        partner = self.Partner.create({"name": "Test Engagement"})
        # Set archetype first (with consent) so events make sense.
        self.Consent.create({
            "partner_id": partner.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        partner.usbea_archetype = "donor"
        # Add a recent donation event
        self.env["usbea.engagement.event"].create({
            "partner_id": partner.id,
            "event_type": "donation",
        })
        partner.invalidate_recordset()  # refresh computed
        self.assertGreater(partner.engagement_score, 0)

    def test_dsar_adapter_exposes_partner_data(self):
        partner = self.Partner.create({"name": "Test DSAR"})
        self.Consent.create({
            "partner_id": partner.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        partner.usbea_archetype = "donor"
        data = self.Partner._get_lgpd_data_for_partner(partner.id)
        self.assertTrue(data["exists"])
        self.assertEqual(data["archetype"], "donor")
        self.assertEqual(data["engagement_events_count"], 0)
