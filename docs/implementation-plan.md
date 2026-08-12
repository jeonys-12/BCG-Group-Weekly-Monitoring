# Implementation plan

> **Scope decision (2026-08-12):** HNX, HOSE, and SSC monitoring is excluded. This decision supersedes the Phase 3 exchange/regulator section below. Do not implement or enable those collectors. Preserve the existing HNX/HOSE/SSC institution-note rows in the Excel template because they are report layout content. The active collection scope remains BCG IR and BCG Land IR.

Phase 3 acceptance is therefore limited to confirming that no exchange/regulator collector, endpoint, fixture, live test, or CLI integration is present and that Phase 1 Excel and Phase 2 IR behavior remain unchanged.

> **Operating decision (2026-08-12):** The owner's PC and Windows Task Scheduler are the initial Phase 6 deployment target. It runs Monday at 07:00 local time, uses the prior completed Monday-Sunday window, and writes to a user-selected local folder. GitHub Actions remains a later optional deployment alternative.

## Phase 1 — Excel report engine

Deliver repository scaffold, immutable-template rules, analyzer, conservative writer, three-record dummy input, and integrity tests.

Acceptance criteria:

- Analyzer reports sheet list, used range, merges, column widths, row heights, styles, trend range, institution-note location, and impact-section location.
- Writer inserts date-sorted new records directly above the institution-note block without rewriting historical records.
- Downstream notes and impact analysis move by exactly the inserted-row count.
- Source-row styles, borders, wrap settings, dimensions, and merge pattern are retained.
- Output reopens with `openpyxl`; all tests pass.
- Approved production template is visually inspected before production acceptance.

## Phase 2 — BCG and BCG Land official collectors

Implement independent IR collectors and a common normalized schema; archive raw responses and source URLs.

Acceptance criteria:

- Both collectors parse representative saved official responses.
- Network/parser failures are explicit and raw payloads remain auditable.
- Normalized records contain all required schema fields and deterministic IDs.

## Phase 3 — HOSE, HNX, and SSC collectors

Implement exchange/regulator adapters without changing Phase 1 report contracts.

Acceptance criteria:

- Each adapter has offline fixtures and parser tests.
- Official document number, publication date, issuer, title, and URL are retained.
- One source failure does not discard successful source results.

## Phase 4 — Deduplication and classification

Add layered duplicate checks, A/B/C importance, Hanwha relevance, and risk direction with review states.

Acceptance criteria:

- Exact URL/document/title matches are deterministic.
- Similarity 85–94 is REVIEW; automatic duplicate decisions are auditable.
- Official sources win over media for the same event.
- Unsupported impact conclusions remain UNCERTAIN.

## Phase 5 — Korean summary and impact analysis

Generate source-grounded Korean summaries and concise impact analysis, clearly separating facts from analysis.

Acceptance criteria:

- Every factual statement maps to archived source material.
- Summary length and tone follow the specification.
- Impact text is conservative, 2–4 sentences, and flags insufficient evidence.
- Human-review candidates are exported separately.

## Phase 6 — GitHub Actions operation

Add Monday 07:00 KST scheduling, manual dispatch, configurable artifact/commit output, and report archival.

Acceptance criteria:

- Scheduled cron uses the correct UTC conversion and manual dispatch works.
- Tests run before artifact publication.
- Partial-source success emits a report with `PARTIAL` status; all-source failure blocks it.
- Secrets and generated artifacts follow repository policy.

## Phase 7 — Hardening and operations

Complete logging, retry/error summaries, end-to-end tests, README operations, retention, and recovery guidance.

Acceptance criteria:

- A non-developer can run, review, and recover the workflow from README instructions.
- History records explain discovered, duplicate, excluded, included, and failed items.
- End-to-end tests cover partial failure and repeat-run idempotency.
- Release quality gates and production-template visual checks are documented and passing.
