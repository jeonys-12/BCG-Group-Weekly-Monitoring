# Phase 2 Codex 작업지시서

## 1. 작업 목적

Phase 1에서 완성한 Excel report engine을 변경하지 않고, 다음 두 공식 IR 출처에서 공시 목록과 상세 자료를 수집하여 공통 schema로 정규화하는 기반을 구현한다.

- Bamboo Capital Group (`BCG IR`)
- BCG Land (`BCG Land IR`)

이번 단계의 최종 산출물은 **공식 페이지 → raw archive → normalized JSON** 파이프라인이다. Excel 반영, 중복 제거, 중요도 분류, 한국어 요약, 영향도 분석, GitHub Actions는 구현하지 않는다.

---

## 2. Phase 1 검토 결과

### 통과한 항목

- 실제 `BCG 동향` Master 구조를 분석하고 DRM-free `.xlsx` Master를 구축했다.
- 신규행 삽입 시 기존 값, style, border, wrap text, row height, column width 및 하단 section 이동을 검증한다.
- 실제 Master hash 불변, output 재개방, `.xlsb` 직접 편집 거부가 테스트된다.
- 현재 전체 pytest 결과는 `7 passed`이다.
- 실제 template anchor는 다음과 같다.
  - sheet: `BCG 동향`
  - report date: `D2`
  - 기존 data: `A5:D37`
  - 기관 설명: 38–40행
  - 영향도 분석: 42행부터

### Phase 2 시작 전 필수 조치

1. **원격 저장소 상태 확인**
   - GitHub의 `jeonys-12/BCG-Group-Weekly-Monitoring`은 현재 empty repository이다.
   - 로컬 작업물도 아직 initial commit이 없다.
   - 기존 로컬 파일을 잃지 말고 상태를 확인한다. 사용자의 별도 승인 없이 push나 PR을 생성하지 않는다.

2. **한국어 문서 UTF-8 검증**
   - Python의 `read_text(encoding="utf-8-sig")` 검사 결과 `PROJECT_SPEC.md`, `docs/design.md`, `docs/implementation-plan.md`는 정상이다.
   - Windows PowerShell 출력 code page에 따라 화면에서만 mojibake가 나타날 수 있으므로 터미널 표시만 보고 재인코딩하지 않는다.
   - 문서 수정 시 UTF-8을 유지하고 Unicode replacement character(`U+FFFD`)가 새로 생기지 않았는지만 검사한다.

3. **Phase 1 회귀 보호**
   - Phase 2 변경 전후에 전체 pytest를 실행한다.
   - `reports/template/BCG_Group_Trend_Master.xlsx`, `src/excel_writer.py`, `config/report_rules.yaml`은 collector 구현을 위해 변경하지 않는다.
   - 불가피한 변경은 이유와 회귀 테스트를 먼저 제시한다.

4. **작은 정리**
   - `src/excel_writer.py`의 사용하지 않는 import를 정리하되 동작 변경은 하지 않는다.
   - `AGENTS.md`에 아래 Phase 2 규칙을 추가한다.

---

## 3. Phase 2 개발 규칙

1. 공식 IR 자료만 수집한다. 언론기사, HOSE, HNX, SSC 수집은 이번 범위가 아니다.
2. BCG와 BCG Land collector는 서로 독립적인 module로 유지한다.
3. 공통 HTTP, parsing, archive 기능만 작은 shared module로 둔다.
4. HTML selector 하나에 의존하지 말고 semantic anchor, URL pattern, date pattern을 함께 검증한다.
5. parsing 실패를 빈 목록 성공으로 처리하지 않는다.
6. source URL, detail URL, attachment URL을 절대 버리지 않는다.
7. 원문 제목과 원문 본문을 저장하며 번역·요약·분류는 하지 않는다.
8. `requests` 기반 구현을 우선한다. BCG Land의 동적 data endpoint를 먼저 조사하고, 운영 collector에 Playwright를 넣는 것은 requests로 불가능함이 입증된 경우에만 허용한다.
9. live site 응답을 unit test에 직접 사용하지 않는다. unit test는 고정 fixture를 사용한다.
10. retry는 idempotent GET의 429/5xx와 일시적 network error에만 제한적으로 적용한다.
11. timeout, User-Agent, rate limit, maximum pages를 configuration으로 관리한다.
12. raw archive에는 수집시각, request URL, HTTP status, content hash, response body 또는 binary attachment metadata를 남긴다.
13. production code에 dummy item을 넣지 않는다.
14. 기존 Excel engine과 template을 변경하거나 실행 pipeline에 연결하지 않는다.

