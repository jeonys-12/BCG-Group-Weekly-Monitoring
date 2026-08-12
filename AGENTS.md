# Development Rules

These rules apply to the entire repository.

1. Implement only the requested phase. Do not add collectors, AI classification, or scraping during Phase 1.
2. Treat every workbook in `reports/template/` as immutable input. Never save over a master template.
3. Write generated workbooks only to `reports/output/`, using a new filename.
4. Preserve all historical cell values, formulas, styles, merges, dimensions, print settings, and workbook metadata unless a requirement explicitly targets them.
5. Insert trend rows immediately before the HNX/HOSE/SSC institution-note block. If anchors are missing or ambiguous, fail loudly instead of guessing.
6. Keep workbook layout anchors in `config/report_rules.yaml`; do not scatter row or cell coordinates through code.
7. Use source-derived facts only. Preserve source names and URLs. Never invent facts or impact conclusions.
8. Keep dummy data under `tests/fixtures/`; production modules must not contain sample records.
9. Every Excel change requires regression tests for historical values, section movement, merges, dimensions, styles, borders, wrapping, and reopenability.
10. Prefer small, typed functions and explicit exceptions. Never silently recover from a malformed template.
11. `.xlsb` files are analysis-only inputs in Phase 1. Convert and approve an `.xlsx` master before writing.
12. Run the complete pytest suite before handing off changes.
13. Phase 2 collects only official BCG IR and BCG Land IR disclosures. Do not add exchange, regulator, media, deduplication, classification, summary, impact-analysis, Excel integration, or workflow features.
14. Archive every live HTTP response with audit metadata, but never store cookies, authorization headers, or other secrets.
15. Treat list/schema failures as explicit collector errors. Never convert a parsing failure into a successful empty result.
16. Unit tests must use fixed local fixtures and make zero live network calls. Mark optional live smoke checks separately.
17. Normalized IDs must be deterministic and must not depend on collection time, page position, or local file paths.