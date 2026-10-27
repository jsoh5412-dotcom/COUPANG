"""수집기 오프라인 테스트: 로컬 가짜 페이지로 스크롤·지연로딩·더보기·섀도DOM·리뷰 페이지 넘김·차단 감지를 확인한다.

실행: python3 shared/collectors/tests/test_offline.py
실사이트 선택자가 맞는지는 이 테스트로 알 수 없다. 그건 TEST_REPORT.md 의 실사이트 테스트로 확인한다.
"""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
COLLECTORS = HERE.parent
FIX = HERE / "fixtures"


def make_site(root: Path) -> None:
    """픽스처 HTML 을 임시 폴더로 복사하고 이미지는 거기서 생성한다 (저장소에 바이너리를 두지 않는다)."""
    for f in FIX.glob("*.html"):
        shutil.copy(f, root / f.name)
    d = root / "img"
    d.mkdir(exist_ok=True)
    for i in range(1, 6):
        Image.new("RGB", (780, 1000), (40 * i, 120, 200)).save(d / f"d{i}.png")
    for i in (1, 2):
        Image.new("RGB", (100, 100), (200, 200, 200)).save(d / f"thumb{i}.png")


def serve(root: Path) -> str:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


def run(script: str, url: str, out: Path, *extra: str) -> int:
    env = {**os.environ, "COLLECTOR_FAST": "1"}
    if Path("/opt/pw-browsers/chromium").exists():
        env.setdefault("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
    cmd = [sys.executable, str(COLLECTORS / script), url, str(out), "--mode", "launch", "--headless",
           "--profile", str(out.parent / f"profile_{out.name}"), *extra]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300).returncode


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    site = tmp / "site"
    site.mkdir()
    make_site(site)
    base = serve(site)
    fails = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail else ""))
        if not cond:
            fails.append(name)

    out = tmp / "detail"
    rc = run("coupang_detail.py", f"{base}/coupang_product.html", out)
    m = json.loads((out / "manifest.json").read_text())
    check("쿠팡 상세: 지연로딩 5장 모두 저장", rc == 0 and m["images_saved"] == 5, f"rc={rc} saved={m.get('images_saved')}")
    check("쿠팡 상세: 썸네일·아이콘 제외, 순서 유지", [i["src"].rsplit("/", 1)[-1] for i in m["images"]] == [f"d{i}.png" for i in range(1, 6)])
    check("쿠팡 상세: 더보기 클릭", bool(m["see_more"]))
    check("쿠팡 상세: HTML 텍스트 저장", (out / "detail_text.txt").exists())

    out = tmp / "reviews"
    rc = run("coupang_reviews.py", f"{base}/coupang_product.html", out, "--pages", "5")
    m = json.loads((out / "manifest.json").read_text())
    check("쿠팡 리뷰: 3페이지 15개, 버튼 없으면 종료", rc == 0 and m["pages_read"] == 3 and m["reviews"] == 15, f"pages={m.get('pages_read')} n={m.get('reviews')}")
    check("쿠팡 리뷰: 별점·본문 파싱", m["rating_parsed"] == 15 and m["body_parsed"] == 15)

    out = tmp / "supplier"
    rc = run("supplier_detail.py", f"{base}/supplier_1688.html", out, "--site", "1688")
    m = json.loads((out / "manifest.json").read_text())
    check("1688: 섀도DOM 상세 4장 (컨테이너로)", rc == 0 and m["images_saved"] == 4 and m["strategy"].startswith("container"), f"rc={rc} saved={m.get('images_saved')} {m.get('strategy')}")
    check("1688: 속성 텍스트 저장", "304" in (out / "spec_text.txt").read_text())

    out = tmp / "domeggook"
    rc = run("supplier_detail.py", f"{base}/supplier_domeggook.html", out, "--site", "domeggook")
    m = json.loads((out / "manifest.json").read_text())
    names = [i["src"].rsplit("/", 1)[-1] for i in m["images"]]
    check("도매꾹: 상세 본문 3장만 (추천상품·대표 썸네일 제외)", rc == 0 and names == ["d1.png", "d2.png", "d3.png"], f"rc={rc} {names}")
    check("도매꾹: 폴백 없이 #lInfoViewItemContents", m["strategy"] == "container:#lInfoViewItemContents", m.get("strategy"))
    check("도매꾹: 판매자 목록 '더보기'(새 탭) 안 누름", m["see_more"] is None, str(m.get("see_more")))
    check("도매꾹: 상품정보 텍스트 저장", "원산지" in (out / "spec_text.txt").read_text())

    out = tmp / "domeggook_single"
    rc = run("supplier_detail.py", f"{base}/supplier_domeggook_single.html", out, "--site", "domeggook")
    m = json.loads((out / "manifest.json").read_text())
    names = [i["src"].rsplit("/", 1)[-1] for i in m["images"]]
    check("도매꾹: 긴 상세 1장이어도 폴백하지 않음", rc == 0 and names == ["d1.png"] and m["strategy"].startswith("container"), f"{m.get('strategy')} {names}")

    out = tmp / "blocked"
    rc = run("coupang_detail.py", f"{base}/blocked.html", out)
    m = json.loads((out / "manifest.json").read_text())
    check("차단 감지: 종료코드 2, 재시도 없이 기록", rc == 2 and m["status"] == "blocked" and m["reason"] == "access_denied")

    print(f"\n{'모두 통과' if not fails else f'실패 {len(fails)}건'}  (결과물: {tmp})")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
