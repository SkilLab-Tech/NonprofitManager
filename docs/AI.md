# AI Layer Architecture

The AI layer is **horizontal**, not phase-scoped. Every pillar in the Nonprofit OS calls into the shared `usbea_ai` module for inference. This doc defines the architecture, prompt patterns, audit log, LGPD safety, and per-pillar feature roadmap.

---

## 1. Module Boundaries

```
┌──────────────────────────────────────────────────────────────┐
│                      Per-pillar modules                       │
│  usbea_tasks · usbea_crm · usbea_grants_seeking · usbea_impact │
│                       · usbea_donations                        │
└─────────────────────────────┬────────────────────────────────┘
                              │  env['usbea.ai'].suggest(template_key, context)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                        usbea_ai module                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Models: usbea.ai.config / usbea.ai.prompt_template /  │  │
│  │          usbea.ai.suggestion (audit log)                │  │
│  └────────────────────────────────────────────────────────┘  │
│                              │                                │
│                              ▼                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Services (Python, not models):                         │  │
│  │   · ModelRouter   (Anthropic SDK + cache + retry)       │  │
│  │   · PromptCache   (5-min in-memory + Odoo bus invalid.) │  │
│  │   · LGPDRedactor  (regex + entity strip before API)     │  │
│  └────────────────────────────────────────────────────────┘  │
│                              │                                │
└──────────────────────────────┼────────────────────────────────┘
                               │  HTTPS
                               ▼
                    ┌──────────────────────┐
                    │   Anthropic API      │
                    │ claude-opus-4-7      │
                    │ claude-sonnet-4-6    │
                    │ claude-haiku-4-5     │
                    └──────────────────────┘
                       (future: + Ollama local fallback)
```

**Contract:** any pillar module calls `env['usbea.ai'].suggest(template_key, context)` and receives a `usbea.ai.suggestion` record. No pillar module ever imports `anthropic` directly. This isolates SDK version churn, prompt-cache logic, and LGPD redaction in one place.

---

## 2. ModelRouter

**Responsibility:** select model, build request, call API, parse, cache, log.

**Model selection (default policy):**
| Template tier | Default model | Use cases |
|---------------|---------------|-----------|
| `quick` | `claude-haiku-4-5-20251001` | Task summarization, segment labels, sentiment |
| `standard` | `claude-sonnet-4-6` | Donor segmentation, fit scoring, next-action suggestion |
| `deep` | `claude-opus-4-7` | Grant writing drafts, impact narratives, DSAR responses |

Per-template override via `usbea.ai.prompt_template.model_preference`.

**Retry policy:** exponential backoff, 3 attempts, surface error to caller after exhaustion (do not silently fail — UX must show "AI unavailable").

**Prompt caching:** uses Anthropic SDK prompt caching (5-min TTL). Cache key = SHA256(system_prompt + first_N_tokens_of_user_prompt). Hit rate target ≥ 60% on warm orgs.

---

## 3. Prompt Patterns

All prompts stored as `usbea.ai.prompt_template` records (DB-driven, editable in admin UI without code deploy). Each template has:
- `name` — human-readable
- `technical_key` — referenced by pillar code (e.g., `"task_next_action"`, `"grant_writing"`)
- `system_prompt` — high-quality system message (PT-BR primary, EN-US fallback per template)
- `user_prompt_template` — Jinja-style template with `{{context}}` interpolation
- `model_preference` — `quick`/`standard`/`deep`
- `max_tokens`, `temperature`

**Seeded templates at install:**
| Key | Tier | Purpose |
|-----|------|---------|
| `task_priority` | quick | Rank a task list by urgency × impact |
| `task_next_action` | standard | Given a task + history, suggest next-action |
| `stale_tasks_summary` | quick | Summarize >7-day stale tasks for board |
| `donor_segmentation` | standard | Cluster donors into actionable segments |
| `donor_next_move` | standard | Suggest next cultivation move |
| `donor_thanks_draft` | quick | Draft personalized thank-you email |
| `grant_writing` | deep | Generate grant application draft sections |
| `grant_fit_score` | standard | Score funder ↔ program fit |
| `grant_translate` | standard | EN↔PT-BR translation pass |
| `impact_narrative` | deep | Generate impact report narrative from indicators |
| `dsar_response_draft` | deep | Draft LGPD DSAR response letter |

---

## 4. LGPD Safety — Pre-API Redaction

**Hard rule:** every prompt body passes through `LGPDRedactor.scrub(text, partner_ids)` before HTTP call.

**Redaction targets (Brazilian PII patterns):**
- CPF (`\d{3}\.?\d{3}\.?\d{3}-?\d{2}`)
- CNPJ (`\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}`)
- RG, CNH, passport patterns
- PIX keys (CPF/CNPJ/email/phone/UUID variants)
- Brazilian phone numbers
- Email addresses (replace with `<email:hash>`)
- Bank account formats (agência + conta)
- Brazilian zip code (CEP) + address combos

**Strategy:** replace with deterministic tokens (`<CPF_1>`, `<CPF_2>`) so model can still reason about distinct entities, but raw PII never leaves Brazil.

**Audit:** `usbea.ai.suggestion.lgpd_redacted = True` if redactor matched anything. Original PII never logged in clear.

**Test coverage requirement:** redactor unit tests with ≥ 50 Brazilian PII samples (positive) + ≥ 50 false-positive guards.

