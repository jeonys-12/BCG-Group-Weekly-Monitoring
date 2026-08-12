# Phase 3 Codex 작업지시서

## 1. 작업 목적

Phase 2에서 구축한 공통 HTTP, raw archive, normalize, deterministic ID, collector result 기반을 그대로 사용하여 다음 공식 기관의 공시 수집기를 구현한다.

- 호찌민증권거래소(`HOSE`)
- 하노이증권거래소(`HNX`)
- 베트남 국가증권위원회(`SSC`)

이번 단계의 최종 산출물은 **공식 거래소·감독기관 원문을 수집하여 기존 normalized JSON schema로 저장하는 파이프라인**이다. 중복 제거, 중요도 분류, 한국어 번역·요약, 영향도 분석, Excel 반영, GitHub Actions는 구현하지 않는다.

---

## 2. 시작 기준과 현재 baseline

1. 작업 시작 전 다음 문서를 전체 읽는다.
   - `AGENTS.md`
   - `PROJECT_SPEC.md`
   - `docs/design.md`
   - `docs/implementation-plan.md`
   - `docs/source-analysis.md`
   - `docs/phase-2-result.md`
   - 이 문서
2. `main`의 Phase 1·2 baseline은 다음과 같다.
   - 전체 pytest: `20 passed, 1 skipped`
   - 선택적 live integration smoke test: `1 passed`
   - Master workbook SHA-256: `A530E4B8F460D05ECDBEB97F27A5A14EFA16D9072D6C3956DA6B41F426BAA732`
3. 구현 전 전체 pytest와 Master hash를 다시 확인하고 결과를 기록한다.
4. 작업은 최신 `main`에서 `codex/` 접두사의 별도 브랜치를 만들어 진행한다.
5. Phase 3 때문에 `reports/template/BCG_Group_Trend_Master.xlsx`, `src/excel_writer.py`, `config/report_rules.yaml`을 변경하지 않는다.
6. 기존 Phase 2 collector와 공통 계약을 불필요하게 깨지 않는다. 공통 모듈 변경이 필요하면 기존 테스트를 먼저 보강한다.

---

## 3. 범위

### 포함

- HOSE의 BCG 관련 공식 공시와 거래소 결정
- HNX의 BCG·BCR 발행인 공시와 거래소 결정
- SSC의 BCG Group·BCG Land 및 관련 법인에 관한 감독·제재·인가·공모 공시
- 공식 list/API 응답, detail 본문, 첨부파일 URL 수집
- 기존 raw archive와 normalized schema 연동
- 고정 fixture 기반 unit test
- 좁은 날짜 범위·최대 1페이지의 선택적 live smoke test
- 소스별 접근 계약과 위험요소 문서화

### 제외

- 언론 기사·SNS·검색엔진 결과 수집
- fuzzy duplicate 처리 또는 source 간 병합
- 중요도 A/B/C, category, risk direction 자동 판정
- 한국어 번역·요약·영향도 분석
- Excel 보고서 쓰기
- 주간 스케줄러와 GitHub Actions
- CAPTCHA, 인증, 차단 또는 접근통제를 우회하는 수집
- HOSE 시세·주문·일반 시장 데이터 수집

Phase 2 IR과 Phase 3 거래소 공시가 같은 문서를 제공할 수 있다. Phase 3에서는 각 공식 source의 record를 그대로 보존하고 source별 deterministic ID를 생성한다. source 간 중복 처리는 Phase 4로 미룬다.

---

## 4. 사전 공식 source 분석 결과

### 4.1 HNX

- BCG 발행인 페이지: `https://www.hnx.vn/vi-vn/m-tim-kiem-BCG.html`
- BCR 발행인 페이지: `https://www.hnx.vn/vi-vn/m-tim-kiem-BCR.html`
- 공개 공시 포털: `https://portal.hnx.vn/vi-vn/thong-tin-cong-bo-up-hnx.html`
- BCR 종목 정보: `https://web02.hnx.vn/cophieu-etfs/chi-tiet-chung-khoan-etf-bcr.html`
- 종목 페이지 경로는 `/m-tim-kiem-{StockCode}.html` 패턴이다.
- 발행인 공시 pagination은 현재 다음 read-only form POST를 사용한다.

