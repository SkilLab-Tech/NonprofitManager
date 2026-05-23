# Brazilian Compliance — Regulatory Map

This is the legal/regulatory reference for USBEA Nonprofit OS. Mapped to features in `MODULES.md`. **Not legal advice** — consult counsel before production rollout. Last reviewed: 2026-05-23.

---

## 1. LGPD — Lei Geral de Proteção de Dados (Lei 13.709/2018)

**In force since:** Sept 2020 (enforcement Aug 2021)
**Regulator:** ANPD (Autoridade Nacional de Proteção de Dados)
**Penalty:** up to 2% of Brazilian revenue or BRL 50M per violation
**Applies to:** every processor of data of subjects in Brazil, regardless of where the processor sits

### Lawful Bases (Art. 7)

USBEA processes personal data under multiple bases — each must be tracked per data class:

| Basis | Use case at USBEA |
|-------|-------------------|
| Consent (Art. 7, I) | Marketing communications, newsletters, event invites |
| Legitimate interest (Art. 7, IX) | Alumni mentorship matching (with privacy assessment) |
| Legal obligation (Art. 7, II) | Donor records for Receita Federal, MROSC reporting |
| Contract execution (Art. 7, V) | Grantee disbursement, program participation |
| Protection of life (Art. 7, VII) | Emergency contacts |

**Feature mapping:** `usbea.lgpd.consent.scope` selection field maps to these bases. `usbea.lgpd.processing_log` records the basis per data class.

### Data Subject Rights (Art. 18)

| Right | SLA | Feature |
|-------|-----|---------|
| Confirmation that data exists | 15 days | DSAR (`usbea.lgpd.dsar.request_type=access`) |
| Access (export) | 15 days | DSAR + portability adapter |
| Correction | 15 days | DSAR (`request_type=correction`) |
| Deletion (when allowed) | 15 days | DSAR (`request_type=deletion`) → cascade |
| Portability | 15 days | DSAR with structured JSON export |
| Information about sharing | 15 days | DSAR + processing log read |
| Consent revocation | immediate | `usbea.lgpd.consent.revoked_at` |

**Feature:** `usbea.lgpd.dsar` model with state machine + 15-day SLA computed deadline + per-module `_get_lgpd_data_for_partner(partner_id)` adapter pattern.

### Processing Log (Art. 37)

Mandatory record of processing activities. Each entry:
- Data class (e.g., "donor contact info")
- Purpose
- Lawful basis
- Retention period
- Sharing recipients (if any)

**Feature:** `usbea.lgpd.processing_log` model + seeded entries per module on install.

### Breach Notification (Art. 48)

Notify ANPD + affected subjects in "reasonable time" (ANPD guidance: 2 business days).

**Feature:** breach-notification template in `usbea_compliance` + manual workflow (no automated breach detection yet).

### Data Transfer Outside Brazil (Art. 33)

When using AI APIs (Anthropic, OpenAI), personal data crosses borders. Lawful basis required:
- Adequate-protection-level country (none currently designated by ANPD)
- Standard contractual clauses
- Explicit consent for the specific transfer
- Or **prior data minimization / pseudonymization** — recommended approach

**Feature:** `usbea_ai.services.lgpd_redactor.LGPDRedactor` strips PII before any external API call; redaction is logged in `usbea.ai.suggestion.lgpd_redacted=True`.

---

## 2. MROSC — Marco Regulatório das Organizações da Sociedade Civil (Lei 13.019/2014)

**Purpose:** governs partnerships between public administration and OSCs (Organizações da Sociedade Civil)
**Applies when:** USBEA receives funding from any federal, state, or municipal government entity in Brazil

### Partnership Instruments

| Instrument | Use case | Compliance burden |
|------------|----------|-------------------|
| Termo de Colaboração | Public initiative, OSC executes | High (chamamento público required) |
| Termo de Fomento | OSC initiative, public funds | High (chamamento público required) |
| Acordo de Cooperação | No financial transfer | Low |

**Feature:** `usbea.mrosc.partnership` model tracks each instrument with `partnership_type`, `instrumento_juridico_ref`, `prestacao_contas_state`.

### Prestação de Contas (Accountability)

OSC must report:
- Final report (relatório de execução do objeto)
- Financial report (relatório de execução financeira)
- Quantitative and qualitative goals achievement

**Feature:** `usbea_compliance` PDF templates (already in feature branch) cover quarterly + final reporting. Phase 2 adds MROSC-specific report types.

### Transparency Portal (Art. 11)

OSCs receiving public funds must publish on their website:
- Statute, register of directors, audited financial statements
- All MROSC instruments (active and concluded)
- Goal achievement

**Feature:** Phase 2 ships `/mrosc-transparency` controller in `usbea_compliance_br` exposing public read-only views.

---

## 3. OSCIP — Organização da Sociedade Civil de Interesse Público (Lei 9.790/1999)

**Status:** **USBEA Brasil seeking OSCIP qualification** (per `usbea-product-vision.md` memory)

### Benefits of OSCIP status
- Public funding partnerships via "Termo de Parceria" (simpler than MROSC Termo de Colaboração)
- Donor tax deduction up to 2% of operational profit (Lei 9.249/95 art. 13 §2º, II) — **conditional** on OSCIP status + finalidade reconhecida
- Federal recognition (Utilidade Pública Federal — UPF) status

