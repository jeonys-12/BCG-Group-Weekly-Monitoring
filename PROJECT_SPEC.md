# BCG Group Weekly Monitoring & Excel Reporting Automation
## Codex 개발 작업지시서

### 1. 프로젝트 개요

프로젝트명:

**BCG Group Weekly Monitoring Automation**

본 프로젝트는 Hanwha의 베트남 King Crown Thao Dien Project 관련 투자금 회수 업무를 지원하기 위한 내부 업무자동화 시스템이다.

현재 담당자는 매주 BCG Group 및 BCG Land의 공식 공시자료, 거래소 자료, 관계기관 발표자료 등을 수작업으로 확인한 후 `BCG 그룹 동향 보고` Excel에 주요 동향을 추가하고 영향도를 분석하여 보고하고 있다.

이 작업을 자동화하여 매주 다음 업무를 수행하는 시스템을 개발한다.

`공식자료 모니터링 → 신규자료 판별 → 중복 제거 → 중요자료 선별 → 한국어 요약 → Hanwha 관련성 분석 → 기존 Excel 양식 업데이트 → 보고서 생성`

---

## 2. 핵심 목표

자동화 시스템은 다음 원칙을 만족해야 한다.

1. 기존 Hanwha 보고서 Excel 디자인을 최대한 변경하지 않는다.
2. 기존 보고자료와 신규자료의 중복을 자동으로 제거한다.
3. 언론기사보다 공식 공시자료를 우선한다.
4. 단순 BCG 뉴스가 아니라 Hanwha의 채권 회수에 영향을 줄 수 있는 정보를 우선한다.
5. AI가 근거 없는 판단이나 사실을 생성하지 않도록 한다.
6. 모든 데이터는 원문 URL과 출처를 추적 가능하게 관리한다.
7. 매주 기존 Excel에 신규 동향만 추가한다.
8. 기존 보고서의 과거 내용은 수정하거나 삭제하지 않는다.
9. 자동화 결과와 원문 데이터 사이에 audit trail을 유지한다.
10. 사람이 최종 검토하기 쉬운 구조로 만든다.

---

## 3. 사업 Context

자동화 시스템이 다음 사업 배경을 알고 중요도를 판단하도록 프로젝트 문서에 기록한다.

### King Crown Project

- 사업 위치: Ho Chi Minh City, former District 2, Thao Dien area, Vietnam
- 사업주체: Sao Sang Sai Gon Joint Stock Company (`SSSG`)
- SSSG 지분:
  - BCG Land: 75%
  - Hanwha: 25%

### Hanwha 투자

- 투자일: 21 January 2020
- 취득주식: 8,500,000 shares
- 투자금: VND 175,000,000,000

2022년 5월 Hanwha는 보유 SSSG 지분 전량을 BCG Land에 매각하기 위한 SPA를 체결하였다.

2025년 3월까지:

- 총 투자원금: VND 175,000,000,000
- 회수금: VND 126,000,000,000
- 미상환 원금: VND 49,000,000,000
- 2025-03-31 기준 누적 지연이자: 약 VND 95,277,191,781
- 미회수 합계: 약 VND 144,277,191,781

따라서 본 시스템의 최우선 목적은 일반적인 BCG 투자정보 제공이 아니라 다음 질문에 답하는 것이다.

> “이번 주 발생한 BCG / BCG Land / SSSG 관련 변화가 Hanwha의 잔여 채권 회수 가능성에 영향을 주는가?”

---

## 4. 기본 기술 Architecture

가능한 한 단순하고 유지보수하기 쉬운 Python 기반 구조로 개발한다.

### 권장 환경

- Python 3.11+
- requests
- BeautifulSoup4
- lxml
- pandas
- openpyxl
- httpx 또는 requests
- python-dateutil
- PyYAML
- rapidfuzz
- pytest

웹페이지가 JavaScript rendering을 요구하는 경우에만 Playwright를 보조적으로 사용한다.

불필요한 frontend framework나 database server는 사용하지 않는다.

초기 버전은 GitHub Repository + GitHub Actions + JSON/SQLite/local files 구조로 구현한다.

---

## 5. Repository 구조

