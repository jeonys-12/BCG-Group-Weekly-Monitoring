# Phase 3 구현 결과

## 기준선

- 시작: `origin/main` = `bed603b55f60034b7f836b064e3c1cdec6586d9c`; 요구 merge commit 이상임을 `merge-base --is-ancestor`로 확인.
- branch: `codex/phase-3-official-collectors`.
- 구현 전: `20 passed, 1 skipped`.
- Master SHA-256 전/후: `A530E4B8F460D05ECDBEB97F27A5A14EFA16D9072D6C3956DA6B41F426BAA732`.

## 생성·변경 파일

- collector: `src/collectors/hnx.py`, `hose.py`, `ssc.py`, exports/CLI 연결.
- 공통: `src/http_client.py` non-retried form POST; `src/normalize.py` 기존 기본값을 보존하는 `source_type` 인자.
- config: `config/sources.yaml` HNX/HOSE/SSC 공식 endpoint와 제한.
- fixture/test: source fixture 4개, source test 3개, Phase 3 CLI test, opt-in live smoke.
- docs: 이 문서와 `docs/source-analysis-phase3.md`.
- Windows sandbox 오류 1385로 내장 `apply_patch`가 반복 실패해, 승인된 fallback인 unified diff 파일 + `git apply --check`/`git apply`를 사용했고 매 적용 후 `git diff --check`를 실행했다.

## 구현 범위

HNX BCG/BCR issuer pagination, HOSE 공식 JSON API pagination/filter, SSC WebCenter list/detail과 `dDocName`, official attachment URL, 기존 archive와 deterministic ID/normalized `CollectorResult`, source별 `SUCCESS/PARTIAL/FAILED`, source/ticker 독립 실패 보존을 구현했다. HNX POST는 자동 retry되지 않는다. 번역·요약·분류·중복 제거·영향 분석·Excel·Actions·언론 수집은 추가하지 않았다.

## 테스트

- HNX: 2 passed.
- HOSE: 3 passed.
- SSC: 3 passed.
- Phase 3 fixture CLI: 1 passed.
- 전체: `29 passed, 2 skipped in 4.91s`.
- fixture unit/CLI test의 live network call: 0.
- Master hash 불변 확인 완료.

## Optional live smoke

각 source 2026-08-07 하루, 최대 1페이지로 실행했다. 결과는 1 failed test이며 collector 결과는 다음과 같다.

- HNX: `FAILED`, BCG/BCR 모두 로컬 CA chain `CERTIFICATE_VERIFY_FAILED`; 검증 우회 없음.
- HOSE: `FAILED`, 공식 `/n/api/v1/news/cate` 익명 GET HTTP 404.
- SSC: `FAILED`, HTTP 200 WebCenter ADF loopback shell이지만 list marker 없음.

이는 website 계약/access 변화와 로컬 TLS 제약을 명시적으로 드러낸 결과이며 빈 성공으로 처리하지 않았다.

## 위험 및 Phase 4 전 확인

- 정상 브라우저 network 조사 재실행 후 HOSE alias/date 형식과 SSC ADF의 비-session 공개 list 계약을 재확인해야 한다.
- HNX 운영 runner CA trust store를 확인하되 TLS 검증은 유지한다.
- HNX CIMS/HOSE static/SSC GET_FILE official attachment host allowlist를 운영 전에 확정한다.
- Phase 2 IR과 exchange record의 source 간 중복 정책, BCG/BCG Land/BCR entity mapping은 Phase 4에서 결정한다.
- API schema 변경 시 fallback scraping 대신 현재 explicit failure를 유지한다.