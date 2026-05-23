# USBEA Nonprofit OS

**A Brazilian-first back-office Nonprofit Operating System for alumni-driven NGOs.** Built on Odoo 19.0 (LGPL-3) with custom `usbea_*` modules and selective [OCA](https://github.com/OCA) extensions.

**Deployed at:** [`manage.usbeabrasil.org`](https://manage.usbeabrasil.org)
**Repo:** `SkilLab-Tech/NonprofitManager`
**Author:** Automation Labs / SkilLab — [automation-labs.co](https://automation-labs.co)

---

## What this is

Five pillars covering the entire back-office surface of a Brazilian alumni-driven nonprofit:

1. **Project & Task Operations** — nonprofit-native templates (program-launch, grant-report, board prep, event planning, donor cultivation, compliance deadlines), Task ↔ Grant ↔ Program linking
2. **Alumni / Donor / Funder CRM** — three contact archetypes, moves management, engagement scoring, LGPD consent
3. **Grant Seeking Pipeline** — application kanban, funder DB, deadline calendar, draft collaboration, **AI grant-writing copilot**
4. **Programs, Volunteers & Impact** — program lifecycle, volunteer management, outcome indicators, narrative reporting
5. **Operations, Compliance & Donations** — LGPD + MROSC + OSCIP + Receita Federal compliance pack, donation rail via PIX Automático (Doare) + Mercado Pago

**AI** is cross-cutting: a shared `usbea_ai` module powers grant copilots, donor segmentation, smart task routing, impact narrative generation, and DSAR response drafting.

---

## What this is not

Not the alumni-facing platform. That's `usbea-digital` — a separate Next.js monorepo with the matchmaking engine, programs portal, and alumni grant application portal. Alumni records live in [Discourse](https://community.usbeabrasil.org); only Diretoria contacts and donor/funder records live in this Nonprofit OS.

See [`docs/PRD.md`](docs/PRD.md) for full positioning and non-goals.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/PRD.md`](docs/PRD.md) | Product Requirements — positioning, personas, 5 pillars, roadmap, success metrics |
| [`docs/MODULES.md`](docs/MODULES.md) | Module-by-module spec with dependencies, models, OCA references, AI hooks |
| [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) | LGPD / MROSC / OSCIP / Receita Federal regulatory map |
| [`docs/AI.md`](docs/AI.md) | AI layer architecture, prompts, audit log, LGPD-safe inference |
| [`INTEGRATION.md`](../INTEGRATION.md) *(parent dir)* | Cross-system architecture (Caddy + Discourse + n8n + WP + Odoo) |
| [`RBAC.md`](../RBAC.md) *(parent dir)* | User tier matrix across all USBEA systems |

---

## Custom Modules

All custom modules live under `addons/usbea_*` and ship with manifests targeting Odoo 19.0, LGPL-3.

| Module | Status | Purpose |
|--------|--------|---------|
| `usbea_rbac` | feature-branch | Multi-tenant RBAC, organization management, user invitations |
| `usbea_grants` | feature-branch | Grant lifecycle (receiving side): application → disbursement → reporting |
| `usbea_programs` | feature-branch | Exchange program + participant + event management |
| `usbea_expenses` | feature-branch | Extended `hr.expense` with grant + program allocation |
| `usbea_portal` | feature-branch | Board read-only dashboard with grant portfolio KPIs |
| `usbea_compliance` | feature-branch | Compliance report templates (PDF generation) |
| `usbea_whitelabel` | feature-branch | Multi-tenant branding scaffold |
| `usbea_ai` | Phase 1 *(planned)* | Shared AI layer — see [`docs/AI.md`](docs/AI.md) |
| `usbea_tasks` | Phase 1 *(planned)* | Branded nonprofit task management atop stock `project` |
| `usbea_crm` | Phase 2 *(planned)* | Donor/Funder/Staff CRM atop OCA `partner-contact` |
| `usbea_compliance_br` | Phase 2 *(planned)* | LGPD + MROSC + OSCIP + Receita Federal extensions |
| `usbea_grants_seeking` | Phase 3 *(planned)* | Grant **application** pipeline (distinct from `usbea_grants`) |
| `usbea_impact` | Phase 4 *(planned)* | Outcome indicators + impact narratives |
| `usbea_donations` | Phase 5 *(planned)* | IRPF-compliant receipts + Pix Automático + Mercado Pago rail |

See [`docs/MODULES.md`](docs/MODULES.md) for full specs.

---

## Stack

- **Runtime:** Odoo 19.0 + PostgreSQL + Redis + Caddy
- **Languages:** Python (modules), XML (views), OWL (frontend widgets)
- **Quality:** ruff + bandit (SAST) + pytest with ≥ 80% coverage gate per module
- **CI:** GitHub Actions
- **AI:** Anthropic API (Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5) with prompt caching + LGPD redaction

---

## Contributing

Custom modules are LGPL-3. Upstream Odoo code follows Odoo's license. New modules:
1. Read [`docs/MODULES.md`](docs/MODULES.md) for conventions (manifest fields, security pattern, test gate, LGPD checklist)
2. Check OCA 19.0 coverage before writing greenfield code — see Build Philosophy in `docs/PRD.md`
3. Open PR with passing tests + bandit clean

---

## Upstream Odoo

This repo is a fork of [`odoo/odoo`](https://github.com/odoo/odoo) at branch `19.0`. Upstream Odoo is a suite of open-source business apps. For upstream documentation and contribution:

- [Odoo Apps](https://www.odoo.com/)
- [Odoo Documentation](https://www.odoo.com/documentation/master/)
- [Odoo eLearning](https://www.odoo.com/slides)
- [Developer tutorials](https://www.odoo.com/documentation/master/developer/howtos.html)

## Security

For security issues in upstream Odoo code, see Odoo's [Responsible Disclosure](https://www.odoo.com/security-report). For security issues in custom `usbea_*` modules, contact: `security@automation-labs.co`.
