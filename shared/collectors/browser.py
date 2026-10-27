"""수집기 공통: 브라우저 연결, 사람 속도 대기, 차단 감지, 스크롤, 이미지 다운로드, 결과 기록.

연결 방식
- cdp (기본): start_chrome.sh / start_chrome.ps1 로 띄운 크롬(전용 프로필)에 붙는다.
  사용자가 그 창에서 직접 로그인해 두면 쿠키를 그대로 쓴다. 사용자의 다른 탭은 건드리지 않는다.
- launch: 플레이라이트가 전용 프로필로 크롬을 직접 띄운다. cdp 연결이 안 될 때만 쓴다.

차단·로그인·캡차를 만나면 Blocked 를 던지고 멈춘다. 우회하거나 재시도하지 않는다 (pdp/CLAUDE.md).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

DEFAULT_CDP = "http://127.0.0.1:9222"
DEFAULT_PROFILE = Path.home() / ".coupang-collector-profile"

# 사람 속도 대기 (초). 페이지 이동 > 다운로드 > 스크롤 순으로 길게.
PACE = {
    "page": (4.0, 8.0),
    "download": (0.8, 2.0),
    "scroll": (0.5, 1.2),
    "click": (1.0, 2.5),
}

BLOCK_PATTERNS = [
    ("access_denied", re.compile(r"access denied|접근이 거부|요청하신 페이지에 접근할 수 없", re.I)),
    ("captcha", re.compile(r"captcha|보안문자|로봇이 아닙니다|robot check|滑动验证|请按住滑块|拖动下方滑块|验证码", re.I)),
    ("rate_limited", re.compile(r"too many requests|일시적으로 차단|비정상적인 접근", re.I)),
]
BLOCK_URL_PATTERNS = [
    ("login_required", re.compile(r"login\.(1688|taobao|tmall)\.com|/member/login|passport\.|/login\.php|login\.coupang\.com", re.I)),
    ("captcha", re.compile(r"/punish|_____tmd_____|x5secdata|/captcha", re.I)),
]


class Blocked(Exception):
    def __init__(self, reason: str, url: str):
        super().__init__(f"{reason} @ {url}")
        self.reason, self.url = reason, url


# 오프라인 테스트 전용 배속. 실사이트에서는 절대 켜지 않는다
_SPEED = 0.02 if os.environ.get("COLLECTOR_FAST") == "1" else 1.0


def wait(kind: str) -> None:
    lo, hi = PACE[kind]
    time.sleep(random.uniform(lo, hi) * _SPEED)


def base_args(desc: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("url")
    p.add_argument("outdir", type=Path)
    p.add_argument("--mode", choices=["cdp", "launch"], default="cdp")
    p.add_argument("--cdp", default=os.environ.get("COLLECTOR_CDP", DEFAULT_CDP))
    p.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="launch 모드 전용 프로필 폴더")
    p.add_argument("--headless", action="store_true", help="테스트용. 실사이트에서는 쓰지 않는다")
    return p


@contextmanager
def open_page(args):
    """새 탭 하나를 열어 넘겨주고, 끝나면 그 탭만 닫는다."""
    with sync_playwright() as pw:
        if args.mode == "cdp":
            try:
                browser = pw.chromium.connect_over_cdp(args.cdp)
            except Exception as e:  # noqa: BLE001
                sys.exit(
                    f"[연결 실패] {args.cdp} 에 크롬이 없습니다. 먼저 shared/collectors/start_chrome 스크립트로 크롬을 띄우세요.\n{e}"
                )
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            try:
                yield page
            finally:
                page.close()
                browser.close()  # cdp 연결만 끊는다. 크롬 창은 그대로 남는다
        else:
            exe = os.environ.get("CHROMIUM_PATH")
            kw = {"executable_path": exe} if exe else {"channel": "chrome"}
            ctx = pw.chromium.launch_persistent_context(
                str(args.profile), headless=args.headless, viewport={"width": 1280, "height": 900}, locale="ko-KR", **kw
            )
            page = ctx.new_page()
            try:
                yield page
            finally:
                ctx.close()


def goto(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:  # noqa: BLE001  광고·추적 스크립트 때문에 idle 이 안 오는 사이트가 많다
        pass
    check_blocked(page)


def check_blocked(page: Page) -> None:
    for reason, pat in BLOCK_URL_PATTERNS:
        if pat.search(page.url):
            raise Blocked(reason, page.url)
    try:
        title = page.title()
        text = page.evaluate("() => (document.body ? document.body.innerText : '').slice(0, 3000)")
    except Exception:  # noqa: BLE001
        return
    for reason, pat in BLOCK_PATTERNS:
        if pat.search(title) or pat.search(text):
            raise Blocked(reason, page.url)
    if len(text.strip()) < 30 and not page.query_selector("img"):
        raise Blocked("empty_page", page.url)


def scroll_to_bottom(page: Page, max_rounds: int = 120) -> int:
    """지연 로딩이 끝날 때까지 한 화면씩 내린다. 높이가 3번 연속 안 늘면 끝으로 본다."""
    last, still = 0, 0
    for _ in range(max_rounds):
        page.mouse.wheel(0, random.randint(600, 900))
        wait("scroll")
        if _SPEED < 1:
            time.sleep(0.05)  # 테스트에서도 지연 로딩이 반응할 최소 시간
        height = page.evaluate("() => document.documentElement.scrollHeight")
        at_bottom = page.evaluate("() => window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 5")
        if at_bottom:
            still = still + 1 if height == last else 0
            if still >= 3:
                break
        last = height
    check_blocked(page)
    return last


def scroll_into_view_all(page: Page, selector: str) -> None:
    """컨테이너 안 이미지마다 화면에 한 번씩 보여서 지연 로딩을 확실히 띄운다."""
    n = page.locator(selector).count()
    for i in range(n):
        try:
            page.locator(selector).nth(i).scroll_into_view_if_needed(timeout=3000)
            time.sleep(random.uniform(0.15, 0.4))
        except Exception:  # noqa: BLE001
            pass


JS_DEEP_QUERY = """
const deepAll = (root, sel) => {
  const out = [...root.querySelectorAll(sel)];
  if (root.shadowRoot) out.push(...deepAll(root.shadowRoot, sel));
  for (const el of root.querySelectorAll('*')) if (el.shadowRoot) out.push(...deepAll(el.shadowRoot, sel));
  return out;
};
"""

JS_COLLECT_IMAGES = """
(sel) => {
  %s
  const roots = sel ? deepAll(document, sel) : [document];
  const out = [];
  for (const root of roots) {
    for (const img of deepAll(root, 'img')) {""" % JS_DEEP_QUERY + """
      const cands = [img.currentSrc, img.getAttribute('src'), img.dataset.src, img.dataset.original,
                     img.dataset.lazySrc, img.dataset.lazyload, img.dataset.imgUrl, img.getAttribute('data-ks-lazyload')];
      const srcset = img.getAttribute('srcset') || img.dataset.srcset;
      if (srcset) cands.push(srcset.split(',').pop().trim().split(' ')[0]);
      const src = cands.find(s => s && !s.startsWith('data:') && !/blank|spacer|loading|placeholder/i.test(s));
      if (!src) continue;
      const r = img.getBoundingClientRect();
      out.push({ src: new URL(src, location.href).href, w: img.naturalWidth, h: img.naturalHeight,
                 dw: Math.round(r.width), top: Math.round(r.top + scrollY) });
    }
  }
  return out;
}
"""


def collect_images(page: Page, selector: str | None) -> list[dict]:
    """메인 문서와 모든 iframe 에서 이미지를 모은다 (상세가 iframe 인 사이트가 있다)."""
    items = []
    for frame in page.frames:
        try:
            got = frame.evaluate(JS_COLLECT_IMAGES, selector)
        except Exception:  # noqa: BLE001
            continue
        for g in got:
            g["frame"] = "main" if frame == page.main_frame else frame.url
        items += got
    return items


def dedupe(items: list[dict], key=lambda x: x["src"]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        k = key(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif|avif)", re.I)


def _ext(url: str, content_type: str) -> str:
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    m = EXT_RE.search(urlparse(url).path)
    return "." + m.group(1).lower().replace("jpeg", "jpg") if m else ".jpg"


def download_all(page: Page, items: list[dict], outdir: Path, upgrade=None) -> list[dict]:
    """브라우저 쿠키·리퍼러를 그대로 써서 순서대로 받는다. upgrade(url)->url 은 원본 화질 주소 변환."""
    outdir.mkdir(parents=True, exist_ok=True)
    req = page.context.request
    results = []
    for i, it in enumerate(items, 1):
        tries = [upgrade(it["src"]), it["src"]] if upgrade else [it["src"]]
        tries = list(dict.fromkeys(t for t in tries if t))
        rec = {**it, "index": i, "status": "failed"}
        for url in tries:
            try:
                r = req.get(url, headers={"Referer": page.url}, timeout=60_000)
            except Exception as e:  # noqa: BLE001
                rec["error"] = str(e)[:200]
                continue
            ctype = r.headers.get("content-type", "")
            if r.ok and ctype.startswith("image"):
                body = r.body()
                path = outdir / f"{i:03d}{_ext(url, ctype)}"
                path.write_bytes(body)
                rec.update(status="ok", url=url, file=path.name, bytes=len(body))
                rec.pop("error", None)
                break
            rec["error"] = f"HTTP {r.status} {ctype}"
        results.append(rec)
        print(f"  [{i}/{len(items)}] {rec['status']} {rec.get('file', rec.get('error', ''))}")
        wait("download")
    return results


def write_manifest(outdir: Path, data: dict) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    data = {"collected_at": datetime.now().isoformat(timespec="seconds"), **data}
    path = outdir / "manifest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run(main_fn, args) -> None:
    """공통 실행 래퍼: 차단이면 manifest 에 남기고 종료코드 2."""
    try:
        main_fn(args)
    except Blocked as b:
        write_manifest(args.outdir, {"source_url": args.url, "status": "blocked", "reason": b.reason, "blocked_url": b.url})
        print(
            f"\n[막힘] {b.reason} — {b.url}\n"
            "재시도·우회하지 않고 멈춥니다. 크롬 창에서 로그인/보안확인을 직접 끝낸 뒤 한 번만 다시 돌리거나,\n"
            "2순위(상세 이미지 직접 업로드 / 리뷰 복붙)로 전환하세요.",
            file=sys.stderr,
        )
        sys.exit(2)
