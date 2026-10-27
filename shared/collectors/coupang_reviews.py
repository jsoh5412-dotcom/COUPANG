"""쿠팡 상품 리뷰 여러 페이지 수집.

사용: python3 shared/collectors/coupang_reviews.py <쿠팡 상품 URL> <저장 폴더> [--pages 10] [--sort recent|best]
결과: reviews.jsonl (1줄 1리뷰), reviews.md (사람이 읽는 용), pages/page_XX.txt (파싱 실패 대비 원문), manifest.json

페이지 사이에는 사람 속도 대기(PACE['page'])를 넣는다. 다음 페이지가 없거나 --pages 에 닿으면 끝.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import base_args, check_blocked, goto, open_page, run, scroll_to_bottom, wait, write_manifest  # noqa: E402

REVIEW_SECTION = ["#sdpReview", ".sdp-review", "[id*='review' i]", "section:has-text('상품평')"]
REVIEW_TAB = ["a[href='#sdpReview']", "li[name='review']", "a:has-text('상품평')", "button:has-text('상품평')", "a:has-text('리뷰')"]
ARTICLE = ["article.sdp-review__article__list", ".sdp-review__article__list", "article[class*='review' i]", "[class*='review-item' i]"]
PAGER = [".sdp-review__article__page", "[class*='review' i] [class*='pag' i]", "[class*='pagination' i]"]
NEXT_BLOCK = [".sdp-review__article__page__next", "button[class*='next' i]", "a[class*='next' i]"]
SORT = {"recent": "최신순", "best": "베스트순"}

JS_PARSE = r"""
(sel) => [...document.querySelectorAll(sel)].map(a => {
  const q = s => a.querySelector(s);
  const txt = s => (q(s)?.innerText || '').trim();
  let rating = null;
  const r = q('[data-rating]');
  if (r) rating = Number(r.getAttribute('data-rating'));
  if (rating === null) {
    const star = q('[class*="star"][style*="width"]');
    const m = star && star.getAttribute('style').match(/width:\s*(\d+)%/);
    if (m) rating = Math.round(Number(m[1]) / 20);
  }
  if (rating === null) {
    const al = q('[aria-label*="별점"], [aria-label*="점"]');
    const m = al && al.getAttribute('aria-label').match(/(\d(\.\d)?)/);
    if (m) rating = Number(m[1]);
  }
  const all = a.innerText.trim();
  const date = (all.match(/20\d{2}[.\-/]\s?\d{1,2}[.\-/]\s?\d{1,2}/) || [null])[0];
  return {
    rating, date,
    option: txt('.sdp-review__article__list__info__product-info__name') || null,
    headline: txt('.sdp-review__article__list__headline') || null,
    body: txt('.sdp-review__article__list__review__content') || txt('[class*="review__content"]') || null,
    helpful: Number(q('[data-count]')?.getAttribute('data-count') || 0) || null,
    survey: txt('.sdp-review__article__list__survey') || null,
    has_photo: !!q('[class*="attachment"] img, [class*="photo"] img'),
    raw: all,
  };
})
"""


def first_present(page, sels):
    return next((s for s in sels if page.locator(s).count()), None)


def click_first(page, sels) -> str | None:
    for s in sels:
        loc = page.locator(s).first
        try:
            if loc.count() and loc.is_visible():
                loc.scroll_into_view_if_needed(timeout=3000)
                wait("click")
                loc.click(timeout=5000)
                return s
        except Exception:  # noqa: BLE001
            continue
    return None


def go_to_page(page, pager: str, n: int) -> bool:
    """n 페이지 버튼을 누른다. 보이는 번호 묶음에 없으면 '다음' 묶음으로 넘긴 뒤 다시 찾는다."""
    for _ in range(2):
        cands = [
            page.locator(f"{pager} [data-page='{n}']").first,
            page.locator(pager).get_by_role("button", name=str(n), exact=True).first,
            page.locator(pager).get_by_text(str(n), exact=True).first,
        ]
        for c in cands:
            try:
                if c.count() and c.is_visible():
                    c.scroll_into_view_if_needed(timeout=3000)
                    wait("click")
                    c.click(timeout=5000)
                    return True
            except Exception:  # noqa: BLE001
                continue
        if not click_first(page, [f"{pager} {s}" for s in NEXT_BLOCK] + NEXT_BLOCK):
            return False
        wait("page")
    return False


def key(r: dict) -> str:
    return hashlib.md5(f"{r.get('date')}|{r.get('body') or r['raw']}".encode()).hexdigest()


def main(args) -> None:
    with open_page(args) as page:
        print(f"열기: {args.url}")
        goto(page, args.url)
        wait("page")
        title = page.title()

        tab = click_first(page, REVIEW_TAB)
        if not tab:
            scroll_to_bottom(page)
        section = first_present(page, REVIEW_SECTION)
        if section:
            page.locator(section).first.scroll_into_view_if_needed(timeout=5000)
        wait("page")

        sorted_by = None
        if args.sort:
            label = SORT[args.sort]
            if click_first(page, [f"{section or 'body'} button:has-text('{label}')", f"{section or 'body'} a:has-text('{label}')"]):
                sorted_by = label
                wait("page")
        check_blocked(page)

        article = first_present(page, ARTICLE)
        if not article:
            raise SystemExit("리뷰 목록을 찾지 못했습니다. ARTICLE 선택자를 확인하세요 (manifest 미작성).")
        pager = first_present(page, PAGER)

        pages_dir = args.outdir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        reviews, seen, page_log = [], set(), []
        for n in range(1, args.pages + 1):
            if n > 1:
                before = page.locator(article).first.inner_text()
                if not pager or not go_to_page(page, pager, n):
                    print(f"{n}페이지 버튼 없음 → 종료")
                    break
                # 목록이 바뀔 때까지 대기 (최대 15초)
                try:
                    page.wait_for_function(
                        "([sel, prev]) => { const a = document.querySelector(sel); return a && a.innerText !== prev; }",
                        arg=[article, before], timeout=15_000,
                    )
                except Exception:  # noqa: BLE001
                    print(f"{n}페이지: 목록이 바뀌지 않음 → 종료")
                    break
                wait("page")
                check_blocked(page)

            got = page.evaluate(JS_PARSE, article)
            (pages_dir / f"page_{n:02d}.txt").write_text("\n\n---\n\n".join(g["raw"] for g in got), encoding="utf-8")
            new = 0
            for g in got:
                k = key(g)
                if k not in seen:
                    seen.add(k)
                    reviews.append({"page": n, **g})
                    new += 1
            page_log.append({"page": n, "found": len(got), "new": new})
            print(f"  {n}페이지: {len(got)}개 (신규 {new})")
            if new == 0:
                print("신규 리뷰 없음 → 종료")
                break

        with open(args.outdir / "reviews.jsonl", "w", encoding="utf-8") as f:
            for r in reviews:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        write_md(args.outdir / "reviews.md", title, args.url, reviews)
        dist = Counter(r["rating"] for r in reviews)
        write_manifest(args.outdir, {
            "source_url": args.url, "title": title, "status": "ok" if reviews else "empty",
            "selectors": {"tab": tab, "section": section, "article": article, "pager": pager},
            "sorted_by": sorted_by, "pages_read": len(page_log), "reviews": len(reviews),
            "rating_parsed": sum(r["rating"] is not None for r in reviews),
            "body_parsed": sum(bool(r["body"]) for r in reviews),
            "rating_distribution": {str(k): v for k, v in sorted(dist.items(), key=lambda x: str(x[0]))},
            "pages": page_log,
        })
        print(f"완료: 리뷰 {len(reviews)}개, {len(page_log)}페이지 → {args.outdir}")


def write_md(path: Path, title: str, url: str, reviews: list[dict]) -> None:
    lines = [f"# 리뷰 수집: {title}", "", f"- 출처: {url}", f"- 개수: {len(reviews)}", ""]
    for i, r in enumerate(reviews, 1):
        star = "★" * int(r["rating"]) if r["rating"] else "?"
        lines += [f"## {i}. {star} {r['date'] or ''} {('· ' + r['option']) if r['option'] else ''}".rstrip()]
        if r["headline"]:
            lines.append(f"**{r['headline']}**")
        lines += [r["body"] or r["raw"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    p = base_args("쿠팡 리뷰 수집")
    p.add_argument("--pages", type=int, default=10)
    p.add_argument("--sort", choices=list(SORT), default=None)
    run(main, p.parse_args())
