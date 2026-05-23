# USBEA Nonprofit OS — Module Spec

This is the canonical module-by-module spec for `addons/usbea_*`. Every module — existing and planned — gets a section with: depends, models, views, OCA references, AI hooks, LGPD considerations, acceptance criteria.

**Versioning:** all modules track Odoo `19.0`, version string `19.0.X.Y.Z` where X.Y.Z is module-specific.

---

## Dependency Graph

```
                                 ┌─────────────┐
                                 │  usbea_rbac │
                                 └──────┬──────┘
                                        │
              ┌───────────────┬─────────┼─────────┬─────────────────┐
              │               │         │         │                 │
        usbea_grants   usbea_programs   │   usbea_whitelabel   usbea_ai (new)
              │               │         │                          │
              └──────┬────────┘         │                          │
                     │                  │                          │
              usbea_expenses     usbea_portal                       │
                                                                   │
              ┌──────────────┬───────────────┬──────────────┬──────┴──────┐
              │              │               │              │             │
       usbea_tasks    usbea_crm     usbea_grants_seeking   usbea_compliance  usbea_donations
       (Phase 1)     (Phase 2)     (Phase 3)              (Phase 2 expand)  (Phase 5)
                                                                                │
                                                                          usbea_impact
                                                                          (Phase 4)
```

---

## Existing Modules (Feature Branch — Merge in Prerequisites)

### `usbea_rbac` (v19.0.1.0.0) — *foundation*
- **Depends:** `base`, `mail`
- **Models:** `usbea.platform_role`, `usbea.user_invitation`, `res.company` (extended), `res.users` (extended)
- **Views:** organization_views, platform_role_views, user_management_views, rbac_menus, invite_user_wizard
- **Purpose:** Multi-tenant RBAC primitive; super-admin role, organization management, invitation workflow
- **Tests:** TBD — add `tests/test_rbac.py` covering role assignment, invitation flow, multi-company isolation

### `usbea_grants` (v19.0.1.0.0) — *grant-receiving lifecycle*
- **Depends:** `base`, `mail`, `account`, `usbea_rbac`
- **Models:** `usbea.grant`, `usbea.grant.budget`, `usbea.grant.expense`, `usbea.grant.disbursement`, `usbea.grant.report`
- **States:** `draft → submitted → under_review → approved → active → reporting → completed`
- **Views:** grant_views, expense_views, disbursement_views, report_views, budget_views
- **Tests:** TBD — state machine transitions, multi-currency rounding, budget vs expense reconciliation
- **Note:** This is the **receiving** side. Grant **seeking** lives in new `usbea_grants_seeking` (Phase 3).

### `usbea_programs` (v19.0.1.0.0)
- **Depends:** `base`, `mail`, `usbea_rbac`, `usbea_grants`
- **Models:** `usbea.program`, `usbea.participant`, `usbea.program.event`
- **Views:** program_views, participant_views, program_event_views
- **Demo:** seed programs (YLAI, Humphrey, Mandela Washington, IVLP, Youth Ambassadors, EIP, BRITE, PDPI, E2C, Fulbright, Other)
- **Tests:** TBD — participant linking, event scheduling, grant↔program linking

### `usbea_expenses` (v19.0.1.0.0)
- **Depends:** `hr_expense`, `usbea_grants`, `usbea_programs`
- **Models:** `hr.expense` (extended) — adds `grant_id`, `program_id`, approval workflow
- **Tests:** TBD — expense allocation, multi-currency conversion

### `usbea_portal` (v19.0.1.0.0)
- **Depends:** `base`, `usbea_rbac`, `usbea_grants`, `usbea_programs`
- **Models:** none (uses SQL views + Odoo dashboards)
- **Views:** portal_dashboard_views (board KPIs, financial pivot/graphs)
- **Note:** Phase 1 will add AI summary widget for stale tasks.

### `usbea_compliance` (v19.0.1.0.0)
- **Depends:** `base`, `usbea_rbac`, `usbea_grants`, `usbea_programs`
- **Reports:** quarterly narrative, financial expenditure, participant impact, final grant closeout
- **Phase 2 expansion** (see new module `usbea_compliance_br` below)

### `usbea_whitelabel` (v19.0.1.0.0)
- **Depends:** `base`, `base_setup`, `usbea_rbac`
- **Models:** `res.company` (branding fields), `res.config.settings` (extended)
- **Views:** branding_settings_views, user_profile_views, whitelabel_menus
- **Note:** Multi-tenant readiness scaffold. Phase 6 hardens for second-tenant onboarding.

---

## Phase 1 — New Modules

