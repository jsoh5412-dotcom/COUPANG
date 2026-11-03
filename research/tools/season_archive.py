#!/usr/bin/env python3
"""season_analyze.py 결과로 트랙 B 시장 파일과 드라이브 아카이브를 만든다. API를 호출하지 않는다.

- 아카이브 기준: 3주기 모두 정점 달 차이 1개월 이내, 강도 3 이상, 데이터 24개월 이상, 묶음 내 규모 1 이상.
- 제외: 인증·규제 표시(flag)가 있는 시장, 상품 검색이 아닌 키워드(NON_PRODUCT).
- 정점 달이 약 3개월 뒤(ALERT_PEAK)인 시장만 `추천`, 나머지는 `신규`.
- 이미 있는 시장 파일은 덮어쓰지 않는다. 시트의 사용자 열(관심, 메모)은 보존한다.

사용법: .venv/bin/python research/tools/season_archive.py <research/raw/season/YYMMDD> --peak 2
"""
from __future__ import annotations

import argparse
import csv
import datetime
import os
import sys
import time
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

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
HEADERS = ["트랙", "시장명", "상태", "추천 점수", "정점 달", "시즌 강도", "추정 일판매", "상위 리뷰수", "평균가",
           "예상 마진", "조회수", "전환율", "한 줄 요약", "최종 갱신일", "저장소 파일", "사용자 관심", "사용자 메모"]
FONT, BOLD = Font(name="Arial"), Font(name="Arial", bold=True)
USER_FILL = PatternFill("solid", fgColor="FFF2CC")
HEAD_FILL = PatternFill("solid", fgColor="D9E1F2")
ALERT_FILL = PatternFill("solid", fgColor="FCE4D6")


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
""")
    return True


def read_user_columns(path: Path) -> dict:
    if not path.exists():
        return {}
    ws = load_workbook(path)["전체"]
    head = [c.value for c in ws[1]]
    n, i, m = head.index("시장명"), head.index("사용자 관심"), head.index("사용자 메모")
    return {row[n]: (row[i], row[m]) for row in ws.iter_rows(min_row=2, values_only=True) if row[n]}


def fill_header(ws, headers: list[str]) -> None:
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = BOLD, HEAD_FILL
    ws.freeze_panes = "A2"


def write_workbook(path: Path, selected: list[dict], status_of: dict, today: str, alert_peak: int) -> None:
    user = read_user_columns(path)
    selected = sorted(selected, key=lambda r: (status_of[r["name"]] != "추천", -float(r["strength"])))
    wb = Workbook()

    ws = wb.active
    ws.title = "전체"
    fill_header(ws, HEADERS)
    for r in selected:
        interest, memo = user.get(r["name"], (None, None))
        ws.append(["B", r["name"], status_of[r["name"]], None, int(r["peak_month"]), float(r["strength"]),
                   None, None, None, None, None, None, summary(r), today, f"research/markets/{r['name']}.md", interest, memo])
        ws.cell(ws.max_row, 16).fill = USER_FILL
        ws.cell(ws.max_row, 17).fill = USER_FILL
    for col, width in {"B": 20, "M": 58, "N": 12, "O": 34, "P": 12, "Q": 30}.items():
        ws.column_dimensions[col].width = width

    cal = wb.create_sheet("시즌 달력")
    fill_header(cal, ["정점 달", "준비 알림 달", "시장", "시장 수"])
    order = [(alert_peak + i - 1) % 12 + 1 for i in range(12)]
    for m in order:
        names = [r["name"] for r in selected if int(r["peak_month"]) == m]
        cal.append([f"{m}월", f"{(m - 4) % 12 + 1}월", ", ".join(names), len(names)])
    for c in cal[2]:
        c.fill = ALERT_FILL
    cal.column_dimensions["B"].width = 12
    cal.column_dimensions["C"].width = 110
    for row in cal.iter_rows(min_row=2):
        row[2].alignment = Alignment(wrap_text=True, vertical="top")

    new = wb.create_sheet("이번 주 신규")
    fill_header(new, ["시장명", "상태", "정점 달", "시즌 강도", "한 줄 요약"])
    for r in selected:
        new.append([r["name"], status_of[r["name"]], int(r["peak_month"]), float(r["strength"]), summary(r)])
    new.column_dimensions["A"].width = 20
    new.column_dimensions["E"].width = 58

    note = wb.create_sheet("안내")
    for line in [
        "노란 칸(사용자 관심, 사용자 메모)만 적어 주세요. 봇은 이 열을 지우지 않습니다.",
        "사용자 관심 칸에 관심 있는 시장은 o를 적습니다. 예: o",
        "시즌 강도 = 주기별 (정점 ÷ 중앙값)의 평균. 네이버 검색어 트렌드 상대값이라 시장 규모를 뜻하지 않습니다.",
        f"측정: {today}, 2023-11~2026-10 월별. 빈 칸(추정 일판매, 리뷰수, 가격, 마진, 조회수, 전환율)은 아직 조사하지 않은 값입니다.",
    ]:
        note.append([line])
    note.column_dimensions["A"].width = 100

    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for c in row:
                c.font = BOLD if (c.row == 1 and sheet.title != "안내") else FONT
    tmp = path.with_suffix(".tmp.xlsx")
    wb.save(tmp)
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--peak", type=int, required=True, help="약 3개월 뒤 정점 달")
    args = ap.parse_args()

    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("COUPANG_DRIVE_DIR="):
            env["dir"] = line.split("=", 1)[1].strip().strip("'\"")
    xlsx = Path(os.path.expanduser(env["dir"])) / "research" / "시장조사_아카이브.xlsx"
    if xlsx.exists() and time.time() - xlsx.stat().st_mtime < 300:
        print("아카이브가 5분 안에 수정됐다. 사용자가 편집 중일 수 있어 쓰지 않고 멈춘다.")
        return 2

    today = datetime.date.today().isoformat()
    selected = select(args.folder / "analysis.csv")
    status_of, created = {}, 0
    for r in selected:
        status_of[r["name"]] = "추천" if int(r["peak_month"]) == args.peak else "신규"
        created += write_market(r, status_of[r["name"]], today)
    write_workbook(xlsx, selected, status_of, today, args.peak)
    print(f"선정 {len(selected)}개, 새 시장 파일 {created}개, 추천 {sum(v == '추천' for v in status_of.values())}개")
    print("추천:", ", ".join(k for k, v in status_of.items() if v == "추천"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
