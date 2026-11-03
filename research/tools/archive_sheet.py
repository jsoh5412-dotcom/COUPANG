#!/usr/bin/env python3
"""시장조사 아카이브 구글 시트를 다룬다 (결정 46). 키 파일 내용은 읽거나 출력하지 않고 shared/sheets로만 쓴다.

사용법:
  .venv/bin/python research/tools/archive_sheet.py migrate     기존 xlsx를 탭·머리글까지 시트로 옮긴다. 시트가 비어 있을 때만 된다
  .venv/bin/python research/tools/archive_sheet.py sync --peak 2  research/markets 파일 내용으로 시트를 갱신한다

- 사용자 열(사용자 관심, 사용자 메모)은 upsert의 protected로 건너뛴다. 이 열을 포함한 범위에 write를 쓰지 않는다.
- 시즌 달력, 이번 주 신규, 안내 탭은 봇 소유라 통째로 다시 쓴다.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "sheets"))
from sheets import _services, read, upsert, write  # noqa: E402

SHEET_ID = "1csl3_-9J6Z-lGBcE7p_5RiccOTjRvjPi_ZYO7DaJrqc"
MARKETS = ROOT / "research" / "markets"
PROTECTED = ["사용자 관심", "사용자 메모"]
BOT_TABS = ["시즌 달력", "이번 주 신규", "안내"]
STATUS_ORDER = {"추천": 0, "관찰": 1, "신규": 2, "보류": 3}


def tab_titles() -> list[str]:
    sheets, _ = _services()
    meta = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    return [s["properties"]["title"] for s in meta["sheets"]]


def ensure_tabs(names: list[str]) -> None:
    sheets, _ = _services()
    meta = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    have = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    requests = [{"addSheet": {"properties": {"title": n}}} for n in names if n not in have]
    # 새 시트의 기본 탭은 비어 있을 때만 첫 탭 이름으로 바꾼다
    if names[0] not in have and len(have) == 1 and not read(SHEET_ID, f"'{next(iter(have))}'"):
        requests[0] = {"updateSheetProperties": {
            "properties": {"sheetId": next(iter(have.values())), "title": names[0]}, "fields": "title"}}
    if requests:
        sheets.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": requests}).execute()


def replace_bot_tab(name: str, rows: list[list]) -> None:
    """봇 소유 탭을 지우고 다시 쓴다. 사용자 열이 있는 전체 탭에는 쓰지 않는다."""
    if name not in BOT_TABS:
        sys.exit(f"[거부] {name} 탭은 봇 소유가 아니다")
    sheets, _ = _services()
    sheets.spreadsheets().values().clear(spreadsheetId=SHEET_ID, range=f"'{name}'").execute()
    write(SHEET_ID, f"'{name}'!A1", rows)


def migrate() -> int:
    from openpyxl import load_workbook

    tabs = tab_titles()
    if any(read(SHEET_ID, f"'{t}'") for t in tabs):
        sys.exit("[거부] 시트가 비어 있지 않다. migrate는 빈 시트에만 한다")
    drive = next(l.split("=", 1)[1].strip().strip("'\"") for l in (ROOT / ".env").read_text().splitlines()
                 if l.startswith("COUPANG_DRIVE_DIR="))
    wb = load_workbook(Path(os.path.expanduser(drive)) / "research" / "시장조사_아카이브.xlsx")
    ensure_tabs(wb.sheetnames)
    ws = wb["전체"]
    header = [c.value for c in ws[1]]
    write(SHEET_ID, "'전체'!A1", [header])
    rows = [{k: ("" if v is None else v) for k, v in zip(header, row)} for row in ws.iter_rows(min_row=2, values_only=True)]
    print("전체:", upsert(SHEET_ID, "전체", key="시장명", rows=rows, protected=PROTECTED))
    for name in BOT_TABS:
        grid = [["" if v is None else v for v in row] for row in wb[name].iter_rows(values_only=True)]
        replace_bot_tab(name, grid)
        print(f"{name}: {len(grid)}행")
    return 0


def parse_market(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    head = text.split("---", 2)[1]

    def field(name: str) -> str:
        m = re.search(rf"^\s*{name}:\s*(.*?)\s*(#.*)?$", head, re.M)
        value = m.group(1).strip() if m else ""
        return "" if value == "null" else value

    summary = re.search(r"## 요약\n(.+)", text)
    peak = re.search(r"peak_months:\s*\[(\d+)", head)
    return {
        "트랙": field("track"), "시장명": field("market"), "상태": field("status"), "추천 점수": field("score"),
        "정점 달": int(peak.group(1)) if peak else "", "시즌 강도": field("season_strength"),
        "추정 일판매": field("est_daily_sales_top"), "상위 리뷰수": field("top_review_count_median"),
        "평균가": field("avg_price"), "예상 마진": field("est_margin"), "조회수": field("wing_views_30d"),
        "전환율": field("est_conversion"), "한 줄 요약": summary.group(1).strip() if summary else "",
        "최종 갱신일": field("measured_at"), "저장소 파일": f"research/markets/{path.name}",
    }


def sync(peak_now: int) -> int:
    today = datetime.date.today().isoformat()
    rows = [parse_market(p) for p in sorted(MARKETS.glob("*.md")) if p.name != "_TEMPLATE.md"]
    rows.sort(key=lambda r: (STATUS_ORDER.get(r["상태"], 9), r["시장명"]))
    print("전체:", upsert(SHEET_ID, "전체", key="시장명", rows=[{k: v for k, v in r.items()} for r in rows], protected=PROTECTED))
    active = [r for r in rows if r["상태"] != "보류"]
    order = [(peak_now + i - 1) % 12 + 1 for i in range(12)]
    calendar = [["정점 달", "준비 알림 달", "시장", "시장 수"]]
    for m in order:
        names = [r["시장명"] for r in active if r["정점 달"] == m]
        calendar.append([f"{m}월", f"{(m - 4) % 12 + 1}월", ", ".join(names), len(names)])
    replace_bot_tab("시즌 달력", calendar)
    changed = [r for r in rows if r["최종 갱신일"] == today]
    weekly = [["시장명", "상태", "정점 달", "시즌 강도", "한 줄 요약"]]
    weekly += [[r["시장명"], r["상태"], r["정점 달"], r["시즌 강도"], r["한 줄 요약"]] for r in changed]
    replace_bot_tab("이번 주 신규", weekly)
    print(f"시즌 달력 {len(calendar) - 1}행, 이번 주 신규 {len(weekly) - 1}행")
    mark_user_columns()
    return 0


def mark_user_columns() -> None:
    """전체 탭의 첫 행을 고정하고 사용자 열에 노란 배경을 넣는다. 서식만 바꾸고 값은 건드리지 않는다."""
    sheets, _ = _services()
    meta = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    tab = next(s["properties"]["sheetId"] for s in meta["sheets"] if s["properties"]["title"] == "전체")
    header = read(SHEET_ID, "'전체'!1:1")[0]
    requests = [{"updateSheetProperties": {
        "properties": {"sheetId": tab, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}}]
    for name in PROTECTED:
        at = header.index(name)
        requests.append({"repeatCell": {
            "range": {"sheetId": tab, "startColumnIndex": at, "endColumnIndex": at + 1, "startRowIndex": 1},
            "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1, "green": 0.95, "blue": 0.8}}},
            "fields": "userEnteredFormat.backgroundColor"}})
    sheets.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": requests}).execute()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["migrate", "sync"])
    ap.add_argument("--peak", type=int, default=2, help="약 3개월 뒤 정점 달")
    args = ap.parse_args()
    return migrate() if args.command == "migrate" else sync(args.peak)


if __name__ == "__main__":
    sys.exit(main())
