#!/usr/bin/env python3
"""쿠팡 상품 상세 공개 페이지에서 시장 판단용 값만 읽어 product.json으로 남긴다. 이미지는 받지 않는다.

사용: COLLECTOR_TEAM=research .venv/bin/python research/tools/coupang_product.py <상품 URL> research/raw/<폴더>
- 상세 1건을 공용 상한에서 쓴다. 차단 징후면 run()이 그날 수집을 멈춘다.
- 파싱이 틀려도 다시 조회하지 않도록 ld+json과 본문 앞부분 원문을 함께 저장한다.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared" / "collectors"))
from browser import base_args, check_blocked, goto, open_page, run, wait, write_manifest  # noqa: E402
from quota import use_quota  # noqa: E402

JS = """
() => ({
  title: document.title,
  text: (document.body ? document.body.innerText : '').slice(0, 12000),
  ldjson: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent),
  breadcrumb: [...document.querySelectorAll('[class*=breadcrumb] a, #breadcrumb a')].map(a => a.innerText.trim()).filter(Boolean),
  options: [...document.querySelectorAll('[class*=option] li, [class*=Option] li, select option')].map(o => o.innerText.trim()).filter(Boolean).slice(0, 80),
})
"""


def main(args) -> None:
    use_quota("detail", args.url)
    with open_page(args) as page:
        print(f"열기: {args.url}")
        goto(page, args.url)
        wait("page")
        page.mouse.wheel(0, 700)
        wait("scroll")
        check_blocked(page)
        got = page.evaluate(JS)
    badge = re.search(r"한 달간\s*([\d,]+)\s*명 이상", got["text"])
    got["badge_month"] = int(badge.group(1).replace(",", "")) if badge else None
    got["source_url"] = args.url
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "product.json").write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
    write_manifest(args.outdir, {"source_url": args.url, "status": "ok", "badge_month": got["badge_month"]})
    print(f"배지 {got['badge_month']}, 옵션 후보 {len(got['options'])}개")


if __name__ == "__main__":
    run(main, base_args("쿠팡 상품 상세 값 읽기").parse_args())
