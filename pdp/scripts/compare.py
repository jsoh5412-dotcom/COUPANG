"""레퍼런스 상세페이지와 우리 렌더를 같은 폭으로 나란히 붙인 비교 이미지.

사용: compare.py <out.png> <열1 폴더 또는 이미지> [<열2> ...] [--labels 바렌,더마풋,우리] [--col 390] [--parts 4]
- 폴더면 안의 이미지(jpg/png, pdp_full 제외)를 이름순으로 세로로 잇는다.
- 각 열은 --col 폭으로 줄이고 위에 라벨을 단다.
- --parts N 이면 <out>_partK.png로 세로 N등분도 함께 저장한다 (보기용).
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def column(src, w):
    p = Path(src)
    files = [p] if p.is_file() else sorted(
        f for f in p.iterdir()
        if f.suffix.lower() in (".jpg", ".jpeg", ".png") and not f.stem.startswith("pdp_full"))
    ims = []
    for f in files:
        im = Image.open(f).convert("RGB")
        ims.append(im.resize((w, round(im.height * w / im.width)), Image.LANCZOS))
    col = Image.new("RGB", (w, sum(i.height for i in ims)), "white")
    y = 0
    for im in ims:
        col.paste(im, (0, y)); y += im.height
    return col


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("cols", nargs="+")
    ap.add_argument("--labels", default="")
    ap.add_argument("--col", type=int, default=390)
    ap.add_argument("--gap", type=int, default=24)
    ap.add_argument("--parts", type=int, default=0)
    a = ap.parse_args()
    labels = a.labels.split(",") if a.labels else [Path(c).name for c in a.cols]
    cols = [column(c, a.col) for c in a.cols]
    head = 60
    W = len(cols) * a.col + (len(cols) - 1) * a.gap
    H = head + max(c.height for c in cols)
    out = Image.new("RGB", (W, H), (235, 235, 235))
    d = ImageDraw.Draw(out)
    font = ImageFont.truetype(FONT, 28)
    for i, (c, lab) in enumerate(zip(cols, labels)):
        x = i * (a.col + a.gap)
        d.text((x + 8, 14), f"{lab}  ({c.height * 780 // a.col:,}px)", fill=(20, 20, 20), font=font)
        out.paste(c, (x, head))
    out.save(a.out, optimize=True)
    print(a.out, out.size)
    if a.parts:
        step = -(-H // a.parts)
        stem = Path(a.out).with_suffix("")
        for k in range(a.parts):
            part = out.crop((0, k * step, W, min(H, (k + 1) * step)))
            part.save(f"{stem}_part{k + 1}.jpg", quality=80)


if __name__ == "__main__":
    main()
