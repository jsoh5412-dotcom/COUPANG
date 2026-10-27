# COUPANG

쿠팡 판매 운영 모노레포. 업무별 폴더에서 각각의 Claude 팀장이 작업한다. 쿠팡-본부-전략팀장(채팅)이 방향을 정하고, 쿠팡-본부-운영팀장-PM(맥북)이 실행을 총괄한다.

| 문서 | 내용 |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 조직 구조, 실행 환경, 소통 방식, 승인 관문 |
| [`ROADMAP.md`](ROADMAP.md) | 쿠팡 테크트리와 진행 상태 |
| [`DECISIONS.md`](DECISIONS.md) | 결정 기록 (새 세션은 여기부터) |
| [`SETUP.md`](SETUP.md) | 사용자가 직접 할 셋업 체크리스트 |
| [`CLAUDE.md`](CLAUDE.md) | 모든 봇의 공통 규칙 |

| 폴더 | 내용 | 상태 |
|---|---|---|
| `shared/` | 공통 도구 (수집, 리뷰 분석, 번역, 브랜드) | 뼈대 |
| `products/` | 상품 카드 (상품별 진행·인수인계) | 양식 |
| `research/` | 시장조사 — 쿠팡-시장조사-팀장 | 기획 다음 신설 |
| `planning/` | 기획 — 쿠팡-기획-팀장 | 신설 중 |
| `pdp/` | 상세페이지·썸네일 — 쿠팡-상페-팀장 | 저장소 이사 PR 검토 중 (`pdp/migration`), 병합 후 맥북 로컬 세션으로 재신설 |
| `listing/` `logistics/` `ads/` | 등록·물류·광고 팀 | 예정 |

처음 쓸 때: `.env.example`을 복사해 `.env`를 만들고 API 키를 넣는다.
