# Integration Tests Guide

Two test layers shipped in this repo:

## 1. Pure-Python unit tests (`usbea_tests/`)

Fast (~0.4s for 291 tests), no Odoo required. Cover all the
state-machine, validation, parsing, and arithmetic in `utils/` and
`services/` packages. Run them locally:

```bash
python -m pytest usbea_tests/ -q
```

CI: `.github/workflows/usbea-ci.yml` (PR #3 adds it).

## 2. Odoo integration tests (`addons/usbea_*/tests/`)

Slower (requires Postgres + full Odoo install). Cover model creation,
@api.constrains gates, state-machine transitions in the live ORM,
record rules, and cross-module wiring (e.g. confirmed donation posts
an engagement event).

Each test class is tagged with `('post_install', '-at_install', '<module>')`
so they run after all installations complete and can be selected
per-module via `--test-tags`.

### Modules with integration tests

| Module | Test file | Critical paths covered |
|--------|-----------|------------------------|
| `usbea_ai` | `test_models.py` | Template rendering, validation, suggestion accept/reject, seeded-template presence, mocked router |
| `usbea_crm` | `test_lgpd_gate.py` | **LGPD consent gate** on archetype assignment; engagement score; DSAR adapter |
| `usbea_compliance_br` | `test_dsar_workflow.py` | DSAR state machine, 15-day SLA, traffic-light status, fulfilled override, cross-module aggregator |
| `usbea_grants_seeking` | `test_pipeline_state_machine.py` | Pipeline transitions (legal paths, illegal skips blocked, terminal states), award handoff, append-only versions, fit-score parsing |
| `usbea_donations` | `test_donation_idempotency.py` | Webhook idempotency, unique constraint, engagement event on confirm, refund gate, OSCIP gate on receipts |

### Running locally

```bash
# Set up Postgres (or rely on docker-compose.yml in the repo root).
# Install Python deps:
pip install -r requirements.txt anthropic

# Per-module:
./odoo-bin --addons-path=addons \
           -d test_usbea_ai \
           -i usbea_ai \
           --test-enable \
           --test-tags /usbea_ai \
           --stop-after-init

# All modules in sequence:
for mod in usbea_ai usbea_crm usbea_compliance_br usbea_grants_seeking usbea_donations; do
    ./odoo-bin --addons-path=addons \
               -d "test_$mod" \
               -i "$mod" \
               --test-enable \
               --test-tags "/$mod" \
               --stop-after-init
done
```

### CI

`.github/workflows/usbea-integration.yml` (this PR) spins up a Postgres
service container and runs the loop above. Logs uploaded as artifacts.
Job runs only when `addons/usbea_*` or the workflow file changes.

### Patterns / conventions

- **Setup is minimal.** Each TestCase has `setUp()` only when it needs
  to build a fixture (a partner, a consent, a funder). Anything more
  belongs in a helper method.
- **No demo data is loaded** (`--without-demo=all`) — tests build
  exactly the records they need so state never bleeds between cases.
- **No external network calls.** The router test mocks the Anthropic
  client; webhook tests inject a stub session.
- **Negative cases enforced.** Every state machine has at least one
  illegal-transition assertion.
- **Cross-module wiring asserted at the boundary.** E.g.,
  `test_confirm_posts_engagement_event` proves the donation→CRM bridge
  works end-to-end at the model layer.

## What's not yet covered

Listed for the next session:
- `usbea_tasks` — template instantiation idempotency, "My Week"
  computed boolean
- `usbea_impact` — indicator current_value computation, story consent
  constraint
- `usbea_volunteers` — hours-log append-only enforcement, opportunity
  ranking via env-mediated path
- `usbea_portal_ai` — board briefing assembly with mocked AI calls
- Multi-company record rule isolation tests (one rule per pillar)
- HTTP/webhook controllers — currently unit-tested at the signature layer;
  `tests/test_controllers.py` with `HttpCase` would close the loop.
