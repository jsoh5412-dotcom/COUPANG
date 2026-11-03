"""page.json 제목과 이미지를 검사한다: 한 페이지 안 같은 제목·같은 사진, 다른 상품과 겹치는 첫 화면·공감·마무리 문구, 어색한 띄어쓰기.

사용: python3 pdp/scripts/lint_copy.py <슬러그> [<슬러그> ...]
- 비교 대상은 pdp/projects/ 아래 page.json이 있는 모든 상품이다. 인자로 준 상품끼리, 그리고 나머지 상품과 비교한다.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "projects"
LABELS = {"자주 묻는 질문", "주의사항", "제품 정보", "한눈에 보기", "색상"}
KEYS = {"hero", "empathy", "finale"}
BAD = [r"\S\s(예요|이에요|이 써요|해요\b)", r"\s(을|를|은|는|이|가)\s(?=[가-힣])"]


def plain(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


def titles(sec: dict) -> str:
    return plain(" ".join(str(sec[k]) for k in ("h1", "big", "h") if sec.get(k)))


def images(obj) -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("img", "img2") and isinstance(v, str):
                out.append(v)
            else:
                out += images(v)
    elif isinstance(obj, list):
        for v in obj:
            out += images(v)
    return out


def main() -> None:
    pages = {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in ROOT.glob("*/page.json")}
    problems = 0
    for slug in sys.argv[1:]:
        secs = pages[slug]["sections"]
        ts = [titles(s) for s in secs if titles(s)]
        for t, n in Counter(ts).items():
            if n > 1 and t not in LABELS:
                print(f"{slug}: 제목 반복 {n}번: {t}")
                problems += 1
        for f, n in Counter(images(secs)).items():
            if not (ROOT / slug / f).exists():
                print(f"{slug}: 사진 없음: {f}")
                problems += 1
            if n > 1:
                print(f"{slug}: 사진 반복 {n}번: {f}")
                problems += 1
        for s in secs:
            t = titles(s)
            if s["type"] in KEYS:
                for other, pg in pages.items():
                    if other != slug and any(titles(x) == t for x in pg["sections"]):
                        print(f"{slug}: {s['type']} 문구가 {other}와 같음: {t}")
                        problems += 1
            text = plain(json.dumps(s, ensure_ascii=False))
            for pat in BAD:
                for m in re.finditer(pat, text):
                    print(f"{slug}: 띄어쓰기 확인: ...{text[max(0, m.start() - 8):m.end() + 6]}...")
    print("문제", problems)


if __name__ == "__main__":
    main()
