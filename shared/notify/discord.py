#!/usr/bin/env python3
"""디스코드 웹후크로 팀 보고를 올린다 (결정 40 1단계, 한 방향).

사용법:
  python3 shared/notify/discord.py <팀> <종류> "<메시지>" [--file 이미지경로 ...] [--dry-run]
  팀:   pm 기획 상페 시장조사 등록 물류 광고 알림 (영문 planning pdp research listing logistics ads alert도 됨)
  종류: 시작 완료 막힘 병합 요약 시험

- 웹후크 주소는 저장소 루트 `.env`의 DISCORD_WEBHOOK_*에서 읽는다. 주소는 어디에도 출력하지 않는다.
- `막힘`은 팀 채널과 #알림 둘 다에 올리고 사용자(DISCORD_USER_ID)를 멘션한다.
- 실패해도 종료 코드는 0이다 (경고만). 본 작업을 멈추지 않기 위해서다.
- 표준 라이브러리만 쓴다 (설치 필요 없음).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = Path.home() / ".cache" / "coupang-notify" / "state.json"

TEAMS = {
    "pm": "PM", "기획": "PLANNING", "planning": "PLANNING", "상페": "PDP", "pdp": "PDP",
    "시장조사": "RESEARCH", "research": "RESEARCH", "등록": "LISTING", "listing": "LISTING",
    "물류": "LOGISTICS", "logistics": "LOGISTICS", "광고": "ADS", "ads": "ADS",
    "알림": "ALERT", "alert": "ALERT",
}
KINDS = {"시작": "▶️", "완료": "✅", "막힘": "🛑", "병합": "🔀", "요약": "📋", "시험": "🧪"}

DEDUP_SECONDS = 600      # 같은 채널에 같은 내용은 10분 안에 다시 보내지 않는다
RATE_PER_MINUTE = 10     # 채널 하나에 분당 최대 전송 수
MAX_FILE_BYTES = 10 * 1024 * 1024  # 부스트 없는 서버의 웹후크 첨부 한도
MAX_CONTENT = 2000       # 디스코드 메시지 글자 수 한도


def warn(msg: str) -> None:
    print(f"[notify] 경고: {msg}", file=sys.stderr)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.removeprefix("export ").strip()
            env[k] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():  # 실행 환경 값이 있으면 우선
        if k.startswith("DISCORD_"):
            env[k] = v
    return env


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state))
    except Exception as e:
        warn(f"상태 파일 저장 실패 ({type(e).__name__})")


def allowed(state: dict, channel: str, content: str, files: list[Path]) -> str | None:
    """보내면 안 되는 이유를 돌려준다. 보내도 되면 None."""
    now = time.time()
    ch = state.setdefault(channel, {"sent": [], "recent": {}})
    ch["sent"] = [t for t in ch["sent"] if now - t < 60]
    ch["recent"] = {h: t for h, t in ch["recent"].items() if now - t < DEDUP_SECONDS}
    digest = hashlib.sha256((content + "|" + "|".join(map(str, files))).encode()).hexdigest()[:16]
    if digest in ch["recent"]:
        return "같은 내용을 10분 안에 이미 보냄"
    if len(ch["sent"]) >= RATE_PER_MINUTE:
        return f"분당 {RATE_PER_MINUTE}건 한도 초과"
    ch["_pending"] = digest
    return None


def mark_sent(state: dict, channel: str) -> None:
    ch = state[channel]
    ch["sent"].append(time.time())
    ch["recent"][ch.pop("_pending")] = time.time()


def post(url: str, payload: dict, files: list[Path]) -> None:
    if not files:
        data = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
    else:
        boundary = uuid.uuid4().hex
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\n'
            f"Content-Type: application/json\r\n\r\n".encode() + json.dumps(payload).encode() + b"\r\n"
        ]
        for i, f in enumerate(files):
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="files[{i}]"; filename="{f.name}"\r\n'
                f"Content-Type: {ctype}\r\n\r\n".encode() + f.read_bytes() + b"\r\n"
            )
        data = b"".join(parts) + f"--{boundary}--\r\n".encode()
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    headers["User-Agent"] = "coupang-notify/1.0"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        if r.status >= 300:
            raise RuntimeError(f"HTTP {r.status}")


def send(team: str, kind: str, message: str, files: list[str] | None = None, dry_run: bool = False) -> bool:
    """다른 파이썬 코드에서 불러 쓸 때의 진입점. 성공하면 True, 실패·생략이면 False (예외를 던지지 않는다)."""
    try:
        key = TEAMS.get(team.lower() if team.isascii() else team)
        if not key:
            warn(f"알 수 없는 팀: {team}")
            return False
        if kind not in KINDS:
            warn(f"알 수 없는 종류: {kind} (가능: {' '.join(KINDS)})")
            return False
        env = load_env()
        paths: list[Path] = []
        for f in files or []:
            p = Path(f)
            if not p.is_file():
                warn(f"첨부 파일 없음: {p.name}")
            elif p.stat().st_size > MAX_FILE_BYTES:
                warn(f"첨부 생략 (10MB 초과): {p.name}")
            else:
                paths.append(p)

        targets = [key] + (["ALERT"] if kind == "막힘" and key != "ALERT" else [])
        mention = ""
        allowed_mentions: dict = {"parse": []}
        if kind == "막힘" and env.get("DISCORD_USER_ID", "").isdigit():
            mention = f"<@{env['DISCORD_USER_ID']}> "
            allowed_mentions = {"users": [env["DISCORD_USER_ID"]]}

        body = f"{KINDS[kind]} **[{kind}]** {message}"
        ok = True
        state = load_state()
        for target in targets:
            url = env.get(f"DISCORD_WEBHOOK_{target}", "")
            if target == "ALERT" and key != "ALERT":
                content = f"{mention}{KINDS[kind]} **[{kind}·{team}]** {message}"
            else:
                content = mention + body
            content = content[:MAX_CONTENT]
            if not url.startswith("https://"):
                warn(f"DISCORD_WEBHOOK_{target}가 .env에 없음")
                ok = False
                continue
            reason = allowed(state, target, content, paths)
            if reason:
                warn(f"{target} 전송 생략: {reason}")
                ok = False
                continue
            payload = {"content": content, "allowed_mentions": allowed_mentions}
            if dry_run:
                print(f"[notify] (dry-run) {target} ← {content[:80]}{' + 첨부 ' + str(len(paths)) if paths else ''}")
                state[target].pop("_pending", None)
                continue
            try:
                post(url, payload, paths)
                mark_sent(state, target)
                print(f"[notify] {target} 전송 완료")
            except urllib.error.HTTPError as e:
                warn(f"{target} 전송 실패 (HTTP {e.code})")
                state[target].pop("_pending", None)
                ok = False
            except Exception as e:
                warn(f"{target} 전송 실패 ({type(e).__name__})")
                state[target].pop("_pending", None)
                ok = False
        save_state(state)
        return ok
    except Exception as e:  # 어떤 경우에도 호출한 작업을 멈추지 않는다
        warn(f"예상 못 한 오류 ({type(e).__name__})")
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="디스코드 팀 채널에 보고를 올린다")
    ap.add_argument("team")
    ap.add_argument("kind")
    ap.add_argument("message")
    ap.add_argument("--file", action="append", default=[], help="첨부 이미지 (여러 번 가능, 파일당 10MB 이하)")
    ap.add_argument("--dry-run", action="store_true", help="보내지 않고 무엇을 보낼지만 출력")
    a = ap.parse_args()
    send(a.team, a.kind, a.message, a.file, a.dry_run)
    sys.exit(0)


if __name__ == "__main__":
    main()
