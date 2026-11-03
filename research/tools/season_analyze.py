#!/usr/bin/env python3
"""season_scan.py 결과에서 시장별 반복 정점을 계산해 analysis.csv로 남긴다. API를 호출하지 않는다.

- 36개월을 12개월씩 3주기로 나눠 주기마다 정점 달을 찾는다. 응답에 없는 달은 0으로 본다.
- 반복: 세 주기 정점 달의 차이가 모두 1개월 이내 (달력은 순환, 12월과 1월은 1개월 차이).
- 강도: 주기별 (정점 ÷ 그 주기 중앙값)의 평균. 네이버 수치는 상대값이라 묶음이 다르면 규모는 비교할 수 없다.

사용법: python3 research/tools/season_analyze.py <research/raw/season/YYMMDD>
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

KEYWORDS = Path(__file__).with_name("season_keywords.csv")


def month_gap(a: int, b: int) -> int:
    d = abs(a - b) % 12
    return min(d, 12 - d)


def analyze(months: list[str], values: dict[str, float]) -> dict:
    series = [values.get(m, 0.0) for m in months]
    cycles = [(months[i:i + 12], series[i:i + 12]) for i in range(0, len(series), 12)]
    peaks, strengths, heights = [], [], []
    for ms, vs in cycles:
        top = max(vs)
        peaks.append(int(ms[vs.index(top)][5:7]))
        heights.append(top)
        strengths.append(top / max(statistics.median(vs), 0.01))
    common = Counter(peaks).most_common(1)[0]
    if common[1] > 1:
        peak = common[0]
    else:
        peak = min(peaks, key=lambda p: sum(month_gap(p, q) for q in peaks))
    return {
        "peaks": peaks,
        "peak_month": peak,
        "repeat": all(month_gap(a, b) <= 1 for a in peaks for b in peaks),
        "strength": round(statistics.mean(strengths), 1),
        "last_vs_first": round(heights[-1] / max(heights[0], 0.01), 2),
        "scale_in_batch": round(max(series), 2),
    }


def main() -> int:
    folder = Path(sys.argv[1])
    with KEYWORDS.open(newline="") as f:
        meta = {r["market"]: r for r in csv.DictReader(f)}
    months = [f"{y}-{m:02d}" for y, m in [(2023, 11), (2023, 12)] + [(2024 + i // 12, i % 12 + 1) for i in range(34)]]
    rows = []
    for path in sorted(folder.glob("batch_*.json")):
        for res in json.loads(path.read_text())["results"]:
            values = {d["period"][:7]: d["ratio"] for d in res["data"]}
            r = analyze(months, values)
            rows.append({
                "market": res["title"],
                "flag": meta[res["title"]]["flag"],
                "keywords": meta[res["title"]]["keywords"],
                "peak_month": r["peak_month"],
                "peaks": "/".join(map(str, r["peaks"])),
                "repeat": r["repeat"],
                "strength": r["strength"],
                "last_vs_first": r["last_vs_first"],
                "scale_in_batch": r["scale_in_batch"],
                "batch": path.stem,
                "months_with_data": len(values),
            })
    with (folder / "analysis.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"시장 {len(rows)}개, 반복 {sum(r['repeat'] for r in rows)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
