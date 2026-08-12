# Official source analysis for Phase 2

Investigation date: 2026-08-12

## Bamboo Capital Group (BCG IR)

Official list: https://bamboocap.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/2026

- Method: normal `GET` returning server-rendered `text/html`.
- List marker: `.congbothongtin-list:not(.detail)`.
- Item fields: `li > a[href]` for title/detail URL and sibling `time` for `DD/MM/YYYY`.
- Pagination: `GET` with query parameter `pagenumber`; for example `?pagenumber=2`.
- Detail marker: `.congbothongtin-list.detail`.
- Detail fields: `h2.title-child`, `h3` date, `.content` paragraphs, and official document anchors inside `.content`.
- Stop condition: discovered numeric page links capped by configured `max_pages`.

The collector treats a missing list/detail marker as a schema error. A failed detail produces a `PARTIAL` result while preserving a source-derived fallback record from the successful list row.

## BCG Land (BCG Land IR)

Official shell: https://www.bcgland.com.vn/vi/quan-he-dau-tu/cong-bo-thong-tin

The initial HTML contains year controls but leaves `.load-report` empty. The official `app.js` function `LoadReport` performs a jQuery AJAX GET to each year control's `data-href`.

- Endpoint method: `GET`.
- Endpoint URL: `https://www.bcgland.com.vn/vi/quan-he-dau-tu/cong-bo-thong-tin/{year}`.
- Required request signal: `X-Requested-With: XMLHttpRequest`, matching jQuery AJAX behavior.
- Query/body parameters: none.
- Pagination: year endpoint selection; the returned fragment contains all rows grouped into visual `.group-box` slides and exposes no additional server-page parameter.
- Response content type/schema: HTML fragment rooted at `.slide-report`; each `.list-box` has an anchor, `.date`, and `.r-text p`.
- Detail/attachment URL: the row anchor is normally a direct official PDF URL, so it is retained as both canonical record URL and attachment URL.

A static shell without year controls or an AJAX response without `.slide-report` is an explicit collector failure, not zero disclosures.

## Investigation method and limitation

The in-app browser could not start because the Windows sandbox helper returned login error 1385. The same public network behavior was therefore verified read-only from the official HTML, the site's official `app.js`, and a bounded AJAX-header request. No authentication, cookies, bypass, or aggressive crawling was used.