```text
bcg-weekly-monitoring/
│
├── AGENTS.md
├── README.md
├── PROJECT_SPEC.md
├── requirements.txt
├── .gitignore
│
├── config/
│   ├── sources.yaml
│   ├── keywords.yaml
│   └── report_rules.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── history/
│   └── monitoring_index.json
│
├── reports/
│   ├── template/
│   │   └── BCG_Group_Trend_Master.xlsx
│   └── output/
│
├── src/
│   ├── collectors/
│   │   ├── bcg_ir.py
│   │   ├── bcg_land_ir.py
│   │   ├── hose.py
│   │   ├── hnx.py
│   │   ├── ssc.py
│   │   └── mps.py
│   │
│   ├── normalize.py
│   ├── deduplicate.py
│   ├── classify.py
│   ├── summarize.py
│   ├── impact_analysis.py
│   ├── excel_writer.py
│   └── main.py
│
├── tests/
│   ├── test_collectors.py
│   ├── test_deduplicate.py
│   ├── test_classify.py
│   └── test_excel_writer.py
│
└── .github/
    └── workflows/
        ├── weekly-monitor.yml
        └── manual-monitor.yml
```

필요하면 구조를 개선할 수 있으나 과도하게 복잡하게 만들지 않는다.

---

## 6. 공식 Monitoring Source

공식자료를 최우선으로 사용한다.

### Priority 1

- Bamboo Capital / BCG Investor Relations
- BCG Land Investor Relations
- HOSE
- HNX
- State Securities Commission of Vietnam (`SSC`)

### Priority 2

- Vietnam Ministry of Public Security
- Vietnamese competent government authorities
- 기타 공식기관

### Priority 3 보완자료

- Vietstock
- CafeF
- The Investor
- Vietnam Investment Review 등

언론은 공식자료를 대체하지 않는다.

동일한 사건에 대해 공식 공시가 존재하면 공식자료를 대표자료로 사용한다.

---

## 7. 검색 대상 Entity

다음 entity를 기본 monitoring 대상으로 설정한다.

### Primary

- BCG
- Bamboo Capital
- BCG Land
- BCR
- Sao Sang Sai Gon
- SSSG
- King Crown
- King Crown Thao Dien

### Key Person

- Nguyen Ho Nam
- BCG senior executives
- BCG Land senior executives

### Regulatory

- HOSE
- HNX
- SSC
- Ministry of Public Security

향후 config 파일에서 entity를 쉽게 추가/삭제할 수 있게 구현한다.

---

## 8. Monitoring Keyword

다음 영역을 별도 keyword group으로 관리한다.

### Financial

- liquidity
- cash flow
- debt
- bond
- repayment
- default
- overdue
- financing
- bank
- loan
- fund raising

### Accounting

- audit
- audited financial statements
- financial statements
- accounting
- auditor
- qualified opinion

### Regulatory

- suspension
- delisting
- listing
- trading restriction
- disclosure violation
- administrative penalty

### Investigation

- investigation
- prosecution
- indictment
- police
- Ministry of Public Security
- asset freeze
- seizure

### Governance

- chairman
- CEO
- CFO
- board
- director
- resignation
- appointment

### Restructuring

- restructuring
- asset disposal
- asset sale
- stake sale
- divestment
- strategic investor

### Hanwha Recovery

- SSSG
- Sao Sang Sai Gon
- King Crown
- Thao Dien
- land
- project sale
- share transfer
- asset disposal
- receivables

영어 및 베트남어 keyword를 함께 관리한다.

---

## 9. 수집 데이터 Schema

모든 자료는 최소 다음 정보를 가져야 한다.

```text
id
published_date
collected_date
company
source
source_type
title_original
title_ko
content_original
summary_ko
url
document_number
category
importance
hanwha_relevance
sssg_relevance
risk_direction
is_duplicate
duplicate_of
excel_included
review_status
created_at
```

---

## 10. 중복 제거 Logic

중복 여부는 다음 순서로 판단한다.

### Level 1
URL exact match

### Level 2
공시번호/document number exact match

### Level 3
Normalized title exact match

### Level 4
Title fuzzy similarity

