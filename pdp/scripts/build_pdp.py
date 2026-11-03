"""page.json을 읽어 v5 톤 상세페이지 pdp.html을 만든다 (템플릿 templates/v5.css, v5.js).

사용: python3 pdp/scripts/build_pdp.py pdp/projects/<슬러그>
- page.json의 sections를 순서대로 그린다. 글자에 <br>, <span class="hl">, <em>을 쓸 수 있다.
- 이미지 경로는 프로젝트 폴더 기준이다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_END = 'style="border-bottom:2px solid var(--line)"'
ICON = {
    "soft": '<path d="M14 66c14 8 54 8 68 0"/><path d="M48 14v34M36 38l12 12 12-12"/>',
    "no": '<circle cx="48" cy="48" r="36"/><path d="M23 23l50 50"/>',
    "stop": '<path d="M32 8h32l24 24v32L64 88H32L8 64V32z"/><path d="M34 48h28"/>',
    "drop": '<path d="M48 12c14 20 24 32 24 46a24 24 0 0 1-48 0c0-14 10-26 24-46z"/>',
    "child": '<circle cx="48" cy="32" r="16"/><path d="M20 84c2-18 14-28 28-28s26 10 28 28"/><path d="M12 12l72 72"/>',
    "wide": '<path d="M10 48h76M24 34L10 48l14 14M72 34l14 14-14 14"/>',
    "foot": '<path d="M38 10v44c0 8 6 12 14 14l20 6c8 2 8 14-2 14H36c-10 0-16-8-16-18V10z"/>',
}


def img(src, style=""):
    st = f' style="{style}"' if style else ""
    return f'<img src="{src}"{st} alt="">'


def hero(s):
    a, b = s["seals"]
    band = " &nbsp;/&nbsp; ".join(s["band"])
    return f'''<section class="s01">
  <img class="bg" src="{s['img']}" alt=""><div class="veil"></div>
  <div class="copy"><h1 style="font-size:{s.get('size', 74)}px">{s['h1']}</h1><h1 style="margin-top:6px"><b style="margin-top:0;font-size:{s.get('bigsize', 130)}px">{s['big']}</b></h1>
  <div class="sub" style="padding:0 20px">{s['sub']}</div></div>
  <div class="seal a"><small>{a[0]}</small><b style="font-size:{a[2] if len(a) > 2 else 62}px">{a[1]}</b></div>
  <div class="seal b"><small>{b[0]}</small><b style="font-size:{b[2] if len(b) > 2 else 62}px">{b[1]}</b></div>
  <div class="band">{band}</div>
</section>'''


def empathy(s):
    st = "height:640px" if s.get("stack") else ""
    grid = ' style="grid-template-columns:1fr"' if s.get("stack") else ""
    figs = "".join(f'<figure>{img(c["img"], st)}<figcaption><b>{c["t"]}</b>{c["c"]}</figcaption></figure>' for c in s["cuts"])
    return f'<section><div class="head"><h2 style="font-size:{s.get("size", 62)}px">{s["h"]}</h2></div><div class="grid4"{grid}>{figs}</div></section>'


def turn(s):
    a, b = s["discs"]
    return f'''<section class="s03 pale"><h2 style="font-size:{s.get('size', 64)}px">{s['h']}</h2><p>{s['p']}</p>
  <div class="two"><div class="disc" style="background:#fff">{img(a['img'], a.get('style', ''))}</div><div class="arr"></div><div class="disc" style="background:#fff">{img(b['img'], b.get('style', ''))}</div></div>
  <div class="labels"><span>{a['t']}</span><span style="color:var(--blue)">{b['t']}</span></div></section>'''


def intro(s):
    top = f'<div class="ph-full">{img(s["img"])}</div>' if s.get("img") else ""
    fs = "".join(f'<div class="f">{img(c["img"], "height:" + str(s.get("h2", 560)) + "px;" + c.get("style", ""))}<div class="cap"><b>{c["t"]}</b><span>{c["c"]}</span></div></div>' for c in s["steps"])
    return f'<section class="s04"><div class="head"><h2 style="font-size:{s.get("size", 68)}px">{s["h"]}</h2></div>{top}<div class="step-row">{fs}</div></section>'


def overview(s):
    g = "".join(f'<div><b>{i[0]}</b><span>{i[1]}</span></div>' for i in s["items"])
    extra = s.get("svg", "")
    return f'<section class="spec pale"><div class="tt">한눈에 보기</div><img class="pic" data-slot="spec" src="{s["img"]}" style="{s.get("style", "")}" alt=""><div class="grid">{g}</div>{extra}</section>'


def number(s):
    tag = f'<div class="tag" style="left:24px;bottom:24px">{s["tag"]}</div>' if s.get("tag") else ""
    bg = ' style="background:#fff"' if s.get("white") else ""
    pic = f'<div class="ph-full"{bg}>{img(s["img"], s.get("style", ""))}{tag}</div>' if s.get("img") else ""
    cls = "num pale" if s.get("pale") else "num"
    return f'''<section class="{cls}"><div class="top"><div class="point">{s['point']}</div><div class="big" style="font-size:{s.get('bigsize', 280)}px">{s['big']}<small style="font-size:{s.get('smallsize', 150)}px">{s.get('unit', '')}</small></div>
  <h2>{s['h']}</h2><div class="why">{s['why']}</div></div>{pic}</section>'''


def feature(s):
    cls = ' class="pale"' if s.get("pale") else ""
    p = f'<div class="sum"><p>{s["p"]}</p></div>' if s.get("p") else '<div style="height:80px"></div>'
    pt = f'<div class="point">{s["point"]}</div>' if s.get("point") else ""
    return f'<section{cls}><div class="hdline">{pt}<h2 style="font-size:{s.get("size", 66)}px">{s["h"]}</h2></div><div class="ph-full">{img(s["img"], s.get("style", ""))}</div>{p}</section>'


def compare(s):
    cols = s["cols"]
    colg = '<col class="lb">' + "<col>" * len(cols)
    head = "<tr><th></th>" + "".join(f"<th>{c}</th>" for c in cols[:-1]) + f'<th class="us">{cols[-1]}</th></tr>'
    rows = "".join("<tr><td>" + r[0] + "</td>" + "".join(f"<td>{c}</td>" for c in r[1:-1]) + f'<td class="us">{r[-1]}</td></tr>' for r in s["rows"])
    return f'''<section class="cmp"><div class="head"><h2 style="font-size:{s.get('size', 64)}px">{s['h']}</h2></div><table><colgroup>{colg}</colgroup>{head}{rows}</table>
  <div class="tbn">유형별 일반적인 구성이며, 제품마다 다를 수 있어요.</div></section>'''


def notice(s):
    return f'<section class="pale"><div class="hdline" style="padding-bottom:30px"><h2 style="font-size:{s.get("size", 68)}px">{s["h"]}</h2></div><div class="sum" style="padding-top:10px"><p>{s["p"]}</p></div></section>'


def howto(s):
    n = len(s["steps"])
    out = []
    for i, c in enumerate(s["steps"]):
        st = CHECK_END if i == n - 1 else ""
        out.append(f'<div class="step" {st}><div class="ph" style="background:var(--pale)">{img(c["img"], c.get("style", ""))}</div><div class="tx"><b>STEP {i + 1}</b><span>{c["c"]}</span>{"<i>" + c["i"] + "</i>" if c.get("i") else ""}</div></div>')
    return f'<section class="s11"><div class="head"><h2 style="font-size:{s.get("size", 60)}px">{s["h"]}</h2></div>{"".join(out)}<div style="height:90px"></div></section>'


def checklist(s):
    n = len(s["items"])
    li = "".join(f"<li {CHECK_END if i == n - 1 else ''}>{t}</li>" for i, t in enumerate(s["items"]))
    return f'<section class="s13"><h2>{s["h"]}</h2><ul data-check>{li}</ul></section>'


def colors(s):
    figs = "".join(f'<figure><div class="box" style="background:#fff">{img(c["img"])}</div><figcaption>{c["t"]}</figcaption></figure>' for c in s["items"])
    return f'<section class="pale"><div class="head"><h2 style="font-size:{s.get("size", 64)}px">{s["h"]}</h2></div><div class="colors">{figs}</div></section>'


def after(s):
    extra = f'<div class="ph-full">{img(s["img2"])}</div>' if s.get("img2") else ""
    return f'<section><div class="hdline" style="padding-bottom:50px"><h2 style="font-size:{s.get("size", 74)}px">{s["h"]}</h2></div><div class="ph-full" style="max-height:1110px">{img(s["img"])}</div>{extra}</section>'


def qa(s):
    n = len(s["items"])
    q = "".join(f'<div class="qa" {CHECK_END if i == n - 1 else ""}><div class="q"><b>Q.</b>{a[0]}</div><div class="a">{a[1]}</div></div>' for i, a in enumerate(s["items"]))
    return f'<section class="s15"><h2>{s["h"]}</h2>{q}</section>'


def info(s):
    n = len(s["rows"])
    r = "".join(f'<div class="row" {CHECK_END if i == n - 1 else ""}><b>{a[0]}</b><span>{a[1]}</span></div>' for i, a in enumerate(s["rows"]))
    return f'<section class="s16 pale"><div class="tt">제품 정보</div>{r}</section>'


def warn(s):
    cells = "".join(f'<div><svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="#0B6FD1" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">{ICON[i[0]]}</svg>{i[1]}</div>' for i in s["items"])
    return f'<section class="s17"><h2 style="font-size:{s.get("size", 72)}px">{s["h"]}</h2><div class="ic6">{cells}</div></section>'


def finale(s):
    return f'''<section class="s18"><img class="bg" src="{s['img']}" alt=""><div class="veil"></div><div class="top"><h2 style="font-size:{s.get('size', 70)}px">{s['h']}<big style="font-size:{s.get('bigsize', 96)}px">{s['big']}</big></h2></div></section>'''


def main() -> None:
    d = Path(sys.argv[1])
    page = json.loads((d / "page.json").read_text(encoding="utf-8"))
    css = (ROOT / "templates/v5.css").read_text(encoding="utf-8")
    js = (ROOT / "templates/v5.js").read_text(encoding="utf-8")
    body = "\n\n".join(globals()[s["type"]](s) for s in page["sections"])
    (d / "pdp.html").write_text(f'''<!DOCTYPE html>
<html lang="ko">
<!-- {page['title']} (page.json에서 생성: python3 pdp/scripts/build_pdp.py {d}) -->
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
{css}</style>
</head>
<body>

{body}

<script>
{js}</script>
</body>
</html>
''', encoding="utf-8")
    print(d / "pdp.html")


if __name__ == "__main__":
    main()