### `usbea_ai` (Phase 1, new)
- **Depends:** `base`, `mail`, `usbea_rbac`
- **Purpose:** Shared AI infrastructure: ModelRouter (Claude wrapper, prompt cache), audit log, LGPD-safe context, per-feature suggestion records
- **OCA check:** No equivalent. **Greenfield justified.**
- **Models:**
  - `usbea.ai.suggestion` — audit log: model_used, prompt_hash, response, accepted (bool), accepted_by, accepted_at, source_module, source_model, source_record_id (Reference field), tokens_used, latency_ms, lgpd_redacted (bool)
  - `usbea.ai.prompt_template` — reusable prompts: name, technical_key, system_prompt, user_prompt_template, model_preference (opus/sonnet/haiku), max_tokens, temperature
  - `usbea.ai.config` — singleton: api_key (encrypted), default_model, cache_ttl_seconds, lgpd_redaction_enabled, audit_retention_days
- **Services (Python, not Odoo models):** `usbea_ai.services.router.ModelRouter`, `usbea_ai.services.cache.PromptCache`, `usbea_ai.services.lgpd_redactor.LGPDRedactor`
- **AI hooks:** none (this IS the AI module)
- **LGPD:** all PII passed through `LGPDRedactor` before hitting Anthropic API; audit retention configurable per tenant; DSAR query exposes all `usbea.ai.suggestion` records for a partner_id
- **Tests:** unit tests for router model selection logic, PII redactor regex coverage, prompt cache hit/miss, audit log write-on-call invariant
- **Acceptance:** (a) Module installs without error; (b) `usbea.ai.config` settings page exposes API key field; (c) calling `env['usbea.ai.config'].suggest(template_key, context)` returns a suggestion record + writes audit log; (d) test coverage ≥ 80%

### `usbea_tasks` (Phase 1, new)
- **Depends:** `project`, `mail`, `usbea_ai`, `usbea_grants`, `usbea_programs`
- **Purpose:** Branded nonprofit task management with templates and cross-pillar linking
- **OCA check:** OCA/project has no nonprofit-specific modules. **Greenfield atop stock `project`.**
- **Models:**
  - `project.task` (extended): adds `usbea_template_id` (m2o), `grant_id` (m2o → usbea.grant), `program_id` (m2o → usbea.program), `usbea_priority_ai` (computed via usbea_ai)
  - `usbea.task.template` — reusable templates: name, category (selection: program_launch, grant_report, board_meeting, event_planning, donor_cultivation, compliance_deadline), checklist_subtasks (o2m), default_assignee_role, default_due_offset_days
  - `usbea.task.checklist_item` — checklist row on a template
- **Views:**
  - `usbea_task_views.xml`: extended kanban + form + list + gantt; "My Week" search view; template selector dialog
  - `usbea_task_template_views.xml`: template CRUD
  - `usbea_task_menus.xml`: menu items + dashboard
- **AI hooks:** (1) on task create, compute `usbea_priority_ai`; (2) "Generate next-action" action button calls `usbea_ai.suggest("task_next_action", task_context)`; (3) board portal widget calls `usbea_ai.suggest("stale_tasks_summary", ...)`
- **LGPD:** task descriptions can contain donor names → redact before AI calls
- **Tests:** template instantiation creates subtasks correctly; grant/program FK constraints enforced; AI priority computed when AI enabled, skipped when disabled
- **Acceptance:** (a) Module installs; (b) Templates seeded (6 nonprofit categories); (c) Creating a task from template auto-creates checklist; (d) AI priority shown in kanban when usbea_ai enabled; (e) Tests ≥ 80% line coverage

---

## Phase 2 — New Modules / Expansions

### `usbea_crm` (Phase 2, new)
- **Depends:** `crm`, `mail`, `usbea_rbac`, `usbea_ai`, `partner_company_group` (OCA), `partner_affiliate` (OCA)
- **Purpose:** Donor/Funder/Staff archetype CRM with nonprofit-native cultivation workflow
- **OCA check:** `OCA/partner-contact` covers ~70% (hierarchies, affiliations, company grouping). **Extend OCA.** `OCA/crm` partial use for `crm.lead` extensions.
- **Models:**
  - `res.partner` (extended): adds `usbea_archetype` (donor/funder/staff/grantee), `engagement_score` (computed), `lgpd_consent_id` (m2o), `soft_credit_partner_ids` (m2m), `cultivation_stage` (selection)
  - `usbea.cultivation.move` — moves management: partner_id, move_type (research/qualification/cultivation/solicitation/stewardship), notes, date, next_move_date, assigned_user_id
  - `usbea.engagement.event` — engagement tracking: partner_id, event_type (donation/event_attendance/email_open/meeting/manual), score_delta, timestamp