### Level 5
동일 회사 + 동일 날짜 + 동일 사건 keyword

`rapidfuzz` 등을 사용하여 similarity score를 계산하되 단순 similarity만으로 자동 삭제하지 않는다.

예:

- score >= 95: duplicate 처리 가능
- 85~94: review candidate
- <85: new candidate

동일 사건의 언론 보도와 공식 공시가 동시에 존재하면 공식 공시를 대표자료로 유지한다.

모든 duplicate 판단 결과는 `monitoring_index.json` 등에 기록한다.

---

## 11. 중요도 Classification

내부적으로 중요도를 A / B / C로 분류한다.

### A – Hanwha 회수에 직접 영향

예:

- BCG Land 자금조달
- BCG Land 채무불이행
- BCG Land 주요 자산 매각
- BCG Land 지분 또는 경영권 매각
- SSSG 관련 자산 처분
- SSSG 지분 동결 또는 해제
- King Crown 사업 변화
- 수사기관의 자산 동결
- 대규모 default
- 구조조정
- 핵심 경영진 사법처리
- BCG Land 지급능력에 중대한 변화

처리:

`Excel 반영 + 비고 작성 + 영향도 분석 반영`

### B – 그룹 정상화 판단에 필요한 사항

예:

- 감사보고서
- 주주총회
- 일반적인 경영진 변경
- 거래정지
- 상장폐지
- 회사채 상태
- 감독기관 제재

처리:

`원칙적으로 Excel 반영`

### C – 일반 기업정보

Hanwha 회수와 관계가 희박한:

- 단순 행사
- 일반 CSR
- 마케팅
- 중요하지 않은 수상
- 반복 홍보
- 사업과 관계없는 일반 기사

처리:

`원칙적으로 Excel 제외`

단, 모든 C급 자료도 raw archive에는 보관할 수 있다.

---

## 12. Hanwha 영향도 판단

내부 데이터에는 다음 항목을 별도로 기록한다.

### hanwha_relevance

- HIGH
- MEDIUM
- LOW
- NONE

### risk_direction

- POSITIVE
- NEUTRAL
- NEGATIVE
- UNCERTAIN

단, Excel 보고서에는 이 raw label을 그대로 표시하지 않아도 된다.

다음 영역을 기준으로 판단한다.

1. BCG 그룹 정상화
2. BCG Land 유동성
3. BCG Land 외부 자금조달 가능성
4. BCG Land 채무상환능력
5. BCG Land 자산매각 가능성
6. SSSG 자산 또는 사업 변동
7. King Crown 사업가치
8. 수사 및 법률 Risk
9. 자산동결
10. Hanwha 채권 회수

근거가 충분하지 않으면 반드시 `UNCERTAIN`으로 표시한다.

AI가 추측으로 NEGATIVE 또는 POSITIVE 판단을 하지 않도록 한다.

---

## 13. 한국어 Summary 작성 Rule

기존 Hanwha Excel 보고서 스타일을 유지한다.

원문 전체 번역이 아니라 핵심 사실만 보고문체로 정리한다.

### 일반사항
2~3줄

### 중요사항
3~5줄

### Hanwha 회수 직접 영향
최대 5~7줄

가능한 작성 구조:

```text
제목

- 주요내용
- 사유
- 진행현황
- 향후계획
```

불필요한 형용사와 평가 표현을 사용하지 않는다.

공식자료에 없는 내용을 추가하지 않는다.

사실과 분석을 명확히 구분한다.

---

## 14. Excel Template

현재 Hanwha에서 사용하는 `BCG 그룹 동향 보고` Excel을 Master Template으로 사용한다.

### 현재 구조

Sheet:
`BCG 동향`

Header:

- A = 날짜
- B = 출처
- C = 주요내용
- D = 비고

상단:

- BCG 그룹 동향 보고
- 보고 기준일

하단:

- `1) BCG 그룹 동향`
- `2) 영향도 분석`

Excel 출력 형식과 디자인을 임의로 변경하지 않는다.

---

## 15. Excel 누적 Rule

기존 과거자료는 수정하거나 삭제하지 않는다.

매주:

`기존 마지막 monitoring data 아래 + HNX / HOSE / SSC 설명행 위`

에 새로운 row를 삽입한다.

신규자료는 날짜 오름차순으로 정렬한다.

새 row는 직전 정상 data row의 다음 서식을 복사한다.

다음 서식을 유지한다.

- font
- border
- fill
- alignment
- wrapping
- row height logic
- number format
- merged cell relationship
- column width

Section 2 영향도 분석 위치는 신규 row 수만큼 아래로 이동시킨다.

---

## 16. 보고 기준일

보고 생성일을 Excel의 기준일 셀에 입력한다.

예:

`2026-08-12 → 2026-08-19`

기존 report date cell 위치를 코드에서 configuration으로 관리하여 향후 Excel 수정에도 대응 가능하게 한다.

---

## 17. 비고 작성 Rule

모든 공시에 비고를 작성하지 않는다.

다음 경우에만 작성한다.

- 유동성 Risk
- 자금조달 변화
- 수사/법률 Risk
- 핵심 경영진 변화
- 감사/회계 Risk
- 구조조정
- 자산 매각
- SSSG 관련
- King Crown 관련
- Hanwha 회수 직접 영향

비고 예시:

- 유동성 제약
- 경영진 변동
- 대외 신용도 저하 및 자금조달 여건 악화
- 검찰조사 개시 공식화
- 구조조정 본격화
- BCG Land 자산매각 가능성 확대

단, 해당 평가를 뒷받침할 명확한 사실이 있을 때만 작성한다.

---

## 18. 영향도 분석 자동작성

Excel 하단 `2) 영향도 분석`을 매주 최신 정보 기준으로 업데이트한다.

길이는 현재 보고서 수준을 유지한다.

기본 분석 프레임:

`그룹 경영상황 → BCG Land 재무상황 → SSSG/King Crown 영향 → Hanwha 채권회수 영향 → 향후 Monitoring 사항`

장문의 보고서를 작성하지 않는다.

최종 Excel에는 약 2~4문장으로 요약한다.

분석 근거가 부족하면 보수적으로 표현한다.

---

## 19. Data Archive

Excel에 표시하지 않는 데이터를 포함하여 모든 monitoring 결과는 별도로 저장한다.

권장:

```text
data/history/YYYY-MM-DD.json
```

예:

```text
data/history/2026-08-19.json
```

각 파일에 다음을 포함한다.

- monitoring range
- searched sources
- discovered items
- duplicate items
- excluded items
- included items
- errors
- generated report filename

이를 통해 왜 특정 공시가 보고서에 포함/제외됐는지 추적할 수 있게 한다.

---

## 20. Manual Review 기능

자동화 결과에 다음 상태를 제공한다.

- AUTO_ACCEPT
- REVIEW
- EXCLUDED

다음 경우 REVIEW로 지정한다.

- title similarity 85~94
- 한화 영향 판단이 UNCERTAIN
- source parsing 실패
- 날짜 확인 불가
- 동일 사건인지 불분명
- 공식자료와 언론자료 내용이 충돌
- 법적 의미 판단 필요

REVIEW 항목은 별도 Markdown 또는 JSON summary로 출력한다.

---

## 21. Weekly GitHub Actions

매주 자동 실행 workflow를 작성한다.

기본 schedule:

- 매주 월요일
- 한국시간 오전 07:00

GitHub Actions cron은 UTC 기준이라는 점을 고려해 설정한다.

또한 `workflow_dispatch`를 제공하여 수동 실행 가능하게 한다.

### Workflow 주요 단계

1. Checkout
2. Python setup
3. Dependency install
4. Run collectors
5. Normalize
6. Deduplicate
7. Classify
8. Generate summaries
9. Generate impact analysis
10. Update Excel
11. Run tests
12. Save artifacts
13. Commit generated data/report 또는 GitHub artifact 업로드

보고서 자동 commit 방식과 artifact 방식은 configuration으로 선택 가능하게 한다.

---

## 22. 실패 처리

특정 source가 실패하더라도 전체 workflow를 즉시 실패시키지 않는다.

예:

- BCG IR 성공
- BCG Land 성공
- HOSE 성공
- HNX 실패
- SSC 성공