---

## 4. 공식 source 기준

### BCG IR

- Vietnamese disclosure list:
  `https://bamboocap.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/{year}`
- English disclosure list:
  `https://bamboocap.com.vn/en-US/investor-relations/disclosure/{year}`
- 2026 Vietnamese page는 server-rendered 목록과 pagination을 제공한다.
- Vietnamese page를 primary로 사용하고 English page는 optional fallback 또는 보조 metadata로만 사용한다.
- 각 목록 item에서 최소 title, published date, detail URL을 수집한다.
- detail page에서 body text, document number 후보, attachment link를 수집한다.
- pagination parameter와 종료 조건을 fixture로 검증한다. page count를 무제한 순회하지 않는다.

### BCG Land IR

- Disclosure page:
  `https://www.bcgland.com.vn/vi/quan-he-dau-tu/cong-bo-thong-tin`
- 현재 HTML shell에는 disclosure section이 보이지만 item data는 정적 HTML에 나타나지 않을 수 있다.
- browser/network inspection으로 실제 XHR/fetch endpoint를 한 번 조사하고 다음을 `docs/source-analysis.md`에 기록한다.
  - endpoint URL과 method
  - query/body parameter
  - pagination 방식
  - response content type/schema
  - detail 및 attachment URL 생성 방식
- endpoint가 확인되면 production collector는 해당 HTTP endpoint를 `requests`로 호출한다.
- endpoint를 확인할 수 없거나 access가 차단되면 빈 성공 결과를 만들지 말고 `REVIEW` 또는 명시적 collector error를 반환한다.

---

## 5. 권장 directory와 파일

```text
config/
├── sources.yaml
└── keywords.yaml                 # entity/keyword seed만 작성, 분류에는 사용하지 않음

src/
├── models.py                     # normalized record, attachment, error/result model
├── http_client.py                # timeout/retry/rate-limit/session
├── archive.py                    # raw response + metadata 저장
├── normalize.py                  # date/text/url/schema normalization
├── collectors/
│   ├── __init__.py
│   ├── base.py
│   ├── bcg_ir.py
│   └── bcg_land_ir.py
└── main.py                       # bounded collect CLI only

tests/
├── fixtures/
│   └── collectors/
│       ├── bcg_ir/
│       └── bcg_land_ir/
├── test_bcg_ir_collector.py
├── test_bcg_land_ir_collector.py
├── test_normalize.py
├── test_archive.py
└── test_phase2_cli.py
```

구조를 더 복잡하게 만들지 않는다. package가 필요하면 최소한으로 추가한다.

---

## 6. 공통 데이터 계약

Normalized record는 프로젝트 최소 schema의 모든 key를 가져야 한다. Phase 2에서 아직 판단하지 않는 값은 `null` 또는 명시된 보수적 default를 사용한다.

```json
{
  "id": "deterministic sha256",
  "published_date": "YYYY-MM-DD",
  "collected_date": "YYYY-MM-DD",
  "company": "BCG | BCG Land",
  "source": "BCG IR | BCG Land IR",
  "source_type": "OFFICIAL_IR",
  "title_original": "Vietnamese original title",
  "title_ko": null,
  "content_original": "source-derived detail text",
  "summary_ko": null,
  "url": "canonical detail URL",
  "document_number": null,
  "category": null,
  "importance": null,
  "hanwha_relevance": null,
  "sssg_relevance": null,
  "risk_direction": null,
  "is_duplicate": false,
  "duplicate_of": null,
  "excel_included": false,
  "review_status": null,
  "created_at": "ISO-8601 UTC timestamp",
  "attachments": [
    {
      "title": "original attachment label",
      "url": "absolute official URL",
      "content_type": null
    }
  ]
}
```

### ID 생성

- 정규화된 `source + canonical URL + document number + published date + original title`을 stable serialization 후 SHA-256한다.
- 수집시각, pagination 위치, local file path는 ID에 포함하지 않는다.
- 동일 input을 여러 번 normalize해도 같은 ID가 나와야 한다.

### 정규화 규칙

