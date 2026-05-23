"""Period x programs impact reports with AI-generated narratives."""

from __future__ import annotations

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UsbeaImpactReport(models.Model):
    _name = "usbea.impact.report"
    _description = "Impact Report"
    _order = "period_end desc, id desc"
    _rec_name = "name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    program_ids = fields.Many2many("usbea.program", string="Programs covered")
    audience = fields.Selection(
        [
            ("board", "Board of directors"),
            ("funders", "Funders"),
            ("public", "Public / website"),
            ("partners", "Partner orgs"),
            ("internal", "Internal team"),
        ],
        default="funders",
        required=True,
    )
    narrative = fields.Html(
        help="AI-generated narrative based on indicator measurements and "
        "consent-cleared story summaries. User can edit before publishing.",
    )
    ai_suggestion_id = fields.Many2one("usbea.ai.suggestion", readonly=True)
    state = fields.Selection(
        [("draft", "Draft"), ("review", "In review"), ("published", "Published")],
        default="draft",
        tracking=True,
    )
    published_at = fields.Datetime()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for rec in self:
            if rec.period_start and rec.period_end and rec.period_end < rec.period_start:
                msg = _("period_end cannot be before period_start.")
                raise UserError(msg)

    def action_generate_narrative(self):
        """Compose the indicators + stories context and call the AI."""
        self.ensure_one()
        AI = self.env["usbea.ai"]
        indicators = self._collect_indicators()
        stories = self._collect_stories_anonymized()
        suggestion = AI.suggest(
            "impact_narrative",
            context={
                "period": "%s to %s" % (self.period_start, self.period_end),
                "programs": ", ".join(self.program_ids.mapped("name")),
                "indicators_json": json.dumps(indicators, default=str, ensure_ascii=False),
                "stories": json.dumps(stories, default=str, ensure_ascii=False),
                "audience": dict(self._fields["audience"].selection).get(self.audience, ""),
            },
            source_module="usbea_impact",
            source_model="usbea.impact.report",
            source_record_id=self.id,
        )
        if suggestion.response and not suggestion.error:
            self.write(
                {"narrative": suggestion.response, "ai_suggestion_id": suggestion.id},
            )
        return suggestion

    def _collect_indicators(self) -> list[dict]:
        Indicator = self.env["usbea.impact.indicator"].sudo()
        return Indicator.search_read(
            [("program_id", "in", self.program_ids.ids)],
            ["name", "unit", "target_value", "current_value", "progress_pct", "status"],
        )

    def _collect_stories_anonymized(self) -> list[dict]:
        """Stories WITHOUT real names by default; include name only if consented."""
        Story = self.env["usbea.impact.story"].sudo()
        results = []
        stories = Story.search([("program_id", "in", self.program_ids.ids)])
        for i, story in enumerate(stories, start=1):
            entry = {
                "token": f"BENEF_{i}",
                "title": story.title,
                "period": story.period,
                "narrative_preview": (story.narrative or "")[:500],
            }
            if story.identified_with_consent and story.beneficiary_partner_id:
                entry["beneficiary_name"] = story.beneficiary_partner_id.name
            results.append(entry)
        return results

    def action_publish(self):
        for rec in self:
            if rec.state == "published":
                continue
            rec.write({"state": "published", "published_at": fields.Datetime.now()})