```text
POST /ModuleMobile/MobileIssuer/ChangePageTCB
StockCode=<BCG|BCR>
MarketCode=<페이지에서 읽은 값>
Page=<1-based page>
```

- 조사 시 BCG 페이지의 `MarketCode`는 `UC`였지만 이를 production code에 영구 상수로 박지 않는다. 최초 공식 페이지에서 값을 읽거나 source configuration으로 명시하고 페이지 값과 교차 검증한다.
- HNX의 공시 첨부 링크는 공식 CIMS 등 별도 host를 가리킬 수 있으므로 official host allowlist를 문서화하고 absolute URL을 보존한다.

### 4.2 HOSE

- 공식 사이트: `https://www.hsx.vn/`
- 공식 공시 화면: `https://www.hsx.vn/vi/thong-tin-cong-bo`
- 공식 공시 규정 화면: `https://www.hsx.vn/vi/quy-dinh-hose/cong-bo-thong-tin`
- 현재 화면은 React shell이며 브라우저 JavaScript가 공식 API를 호출한다.
- 사전 조사에서 공개 API 계열은 `https://api.hsx.vn/n/api/v1`이며 공시 목록은 `/news`, `/news/cate`, `/news/securitiesType/{type}` 계열을 사용한다. `pageIndex`, `pageSize`, `startDate`, `endDate`, `title` 등의 query가 관찰됐지만, 구현 전에 실제 브라우저 network 요청으로 정확한 request/response 계약을 다시 확인해야 한다.
- runtime collector가 React bundle을 매번 내려받아 문자열을 분석하거나 렌더링된 DOM을 긁도록 만들지 않는다. 한 번 검증한 공개 API 계약을 fixture와 문서로 고정하고 `requests`로 호출한다.
- 공개 bundle에 포함된 내부 값, 비밀번호처럼 보이는 문자열, authorization 값 또는 session 정보를 코드·fixture·문서에 복사하거나 커밋하지 않는다. 필요한 공개 header가 있다면 브라우저의 정상 공시 요청에서 최소 항목만 확인하고 비밀정보가 아님을 검토한다.

### 4.3 SSC

- 공식 포털: `https://ssc.gov.vn/`
- 공식 detail URL은 현재 다음 패턴을 사용한다.

```text
https://ssc.gov.vn/webcenter/portal/ubck/pages_r/l/chitit?dDocName=<DOCUMENT_ID>
```

- 예시로 BCG Land 관련 공식 제재 결정 detail이 이 패턴에서 확인됐다.
- SSC는 Oracle WebCenter 기반 동적 목록일 수 있으므로 list/search 요청을 브라우저 network에서 한 번 조사하고 정확한 endpoint, method, parameter, pagination, response schema를 `docs/source-analysis-phase3.md`에 기록한다.
- Windows `curl`의 Schannel 오류는 특정 클라이언트/TLS 환경 문제일 수 있으며 source 자체의 장애나 공시 0건을 의미하지 않는다. Python `requests`와 정상 브라우저를 각각 확인하여 원인을 구분한다. 인증서 검증을 끄는 방식으로 해결하지 않는다.

---

## 5. 개발 규칙

1. 공식 HOSE·HNX·SSC 도메인과 공식 첨부파일 host만 사용한다.
2. 검색엔진은 source endpoint 발견 보조에만 사용할 수 있고, 검색 결과 snippet을 record 원문으로 저장하지 않는다.
3. list/schema parsing 실패를 빈 성공 결과로 바꾸지 않는다.
4. 필수 항목이 없는 item은 명시적 item error로 기록한다.
5. 원문 title, body, document number, URL, attachment label/URL을 훼손하지 않는다.
6. 번역, 요약, 중요도, 관련성, 위험 방향을 추측하지 않는다.
7. 모든 live HTTP 응답은 기존 archive 정책에 따라 저장하되 cookie, authorization, API key, session identifier, 개인 데이터를 저장하지 않는다.
8. unit test는 고정 local fixture만 사용하고 live network call은 0건이어야 한다.
9. retry는 기존 정책대로 idempotent GET의 일시 오류에만 적용한다.
10. HNX pagination POST는 조회 전용이지만 기본적으로 자동 retry하지 않는다. 안전한 재시도를 추가하려면 해당 endpoint가 side effect 없는 조회임을 문서화하고, 별도 명시 옵션과 작은 retry 횟수로 제한한다.
11. 각 source에 timeout, request interval, max pages를 적용한다.
12. 공식 API나 schema가 바뀌면 조용히 fallback scraping하지 말고 `FAILED` 또는 `PARTIAL`과 구조화된 error를 반환한다.
13. 한 source 실패가 다른 source 결과를 지우지 않게 source별 결과를 독립 보존한다.
14. production module에 dummy item, 실제 response 전문, 비밀값을 넣지 않는다.
15. 한국어 Markdown은 UTF-8로 저장하고 `U+FFFD`가 새로 생기지 않았는지 검사한다.

