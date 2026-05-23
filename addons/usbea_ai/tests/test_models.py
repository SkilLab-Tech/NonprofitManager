"""Odoo integration tests for usbea_ai models.

Run via ``odoo-bin -i usbea_ai --test-enable --stop-after-init -d <db>``.
Covers prompt template rendering, suggestion audit log creation paths
(including error / budget paths), and the AbstractModel public surface.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "usbea_ai")
class TestUsbeaAIPromptTemplate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Template = self.env["usbea.ai.prompt_template"]

    def test_render_substitutes_placeholders(self):
        tmpl = self.Template.create({
            "name": "Test",
            "technical_key": "test_render_substitutes_placeholders",
            "system_prompt": "Hello {{who}}",
            "user_prompt_template": "Talk about {{topic}}",
            "max_tokens": 256,
        })
        rendered = tmpl.render({"who": "world", "topic": "tasks"})
        self.assertEqual(rendered["system"], "Hello world")
        self.assertEqual(rendered["user"], "Talk about tasks")

    def test_render_missing_variable_raises(self):
        tmpl = self.Template.create({
            "name": "Test",
            "technical_key": "test_render_missing_variable_raises",
            "system_prompt": "system",
            "user_prompt_template": "{{missing_var}}",
        })
        with self.assertRaises(ValidationError):
            tmpl.render({})

    def test_technical_key_must_be_snake_case(self):
        with self.assertRaises(ValidationError):
            self.Template.create({
                "name": "Test",
                "technical_key": "BAD-Key",
                "system_prompt": "s",
                "user_prompt_template": "u",
            })

    def test_temperature_bounds_enforced(self):
        with self.assertRaises(ValidationError):
            self.Template.create({
                "name": "Test",
                "technical_key": "test_temp",
                "system_prompt": "s",
                "user_prompt_template": "u",
                "temperature": 5.0,
            })

    def test_max_tokens_bounds_enforced(self):
        with self.assertRaises(ValidationError):
            self.Template.create({
                "name": "Test",
                "technical_key": "test_max_tok",
                "system_prompt": "s",
                "user_prompt_template": "u",
                "max_tokens": 10,
            })

    def test_seeded_templates_exist(self):
        # docs/AI.md lists 11 seeded templates. We assert presence by technical_key.
        keys = [
            "task_priority", "task_next_action", "stale_tasks_summary",
            "donor_segmentation", "donor_next_move", "donor_thanks_draft",
            "dsar_response_draft",
            "grant_writing", "grant_fit_score", "grant_translate",
            "impact_narrative",
        ]
        for k in keys:
            with self.subTest(key=k):
                self.assertTrue(
                    self.Template.search([("technical_key", "=", k)], limit=1),
                    f"Seeded template {k} not found",
                )


@tagged("post_install", "-at_install", "usbea_ai")
class TestUsbeaAISuggestion(TransactionCase):

    def test_accept_marks_user_and_time(self):
        tmpl = self.env["usbea.ai.prompt_template"].search(
            [("technical_key", "=", "task_priority")], limit=1,
        )
        suggestion = self.env["usbea.ai.suggestion"].create({
            "template_id": tmpl.id,
            "model_used": "claude-haiku-4-5-20251001",
            "response": "ok",
        })
        suggestion.action_accept()
        self.assertTrue(suggestion.accepted)
        self.assertEqual(suggestion.accepted_by, self.env.user)
        self.assertTrue(suggestion.accepted_at)

    def test_reject_clears_accepted(self):
        tmpl = self.env["usbea.ai.prompt_template"].search(
            [("technical_key", "=", "task_priority")], limit=1,
        )
        suggestion = self.env["usbea.ai.suggestion"].create({
            "template_id": tmpl.id,
            "response": "ok",
        })
        suggestion.action_accept()
        suggestion.action_reject()
        self.assertFalse(suggestion.accepted)
        self.assertTrue(suggestion.rejected)
        self.assertFalse(suggestion.accepted_by)


@tagged("post_install", "-at_install", "usbea_ai")
class TestUsbeaAISuggestService(TransactionCase):

    def test_suggest_unknown_template_raises(self):
        with self.assertRaises(UserError):
            self.env["usbea.ai"].suggest("nonexistent_template")

    def test_suggest_without_api_key_records_error(self):
        # No API key set → router build fails → suggestion record with error.
        # Force unset.
        self.env["ir.config_parameter"].sudo().set_param(
            "usbea_ai.anthropic_api_key", "",
        )
        # We also need to invalidate any cached router.
        self.env["usbea.ai"]._invalidate_router_cache()
        result = self.env["usbea.ai"].suggest(
            "task_priority",
            context={"tasks_json": "[]", "context_notes": ""},
        )
        self.assertTrue(result.error)
        self.assertFalse(result.response)

    def test_suggest_with_mocked_router_records_success(self):
        # Mock the router builder to short-circuit Anthropic calls.
        from odoo.addons.usbea_ai.services.router import RouterResponse  # noqa: PLC0415

        mock_router = MagicMock()
        mock_router.call.return_value = RouterResponse(
            response="mocked output",
            model_used="claude-haiku-4-5-20251001",
            tokens_in=10,
            tokens_out=20,
            cache_hit=False,
            latency_ms=42,
            lgpd_redacted=False,
            redaction_types=[],
        )
        with patch.object(
            self.env["usbea.ai"].__class__, "_get_router", return_value=mock_router,
        ):
            suggestion = self.env["usbea.ai"].suggest(
                "task_priority",
                context={"tasks_json": "[]", "context_notes": ""},
            )
        self.assertEqual(suggestion.response, "mocked output")
        self.assertEqual(suggestion.tokens_in, 10)
        self.assertFalse(suggestion.error)