---

## 5. Audit Log — `usbea.ai.suggestion`

Every AI call writes one row. Schema:

| Field | Type | Purpose |
|-------|------|---------|
| `template_id` | m2o | Which template was used |
| `model_used` | char | Exact model ID (e.g., `claude-sonnet-4-6`) |
| `prompt_hash` | char(64) | SHA256 of post-redaction prompt — for cache + audit |
| `response` | text | Model output |
| `accepted` | bool | Did user accept the suggestion? |
| `accepted_by` | m2o res.users | Who accepted |
| `accepted_at` | datetime | When |
| `source_module` | char | E.g., `usbea_tasks` |
| `source_model` | char | E.g., `project.task` |
| `source_record_id` | int | Source record ID (Reference field for navigation) |
| `tokens_in` / `tokens_out` | int | Cost tracking |
| `cache_hit` | bool | Cache hit flag |
| `latency_ms` | int | Latency observed |
| `lgpd_redacted` | bool | Did redactor match? |
| `partner_ids` | m2m | Partners whose data appeared (for DSAR aggregation) |
| `error` | char | If call failed |

**Retention:** default 365 days, configurable per tenant. DSAR aggregator iterates this table by `partner_ids` to surface "what did AI see about me?"

**Cost dashboard:** `usbea_portal` adds a panel showing monthly AI spend, top-templates by token use, cache hit rate.

---

## 6. Acceptance Loop — How Suggestions Improve

Every suggestion has an "accept / reject / edit-and-accept" UI affordance. Acceptance signal feeds:
1. **Per-template accept rate** — surfaced in admin (templates < 30% accept rate flagged for review)
2. **Per-model accept rate** — informs whether to upgrade/downgrade default model for a tier
3. **Edit deltas** (Phase 2.5) — Diff between AI draft and user-edited version; future eval signal for prompt revisions

---

## 7. Failure Modes (KNOWN_FAILURE_MODES)

| Mode | Cause | Mitigation |
|------|-------|------------|
| FM-AI-001 | Anthropic API outage | Surface "AI unavailable, try again" — never auto-fallback to stale cache silently |
| FM-AI-002 | Redactor misses a PII pattern | Suggestion logged with `lgpd_redacted=False`; manual audit reviews these; new regex added |
| FM-AI-003 | Model returns malformed JSON | Retry once with stricter schema instruction; fall back to plain-text mode |
| FM-AI-004 | Long context overflows | Truncate context per pillar — never silently drop; warn user |
| FM-AI-005 | Tenant exceeds monthly token budget | Soft cap warns at 80%, hard cap at 100% (return error suggestion to caller) |
| FM-AI-006 | Prompt cache key collision (extremely unlikely with SHA256 but defense) | Cache miss on hash mismatch, recompute |
| FM-AI-007 | LGPD redactor over-redacts (false positive) | Confidence flag per match; user can re-run "without redaction" only if has data-protection-officer permission |

---

## 8. Per-Pillar AI Feature Roadmap

| Pillar | Phase | Feature | Template | Priority |
|--------|-------|---------|----------|----------|
| Tasks | 1 | Smart task prioritization | `task_priority` | P0 |
| Tasks | 1 | Next-action suggestion | `task_next_action` | P1 |
| Tasks | 1 | Stale tasks summary on board portal | `stale_tasks_summary` | P1 |
| CRM | 2 | Donor segmentation | `donor_segmentation` | P0 |
| CRM | 2 | Suggested next move | `donor_next_move` | P1 |
| CRM | 2 | Thank-you draft | `donor_thanks_draft` | P2 |
| Compliance | 2 | DSAR response draft | `dsar_response_draft` | P1 |
| Grants Seeking | 3 | **Grant-writing copilot** | `grant_writing` | **P0 — flagship** |
| Grants Seeking | 3 | Funder fit scoring | `grant_fit_score` | P0 |
| Grants Seeking | 3 | EN↔PT-BR translation | `grant_translate` | P1 |
| Impact | 4 | Impact narrative generation | `impact_narrative` | P0 |
| Impact | 4 | Photo/video auto-tagging | (vision API, future) | P2 |
| Donations | 5 | Donor churn prediction | `donor_churn` (TBD template) | P1 |
| Donations | 5 | Personalized thank-you per segment | (extends `donor_thanks_draft`) | P1 |

---

## 9. Future Considerations

### Local Fallback (Ollama)
Per `/root/CLAUDE.md`, Ollama is available locally on Tier 3. **Not yet** integrated — would require:
- Model selection extended with `local` tier
- Offline mode flag in `usbea.ai.config`
- Smaller-model prompt versions (different `prompt_template` records)
- Quality regression testing per-template before promoting any feature to local

**Status:** Phase 6+ if cost or sovereignty pressure demands it.

### Self-Hosted Embeddings for CRM Segmentation
Phase 2 donor segmentation may benefit from embeddings — explore `sentence-transformers` or Anthropic embeddings when available. Track in Phase 2 mid-point review.

### Eval Pipeline
Phase 4+: build per-template eval suite (golden inputs + expected outputs + LLM-as-judge scoring) running in CI on prompt changes. Currently out of scope; tracked as P3 backlog.

---

## 10. References

- Anthropic SDK Python: https://github.com/anthropics/anthropic-sdk-python
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- LGPD: see `COMPLIANCE.md`
- Model IDs (Claude 4.X family): `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