---

## 6. 권장 directory와 변경 파일

```text
config/
├── sources.yaml                    # HOSE/HNX/SSC endpoint와 제한 추가
└── keywords.yaml                   # entity·ticker seed만 추가

src/
├── http_client.py                  # 필요 시 명시적 form POST 지원
├── collectors/
│   ├── hose.py
│   ├── hnx.py
│   └── ssc.py
└── main.py                         # 새 collector 선택·통합

tests/
├── fixtures/collectors/
│   ├── hose/
│   ├── hnx/
│   └── ssc/
├── test_hose_collector.py
├── test_hnx_collector.py
├── test_ssc_collector.py
└── test_phase3_cli.py

docs/
├── source-analysis-phase3.md
└── phase-3-result.md
```

기존 구조와 이름이 이미 같은 역할을 수행하면 중복 모듈을 만들지 않는다. `requirements.txt`에는 실제 production/test code가 사용하는 최소 dependency만 추가한다. Playwright나 Selenium은 `requests`로 공식 공개 endpoint를 재현할 수 없다는 증거가 있을 때만 검토하며 기본 dependency로 추가하지 않는다.

---

## 7. configuration 계약

기존 `config/sources.yaml` 형식을 유지하면서 최소 다음 정보를 추가한다. 실제 key 이름은 현재 loader와 일치시킨다.

```yaml
sources:
  hnx:
    enabled: true
    base_url: "https://www.hnx.vn"
    issuer_page_template: "https://www.hnx.vn/vi-vn/m-tim-kiem-{ticker}.html"
    disclosure_page_path: "/ModuleMobile/MobileIssuer/ChangePageTCB"
    tickers: ["BCG", "BCR"]
    max_pages: 10

  hose:
    enabled: true
    base_url: "https://www.hsx.vn"
    api_base_url: "https://api.hsx.vn/n/api/v1"
    tickers: ["BCG"]
    max_pages: 10

  ssc:
    enabled: true
    base_url: "https://ssc.gov.vn"
    max_pages: 10
```

- 현재 상장 시장과 ticker 관계는 바뀔 수 있다. 실행 시 공식 source 정보와 configuration을 교차 검증하고, BCG가 어느 거래소에 있다는 가정을 코드 전체에 분산시키지 않는다.
- entity seed는 최소 `BCG`, `Bamboo Capital`, `BCG Land`, `BCR`을 포함한다.
- `Sao Sang Sai Gon`/`SSSG` 같은 관련 법인은 감독기관 원문에서 BCG 관계가 명시되거나 프로젝트 spec의 범위와 명확히 연결될 때만 SSC 필터 seed로 사용한다.

---

## 8. 공통 data 계약

Phase 2의 normalized record key를 추가·삭제·이름 변경하지 않는다.

- HOSE와 HNX:
  - `source`: `HOSE` 또는 `HNX`
  - `source_type`: `EXCHANGE`
- SSC:
  - `source`: `SSC`
  - `source_type`: `REGULATOR`
