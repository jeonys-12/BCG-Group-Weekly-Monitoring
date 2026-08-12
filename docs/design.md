# Architecture and data flow

## Scope

Phase 1 is limited to a safe Excel report engine. The repository was initially empty. The authoritative 20260812_BCG 그룹 동향 보고.xlsb was subsequently supplied and analyzed through Microsoft Excel in read-only mode.

## Architecture

    approved XLSB reference
            |
            v
    Excel COM snapshot -> DRM-free XLSX Master
            |
            v
    excel_template_analyzer.py -> JSON structure report / anchor review
            |
            v
    report_rules.yaml + validated monitoring items
            |
            v
    excel_writer.py -> new XLSX report (Master is never overwritten)
            |
            v
    pytest integrity gates + reopen and visual checks

- src/excel_template_analyzer.py inventories sheets, used ranges, merged cells, dimensions, style distribution, current trend data range, institution notes, and impact-analysis anchors.
- src/excel_writer.py validates anchors, sorts only the new records by date, inserts them before the institution-note block, copies the immediately preceding data-row formatting, shifts row metadata, updates the configured report-date cell, and saves to a different path.
- config/report_rules.yaml contains layout anchors so template revisions do not require source edits.
- tests include both a small structural fixture and regression checks against the real Master.

## Preservation strategy

Before editing, tests record historical cell values, styles, dimensions, merges, and the Master file hash. The writer refuses to proceed when the trend section, impact section, institution block, or source style row cannot be identified uniquely. New rows are inserted at the ordered HNX, HOSE, SSC explanation block. Cell styles and downstream cells move with the insertion; row height and hidden/outline metadata are shifted explicitly because openpyxl insert_rows does not move row dimensions.

The writer changes only:

1. the configured report-date cell;
2. newly inserted rows;
3. coordinates of content below the insertion point as a consequence of insertion.

Historical trend values are never sorted or rewritten. Only the new records are sorted among themselves.

## XLSB, DRM, and XLSX Master policy

Direct XLSB editing is not suitable for a portable Python engine. openpyxl cannot serialize binary workbooks, while pyxlsb is reading-oriented and does not provide high-fidelity style, drawing, merge, print-layout, macro, and relationship round-tripping.

The supplied file also has a SoftCamp DRM envelope with an SCDSA002 signature. Even Excel SaveAs to format 51 produced an encrypted XLSX that was not an OOXML ZIP package and could not be opened by openpyxl or GitHub Actions. Phase 1 therefore uses a controlled one-time extraction path:

1. Excel opens the XLSB read-only with macros disabled.
2. scripts/extract_xlsb_template.ps1 records values, styles, borders, alignment, dimensions, sheet view, and page setup.
3. scripts/build_master_from_snapshot.py creates the DRM-free OOXML Master.
4. Python analysis and regression tests verify the Master before use.

The actual workbook contains no VBA, shapes, hyperlinks, conditional formatting, formulas, or merged cells, which materially reduces reconstruction risk. The reconstruction script stops when the snapshot reports unsupported high-risk features.

## Verified template map

- Sheet: BCG 동향
- Used range: A1:D55
- Report date: D2
- Trend section label: row 3
- Headers: row 4
- Existing trend data: A5:D37
- Institution explanations: rows 38-40 (HNX, HOSE, SSC)
- Impact analysis label: row 42
- Impact analysis text: rows 43-44
- Column widths: A 15.25, B 15.25, C 75.75, D 24.25
- Merged cells: none
- New-row style source: row 37

## Visual validation limitation

SoftCamp blocks clipboard image capture and wraps Excel-exported PDF files, so an automated pixel comparison against the protected source is unavailable. Structural and style properties are instead captured through Excel COM and checked through Python regression tests. The final DRM-free XLSX is rendered and visually inspected independently. A human Excel review remains recommended before operational adoption.

## Later-phase data flow

Phases 2-5 will feed normalized, traceable monitoring records to this engine. Phase 6 orchestrates execution and artifacts. Phase 7 adds operational hardening. Raw source facts and generated analysis remain separate; every included item retains its source URL in the archive even though the current four-column report has no URL column.
## Phase 2 collection architecture

    official BCG/BCG Land IR endpoints
                    |
                    v
        bounded HTTPClient (GET retry + pacing)
             |                       |
             v                       v
      immutable raw archive     source collectors
      response + metadata        list/detail/PDF
                                      |
                                      v
                         source-preserving normalize
                         deterministic SHA-256 ID
                                      |
                                      v
                          bounded normalized JSON CLI

`src/http_client.py` retries only idempotent GET requests for transient network errors, HTTP 429, and selected 5xx responses. `src/archive.py` stores response bytes plus URL, method, status, timestamp, content type, encoding, length, and SHA-256 without request cookies or authorization data. `src/collectors/bcg_ir.py` parses the server-rendered BCG list, detail body, and attachments. `src/collectors/bcg_land_ir.py` validates the public shell and calls its year-specific AJAX HTML-fragment endpoint with `X-Requested-With: XMLHttpRequest`.

Both collectors emit the common contract in `src/models.py` through `src/normalize.py`. Collection timestamps are excluded from record identity, so the same official item receives the same ID on repeat runs. Phase 2 stops at normalized JSON and does not invoke the Excel writer.