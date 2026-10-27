"""쿠팡 대표이미지(썸네일) 1000×1000 생성.

흰 배경 가운데에 누끼를 비율 그대로 맞춰 넣고, 바닥 그림자만 코드로 만든다.
제품의 형태·색은 바꾸지 않는다 (균일 확대·축소만). 글자는 넣지 않는다.

사용: python3 pdp/scripts/thumbnail.py <누끼.png> <출력.jpg> [--fill 0.82] [--size 1000] [--bottom]
  --bottom: 어깨선처럼 아래가 잘린 착용 사진용. 아래 가장자리에 붙이고 그림자는 넣지 않는다.
"""
from __future__ import annotations

import argparse

from PIL import Image, ImageFilter


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("nukki")
    p.add_argument("out")
    p.add_argument("--fill", type=float, default=0.82, help="제품이 차지할 최대 비율 (가로·세로 중 긴 쪽)")
    p.add_argument("--size", type=int, default=1000)
    p.add_argument("--bottom", action="store_true", help="아래 가장자리에 붙이기 (착용 사진)")
    a = p.parse_args()

    S = a.size
    src = Image.open(a.nukki).convert("RGBA")
    src = src.crop(src.getbbox())  # 투명 여백 제거
    scale = min(S * a.fill / src.width, S * a.fill / src.height)
    prod = src.resize((round(src.width * scale), round(src.height * scale)), Image.LANCZOS)

    canvas = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    x = (S - prod.width) // 2
    if a.bottom:
        canvas.alpha_composite(prod, (x, S - prod.height))
        canvas.convert("RGB").save(a.out, quality=95)
        print(f"ok {a.out} {S}x{S} product {prod.width}x{prod.height} (scale {scale:.2f}, bottom)")
        return
    y = (S - prod.height) // 2 - round(S * 0.015)

    # 바닥 그림자: 제품 아래쪽에 납작한 타원을 흐리게
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sw, shh = round(prod.width * 0.9), max(14, round(S * 0.035))
    ell = Image.new("L", (sw, shh), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(ell).ellipse((0, 0, sw - 1, shh - 1), fill=70)
    sh.paste((0, 0, 0, 255), ((S - sw) // 2, y + prod.height - shh // 2), ell)
    sh = sh.filter(ImageFilter.GaussianBlur(S * 0.012))
    canvas = Image.alpha_composite(canvas, sh)

    canvas.alpha_composite(prod, (x, y))
    canvas.convert("RGB").save(a.out, quality=95)
    print(f"ok {a.out} {S}x{S} product {prod.width}x{prod.height} (scale {scale:.2f})")


if __name__ == "__main__":
    main()
