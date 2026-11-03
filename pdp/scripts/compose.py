"""제품 없는 장면 위에 공급처 누끼를 그림자와 함께 합성한다. 제품의 형태·색은 바꾸지 않는다 (균일 확대·축소와 회전만).

사용: .venv/bin/python pdp/scripts/compose.py <장면> <누끼.png> <출력.jpg> --scale 0.4 --angle -62 --xy 70,600 [--soft 20,20,16,.26] [--hard 4,5,4,.42] [--over 장면 마스크.png]
- --soft / --hard: 그림자 x,y,번짐,진하기. 빛이 오는 반대쪽으로 민다. 멀리 번지는 그림자와 닿는 곳의 진한 그림자를 함께 써야 떠 보이지 않는다.
- --over: 흰색 부분의 장면을 제품 위에 다시 얹는다 (고리, 손가락처럼 제품 앞에 있어야 할 것).
"""
from __future__ import annotations

import argparse

from PIL import Image, ImageChops, ImageFilter


def shadow(bg: Image.Image, product: Image.Image, xy: tuple[int, int], spec: str) -> None:
    dx, dy, blur, strength = (float(v) for v in spec.split(","))
    a = Image.new("L", bg.size, 0)
    a.paste(product.getchannel("A"), xy)
    a = ImageChops.offset(a, int(dx), int(dy)).filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * strength))
    bg.paste(Image.new("RGB", bg.size, (40, 50, 70)), (0, 0), a)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("scene")
    p.add_argument("nukki")
    p.add_argument("out")
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--angle", type=float, default=0.0)
    p.add_argument("--xy", required=True)
    p.add_argument("--soft", default="20,20,16,.26")
    p.add_argument("--hard", default="4,5,4,.42")
    p.add_argument("--over")
    a = p.parse_args()
    scene = Image.open(a.scene).convert("RGB")
    bg = scene.copy()
    prod = Image.open(a.nukki).convert("RGBA")
    prod = prod.resize((round(prod.width * a.scale), round(prod.height * a.scale)), Image.LANCZOS).rotate(a.angle, expand=True, resample=Image.BICUBIC)
    xy = tuple(int(v) for v in a.xy.split(","))
    shadow(bg, prod, xy, a.soft)
    shadow(bg, prod, xy, a.hard)
    bg.paste(prod, xy, prod)
    if a.over:
        bg.paste(scene, (0, 0), Image.open(a.over).convert("L"))
    bg.save(a.out, quality=95)
    print(a.out, bg.size)


if __name__ == "__main__":
    main()
