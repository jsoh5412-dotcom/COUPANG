"""쿠팡 검색 결과 상위 상품의 대표이미지(썸네일)를 받는다. 썸네일 비교용 (로그인 없이 공개 페이지).

사용: .venv/bin/python pdp/scripts/search_thumbs.py "<검색어>" <outdir> [--n 8]
- 수집 전용 크롬(127.0.0.1:9222)에 붙어 새 탭 하나만 쓰고 닫는다 (shared/collectors/browser.py).
- 광고 표시가 붙은 상품은 건너뛴다. 원본 화질 주소로 바꿔 받는다.
"""
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared" / "collectors"))
from browser import base_args, check_blocked, download_all, goto, open_page, run, scroll_to_bottom, wait, write_manifest  # noqa: E402
from coupang_detail import upgrade  # noqa: E402
from quota import use_quota  # noqa: E402

JS = """
(n) => {
  const out = [];
  const cards = document.querySelectorAll('#product-list > li, ul[class*=productList] > li, li.search-product');
  for (const li of cards) {
    const text = li.innerText || '';
    if (/광고|AD\\b/.test(text.slice(0, 40)) || li.querySelector('[class*=AdMark], .ad-badge')) continue;
    const img = li.querySelector('img[src*="coupangcdn"]');
    const a = li.querySelector('a[href*="/vp/products/"]');
    if (!img || !a) continue;
    const name = (li.querySelector('[class*=productName], .name') || {}).innerText || '';
    out.push({src: img.currentSrc || img.src, href: a.href, name: name.trim(), w: img.naturalWidth, dw: img.width, top: out.length});
    if (out.length >= n) break;
  }
  return out;
}
"""


def main(args) -> None:
    url = f"https://www.coupang.com/np/search?q={quote(args.url)}"
    use_quota("keyword", url)
    with open_page(args) as page:
        print(f"열기: {url}")
        goto(page, url)
        wait("page")
        scroll_to_bottom(page, max_rounds=6)
        check_blocked(page)
        items = page.evaluate(JS, args.n)
        print(f"상품 {len(items)}개")
        res = download_all(page, items, args.outdir, upgrade=upgrade)
        write_manifest(args.outdir, {"query": args.url, "source_url": url, "images": res})


if __name__ == "__main__":
    p = base_args("쿠팡 검색 상위 썸네일 수집")
    p.add_argument("--n", type=int, default=8)
    run(main, p.parse_args())
