"""공급처(1688·도매꾹·도매매) 상세 이미지 수집.

사용: python3 shared/collectors/supplier_detail.py <공급처 URL> <저장 폴더> [--site 1688|domeggook]
예)  python3 shared/collectors/supplier_detail.py "https://detail.1688.com/offer/123.html" pdp/projects/foo/inputs/source

결과: 001.jpg ... (상세 순서대로), spec_text.txt (속성표·상품정보 글자), manifest.json
번역·판독은 shared/translate 에서 한다. 여기서는 원본을 빠짐없이 받는 것까지만.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import (  # noqa: E402
    base_args, check_blocked, collect_images, dedupe, download_all, goto, open_page, run,
    scroll_into_view_all, scroll_to_bottom, wait, write_manifest,
)

SITES = {
    "1688": {
        "detail": [
            "#detailContentContainer", ".content-detail", "#desc-lazyload-container", ".html-description",
            "[class*='detail-desc' i]", "[class*='description' i]",
        ],
        "spec": [".offer-attr", ".od-pc-attribute", "[class*='attribute' i]", "[class*='offer-attr' i]"],
        "see_more": ["text=查看全部详情", "text=展开全部", "text=查看更多"],
        "noise": re.compile(r"/tps/|gw\.alicdn\.com/imgextra/.*-2-tps|\.gif$|/icon|avatar|logo", re.I),
        "min_w": 400,
    },
    "domeggook": {
        # 상세 본문은 #lInfoView 안의 #lInfoViewItemContents 다 (2026-10 실사이트 확인).
        # 예전 첫 후보 #lInfoBody 는 큰 이미지가 거의 없어 폴백(페이지 전체)으로 빠졌고, 추천상품 썸네일 100여 장이 섞였다.
        "detail": [
            "#lInfoViewItemContents", "#lInfoView", "#lInfoBody", "#itemDetail", ".lItemDetail", "#lDetail",
        ],
        "spec": ["#lInfoNotice", "[id*='notice' i] table", "table:has-text('상품정보제공고시')", "table:has-text('원산지')"],
        # "더보기"는 상세 영역 안에서만 찾는다. 페이지 전체에서 찾으면 판매자 상품목록 링크(target=_blank)를 눌러 새 탭이 남았다.
        "see_more": [
            "#lInfoView button:has-text('상세정보 펼치기')", "#lInfoView a:has-text('상세정보 더보기')",
            "#lInfoView button:has-text('더보기')",
        ],
        "noise": re.compile(r"/common/|/btn_|/icon|/banner|logo|\.gif$", re.I),
        "min_w": 300,
        # 도매꾹 상세는 긴 이미지 1장으로 된 경우가 많다 → 상세 본문에 큰 이미지가 1장만 있어도 폴백하지 않는다
        "min_items": 1,
    },
}


def detect_site(url: str) -> str:
    host = urlparse(url).netloc
    if "1688.com" in host:
        return "1688"
    if "domeggook.com" in host or "domeme" in host:
        return "domeggook"
    raise SystemExit(f"지원하지 않는 공급처입니다: {host} (--site 로 지정 가능)")


def upgrade(url: str) -> str:
    """alicdn 리사이즈·webp 접미사 제거 → 원본. 예) xxx.jpg_400x400.jpg, xxx.jpg_.webp → xxx.jpg"""
    if "alicdn.com" in url:
        return re.sub(r"(\.(?:jpe?g|png|gif|webp))_[^/]*$", r"\1", url)
    return url


def main(args) -> None:
    site = args.site or detect_site(args.url)
    cfg = SITES[site]
    with open_page(args) as page:
        print(f"열기({site}): {args.url}")
        goto(page, args.url)
        wait("page")
        title = page.title()

        scroll_to_bottom(page)
        opened = None
        for sel in cfg["see_more"]:
            loc = page.locator(sel).first
            try:
                if loc.count() and loc.is_visible():
                    loc.scroll_into_view_if_needed(timeout=3000)
                    wait("click")
                    loc.click(timeout=5000)
                    opened = sel
                    wait("click")
                    scroll_to_bottom(page)
                    break
            except Exception:  # noqa: BLE001
                continue

        container = next((s for s in cfg["detail"] if page.locator(s).count()), None)
        if container:
            scroll_into_view_all(page, f"{container} img")
        check_blocked(page)

        items = collect_images(page, container)
        strategy = f"container:{container}"
        big = lambda i: max(i["w"], i["dw"]) >= cfg["min_w"]  # noqa: E731
        if not container or sum(map(big, items)) < cfg.get("min_items", 2):
            # 폴백: 첫 화면 아래의 큰 이미지 전부 (상단 갤러리는 위치로 거른다)
            items = [i for i in collect_images(page, None) if i["top"] > 900]
            strategy = "fallback:large-below-fold"
        items = [i for i in items if big(i) and not cfg["noise"].search(i["src"])]
        items = sorted(dedupe(items, key=lambda x: upgrade(x["src"])), key=lambda x: x["top"])
        print(f"상세 이미지 {len(items)}개 ({strategy}) 다운로드 시작")

        args.outdir.mkdir(parents=True, exist_ok=True)
        spec_sel = next((s for s in cfg["spec"] if page.locator(s).count()), None)
        spec = page.locator(spec_sel).first.inner_text().strip() if spec_sel else ""
        if spec:
            (args.outdir / "spec_text.txt").write_text(spec, encoding="utf-8")

        results = download_all(page, items, args.outdir, upgrade=upgrade)
        ok = sum(r["status"] == "ok" for r in results)
        write_manifest(args.outdir, {
            "source_url": args.url, "site": site, "title": title, "status": "ok" if ok else "empty",
            "strategy": strategy, "see_more": opened, "spec_selector": spec_sel,
            "images_found": len(items), "images_saved": ok, "images": results,
        })
        print(f"완료: {ok}/{len(items)}장 → {args.outdir}")


if __name__ == "__main__":
    p = base_args("공급처 상세 이미지 수집")
    p.add_argument("--site", choices=list(SITES), default=None)
    run(main, p.parse_args())
