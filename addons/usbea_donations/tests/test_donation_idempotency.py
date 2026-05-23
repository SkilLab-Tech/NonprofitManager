"""Integration tests for donation webhook idempotency + engagement-event wiring."""

from __future__ import annotations

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "usbea_donations")
class TestDonationIdempotency(TransactionCase):

    def setUp(self):
        super().setUp()
        Partner = self.env["res.partner"]
        self.Consent = self.env["usbea.lgpd.consent"]
        self.donor = Partner.create({"name": "Donor A", "vat": "529.982.247-25"})
        self.Consent.create({
            "partner_id": self.donor.id,
            "scope": "newsletter",
            "lawful_basis": "consent",
        })
        self.donor.usbea_archetype = "donor"
        self.Donation = self.env["usbea.donation"]

    def test_upsert_creates_new_donation(self):
        rec = self.Donation.upsert_from_webhook(
            rail="doare",
            external_ref="ext-1",
            donor_partner=self.donor,
            amount=100.0,
            donation_date=fields.Date.context_today(self.Donation),
            payment_method="pix_one_off",
            state="confirmed",
        )
        self.assertEqual(rec.rail, "doare")
        self.assertEqual(rec.external_ref, "ext-1")
        self.assertEqual(rec.state, "confirmed")

    def test_upsert_is_idempotent(self):
        kwargs = {
            "rail": "doare",
            "external_ref": "ext-dup",
            "donor_partner": self.donor,
            "amount": 100.0,
            "donation_date": fields.Date.context_today(self.Donation),
            "payment_method": "pix_one_off",
            "state": "confirmed",
        }
        a = self.Donation.upsert_from_webhook(**kwargs)
        b = self.Donation.upsert_from_webhook(**kwargs)
        self.assertEqual(a.id, b.id, "Webhook re-delivery must not create a duplicate")

    def test_unique_constraint_per_rail_external_ref(self):
        self.Donation.create({
            "donor_partner_id": self.donor.id,
            "amount": 50.0,
            "donation_date": fields.Date.context_today(self.Donation),
            "payment_method": "pix_one_off",
            "rail": "doare",
            "external_ref": "ext-collision",
        })
        with self.assertRaises(Exception):  # noqa: B017 — postgres unique violation
            self.Donation.create({
                "donor_partner_id": self.donor.id,
                "amount": 75.0,
                "donation_date": fields.Date.context_today(self.Donation),
                "payment_method": "pix_one_off",
                "rail": "doare",
                "external_ref": "ext-collision",
            })

    def test_confirm_posts_engagement_event(self):
        donation = self.Donation.create({
            "donor_partner_id": self.donor.id,
            "amount": 100.0,
            "donation_date": fields.Date.context_today(self.Donation),
            "payment_method": "pix_one_off",
            "rail": "manual",
            "state": "pending",
        })
        events_before = self.env["usbea.engagement.event"].search_count([
            ("partner_id", "=", self.donor.id),
        ])
        donation.action_confirm()
        events_after = self.env["usbea.engagement.event"].search_count([
            ("partner_id", "=", self.donor.id),
        ])
        self.assertEqual(events_after, events_before + 1)

    def test_negative_amount_blocked(self):
        with self.assertRaises(ValidationError):
            self.Donation.create({
                "donor_partner_id": self.donor.id,
                "amount": -10.0,
                "donation_date": fields.Date.context_today(self.Donation),
                "payment_method": "pix_one_off",
                "rail": "manual",
            })

    def test_refund_only_from_confirmed(self):
        donation = self.Donation.create({
            "donor_partner_id": self.donor.id,
            "amount": 100.0,
            "donation_date": fields.Date.context_today(self.Donation),
            "payment_method": "pix_one_off",
            "rail": "manual",
            "state": "pending",
        })
        with self.assertRaises(UserError):
            donation.action_refund()
        donation.action_confirm()
        donation.action_refund()
        self.assertEqual(donation.state, "refunded")

    def test_receipt_requires_confirmed(self):
        donation = self.Donation.create({
            "donor_partner_id": self.donor.id,
            "amount": 100.0,
            "donation_date": fields.Date.context_today(self.Donation),
            "payment_method": "pix_one_off",
            "rail": "manual",
            "state": "pending",
        })
        with self.assertRaises(UserError):
            donation.action_issue_receipt()

    def test_receipt_requires_oscip_active(self):
        donation = self.Donation.create({
            "donor_partner_id": self.donor.id,
            "amount": 100.0,
            "donation_date": fields.Date.context_today(self.Donation),
            "payment_method": "pix_one_off",
            "rail": "manual",
            "state": "pending",
        })
        donation.action_confirm()
        # No OSCIP status configured — receipt issuance must fail with informative error.
        with self.assertRaises(UserError) as ctx:
            donation.action_issue_receipt()
        self.assertIn("OSCIP", str(ctx.exception))
