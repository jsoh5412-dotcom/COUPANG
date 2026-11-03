#!/usr/bin/env python3
"""도매꾹·도매매 OpenAPI 상품 목록으로 소싱처 존재 여부와 대략 원가를 본다 (getItemList v4.1). 공급처에 연락하지 않는다.

사용: python3 research/tools/domeggook_list.py <저장 폴더> [--kw 검색어 | --ca 카테고리] [--market supply|dome] [--so ha] [--sz 50]
- 호출마다 research/usage/domeggook_api_calls.csv에 기록한다. 키 값은 출력·기록하지 않는다.
- 200이 아니거나 응답에 errors가 있으면 재시도하지 않고 멈춘다 (종료 코드 2).
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USAGE = ROOT / "research" / "usage" / "domeggook_api_calls.csv"
URL = "https://www.domeggook.com/ssl/api/"


def read_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("DOMEGGOOK_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("DOMEGGOOK_API_KEY가 .env에 없다")


def log_call(status, note: str) -> None:
    new = not USAGE.exists()
    with USAGE.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "api", "calls", "status", "note"])
        w.writerow([datetime.date.today().isoformat(), "getItemList", 1, status, note])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--kw")
    ap.add_argument("--ca")
    ap.add_argument("--market", default="supply", choices=["supply", "dome"])
    ap.add_argument("--so", default="ha")
    ap.add_argument("--sz", type=int, default=50)
    args = ap.parse_args()
    key = read_key()

    params = {"ver": "4.1", "mode": "getItemList", "aid": key, "market": args.market, "om": "json",
              "sz": args.sz, "pg": 1, "so": args.so}
    if args.kw:
        params["kw"] = args.kw
    if args.ca:
        params["ca"] = args.ca
    note = f"{args.market} {args.kw or args.ca} so={args.so}"
    status, text = "no_response", ""
    try:
        with urllib.request.urlopen(f"{URL}?{urllib.parse.urlencode(params)}", timeout=30) as r:
            status, text = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode(errors="replace")
    except Exception as e:
        text = f"{type(e).__name__}"
    log_call(status, note)
    text = text.replace(key, "***")
    if status != 200 or '"errors"' in text[:200]:
        print(f"실패, 재시도 없이 멈춤. {note} HTTP {status}: {text[:400]}")
        return 2
    args.outdir.mkdir(parents=True, exist_ok=True)
    name = f"{args.market}_{args.kw or args.ca}_{args.so}.json".replace(" ", "")
    (args.outdir / name).write_text(text, encoding="utf-8")
    data = json.loads(text)["domeggook"]
    header = data.get("header", {})
    print(f"{note}: 전체 {header.get('numberOfItems')}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