- **Views:** partner form extended (archetype tabs), cultivation kanban, moves-management board
- **AI hooks:** (1) donor segmentation — clusters via embedding similarity; (2) "Suggest next move" action button; (3) AI-drafted personalization tokens for campaigns
- **LGPD:** every `res.partner` with archetype must have `lgpd_consent_id` set; `usbea.cultivation.move` accessible only to assigned user + Diretoria
- **Tests:** archetype CRUD, engagement score computation deterministic, soft-credit graph traversal, LGPD consent gate (cannot create donor without consent record)
- **Acceptance:** (a) Module installs; (b) 3 archetype demo records seed; (c) Engagement score computed correctly; (d) LGPD consent gate prevents partner creation without consent; (e) Tests ≥ 80%

### `usbea_compliance_br` (Phase 2, expand `usbea_compliance`)
- **Depends:** `usbea_compliance`, `usbea_rbac`, `usbea_crm`, `account`
- **Purpose:** Brazilian regulatory pack — LGPD + MROSC + OSCIP + Receita Federal
- **OCA check:** No Brazilian-specific nonprofit modules. **Greenfield.**
- **Models:**
  - `usbea.lgpd.consent` — partner_id, scope (selection: marketing/communications/research/sharing), granted_at, granted_via (email/in_person/form), expires_at, revoked_at, revocation_reason
  - `usbea.lgpd.dsar` — data subject access request: partner_id, request_type (access/portability/deletion/correction), status (received/processing/fulfilled/denied), received_at, fulfilled_at, sla_deadline (computed: received + 15 days), notes
  - `usbea.lgpd.processing_log` — what data is processed where, lawful basis, retention period
  - `usbea.mrosc.partnership` — public-sector partnership (Lei 13.019/2014): partner_id (funder), partnership_type (termo_colaboracao/termo_fomento/acordo_cooperacao), instrumento_juridico_ref, start_date, end_date, total_value, prestacao_contas_state
  - `usbea.oscip.status` — OSCIP certification tracker: granted_at, granted_by, renewed_until, qualifying_finalities
  - `usbea.receita.dirf_line` — DIRF prep: beneficiary partner_id, gross_amount, ir_withheld, calendar_year
  - `usbea.receita.ecf_export` — annual ECF prep wizard
- **Views:** consent registry, DSAR kanban (states), processing-log table, MROSC partnerships board, OSCIP status card, DIRF/ECF wizards
- **AI hooks:** AI-drafted DSAR responses, AI summarization of processing logs for ANPD audit prep
- **LGPD:** this IS the LGPD module
- **Tests:** consent state machine, DSAR SLA computation, redaction simulation, MROSC partnership lifecycle
- **Acceptance:** (a) Module installs; (b) Creating a partner with archetype prompts for consent; (c) DSAR demo (access/deletion request → fulfillment) passes legal-review spec; (d) Tests ≥ 80%

---

## Phase 3 — New Module

### `usbea_grants_seeking` (Phase 3, new)
- **Depends:** `mail`, `usbea_rbac`, `usbea_crm`, `usbea_grants`, `usbea_ai`, `dms` (OCA)
- **Purpose:** Grant **application** pipeline — distinct from `usbea_grants` (which handles received grants)
- **OCA check:** `OCA/dms` provides ~80% of attachment vault. **Extend OCA/dms.**
- **Models:**
  - `usbea.grant_application` — name, funder_partner_id (m2o → res.partner archetype=funder), program_id (m2o), requested_amount, currency_id, deadline, state (`prospect → researching → drafting → submitted → under_review → awarded | declined | withdrawn`), submitted_at, decision_at, draft_dms_directory_id (m2o → dms.directory), assigned_writer_id, fit_score_ai (computed)
  - `usbea.funder` — extends `res.partner` archetype=funder: typical_grant_size_min/max, focus_areas, application_seasons, funder_type (foundation/government/corporate/individual_major)
  - `usbea.grant_application.draft_version` — version history: application_id, version_num, content (text), created_by, created_at, ai_assisted (bool)
  - `usbea.grant_application.comment` — collaboration: application_id, body, author_id, created_at
- **Views:** application kanban, calendar (deadlines), form with draft+versions tab, funder DB list
- **AI hooks:** (1) **Grant-writing copilot** — primary feature, calls `usbea_ai.suggest("grant_writing", {funder, program, draft_so_far})`; (2) Funder-fit scoring on creation; (3) AI translation EN↔PT-BR drafts
- **LGPD:** application drafts may reference donor data → redact before AI
- **Tests:** state machine, version history immutability, fit scoring deterministic given inputs, award handoff to `usbea_grants`
- **Acceptance:** (a) Module installs; (b) Creating an application from a funder seeds fit score; (c) Grant copilot returns a coherent draft suggestion; (d) Awarded state transitions create `usbea.grant` record; (e) Tests ≥ 80%

---

## Phase 4 — New Module / Expansion

### `usbea_programs` (Phase 4 expansion)
- **Adds:** `usbea.volunteer` (extends `res.partner` archetype=volunteer? or separate), volunteer skills m2m, availability slots, hours tracking, background-check status
- **Tests:** volunteer registration flow, hours tracking, background-check expiry alerts