- Unicode는 NFC로 정규화한다.
- title의 연속 whitespace만 정리하고 원문 의미나 구두점을 임의로 바꾸지 않는다.
- detail body는 paragraph와 bullet 경계를 유지한다.
- relative URL은 official origin 기준 absolute URL로 변환한다.
- tracking parameter와 fragment만 제거한다. 의미 있는 query parameter는 보존한다.
- Vietnamese/English date format을 locale-aware하게 parsing하고 불명확한 날짜를 추측하지 않는다.
- document number는 명확한 pattern이 있을 때만 추출한다.
- 필수값 `published_date`, `source`, `title_original`, `url` 중 하나가 없으면 정상 item으로 조용히 통과시키지 않는다.

---

## 7. Collector interface

공통 interface는 다음 의미를 제공해야 한다. 정확한 class 이름보다 계약의 명확성을 우선한다.

```python
class Collector(Protocol):
    source_name: str

    def collect(
        self,
        start_date: date,
        end_date: date,
        *,
        max_pages: int | None = None,
    ) -> CollectorResult:
        ...
```

`CollectorResult`는 다음을 포함한다.

- `source`
- `status`: `SUCCESS`, `PARTIAL`, `FAILED`
- `items`
- `errors`
- `requested_range`
- `visited_urls`
- `collected_at`

한 detail page나 attachment parsing이 실패했지만 다른 item은 성공한 경우 `PARTIAL`이다. 목록 자체를 읽지 못한 경우 `FAILED`이다. item 0건은 요청 기간에 실제 공시가 없음을 검증한 경우에만 `SUCCESS`이다.

---

## 8. HTTP 및 archive 규칙

`config/sources.yaml`에 최소 다음을 둔다.

```yaml
http:
  user_agent: "BCG-Weekly-Monitor/0.2 (+internal compliance monitoring)"
  connect_timeout_seconds: 10
  read_timeout_seconds: 30
  max_retries: 2
  min_request_interval_seconds: 1.0

sources:
  bcg_ir:
    enabled: true
    base_url: "https://bamboocap.com.vn"
    disclosure_url_template: "https://bamboocap.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/{year}"
    max_pages: 10
  bcg_land_ir:
    enabled: true
    base_url: "https://www.bcgland.com.vn"
    disclosure_url: "https://www.bcgland.com.vn/vi/quan-he-dau-tu/cong-bo-thong-tin"
    max_pages: 10
```

Raw archive 권장 구조:

```text
data/raw/YYYY-MM-DD/<source>/<timestamp>-<sha256>/
├── response.bin 또는 response.html
└── metadata.json
```

`metadata.json`은 URL, method, status, collected_at, content type, encoding, byte length, SHA-256, error를 포함한다. secret, cookie, authorization header는 저장하지 않는다.

---

## 9. 구현 순서

1. repository 상태와 Phase 1 pytest baseline을 기록한다.
2. 기존 문서가 UTF-8로 정상 해석되는지 검사하고 손상문자 scan을 추가한다.
3. `requirements.txt`에 Phase 2 최소 dependency를 추가한다.
   - `requests`
   - `beautifulsoup4`
   - `lxml`
   - `python-dateutil`
   - 기존 dependency 유지
4. `config/sources.yaml`, `config/keywords.yaml`을 작성한다.
5. models, HTTP client, raw archive를 구현하고 단위 테스트한다.
6. BCG IR fixture를 먼저 만들고 list → detail → attachment parsing을 구현한다.
7. BCG Land endpoint를 조사하여 `docs/source-analysis.md`에 근거를 남긴다.
8. BCG Land fixture와 collector를 구현한다.
9. common normalization과 deterministic ID를 구현한다.
10. fixture 기반 end-to-end CLI를 구현한다.
11. network가 허용되는 환경에서 각 source를 최대 1 page, 좁은 기간으로 live smoke test한다.
12. 전체 pytest 및 Phase 1 Excel regression test를 실행한다.
13. 결과와 제한사항을 `docs/phase-2-result.md`에 기록한다.

---

## 10. 필수 테스트

### BCG IR

- 연도별 list page parsing
- pagination 다음 page 처리와 max page 제한
- title/date/detail URL 추출
- detail body와 attachment absolute URL 추출
- Vietnamese Unicode 보존
- 요청기간 밖 item 제외
- detail 한 건 실패 시 `PARTIAL`

### BCG Land IR

- 확인된 API/HTML response schema parsing
- empty shell을 공시 0건으로 오판하지 않음
- pagination/date range 처리
- attachment URL 보존
- endpoint 변경 또는 예상 schema 누락 시 explicit error

