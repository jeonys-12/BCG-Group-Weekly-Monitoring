# Phase 3 공식 source 분석

조사일: 2026-08-12. 공식 HOSE·HNX·SSC host만 사용했다. 정상 브라우저 연결은 Windows sandbox 로그인 오류 1385로 시작되지 않았다. 따라서 기존 사전 분석, 공식 HTML/JavaScript가 노출하는 공개 경로, 비인증 Python `requests` 응답을 교차 확인했다. 인증서 검증을 끄거나 cookie·authorization·session 값을 추출하지 않았다. 공식 bundle은 endpoint 이름 확인에만 일시적으로 사용했으며 내부값은 코드·fixture·문서에 저장하지 않았다.

## HNX

- issuer GET: `https://www.hnx.vn/vi-vn/m-tim-kiem-{BCG|BCR}.html`
- pagination: `POST https://www.hnx.vn/ModuleMobile/MobileIssuer/ChangePageTCB`
- form: `StockCode`, issuer page에서 읽은 `MarketCode`, 1-based `Page`
- 첫 issuer HTML과 POST fragment는 동일 disclosure container/row parser 계약을 사용한다.
- 종료: max pages, 빈 body, 빈 item list, 반복 response SHA-256.
- detail은 issuer row의 공식 상대/절대 URL, attachment는 HNX/CIMS 공식 URL을 absolute URL로 보존한다.
- POST는 `requests.Session.post`를 한 번 호출하며 urllib3 retry adapter의 allowed method는 GET뿐이다.
- 현재 환경 live GET은 BCG·BCR 모두 로컬 CA chain의 `CERTIFICATE_VERIFY_FAILED`로 종료됐다. 검증을 비활성화하지 않았다.

## HOSE

공식 shell `https://www.hsx.vn/vi/thong-tin-cong-bo`는 React이며 현재 공개 bundle이 `https://api.hsx.vn/n/api/v1`의 `/news`, `/news/cate`, `/news/securitiesType/{type}`를 호출한다. collector는 bundle/DOM을 runtime scraping하지 않고 다음 고정 공개 계약만 호출한다.

- method/path: `GET /news/cate`
- query: `pageIndex`, `pageSize`, ISO `startDate`, ISO `endDate`, `aliasCate=thong-tin-cong-bo`, `title=BCG`
- expected JSON: top-level `success=true`; `data.items` 또는 `data.rows`; 선택 `data.totalCount`/`data.total`
- item: `id`, `securityCode`/`issuer`, `title`, `publishDate`/`publishedDate`, 선택 `content`, `number`, `url`, `attachments[].{name,url}`
- 종료: total 교차검증, short/empty page, 반복 response hash, max pages.
- canonical detail URL은 API `url`; 없을 때만 공식 HSX detail pattern을 사용한다. attachment는 official absolute URL로 보존한다.
- JSON content type 또는 필수 key가 없으면 `API_FETCH_OR_SCHEMA_FAILED`다.

2026-08-12의 익명 공식 API 호출은 `/news*` 계열에서 HTTP 404를 반환했다. collector가 이를 `FAILED`로 보존하며 React DOM fallback은 없다.

## SSC

- list GET: `https://ssc.gov.vn/webcenter/portal/ubck/pages_r/l/tintuc?page={1-based}`
- detail GET: `https://ssc.gov.vn/webcenter/portal/ubck/pages_r/l/chitit?dDocName=<DOCUMENT_ID>`
- list schema: `.news-list` 또는 `#list-news` 아래 `dDocName` anchor.
- detail schema: `article`, `.detail-news`, `#detail-news`; title/date/body와 `GET_FILE` 또는 문서 확장자 attachment.
- canonical URL은 `dDocName` query를 유지한다. attachment는 `/cs/idcplg?IdcService=GET_FILE...` 등 공식 SSC URL로 절대화한다.
- list/schema 실패는 `FAILED`; 일부 detail 실패는 `PARTIAL`; entity boundary filter로 `ABCG` 같은 false positive를 제외한다.

현재 비인증 GET은 HTTP 200이지만 Oracle ADF JavaScript loopback shell(6,723 bytes)만 반환해 list marker가 없었다. cookie/session을 재현하지 않고 `LIST_FETCH_OR_SCHEMA_FAILED`로 처리한다.

## Fixture 정책

공식 계약을 최소화한 UTF-8 local fixture 4개(HNX 1, HOSE JSON 1, SSC list/detail 2)를 사용한다. 실제 credential, cookie, authorization, session identifier, 전체 live response는 fixture에 없다. unit test는 injected HTTP fake만 사용하므로 live network call은 0건이다.