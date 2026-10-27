---
market: 시장 이름 (예: 수면안대)
aliases: []                 # 같은 시장의 다른 이름·키워드
track: A                    # A 상시 / B 시즌·이벤트 / C 틈새
status: 신규                # 신규 / 관찰 / 추천 / 선택 대기 / 선택 / 테스트 / 성공 / 실패 / 보류
score: null                 # 추천 점수 0~100
keywords: []                # 쿠팡 검색 키워드
season:                     # 트랙 B만
  peak_months: []           # 예: [11, 12]
  alert_month: null         # 정점 약 3개월 전 (예: 8)
metrics:                    # 가장 최근 측정값
  measured_at: null         # YYYY-MM-DD
  est_daily_sales_top: null # 1페이지 상위 상품 추정 일판매 (리뷰 증가 속도 기준)
  top_review_count_median: null
  avg_price: null
  rocket_share: null        # 1페이지 로켓 비율
  pb_share: null
  wing_views_30d: null      # 윙 조회수 (추천 단계에서만)
  est_conversion: null      # 추정 판매량 ÷ 조회수
  sourcing: null            # 도매매/1688 링크 또는 "없음"
  est_margin: null          # 광고비 25% 포함 영업이익 추정
user:
  interest: false           # 드라이브 시트에서 읽어 옴 (사용자 소유)
  memo: ""
---

## 요약
한두 문장: 왜 이 시장을 보는가, 무엇으로 이길 수 있는가.

## 근거
- 수치와 출처, 측정일

## 리스크
- 인증, 시즌 끝 재고, 경쟁 강도 변화 등

## 기록
- YYYY-MM-DD 신규 등록 (트랙 A, 점수 ..)
