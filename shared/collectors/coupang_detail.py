"""쿠팡 상품 상세 이미지 전체 수집.

사용: python3 shared/collectors/coupang_detail.py <쿠팡 상품 URL> <저장 폴더>
예)  python3 shared/collectors/coupang_detail.py "https://www.coupang.com/vp/products/123" pdp/projects/foo/inputs/ref

결과: 001.jpg ... (상세 순서대로), detail_text.txt (HTML형 상세의 글자), manifest.json
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import (  # noqa: E402
    base_args, check_blocked, collect_images, dedupe, download_all, goto, open_page, run,
    scroll_into_view_all, scroll_to_bottom, wait, write_manifest,
)

# 위에서부터 먼저 맞는 것을 쓴다. 쿠팡이 구조를 바꾸면 여기만 고친다.
DETAIL_CONTAINERS = [
    "#productDetail .product-detail-content-inside",
    ".product-detail-content-inside",
    "#productDetail",
    ".product-detail-content",
    "[class*='productDetail']",
    "[id*='detail' i] [class*='content' i]",
]
SEE_MORE = [
    "button.product-detail-seemore-btn",
    ".product-detail-seemore-btn",
    "button:has-text('상품정보 더보기')",
    "a:has-text('상품정보 더보기')",
    "button:has-text('더보기'):near(#productDetail)",
]
NOISE_HOST = re.compile(r"static\.coupangcdn|front\.coupangcdn|img1a\.coupangcdn\.com/image/coupang/common", re.I)


def upgrade(url: str) -> str:
    """썸네일 리사이즈 주소 → 원본 주소. 실패하면 download_all 이 원래 주소로 다시 받는다."""
    return re.sub(r"//thumbnail(\d+)\.coupangcdn\.com/thumbnails/remote/[^/]+/image/", r"//image\1.coupangcdn.com/image/", url)


def main(args) -> None:
    with open_page(args) as page:
        print(f"열기: {args.url}")
        goto(page, args.url)
        wait("page")
        title = page.title()

        # 1) 상세 영역까지 내려가면서 지연 로딩 띄우기
        scroll_to_bottom(page)

        # 2) '상품정보 더보기' 펼치기
        opened = None
        for sel in SEE_MORE:
            loc = page.locator(sel).first
            try:
                if loc.count() and loc.is_visible():
                    loc.scroll_into_view_if_needed(timeout=3000)
                    wait("click")
                    loc.click(timeout=5000)
                    opened = sel
                    wait("click")
                    break
            except Exception:  # noqa: BLE001
                continue
        if opened:
            scroll_to_bottom(page)

        # 3) 상세 컨테이너 찾기
        container = next((s for s in DETAIL_CONTAINERS if page.locator(s).count()), None)
        if container:
            scroll_into_view_all(page, f"{container} img")
        check_blocked(page)

        items = collect_images(page, container)
        strategy = f"container:{container}"
        if not container or len(items) < 2:
            # 폴백: 페이지 전체에서 큰 쿠팡 CDN 이미지. 상단 갤러리(작은 썸네일)는 크기로 거른다
            items = [i for i in collect_images(page, None) if "coupangcdn" in i["src"] and (i["w"] >= 600 or i["dw"] >= 600)]
            strategy = "fallback:large-coupangcdn"
        items = [i for i in items if not NOISE_HOST.search(i["src"]) and max(i["w"], i["dw"]) >= 200]
        items = sorted(dedupe(items, key=lambda x: upgrade(x["src"])), key=lambda x: x["top"])
        print(f"상세 이미지 {len(items)}개 ({strategy}) 다운로드 시작")

        text = page.locator(container).first.inner_text() if container else ""
        args.outdir.mkdir(parents=True, exist_ok=True)
        if len(text.strip()) > 20:
            (args.outdir / "detail_text.txt").write_text(text.strip(), encoding="utf-8")

        results = download_all(page, items, args.outdir, upgrade=upgrade)
        ok = sum(r["status"] == "ok" for r in results)
        write_manifest(args.outdir, {
            "source_url": args.url, "title": title, "status": "ok" if ok else "empty",
            "strategy": strategy, "see_more": opened, "images_found": len(items), "images_saved": ok,
            "has_detail_text": len(text.strip()) > 20, "images": results,
        })
        print(f"완료: {ok}/{len(items)}장 → {args.outdir}")


if __name__ == "__main__":
    a = base_args("쿠팡 상세 이미지 수집").parse_args()
    run(main, a)
