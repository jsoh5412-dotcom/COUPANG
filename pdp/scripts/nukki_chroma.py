"""채도가 높은 단색 배경(분홍·하늘 등) 공급처 사진에서 무채색 제품의 누끼를 선명하게 딴다.

사용: .venv/bin/python pdp/scripts/nukki_chroma.py <입력> <출력.png> --box x0,y0,x1,y1 [--scale 2] [--sat 33]
- 제품의 형태·색은 바꾸지 않는다. 가장자리에 번진 배경색만 뺀다.
- --box는 사진 테두리(흰 여백)를 빼고 배경만 네 모서리에 닿게 잡는다. 모서리가 배경이 아니면 배경을 못 지운다.
- 흰 배경 사진이나 채도 높은 제품에는 맞지 않는다. 그럴 때는 nukki.swift를 쓴다.
"""
from __future__ import annotations

import argparse

from PIL import Image, ImageChops, ImageDraw, ImageFilter

Image.MAX_IMAGE_PIXELS = None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--box", required=True)
    p.add_argument("--scale", type=int, default=2)
    p.add_argument("--sat", type=int, default=33, help="이 채도(0~255)보다 낮으면 제품으로 본다")
    a = p.parse_args()
    box = tuple(int(v) for v in a.box.split(","))
    im = Image.open(a.src).convert("RGB").crop(box)
    im = im.resize((im.width * a.scale, im.height * a.scale), Image.LANCZOS)
    sat = im.convert("HSV").split()[1].filter(ImageFilter.MedianFilter(5))
    mask = sat.point(lambda v: 255 if v < a.sat else 0)
    # 네 모서리에서 이어진 곳만 바깥 배경으로 본다
    outside = mask.copy()
    w, h = outside.size
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if outside.getpixel(corner) == 0:
            ImageDraw.floodfill(outside, corner, 128)
    bg = outside.point(lambda v: 255 if v == 128 else 0).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    # 걸이 구멍처럼 제품 안쪽의 배경 덩어리는 투명으로 남고, 잔티끌만 메워진다
    alpha = ImageChops.multiply(ImageChops.invert(bg), mask.filter(ImageFilter.MaxFilter(3)))
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    edge = alpha.point(lambda v: 255 if 0 < v < 250 else 0).filter(ImageFilter.MaxFilter(3))
    rgb = Image.composite(im.convert("L").convert("RGB"), im, edge)
    rgb.putalpha(alpha)
    out = rgb.crop(alpha.point(lambda v: 255 if v > 20 else 0).getbbox())
    out.save(a.out)
    print(a.out, out.size)


if __name__ == "__main__":
    main()