- `company`는 source의 issuer/ticker 또는 원문에서 확인된 `BCG`, `BCG Land` 등 검증 가능한 entity를 사용한다.
- 단순 keyword hit만 있고 대상 회사가 불명확하면 억지로 회사를 추정하지 말고 item error/review 가능한 보수적 처리 규칙을 문서화한다.
- `title_original`과 `content_original`은 베트남어 원문을 보존한다.
- `title_ko`, `summary_ko`, `category`, `importance`, relevance와 risk field는 Phase 3에서 채우지 않는다.
- `url`은 canonical official detail URL이다. detail URL이 존재하지 않는 공식 API item만 검증된 list permalink를 사용할 수 있다.
- `attachments`는 label, absolute URL, 확인 가능한 content type만 기록한다.

ID는 기존 공식을 그대로 사용한다.

```text
sha256(stable serialization(
  source + canonical URL + document number + published date + original title
))
```

수집 시각, 페이지 번호, local archive 경로, API response 순서는 ID에 포함하지 않는다.

---

## 9. source별 구현 요구사항

### 9.1 HNX collector

1. BCG와 BCR issuer page를 각각 독립 수집한다.
2. 최초 page에서 ticker와 market code를 검증한다.
3. 첫 page의 server-rendered disclosure list와 이후 `ChangePageTCB` response를 동일 parser 계약으로 처리한다.
4. page 번호 증가, 마지막 page, 빈 response, 반복 page hash를 모두 종료 조건에 포함한다.
5. title, published date/time, issuer/ticker, detail URL, attachment URL을 추출한다.
6. 상대 URL은 source origin 또는 검증된 official attachment host 기준으로 absolute URL로 바꾼다.
7. 한 ticker 실패 시 다른 ticker를 계속 수집하고 전체 결과는 `PARTIAL`로 반환한다.
8. portal 결과는 issuer page 누락 여부의 분석·smoke cross-check에 사용할 수 있지만 같은 item을 Phase 3에서 병합하지 않는다.

### 9.2 HOSE collector

1. 정상 브라우저에서 공식 공시 화면의 network 요청을 확인한다.
2. endpoint, method, 필수 query, 날짜 형식, pagination, response key, attachment/detail URL 규칙을 문서화한다.
3. BCG ticker 또는 원문 entity 조건으로 관련 공시와 거래소 결정을 수집한다.
4. BCG의 과거 상장·거래정지·상장폐지·시장 이전 같은 전환 공시를 날짜 범위 안에서 보존한다.
5. 일반 지수, 호가, 가격, 전체 시장 뉴스는 수집하지 않는다.
6. API가 total count를 제공하면 page 종료와 교차 검증하고, 제공하지 않으면 page length와 반복 hash를 함께 사용한다.
7. API response key 누락, content type 변경, 인증 요구로 전환되면 explicit collector error를 반환한다.
8. runtime code가 minified JavaScript bundle을 endpoint discovery 용도로 해석하지 않게 한다.

### 9.3 SSC collector

1. 공식 list/search endpoint 계약을 먼저 조사한다.
2. date range와 entity keyword를 source가 지원하면 server-side parameter로 적용하고, 결과에도 client-side 보수 필터를 적용한다.
3. detail page에서 title, published date, decision/document number, body, 대상 entity, attachment URL을 추출한다.
4. `dDocName` query를 보존한 canonical official URL을 사용한다.
5. 제재·과징금·공시위반·등록/인가·공모/발행 관련 문서를 범위에 포함한다.
6. 단순히 BCG 문자열이 다른 의미로 등장한 false positive를 제외할 수 있도록 title/body entity 문맥을 검증한다.
7. list 성공 후 일부 detail 실패는 `PARTIAL`, list/search 계약 실패는 `FAILED`다.
8. TLS/Schannel 오류, timeout, HTTP 오류, schema 오류를 서로 다른 error type/message로 남긴다.

---

## 10. HTTP와 raw archive 요구사항

- 기존 shared session, timeout, rate limit, GET retry 정책을 재사용한다.
- form POST가 필요하면 `HttpClient`에 목적이 명확한 작은 method를 추가하고 method, URL, form key 이름, status, response hash를 archive metadata에 남긴다.
- archive metadata에 request body의 값 전체를 무조건 저장하지 않는다. 공개 pagination parameter만 allowlist로 남기고 secret/cookie/header는 제외한다.
- JSON과 HTML response 모두 원본 bytes hash와 byte length가 일치해야 한다.
- attachment는 Phase 3 acceptance에 binary download가 필수는 아니다. URL과 metadata를 보존하되 다운로드를 구현한다면 크기 제한, content type, streaming, hash test를 추가한다.
- HTTP 200이더라도 login page, access denied HTML, 예상치 못한 shell이면 성공으로 처리하지 않는다.

