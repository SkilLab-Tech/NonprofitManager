# USBEA Nonprofit OS — Product Requirements Document

**Status:** v1.0 — supersedes "USBEA NonprofitManager (financial app)" framing
**Owner:** Ivan Prado / Diretoria USBEA Brasil
**Last updated:** 2026-05-23

---

## 1. Positioning

**Product:** USBEA Nonprofit OS
**Repo:** `SkilLab-Tech/NonprofitManager`
**Deployed at:** `https://manage.usbeabrasil.org`
**Built on:** Odoo 19.0 (LGPL-3 fork) + custom `usbea_*` modules + selective OCA module extensions

**One-liner.** A Brazilian-first back-office Nonprofit OS for alumni-driven NGOs — CRM, project & task management, grant seeking pipeline, programs/volunteers/impact, donations & compliance — with AI baked into every pillar.

**Audience.** USBEA Brasil Diretoria + staff. **Not** the alumni-facing platform (that's `usbea-digital`, separate repo). The Nonprofit OS holds Diretoria contacts, donors, funders, grantees, and all governance/finance data; alumni records remain in Discourse and sync only in the direction Diretoria→Odoo for staff users.

**Differentiation.**
- Brazilian regulatory layer no US vendor offers: LGPD, MROSC/Lei 13.019, OSCIP, Receita Federal, PIX/Doare donation rail
- AI cross-cutting across all pillars (grant copilot, donor segmentation, smart task routing, impact narrative generation)
- White-label-ready from day one (`usbea_whitelabel` module already scaffolds multi-tenant branding)
- Built on open-source Odoo + OCA — no vendor lock-in, no per-seat economics

---

## 2. Personas

| Persona | Daily job | Critical workflows |
|---------|-----------|---------------------|
| **President / ED (Diretoria)** | Strategic oversight, fundraising, board reporting | Board dashboard, grant portfolio KPIs, donor cultivation, impact narratives |
| **Operations Manager (Staff)** | Day-to-day program execution | Project/task management, program tracking, volunteer coordination |
| **Treasurer / Finance Lead** | Money in/out, compliance, audits | Expense allocation, donation receipts, OSCIP reporting, Receita Federal filings |
| **Grant Writer (Staff or contractor)** | Pursue funding | Grant-seeking pipeline, draft collaboration, AI grant-writing copilot |
| **Board Member (Diretoria, read-only)** | Governance oversight | Read-only board portal, compliance status, impact dashboards |

**Out of persona scope:** alumni (they live in `usbea-digital` + Discourse), general public.

---

## 3. The Five Pillars

### Pillar 1 — Project & Task Operations
Custom Kanban + Gantt + List views for staff ops with nonprofit-native task templates (program-launch, grant-report cadence, board-meeting prep, event-planning, donor-cultivation cycle, compliance-deadline tracker). Task ↔ Grant ↔ Program three-way linking. Time-tracking rolls into `usbea.grant.expense` per Pillar 5.

**AI:** smart prioritization, deadline extraction from emails, suggested next-actions, board-portal stale-task summary.

### Pillar 2 — Alumni / Donor / Funder CRM
Three contact archetypes sharing one schema (`res.partner` extended): **Donors** (individuals + corporate), **Funders** (foundations, embassies, agencies), **Diretoria/Staff/Board** (sync from Discourse per existing `INTEGRATION.md`). Moves management pipeline (Bloomerang/NPSP-style cultivation), engagement scoring, soft-credit tracking, household linking, LGPD consent state machine, Mailchimp/Sendpulse/Resend campaign integration.

**AI:** donor segmentation, churn-risk prediction, suggested outreach timing, AI-drafted personalization tokens.

### Pillar 3 — Grant Seeking Pipeline
**Distinct from existing `usbea_grants`** (which handles grant-receiving lifecycle once awarded). Pipeline kanban: `prospect → researching → drafting → submitted → under_review → awarded | declined`. Funder database (initially manual, later Instrumentl-style discovery integration). Deadline calendar with automated reminders. Draft collaboration with version history. Attachment vault on top of `OCA/dms`. Win/loss reporting. Award transitions trigger `usbea_grants` record creation (lifecycle → disbursement → reporting).

**AI:** grant-writing copilot (Claude-powered), funder-fit scoring against USBEA programs, AI draft of cover letters from program data, Portuguese↔English translation passes.

### Pillar 4 — Programs, Volunteers & Impact
Extends `usbea_programs` with volunteer management (registration, skills, availability, hours, background-check status). New `usbea_impact` module: outcome indicators, theory-of-change, narrative + quantitative outcome tracking, donor/funder reports. Program → Participant → Volunteer → Donor lifecycle stitched (the gap US suites consistently miss). Event scheduling + RSVP + check-in.

**AI:** auto-generated impact narratives from indicator data, photo/video auto-tagging for impact stories, outcome trend detection.

### Pillar 5 — Operations, Compliance & Donations
**Compliance pack** (extends `usbea_compliance`): LGPD module (consent registry, DSAR, retention, breach template), MROSC module (Lei 13.019 public-partnership tracking + transparency portal + prestação de contas), OSCIP module (annual reporting templates, utilidade pública federal tracker), Receita Federal hooks (DIRF, ECF prep, IRPF-compliant donation receipts per Lei 9.249/95 art. 13).

**Donations rail** (`usbea_donations` greenfield): receipts, recurring giving via **Pix Automático** (Doare API, integrated June 2025) + Mercado Pago Subscriptions v2, P2P pages, reconciliation against Odoo accounting.

**AI:** donation pattern detection, recurring-giver churn prediction, AI-drafted thank-you emails per donor segment.

---

## 4. Non-Goals (Explicit)

- **Not the member-facing platform.** No alumni login, no networking, no matching, no member directory. That's `usbea-digital`.
- **Not a general-purpose CRM.** Optimized for nonprofit cultivation workflows, not B2B sales.
- **Not a marketing automation suite.** Integrate with Mailchimp/Sendpulse, don't compete with them.
- **Not a website builder.** WordPress (`usbeabrasil.org`) handles public marketing.
- **Not a community forum.** Discourse (`community.usbeabrasil.org`) owns alumni discussion.
- **No alumni PII in Odoo by default.** Only Diretoria-tier contacts plus donors/funders explicitly added.

---

## 5. Success Metrics

| Metric | Phase 1 target | Phase 3 target | Phase 5 target |
|--------|----------------|----------------|----------------|
| Active Diretoria users / week | ≥ 5 | ≥ 8 | ≥ 12 |
| Tasks created / week | ≥ 25 | ≥ 60 | ≥ 100 |
| Donor/funder contacts in CRM | 0 | ≥ 100 | ≥ 500 |
| Grants in pipeline (any state) | 0 | ≥ 10 | ≥ 25 |
| Grant applications submitted from tool | 0 | ≥ 1 | ≥ 5 |
| Recurring donors via PIX rail | 0 | 0 | ≥ 50 |
| LGPD DSAR fulfillment SLA | N/A | < 15 days | < 7 days |
| AI suggestion acceptance rate | ≥ 30% | ≥ 50% | ≥ 60% |
| Mean time to close a board task | < 14d | < 7d | < 5d |

---

## 6. Phased Roadmap

Prerequisite: merge feature branch `claude/usbea-nonprofit-platform-ZcYCQ` to `19.0`, verify all 7 current modules load.

| Phase | Scope | Duration | Exit criteria |
|-------|-------|----------|---------------|
| **1** | Project/Task Ops + AI baseline. Ship `usbea_tasks` + `usbea_ai`. 6 nonprofit task templates. Task↔Grant↔Program linking. AI smart-prioritization. | 8–10w | Diretoria using it ≥2 weeks of real work; ≥50 tasks created |
| **2** | CRM + Brazilian Compliance. Ship `usbea_crm` (extends OCA partner-contact + partial OCA crm) + LGPD/MROSC/OSCIP/Receita extensions in `usbea_compliance`. LGPD consent gate on every CRM record. | 8–10w | LGPD DSAR demo passes legal review; ≥100 contacts loaded |
| **3** | Grant Seeking. Ship `usbea_grants_seeking` (extends OCA/dms) + grant-writing copilot. Funder DB seeded. | 6–8w | First real grant application drafted in-tool start-to-finish |
| **4** | Programs + Impact. Extend `usbea_programs` (volunteers), ship `usbea_impact`. | 6–8w | One program's full participant/volunteer/outcome cycle tracked |
| **5** | Donations + Payments rail. `usbea_donations` (greenfield) + Pix Automático (Doare) + Mercado Pago Subscriptions v2. | 6w | First R$1k recurring donation processed with IRPF receipt |
| **6** | Polish + white-label hardening. Tighten `usbea_whitelabel`, second-tenant onboarding rehearsal. | 4w | Second tenant onboarded in <1 day |

**Total runway:** ~11–14 months calendar including prerequisites.

---

## 7. Build Philosophy & OCA Strategy

**Custom USBEA modules**, not lean-into-stock Odoo. Brand consistency, white-label asset value, nonprofit-native UX justify the build cost.

**OCA extension where coverage is strong:**

| Area | OCA module (19.0) | Coverage | Strategy |
|------|-------------------|----------|----------|
| DMS (grant/compliance docs) | `OCA/dms` | ~80% | **Extend OCA** |
| Partner/org hierarchies | `OCA/partner-contact` | ~70% | **Extend OCA** |
| CRM extensions | `OCA/crm` | ~30% | **Partial extend** |
| Project workflows | `OCA/project` (no NP specifics) | ~10% | **Greenfield** atop stock `project` |
| Donations | `OCA/donation` (19.0 stalled) | ~10% | **Greenfield** |

**Every new module's spec in `MODULES.md` must answer "did we check OCA 19.0 first?" before greenfield is justified.**

---

## 8. AI Layer (Cross-Cutting)

AI is horizontal, not phase-scoped. See `AI.md` for full architecture. Summary:

- **Shared base:** `usbea_ai` module with ModelRouter (Claude API + prompt cache), AiSuggestion audit log, LGPD-safe context builder.
- **Per-pillar features:** Task prioritization (P1) → Donor segmentation (P2) → **Grant copilot (P3 — highest leverage)** → Impact narratives (P4) → Donation analytics (P5).
- **LGPD-first:** AI prompts never include un-consented PII; every AI use logged for DSAR responses.

---

## 9. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-23 | Reposition from "financial app" to "Nonprofit OS" | Existing scope is 2.5/5 pillars; user explicit ask to expand to full suite |
| 2026-05-23 | Build philosophy: custom USBEA modules over stock Odoo | Brand consistency + white-label asset value + NP-native UX |
| 2026-05-23 | Phase 1 = Project/Task Ops (not CRM, not Grants) | Quick staff-productivity win; foundation for cross-pillar linking |
| 2026-05-23 | LGPD = Phase 2 fast-follow (not Phase 1 gating) | Pragmatic balance; minimal scaffolding in P1, full pack in P2 |
| 2026-05-23 | AI = cross-cutting layer | Differentiator vs Bonterra/Bloomerang in 2025-2026 window |
| 2026-05-23 | Extend OCA/dms + OCA/partner-contact where ≥60% coverage | Concrete spec for "custom" — never blind greenfield when OCA exists |
| 2026-05-23 | Custom modules stay `usbea_*` prefix until Phase 6 white-label rename consideration | Avoid premature rename churn |

---

## 10. Open Questions (Tracked, not blocking)

1. **Discourse SSO timing** — `INTEGRATION.md` mentions "Phase 2 future" SSO. Should Nonprofit OS Phase 2 take that on as a requirement?
2. **Multi-currency policy** — current `usbea_grants` supports USD/BRL. Should `usbea_crm` defaults be BRL with USD opt-in or vice versa?
3. **Instrumentl integration** — paid SaaS dependency vs build funder DB ourselves. Decide before Phase 3 mid-point.
4. **Embedded BI** — Odoo Spreadsheet vs Metabase vs custom OWL components for portal dashboards beyond `usbea_portal`'s current scope.

---

## Related docs

- [MODULES.md](MODULES.md) — module-by-module spec, dependency graph, OCA references
- [COMPLIANCE.md](COMPLIANCE.md) — Brazilian regulatory mapping (LGPD/MROSC/OSCIP/Receita Federal)
- [AI.md](AI.md) — AI architecture, prompts, audit, LGPD safety
- [../INTEGRATION.md](../INTEGRATION.md) — cross-system integration (Caddy / Discourse / n8n / WP)
- [../RBAC.md](../RBAC.md) — user tier matrix
- [Memory: usbea-product-vision](/root/.claude/projects/-root/memory/usbea-product-vision.md) — member-facing platform vision (different product)