### `usbea_impact` (Phase 4, new)
- **Depends:** `usbea_programs`, `usbea_rbac`, `usbea_ai`
- **Purpose:** Outcome indicators, theory-of-change, narrative + quantitative impact tracking
- **OCA check:** No equivalent. **Greenfield.**
- **Models:**
  - `usbea.impact.indicator` — program_id, name, unit, target_value, current_value, frequency (annual/quarterly/monthly)
  - `usbea.impact.measurement` — indicator_id, value, date, source (manual/survey/sensor/external)
  - `usbea.impact.story` — partner_id (beneficiary), program_id, narrative, media_attachment_ids
  - `usbea.impact.report` — period, programs, indicators, narratives, generated_pdf (Phase 1 PDF generation in `usbea_compliance` extends here)
- **AI hooks:** auto-generate narrative reports from measurement data; photo auto-tagging via vision
- **Tests:** indicator computation, story PII redaction, report PDF assembly
- **Acceptance:** (a) Module installs; (b) Creating indicators + measurements aggregates correctly; (c) AI-generated impact narrative passes manual review

---

## Phase 5 — New Module

### `usbea_donations` (Phase 5, new)
- **Depends:** `account`, `mail`, `usbea_rbac`, `usbea_crm`, `usbea_ai`
- **Purpose:** Donation receipts (IRPF-compliant when OSCIP active), recurring giving via Pix Automático + Mercado Pago, P2P pages
- **OCA check:** `OCA/donation` 19.0 is a skeleton — port stalled. 18.0 has working models. **Greenfield, but mine 18.0 OCA models as reference.**
- **Models:**
  - `usbea.donation` — donor_partner_id, amount, currency_id, donation_date, payment_method (pix_one_off/pix_recurring/cc_one_off/cc_recurring/boleto/cash/in_kind), rail (doare/mercado_pago/manual), external_ref, account_move_id (reconciliation), receipt_issued (bool), receipt_pdf
  - `usbea.donation.recurring_plan` — donor_partner_id, amount, frequency (monthly/quarterly/annual), rail, external_subscription_id, state (active/paused/cancelled), next_charge_date
  - `usbea.donation.p2p_campaign` — name, host_partner_id, target_amount, current_amount, donation_ids
  - `usbea.donation.receipt_template` — IRPF compliance fields (OSCIP cert ref, Lei 9.249/95 art. 13 ref, organization CNPJ, beneficiary CPF)
- **Integrations:**
  - **Doare API** for Pix Automático: `usbea_donations.services.doare.DoareClient` (webhook handler in `controllers/`)
  - **Mercado Pago Subscriptions v2**: `usbea_donations.services.mercado_pago.MPClient`
- **AI hooks:** donation pattern detection (anomaly alerts), churn prediction for recurring donors, AI-drafted thank-you emails per segment
- **LGPD:** donation records hold donor PII → strict access control; receipts retained per Receita Federal 5-year rule
- **Tests:** receipt generation correctness, recurring plan state machine, webhook signature verification, idempotent donation insertion
- **Acceptance:** (a) Module installs; (b) Manual donation creates accounting entry; (c) IRPF receipt PDF generates with valid OSCIP fields; (d) Doare webhook test (signed payload) creates recurring plan; (e) Tests ≥ 80%

---

## Cross-Module Conventions

**Module naming.** All custom modules use `usbea_*` prefix. Phase 6 will evaluate rename to `nonprofitos_*` for white-label launch.

**Manifest fields.** Every module:
- `category`: `'Nonprofit'`
- `author`: `'Automation Labs / SkilLab'`
- `website`: `'https://automation-labs.co'`
- `license`: `'LGPL-3'`
- `version`: `'19.0.X.Y.Z'`

**Security.** Every module ships:
- `security/<module>_security.xml` — record rules
- `security/ir.model.access.csv` — model-level ACLs

**Tests.** Every module ships `tests/` directory with `__init__.py` + `test_<feature>.py` files. Coverage gate: ≥ 80% line coverage per module enforced by CI.

**SAST.** Bandit + ruff run on every PR. New issues block merge.

**LGPD checklist** (every module touching PII):
- Document data classes in `usbea.lgpd.processing_log`
- Add consent gate on new model where applicable
- Add DSAR adapter (`_get_lgpd_data_for_partner(partner_id)`)
- Pass PII through `usbea_ai.services.lgpd_redactor` before any AI call

**Multi-currency.** All money fields use `currency_id` m2o + `amount` Monetary. Default to `company_currency_id` from `res.company`. USBEA uses BRL primary, USD secondary.

**Multi-company / multi-tenant.** All models with sensitive data carry `company_id` m2o and respect `res.company` multi-tenant record rules (extended by `usbea_rbac`).
