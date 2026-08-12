# Phase 2 implementation result

## Phase 1 baseline

- Baseline pytest: 7 passed.
- Approved Master SHA-256 before Phase 2: `A530E4B8F460D05ECDBEB97F27A5A14EFA16D9072D6C3956DA6B41F426BAA732`.
- The Master, report rules, and Excel writer behavior were not changed. Only two unused imports were removed from the writer.
- UTF-8 documents were verified as valid; apparent Korean mojibake can be a PowerShell console-code-page display issue.

## Implemented

- Independent BCG IR and BCG Land IR collectors.
- GET-only retry, timeout, pacing, and User-Agent configuration.
- Raw response/body archive with audit metadata and SHA-256.
- Common schema, URL/text/date normalization, source-derived attachment preservation, and deterministic record IDs.
- Bounded normalized JSON CLI.
- Fixed offline fixtures based on the verified official DOM structures.
- Explicit `SUCCESS`, `PARTIAL`, and `FAILED` behavior with no silent empty parsing success.

## Verification

Bounded live smoke range: 2026-08-06 through 2026-08-07, maximum one page/year endpoint.

- BCG IR: `SUCCESS`, 2 items, 0 errors, 3 visited URLs.
- BCG Land IR: `SUCCESS`, 2 items, 0 errors, 2 visited URLs.
- Raw archive metadata and payload hashes were generated under ignored `work/live-raw` for inspection.
- Default pytest after implementation: 20 passed, 1 skipped integration test.
- Explicit live integration run: 1 passed, 20 deselected.

## Known source risks

- BCG CSS classes, year slugs, or `pagenumber` may change.
- BCG Land depends on public year endpoints and the AJAX response marker `.slide-report`.
- BCG Land rows link directly to PDFs; Phase 2 preserves the PDF and list text but does not extract PDF body text.
- Official sites can rate-limit or temporarily fail; bounded retries may still yield `PARTIAL`/`FAILED`.
- Raw archives grow over time and need a retention policy before scheduled operation.

## Before Phase 3

- Confirm official HOSE/HNX/SSC source endpoints and usage restrictions.
- Decide raw-archive retention and whether PDF binaries should be downloaded or only referenced.
- Decide whether BCG Land PDF text extraction belongs in Phase 3 or a Phase 2 hardening pass.
- Initialize and publish the currently empty GitHub repository only with explicit user approval.

No commit, push, or pull request was created.