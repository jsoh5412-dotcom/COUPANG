"""상세 이미지 폴더 → 글자 크기순 헤드라인 목록 (카피 참고집 재료).

사용: .venv/bin/python pdp/scripts/headlines.py <ocr 실행파일> <상세 이미지 폴더> [<폴더> ...] [--min 44]
- ocr 실행파일: pdp/scripts/ocr.swift를 컴파일한 것.
- 이미지 폭을 780px로 환산한 글자 높이가 --min 이상이면 헤드라인(##), 30 이상이면 보조(-)로 적는다.
- 결과는 폴더마다 headlines.md로 저장하고 경로를 출력한다. 수집 원본과 같은 폴더라 커밋되지 않는다.
"""
import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image

EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ocr")
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--min", type=int, default=44)
    a = ap.parse_args()
    for d in a.dirs:
        files = sorted(f for f in d.iterdir() if f.suffix.lower() in EXT)
        if not files:
            continue
        widths = {}
        for f in files:
            try:
                widths[f.name] = Image.open(f).width
            except Exception:  # noqa: BLE001
                pass
        files = [f for f in files if f.name in widths]
        out = subprocess.run([a.ocr, *map(str, files)], capture_output=True, text=True).stdout
        title = ""
        man = d / "manifest.json"
        if man.exists():
            title = json.loads(man.read_text()).get("title", "")
        lines = [f"# {d.name} {title}", ""]
        for row in map(json.loads, filter(None, out.splitlines())):
            h = row["h"] * 780 / widths[row["file"]]
            if h >= a.min:
                lines.append(f"## {row['text']}  ({row['file']}, {h:.0f})")
            elif h >= 30:
                lines.append(f"- {row['text']}")
        (d / "headlines.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(d / "headlines.md", len(lines) - 2)


if __name__ == "__main__":
    main()