이라면 나머지 결과로 report를 생성하되:

```text
monitoring status: PARTIAL
```

을 기록한다.

그리고 error summary에:

```text
HNX collection failed
```

을 남긴다.

모든 source가 실패했을 때만 report 생성 실패로 처리한다.

---

## 23. Quality Gate

Excel 생성 전 다음 검사를 한다.

- 날짜 누락 없음
- 출처 누락 없음
- URL 저장 여부
- 기존 row 삭제 여부
- 기존 row 내용 변경 여부
- duplicate 신규 추가 여부
- Excel 열 너비 유지 여부
- merged cell 손상 여부
- Section 이동 여부
- 보고 기준일 변경 여부
- 파일 정상 open 가능 여부

이 중 중요한 검사를 자동 pytest로 작성한다.

---

## 24. 개발 단계

한 번에 모든 기능을 만들지 말고 다음 단계로 진행한다.

### PHASE 1

- Repository scaffold 구축
- Master Excel 분석
- Excel writer 개발
- dummy data 3건을 이용해 실제 보고서 생성

### PHASE 2

- BCG IR collector
- BCG Land IR collector
- 데이터 normalize

### PHASE 3

- HOSE
- HNX
- SSC collector

### PHASE 4

- deduplicate engine
- importance classification
- Hanwha relevance classification

### PHASE 5

- summary
- impact analysis

### PHASE 6

- GitHub Actions
- weekly schedule
- manual dispatch
- artifact/report generation

### PHASE 7

- error handling
- logging
- tests
- README
- 운영 documentation

각 Phase 완료 후 반드시 실제 실행 테스트를 한다.

---

## 25. 최초 Codex 수행사항

지금 바로 모든 기능을 무작정 구현하지 말고 다음 순서로 시작한다.

1. Repository 전체를 확인한다.
2. 업로드되거나 repository에 저장된 기존 `BCG 그룹 동향 보고` Excel 구조를 프로그램으로 분석한다.
3. 다음 내용을 출력한다.
   - sheet 목록
   - used range
   - merged cells
   - row heights
   - column widths
   - style distribution
   - 주요 section 위치
   - Excel editing risk
4. 설계 내용을 `docs/design.md`에 작성한다.
5. 실제 개발계획을 `docs/implementation-plan.md`에 작성한다.
6. 그 후 Phase 1 코드를 구현한다.
7. 기존 Excel을 손상시키지 않고 dummy 신규자료 3건을 넣은 output file을 만든다.
8. pytest를 실행한다.
9. 결과를 확인하고 문제가 있으면 수정한다.
10. 완료 후 변경파일과 테스트 결과를 요약한다.

사용자에게 구현 방법만 설명하지 말고 실제 repository에 코드를 작성하고 테스트까지 수행한다.

---

## 26. Coding 원칙

- Simple is better than clever.
- 기능을 과도하게 추상화하지 않는다.
- Source별 collector는 독립적으로 유지한다.
- Configuration은 코드에 hard coding하지 않는다.
- Parsing 실패 시 silent failure하지 않는다.
- 공시 원문을 가능한 한 저장한다.
- Source URL을 반드시 보존한다.
- AI 생성결과와 source-derived facts를 구분한다.
- Excel 기존 데이터는 보호한다.
- 프로덕션 코드에 임시 dummy data를 남기지 않는다.
- Test fixture와 production data를 분리한다.

---

## 27. 완료 조건 Definition of Done

최소 다음 조건을 모두 만족해야 첫 번째 release로 인정한다.

- 신규 official disclosure 자동 수집 가능
- 기존자료 duplicate 제거 가능
- 중요도 A/B/C 분류 가능
- Hanwha relevance 판정 가능
- 기존 Excel format 유지 가능
- 신규 data row 자동 추가 가능
- 기준일 자동 변경 가능
- 영향도 분석 업데이트 가능
- weekly GitHub Actions 동작 가능
- manual workflow 실행 가능
- error log 제공
- raw monitoring history 저장
- pytest 성공
- README 운영방법 작성

최종 결과는 비개발자도 README만 보고 운영할 수 있도록 작성한다.
