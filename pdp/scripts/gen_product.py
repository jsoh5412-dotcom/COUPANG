"""실제 제품 사진을 기준으로 제품이 들어간 장면을 만든다 (OpenAI 이미지 편집 API). 사용자 지시가 있는 작업에서만 쓴다.

사용: python3 pdp/scripts/gen_product.py <출력.png> "<프롬프트>" --image <기준 사진> [--image ...] --log <비용 기록> [--size 1024x1536] [--quality high]
- 키는 .env 의 OPENAI_API_KEY (값을 출력하지 않는다).
- 만든 뒤에는 실제 제품 사진과 나란히 놓고 형태·색·돌기를 대조한다.
"""
from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEEP = (" Keep the product exactly as in the reference photo: same shape, proportions, color, parts and surface details."
        " Do not add logos, text, watermarks or extra products."
        " Photorealistic commercial photography, natural hands and feet with five fingers or toes each.")
# gpt-image-2 공식 Standard 단가 (USD / 1M 토큰, OpenAI Pricing 페이지 2026-11-03 확인): 텍스트 입력 5, 이미지 입력 8, 이미지 출력 30
PRICE = {"text": 5 / 1e6, "image": 8 / 1e6, "output": 30 / 1e6}
KRW = 1400  # 환율 가정


def key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("OPENAI_API_KEY 없음")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("prompt")
    p.add_argument("--image", action="append", required=True, type=Path)
    p.add_argument("--size", default="1024x1536")
    p.add_argument("--quality", default="high")
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--log", type=Path, required=True)
    a = p.parse_args()
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in (("model", a.model), ("prompt", a.prompt + KEEP), ("size", a.size), ("quality", a.quality), ("n", "1")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for f in a.image:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="{f.name}"\r\nContent-Type: image/png\r\n\r\n'.encode() + f.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=b"".join(parts),
                                 headers={"Authorization": f"Bearer {key()}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:  # 키는 출력하지 않고 오류 본문만
        raise SystemExit(f"API 오류 {e.code}: {e.read().decode()[:500]}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(base64.b64decode(res["data"][0]["b64_json"]))
    u = res.get("usage", {})
    d = u.get("input_tokens_details", {})
    usd = d.get("text_tokens", u.get("input_tokens", 0)) * PRICE["text"] + d.get("image_tokens", 0) * PRICE["image"] + u.get("output_tokens", 0) * PRICE["output"]
    rec = {"file": str(a.out), "model": a.model, "mode": "edit", "size": a.size, "quality": a.quality, "usage": u,
           "usd": round(usd, 4), "krw": round(usd * KRW), "sec": round(time.time() - t, 1)}
    with a.log.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(a.out.name, rec["krw"], "원", u.get("input_tokens"), u.get("output_tokens"))


if __name__ == "__main__":
    main()
