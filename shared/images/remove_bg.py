"""누끼(배경 제거). 사용법: python3 shared/images/remove_bg.py <입력이미지|폴더> <출력.png|폴더>

rembg(무료, 로컬) 사용. 머리카락·투명 소재처럼 어려운 컷은 결과를 확인하고,
부족하면 remove.bg / Photoroom API로 교체한다.
"""
import sys
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def run(src: Path, dst: Path, session) -> None:
    img = Image.open(src).convert("RGBA")
    out = remove(img, session=session, post_process_mask=True)
    bbox = out.getbbox()  # 투명 여백 잘라내기
    if bbox:
        out = out.crop(bbox)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    print(f"{src} -> {dst} {out.size}")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    session = new_session("isnet-general-use")
    if src.is_dir():
        for f in sorted(p for p in src.iterdir() if p.suffix.lower() in EXTS):
            run(f, dst / f"{f.stem}_nukki.png", session)
    else:
        run(src, dst, session)


if __name__ == "__main__":
    main()
