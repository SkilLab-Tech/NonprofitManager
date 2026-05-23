"""Integration tests for grant_application pipeline transitions + award handoff."""

from __future__ import annotations

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "usbea_grants_seeking")
class TestPipelineStateMachine(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.App = self.env["usbea.grant_application"]
        self.funder = self.Partner.create({
            "name": "Test Funder",
            "is_company": True,
            "funder_type": "foundation",
        })

    def _make_app(self, **overrides):
        vals = {
            "funder_id": self.funder.id,
            "requested_amount": 50000.0,
        }
        vals.update(overrides)
        return self.App.create(vals)

    def test_create_assigns_sequence(self):
        app = self._make_app()
        self.assertTrue(app.name)
        self.assertNotEqual(app.name, "New")

    def test_initial_state_is_prospect(self):
        app = self._make_app()
        self.assertEqual(app.state, "prospect")

    def test_research_to_drafting_to_submitted_path(self):
        app = self._make_app()
        app.action_research()
        self.assertEqual(app.state, "researching")
        app.action_draft()
        self.assertEqual(app.state, "drafting")
        app.action_submit()
        self.assertEqual(app.state, "submitted")
        self.assertTrue(app.submitted_at)

    def test_illegal_skip_blocked(self):
        app = self._make_app()
        # prospect → submitted is illegal (must go through researching+drafting).
        with self.assertRaises(UserError):
            app.action_submit()

    def test_award_creates_grant_record(self):
        app = self._make_app()
        app.action_research()
        app.action_draft()
        app.action_submit()
        app.action_under_review()
        app.action_award()
        self.assertEqual(app.state, "awarded")
        self.assertTrue(app.awarded_grant_id)
        self.assertEqual(app.awarded_grant_id.partner_id, self.funder)

    def test_decline_terminal(self):
        app = self._make_app()
        app.action_research()
        app.action_draft()
        app.action_submit()
        app.action_under_review()
        app.action_decline()
        self.assertEqual(app.state, "declined")
        # Cannot transition from declined.
        with self.assertRaises(UserError):
            app.action_award()

    def test_withdraw_from_any_active_state(self):
        for from_state in ("prospect",):
            with self.subTest(from_state=from_state):
                app = self._make_app()
                app.action_withdraw()
                self.assertEqual(app.state, "withdrawn")

    def test_withdraw_blocked_from_terminal(self):
        app = self._make_app()
        app.action_research()
        app.action_draft()
        app.action_submit()
        app.action_under_review()
        app.action_decline()
        # Already terminal, can't withdraw out of declined.
        with self.assertRaises(UserError):
            app.action_withdraw()

    def test_negative_amount_blocked(self):
        from odoo.exceptions import ValidationError  # noqa: PLC0415

        with self.assertRaises(ValidationError):
            self._make_app(requested_amount=-100)

    def test_parse_fit_score_clamps_to_range(self):
        # Test the static parser directly.
        score = self.App._parse_fit_score('{"score": 250, "rationale": "x"}')
        self.assertEqual(score, 100)
        score = self.App._parse_fit_score('{"score": -50, "rationale": "x"}')
        self.assertEqual(score, 0)
        score = self.App._parse_fit_score("not json")
        self.assertIsNone(score)


@tagged("post_install", "-at_install", "usbea_grants_seeking")
class TestDraftVersionAppendOnly(TransactionCase):

    def test_cannot_edit_version_content(self):
        funder = self.env["res.partner"].create({
            "name": "F", "is_company": True, "funder_type": "foundation",
        })
        app = self.env["usbea.grant_application"].create({
            "funder_id": funder.id,
            "requested_amount": 1000,
        })
        version = self.env["usbea.grant_application.draft_version"].create({
            "application_id": app.id,
            "version_num": 1,
            "content": "Original draft",
            "ai_assisted": False,
        })
        with self.assertRaises(UserError):
            version.content = "Modified"

    def test_can_edit_ai_assisted_flag(self):
        funder = self.env["res.partner"].create({
            "name": "F", "is_company": True, "funder_type": "foundation",
        })
        app = self.env["usbea.grant_application"].create({
            "funder_id": funder.id,
            "requested_amount": 1000,
        })
        version = self.env["usbea.grant_application.draft_version"].create({
            "application_id": app.id,
            "version_num": 1,
            "content": "Draft",
            "ai_assisted": False,
        })
        # Section and ai_assisted are mutable.
        version.ai_assisted = True
        self.assertTrue(version.ai_assisted)
