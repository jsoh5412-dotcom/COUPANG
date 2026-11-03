#!/usr/bin/env python3
"""쿠팡 검색 1페이지 상위 상품을 읽어 search.json으로 남긴다 (로그인 없이 공개 페이지). 이미지는 받지 않는다.

사용: COLLECTOR_TEAM=research .venv/bin/python research/tools/coupang_search.py "<검색어>" research/raw/<폴더> [--n 40]
- 키워드 1건을 공용 상한에서 쓴다. 차단 징후면 run()이 그날 수집을 멈춘다.
- 파싱이 틀려도 다시 조회하지 않도록 카드 원문(raw)을 함께 저장한다.
"""
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared" / "collectors"))
from browser import base_args, check_blocked, goto, open_page, run, scroll_to_bottom, wait, write_manifest  # noqa: E402
from quota import use_quota  # noqa: E402

JS = """
(n) => {
  const out = [];
  const cards = document.querySelectorAll('#product-list > li, ul[class*=productList] > li, li.search-product');
  for (const li of cards) {
    const a = li.querySelector('a[href*="/vp/products/"]');
    if (!a) continue;
    const m = a.href.match(/products\\/(\\d+)/);
    const raw = (li.innerText || '').trim();
    const ad = !!li.querySelector('[class*=AdMark], .ad-badge') || /광고\\s*$/.test(raw);
    const delivery = [...li.querySelectorAll('img')].map(i => i.getAttribute('alt') || i.src || '').filter(s => /rocket|로켓/i.test(s));
    const name = (li.querySelector('[class*=productName], .name') || {}).innerText || '';
    out.push({rank: out.length + 1, product_id: m && m[1], href: a.href.split('?')[0], name: name.trim(), ad, delivery, raw});
    if (out.length >= n) break;
  }
  return out;
}
"""


def main(args) -> None:
    url = f"https://www.coupang.com/np/search?q={quote(args.url)}"
    if args.category:  # 검색어 자리에 카테고리 번호를 받아 판매량순 목록을 본다 (트랙 A 씨앗)
        url = f"https://www.coupang.com/np/categories/{args.url}?sorter=saleCountDesc&listSize=60"
    use_quota("keyword", url)
    with open_page(args) as page:
        print(f"열기: {url}")
        goto(page, url)
        wait("page")
        scroll_to_bottom(page, max_rounds=6)
        check_blocked(page)
        items = page.evaluate(JS, args.n)
        print(f"상품 {len(items)}개")
        args.outdir.mkdir(parents=True, exist_ok=True)
        (args.outdir / "search.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        write_manifest(args.outdir, {"query": args.url, "source_url": url, "status": "ok" if items else "empty", "items": len(items)})


if __name__ == "__main__":
    p = base_args("쿠팡 검색 1페이지 읽기")
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--category", action="store_true", help="첫 인자를 쿠팡 카테고리 번호로 본다")
    run(main, p.parse_args())