---

## 11. 필수 fixture와 테스트

### HNX

- BCG issuer 첫 page parser
- BCR issuer 첫 page parser
- `MarketCode` 추출과 request form 생성
- pagination 2 page 이상과 종료 조건
- title/date/detail/attachment absolute URL
- date range 필터
- 동일 page 반복 방지
- 한 ticker 실패 시 `PARTIAL`과 다른 ticker 결과 보존
- markup/schema 변경 시 explicit error
- POST가 기본 retry되지 않는지 확인

### HOSE

- 공식 API를 익명화·최소화한 JSON fixture parser
- page/total 종료 조건
- BCG ticker/entity 필터
- 상장폐지·거래상태·시장 이전 같은 exchange decision 보존
- detail/attachment URL canonicalization
- 일반 시장 데이터 제외
- 필수 response key 누락과 content type 변경 시 explicit error
- fixture에 cookie, authorization, 내부 credential이 없다는 검사

### SSC

- list/search fixture parser
- `dDocName` detail URL 보존
- detail title/date/document number/body/attachment 추출
- BCG와 BCG Land entity 필터
- false-positive keyword 제외
- 일부 detail 실패 시 `PARTIAL`
- TLS/network 실패와 schema 실패 구분
- 제재 결정 예시가 normalized schema에 안정적으로 매핑되는지 확인

### 공통·회귀

- 세 collector가 기존 `CollectorResult`/normalized model 계약을 준수한다.
- 동일 input의 deterministic ID가 반복 실행에도 같다.
- source_type과 source 값이 정확하다.
- raw archive hash/metadata가 실제 response와 일치한다.
- unit test에서 live network call이 0건이다.
- Phase 1·2 전체 테스트가 통과한다.
- Master workbook hash가 baseline과 같다.
- 한국어 Markdown UTF-8과 `U+FFFD` 부재를 검사한다.

Optional live smoke test는 `integration` marker로 분리하고 기본 pytest에서는 skip한다. 각 source별 최대 1 page, 좁은 날짜 범위, 낮은 요청 빈도로 실행한다. live test 실패가 website 변경인지 로컬 network 제한인지 결과 문서에서 구분한다.

---

## 12. 구현 순서

1. 문서 전체와 repository 상태를 확인한다.
2. 전체 pytest, 선택적 integration baseline, Master hash를 기록한다.
3. `docs/source-analysis-phase3.md`에 HNX·HOSE·SSC 실제 request/response 계약을 작성한다.
4. source analysis 과정에서 얻은 response를 최소·익명화 fixture로 만든다.
5. configuration과 source/entity seed를 추가한다.
6. 필요하면 공통 HTTP client에 안전한 form POST와 archive metadata 지원을 추가하고 먼저 단위 테스트한다.
7. HNX collector와 테스트를 구현한다.
8. HOSE collector와 테스트를 구현한다.
9. SSC collector와 테스트를 구현한다.
10. 기존 CLI에 세 collector를 선택 가능하게 연결하되 Excel writer에는 연결하지 않는다.
11. fixture 기반 Phase 3 end-to-end CLI test를 추가한다.
12. 좁은 optional live smoke test를 실행한다.
13. 전체 pytest와 Master hash를 다시 검증한다.
14. `docs/phase-3-result.md`에 결과·제약·Phase 4 확인사항을 기록한다.

구현 중 공식 endpoint를 확정할 수 없으면 결과를 만들어내기 위한 임의 selector나 비공식 mirror를 추가하지 않는다. 조사 근거, 실패 단계, 재현 방법을 기록하고 해당 collector를 명시적 `FAILED` 상태로 둔다.

---

## 13. acceptance criteria

