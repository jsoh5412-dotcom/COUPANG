#!/usr/bin/env python3
"""트랙 B 시즌 스캔: 네이버 검색어 트렌드로 키워드별 반복 정점을 찾는다.

- 호출 1건에 시장 5개씩 묶는다. 결과는 research/raw/season/<YYMMDD>/에 저장하고, 이미 받은 묶음은 다시 호출하지 않는다.
- 호출마다 research/usage/naver_api_calls.csv에 기록한다. 키 값은 출력·기록하지 않는다.
- 이번 달 호출 합계(검색어 트렌드 + 쇼핑인사이트)가 --stop-at에 닿으면 멈춘다.
- 200이 아닌 응답이나 네트워크 오류가 나면 재시도하지 않고 멈춘다 (종료 코드 2).

사용법: python3 research/tools/season_scan.py [--limit 묶음수] [--start 2023-11-01 --end 2026-10-31]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USAGE = ROOT / "research" / "usage" / "naver_api_calls.csv"
KEYWORDS = Path(__file__).with_name("season_keywords.csv")
URL = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
API = "datalab_search_trend"


def read_env() -> tuple[str, str]:
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env["NAVER_CLIENT_ID"], env["NAVER_CLIENT_SECRET"]


def month_total(month: str) -> int:
    if not USAGE.exists():
        return 0
    with USAGE.open(newline="") as f:
        return sum(int(r["calls"]) for r in csv.DictReader(f) if r["date"].startswith(month))


def log_call(status, note: str) -> None:
    with USAGE.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.date.today().isoformat(), API, 1, status, note])


def load_groups() -> list[dict]:
    with KEYWORDS.open(newline="") as f:
        rows = list(csv.DictReader(f))
    seen, groups = set(), []
    for r in rows:
        if r["market"] in seen:
            continue
        seen.add(r["market"])
        groups.append({"groupName": r["market"], "keywords": r["keywords"].split("|")})
    return groups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="이번 실행에서 호출할 최대 묶음 수 (0은 전부)")
    ap.add_argument("--stop-at", type=int, default=450)
    ap.add_argument("--start", default="2023-11-01")
    ap.add_argument("--end", default="2026-10-31")
    args = ap.parse_args()

    today = datetime.date.today()
    out = ROOT / "research" / "raw" / "season" / today.strftime("%y%m%d")
    out.mkdir(parents=True, exist_ok=True)
    cid, secret = read_env()
    groups = load_groups()
    batches = [groups[i:i + 5] for i in range(0, len(groups), 5)]
    print(f"시장 {len(groups)}개, 묶음 {len(batches)}개")

    called = 0
    for n, batch in enumerate(batches, 1):
        path = out / f"batch_{n:03d}.json"
        if path.exists():
            continue
        if args.limit and called >= args.limit:
            break
        if month_total(today.strftime("%Y-%m")) >= args.stop_at:
            print(f"이번 달 호출이 {args.stop_at}건에 닿아 멈춤")
            return 2
        body = {"startDate": args.start, "endDate": args.end, "timeUnit": "month", "keywordGroups": batch}
        req = urllib.request.Request(
            URL,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "X-NCP-APIGW-API-KEY-ID": cid,
                "X-NCP-APIGW-API-KEY": secret,
                "Content-Type": "application/json",
            },
        )
        status, text = "no_response", ""
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                status, text = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode(errors="replace")
        except Exception as e:
            text = f"{type(e).__name__}: {e}"
        log_call(status, f"시즌 스캔 묶음 {n}/{len(batches)}")
        called += 1
        if status != 200:
            for s in (cid, secret):
                text = text.replace(s, "***")
            print(f"묶음 {n} 실패, 재시도 없이 멈춤. HTTP {status}: {text[:500]}")
            return 2
        path.write_text(text)
        time.sleep(0.5)

    print(f"이번 실행 호출 {called}건, 이번 달 합계 {month_total(today.strftime('%Y-%m'))}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
