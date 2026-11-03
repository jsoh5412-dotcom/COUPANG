#!/usr/bin/env python3
"""season_analyze.py 결과로 트랙 B 시장 파일을 만든다. API를 호출하지 않는다. 시트 갱신은 archive_sheet.py sync로 한다.

- 아카이브 기준: 3주기 모두 정점 달 차이 1개월 이내, 강도 3 이상, 데이터 24개월 이상, 묶음 내 규모 1 이상.
- 제외: 인증·규제 표시(flag)가 있는 시장, 상품 검색이 아닌 키워드(NON_PRODUCT).
- 정점 달이 약 3개월 뒤인 시장만 `추천`, 나머지는 `신규`.
- 이미 있는 시장 파일은 덮어쓰지 않는다.

사용법: python3 research/tools/season_archive.py <research/raw/season/YYMMDD> --peak 2
"""
from __future__ import annotations

import argparse
import csv
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKETS = ROOT / "research" / "markets"
NON_PRODUCT = {"시간표 자석", "스승의날 선물 포장", "수능 간식 포장", "고추 건조기망"}
# 스캔 때 붙인 이름이 실제 키워드와 다른 시장은 키워드 기준으로 표시한다.
DISPLAY = {
    "봄 원피스 잠옷": "봄 잠옷",
    "외풍 차단 커튼": "방풍 비닐",
    "잔디깎이 낫": "예초기 날",
    "핫 물주머니": "물주머니",
    "창문 먼지 필터": "창문 필터",
    "미끄럼 방지 아이젠": "아이젠",
    "귀마개 방한": "방한 귀마개",
    "타이어 체인 스프레이": "스프레이 체인",
    "발 토시": "레그워머",
    "겨울 이불 커버": "극세사 이불",
}


def select(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if (r["repeat"] == "True" and float(r["strength"]) >= 3 and int(r["months_with_data"]) >= 24
                and float(r["scale_in_batch"]) >= 1 and not r["flag"] and r["market"] not in NON_PRODUCT):
            r["name"] = DISPLAY.get(r["market"], r["market"])
            out.append(r)
    return out


def summary(r: dict) -> str:
    return f"{r['peak_month']}월 정점, 3주기 반복 ({r['peaks']}월), 강도 {r['strength']}. 쿠팡 경쟁·소싱 미확인"


def write_market(r: dict, status: str, today: str) -> bool:
    path = MARKETS / f"{r['name']}.md"
    if path.exists():
        return False
    peak = int(r["peak_month"])
    alert = (peak - 3 - 1) % 12 + 1
    keywords = r["keywords"].split("|")
    path.write_text(f"""---
market: {r['name']}
aliases: []
track: B
status: {status}
score: null
keywords: [{', '.join(keywords)}]
season:
  peak_months: [{peak}]
  alert_month: {alert}
  season_strength: {r['strength']}
metrics:
  measured_at: {today}
  est_daily_sales_top: null
  top_review_count_median: null
  avg_price: null
  rocket_share: null
  pb_share: null
  wing_views_30d: null
  est_conversion: null
  sourcing: null
  est_margin: null
user:
  interest: false
  memo: ""
---

## 요약
{summary(r)}.

## 근거
- 네이버 검색어 트렌드, 2023-11~2026-10 월별, 키워드 {', '.join(keywords)} ({today} 측정)
- 주기별 정점 달: {r['peaks']}월, 강도(정점 ÷ 주기 중앙값 평균): {r['strength']}, 마지막 정점 ÷ 첫 정점: {r['last_vs_first']}
- 네이버 수치는 상대값이라 실제 수요 규모가 아니다. 쿠팡 수치는 아직 없다.

## 리스크
- 쿠팡 경쟁, 소싱, 인증, 정점 전 입고 가능 여부, 시즌 끝 재고 모두 미확인

## 기록
- {today} 신규 등록 (트랙 B, 상태 {status})
""", encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--peak", type=int, required=True, help="약 3개월 뒤 정점 달")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    selected = select(args.folder / "analysis.csv")
    created, recommended = 0, []
    for r in selected:
        status = "추천" if int(r["peak_month"]) == args.peak else "신규"
        created += write_market(r, status, today)
        if status == "추천":
            recommended.append(r["name"])
    print(f"선정 {len(selected)}개, 새 시장 파일 {created}개, 추천 {len(recommended)}개")
    print("추천:", ", ".join(recommended))
    return 0


if __name__ == "__main__":
    sys.exit(main())
