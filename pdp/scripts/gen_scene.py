"""AI 장면 이미지 생성 (OpenAI 이미지 API). 제품이 없는 배경·인물·신체 장면만 만든다 (콘텐츠 원칙 4).

사용: python3 pdp/scripts/gen_scene.py <출력.png> "<프롬프트>" [--size 1024x1536] [--quality medium]
- 키는 .env 의 OPENAI_API_KEY (값을 출력하지 않는다).
- 실제 사용 토큰과 추정 비용을 pdp/projects/<슬러그>/output/image_cost.jsonl 같은 기록 파일에 한 줄씩 남긴다 (--log).
- 프롬프트 끝에 "제품·글자·로고 없음" 조건을 항상 붙인다.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NO_PRODUCT = (" No foot file, no tools, no products of any kind, no packaging, no text, no letters, no logos, no watermarks."
              " Photorealistic commercial photography, natural skin, anatomically correct feet and hands with five toes each.")
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
    p.add_argument("--size", default="1024x1536")
    p.add_argument("--quality", default="medium")
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--log", type=Path, required=True)
    a = p.parse_args()
    body = json.dumps({"model": a.model, "prompt": a.prompt + NO_PRODUCT, "size": a.size, "quality": a.quality, "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
                                 headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"})
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
    rec = {"file": str(a.out), "model": a.model, "size": a.size, "quality": a.quality, "usage": u,
           "usd": round(usd, 4), "krw": round(usd * KRW), "sec": round(time.time() - t, 1)}
    a.log.parent.mkdir(parents=True, exist_ok=True)
    with a.log.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