### Qualifying Finalities (Art. 3)
USBEA fits multiple: educational promotion, cultural promotion, voluntary citizen experience, scientific/technological promotion.

**Feature:** `usbea.oscip.status` model tracks: `granted_at`, `granted_by` (MJ — Ministério da Justiça), `renewed_until`, `qualifying_finalities` (m2m selection).

### Annual Reporting
OSCIPs file annual report with MJ + maintain public transparency.

**Feature:** `usbea_compliance_br` annual OSCIP report template.

---

## 4. Receita Federal Obligations

### Donor Tax Receipts (Lei 9.249/95 art. 13)
For donors to deduct, USBEA must:
- Have OSCIP **and** UPF status
- Issue receipts with: CNPJ, donor CPF/CNPJ, amount, date, OSCIP qualifying article reference

**Feature:** `usbea.donation.receipt_template` includes mandatory IRPF fields. Receipts only issued when `usbea.oscip.status` is active.

### DIRF — Declaração do Imposto Retido na Fonte
Annual filing if USBEA pays contractors/employees with IR withholding.

**Feature:** `usbea.receita.dirf_line` model + wizard to export DIRF text file per Receita Federal layout (TXT layout updated annually — needs maintenance).

### ECF — Escrituração Contábil Fiscal
Annual filing required for tax-immune nonprofits above revenue thresholds. Integrates with Odoo accounting via SPED export.

**Feature:** `usbea.receita.ecf_export` wizard. Integrates with stock Odoo `l10n_br` localization (must be installed in production).

### EFD-Reinf
Replaces parts of DIRF in 2025-2026 transition. Monitor regulatory updates.

**Status:** **Watch.** No feature yet. Phase 5+ as Receita Federal finalizes layout.

---

## 5. Other Brazilian Obligations Worth Tracking

| Obligation | Source | When relevant |
|------------|--------|---------------|
| Lei Anticorrupção (12.846/2013) | Federal | Any public-sector dealings → integrity program required |
| Lei de Acesso à Informação (12.527/2011) | Federal | Public-funded OSCs must respond to LAI requests |
| eSocial | Federal | When USBEA has CLT employees (currently small staff) |
| ICP-Brasil digital signature | Federal | For some MROSC/government submissions |
| LGPD ANPD reporting (when applicable) | ANPD | Breach notifications |

---

## 6. Multi-System Compliance Surface

USBEA Brasil holds personal data across **three systems**:

| System | Data | Compliance owner |
|--------|------|------------------|
| Discourse (`community.usbeabrasil.org`) | Alumni profiles, posts, DMs | Discourse-side LGPD config + DSAR adapter (TBD) |
| WordPress (`usbeabrasil.org`) | Newsletter signups, contact form submissions | WP plugin LGPD compliance |
| Odoo (`manage.usbeabrasil.org`) | Donor/funder records, staff, financial data | `usbea_compliance_br` (this scope) |

**DSAR challenge:** A subject's "all my data" request must aggregate across all three systems. n8n workflow needed (Phase 2.5 nice-to-have).

---

## 7. Compliance Checklist by Phase

### Phase 1 (Task ops) — minimal LGPD scaffolding
- [ ] Add `lgpd_redacted` flag to AI suggestions
- [ ] Document task descriptions may contain PII; redact before AI

### Phase 2 (CRM + Compliance) — LGPD full pack
- [ ] `usbea_compliance_br` module installs
- [ ] Consent flow at partner creation
- [ ] DSAR demo (access + deletion) passes legal review
- [ ] Processing log seeded with all current data classes
- [ ] AI redactor tested against Brazilian PII patterns (CPF, CNPJ, RG, PIX keys)

### Phase 3 (Grant seeking)
- [ ] Grant draft PII review (some funders require beneficiary data → consent gate)
- [ ] AI grant-writing prompts pass redactor

### Phase 4 (Programs + Impact)
- [ ] Beneficiary stories require explicit consent for publication
- [ ] Photo/video media assets have model release tracking

### Phase 5 (Donations)
- [ ] OSCIP status verification before receipt issuance
- [ ] Receita Federal donor data retention 5 years minimum
- [ ] Doare/Mercado Pago DPAs (data processing agreements) on file
- [ ] PIX webhook signature verification (security, not LGPD)

---

## 8. Legal Review Triggers

Schedule legal counsel review **before** these milestones:
1. End of Phase 2 — LGPD/MROSC/OSCIP module spec review
2. Before first DSAR fulfillment in production
3. Before OSCIP application submission to Ministry of Justice
4. Before first PIX Automático donation in production
5. Before second-tenant onboarding (Phase 6) — DPA + sub-processor disclosures

---

## Sources

- LGPD: http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- Lei 13.019/2014 (MROSC): http://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l13019.htm
- Lei 9.790/1999 (OSCIP): http://www.planalto.gov.br/ccivil_03/leis/l9790.htm
- Lei 9.249/95 art. 13 (donor deduction): http://www.planalto.gov.br/ccivil_03/leis/l9249.htm
- ANPD guidance: https://www.gov.br/anpd
- Doare Pix Automático: https://doare.org/artigopixautomatico