### Normalize/archive

- 여러 date format의 deterministic ISO date 변환
- invalid/ambiguous date 거부
- Unicode NFC 및 whitespace 처리
- relative URL resolution과 safe canonicalization
- 동일 input의 stable ID
- raw response와 metadata hash 일치
- cookie/authorization 미저장

### Regression

- 기존 Phase 1 test 전부 통과
- Master workbook hash 불변
- collector unit test 중 실제 network call 0건
- optional live test는 `integration` marker로 분리하고 기본 pytest에서는 skip

---

## 11. Phase 2 acceptance criteria

아래 조건을 모두 만족해야 완료다.

- [ ] Phase 1의 7개 테스트를 포함한 전체 pytest가 성공한다.
- [ ] BCG IR와 BCG Land IR collector가 독립적으로 실행된다.
- [ ] 두 collector 모두 offline fixture 기반 test가 있다.
- [ ] BCG IR는 list, detail, attachment URL을 실제 구조 기준으로 parsing한다.
- [ ] BCG Land의 동적 endpoint 또는 명확한 fallback 전략이 문서화된다.
- [ ] 모든 normalized record가 최소 schema key를 가진다.
- [ ] `id`가 반복 실행에도 안정적이다.
- [ ] URL과 원문 title/content가 보존된다.
- [ ] raw response와 metadata가 audit 가능하게 저장된다.
- [ ] parser/network failure가 silent empty success가 아니다.
- [ ] live smoke 결과 또는 network 제한 사유가 기록된다.
- [ ] Excel Master, 기존 data, Excel writer 동작이 변경되지 않는다.
- [ ] Phase 3 이상의 기능이 포함되지 않는다.

---

## 12. 이번 단계에서 하지 말 것

- HOSE/HNX/SSC collector
- 언론기사 수집
- fuzzy duplicate 제거
- 중요도 A/B/C 분류
- Hanwha relevance/risk 판단
- 한국어 번역·요약
- 영향도 분석 생성
- Excel report에 실제 수집자료 삽입
- weekly GitHub Actions
- database server 또는 frontend
- source 차단을 우회하는 공격적 crawling

---

## 13. 완료 보고 형식

작업 완료 후 다음을 보고한다.

1. Phase 1 사전 점검 및 인코딩 복구 결과
2. 생성·변경 파일
3. source별 실제 접근 방식과 endpoint
4. 구현한 수집·정규화·archive 기능
5. fixture 및 live smoke test 결과
6. 전체 pytest 결과
7. 수집 실패 또는 website 변경 위험
8. Phase 3 전에 확인할 사항
9. 원격 저장소가 비어 있으면 commit/push 여부와 필요한 사용자 승인

---

## 14. Codex에 그대로 전달할 실행 prompt

```text
반드시 AGENTS.md, PROJECT_SPEC.md, docs/design.md, docs/implementation-plan.md,
docs/phase-2-codex-instructions.md 전체를 먼저 읽어라.

이번 작업은 Phase 2만 구현한다.

먼저 Phase 1 결과를 검증하고 pytest baseline을 기록하라. 원격 GitHub 저장소가
비어 있지만 한국어 Markdown은 Python 검사에서 정상 UTF-8로 확인됐다. PowerShell
화면에서만 mojibake가 보일 수 있으므로 터미널 표시만 보고 재인코딩하지 마라. 별도 승인 없이 push나
PR을 만들지 마라.

그 다음 BCG IR와 BCG Land IR 공식 공시 collector, raw archive, 공통 normalize와
deterministic schema를 실제 코드로 구현하라. requests를 우선 사용하고 BCG Land의
동적 data endpoint는 조사 근거를 docs/source-analysis.md에 기록하라. parsing 실패를
빈 성공으로 처리하지 말고 URL·원문·attachment를 보존하라.

HOSE/HNX/SSC, 언론, 중복 제거, 분류, 요약, 영향도 분석, Excel 반영, GitHub Actions는
구현하지 마라. fixture 기반 unit test와 제한된 live smoke test를 실행하고 기존 Phase 1
Excel 회귀 테스트를 모두 유지하라. 실패를 수정한 뒤 docs/phase-2-result.md에 결과와
위험요소를 작성하고 변경 파일 및 전체 pytest 결과를 보고하라.
```