- [ ] 작업 전후 전체 pytest가 통과하고 결과가 기록됐다.
- [ ] Master workbook hash가 baseline과 같다.
- [ ] HOSE, HNX, SSC의 공식 request/response 계약이 문서화됐다.
- [ ] 각 source collector가 기존 공통 interface와 normalized schema를 사용한다.
- [ ] HNX가 BCG와 BCR issuer 공시를 pagination 포함 수집한다.
- [ ] HOSE가 공식 공개 API를 사용해 BCG 관련 공시·거래소 결정을 수집한다.
- [ ] SSC가 공식 list/detail에서 관련 감독·제재 문서를 수집한다.
- [ ] 모든 정상 record에 date, source, title, canonical official URL이 있다.
- [ ] 원문과 attachment URL이 보존된다.
- [ ] deterministic ID가 반복 실행에 안정적이다.
- [ ] raw archive에 audit metadata와 hash가 있으며 secret이 없다.
- [ ] parser/schema/network 실패가 silent empty success로 처리되지 않는다.
- [ ] 한 source/ticker 실패 시 이미 수집한 다른 결과가 보존된다.
- [ ] unit test가 local fixture만 사용한다.
- [ ] optional live smoke 결과 또는 실행 불가 사유가 기록됐다.
- [ ] Phase 2 IR collector와 Phase 1 Excel regression이 깨지지 않았다.
- [ ] 중복 제거·분류·요약·Excel·Actions 등 Phase 4 이후 기능이 포함되지 않았다.

---

## 14. 완료 보고 형식

작업 완료 후 다음을 보고한다.

1. 시작 branch/commit과 baseline pytest·Master hash
2. 생성·변경한 파일
3. source별 실제 endpoint, method, pagination, detail/attachment 방식
4. 구현한 수집·정규화·archive 기능
5. fixture 수와 source별 test 결과
6. optional live smoke 결과
7. 전체 pytest 결과와 Master hash 재검증
8. 발견된 source/API/TLS/schema 위험요소
9. 실패 또는 제한된 기능과 재현 방법
10. Phase 4 전에 결정해야 할 source 간 중복·entity mapping 사항

---

## 15. Codex에 그대로 전달할 실행 prompt

```text
반드시 AGENTS.md, PROJECT_SPEC.md, docs/design.md, docs/implementation-plan.md,
docs/source-analysis.md, docs/phase-2-result.md,
docs/phase-3-codex-instructions.md 전체를 먼저 읽어라.

이번 작업은 Phase 3만 구현한다. 최신 main에서 codex/ 접두사의 별도 branch를 만들고,
작업 전 전체 pytest와 Master workbook SHA-256을 기록하라. Phase 1 Excel template/writer와
Phase 2 BCG IR·BCG Land IR collector의 기존 계약을 보존하라.

HOSE, HNX, SSC의 공식 source만 사용하여 공시 collector를 실제 코드로 구현하라.
먼저 정상 브라우저의 network와 공식 응답을 조사하여 endpoint, method, parameter,
pagination, response schema, detail·attachment URL 규칙을 docs/source-analysis-phase3.md에
기록하라. HNX는 BCG·BCR issuer page와 ChangePageTCB 조회 계약을 검증하고, HOSE는
React DOM이나 bundle runtime scraping 대신 검증된 공식 공개 API를 사용하라. SSC는
WebCenter list/detail 계약과 dDocName URL을 검증하라. 공개 bundle에서 발견되는 내부값,
cookie, authorization, session, credential은 코드·fixture·문서에 저장하지 마라.

기존 공통 HTTP, archive, normalize, deterministic ID, CollectorResult를 재사용하라.
HNX의 조회용 POST는 기본 자동 retry를 금지하고, parser/schema/network 실패를 빈 성공으로
처리하지 마라. 고정 local fixture 기반 unit test와 좁은 integration smoke test를 작성하라.
unit test에서는 live network call이 0건이어야 한다.

중복 제거, 중요도·관련성·risk 분류, 번역·요약, 영향도 분석, Excel 반영, GitHub Actions,
언론 수집은 구현하지 마라. 전체 pytest를 실행하여 실패를 수정하고 Master hash 불변을
확인한 뒤 docs/phase-3-result.md에 생성·변경 파일, 실제 source 계약, 구현 기능, 테스트,
위험요소, Phase 4 전 확인사항을 보고하라.
```
