# COUPANG

쿠팡 판매 운영 모노레포. 업무별 폴더에서 각각의 Claude 봇이 작업한다.

| 폴더 | 내용 | 상태 |
|---|---|---|
| `shared/` | 공통 도구 (수집, 리뷰 분석, 번역, 브랜드) | 뼈대 |
| `pdp/` | 상세페이지 제작 봇 | 뼈대 |

- 공통 규칙: [`CLAUDE.md`](CLAUDE.md)
- 상세페이지 봇 규칙: [`pdp/CLAUDE.md`](pdp/CLAUDE.md)
- 처음 쓸 때: `.env.example` 을 복사해 `.env` 를 만들고 API 키를 넣는다.
