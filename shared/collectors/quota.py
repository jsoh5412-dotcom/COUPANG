#!/usr/bin/env python3
"""쿠팡 하루 수집 상한을 모든 팀 합계로 센다 (결정 43). 차단은 맥북 IP 단위라 프로필을 나눠도 상한은 하나다.

사용법:
  python3 shared/collectors/quota.py              오늘 쓴 건수와 중지 여부 보기
  python3 shared/collectors/quota.py use keyword  키워드 1건 쓰기 (상한 초과·중지면 종료코드 3)

- 코드에서는 `use_quota("detail", url)`. 쿠팡 주소가 아니면 세지 않는다.
- 쿠팡에서 차단 징후가 나오면 `run()`이 그날 수집을 중지로 표시하고, 모든 팀의 다음 수집이 멈춘다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

try:
    import fcntl
except ImportError:  # 윈도우에는 없다
    fcntl = None

DAILY_LIMITS = {"keyword": 30, "detail": 150}
QUOTA_EXIT = 3


def state_dir() -> Path:
    return Path(os.environ.get("COLLECTOR_STATE_DIR", Path.home() / ".cache" / "coupang-collector"))


def _update(change) -> dict:
    """오늘 파일을 잠그고 읽어 change(data)를 적용한 뒤 저장한다. 팀 사이 동시 실행에도 건수가 틀리지 않는다."""
    path = state_dir() / f"quota_{date.today().isoformat()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as f:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        text = f.read()
        data = json.loads(text) if text.strip() else {"keyword": 0, "detail": 0, "stopped": None}
        change(data)
        f.seek(0)
        f.truncate()
        json.dump(data, f, ensure_ascii=False)
        f.flush()
    return data


def is_coupang(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host == "coupang.com" or host.endswith(".coupang.com")


def use_quota(kind: str, url: str = "https://www.coupang.com", n: int = 1) -> None:
    """상한 안이면 건수를 더한다. 넘거나 오늘 중지 상태면 건수를 더하지 않고 종료코드 3으로 멈춘다."""
    if not is_coupang(url):
        return
    refused: list[str] = []

    def change(data: dict) -> None:
        if data["stopped"]:
            refused.append(f"오늘은 차단 징후로 쿠팡 수집이 중지됐습니다 ({data['stopped']})")
        elif data[kind] + n > DAILY_LIMITS[kind]:
            refused.append(f"{kind} 하루 상한 {DAILY_LIMITS[kind]}건(모든 팀 합계)을 넘습니다. 지금 {data[kind]}건")
        else:
            data[kind] += n

    _update(change)
    if refused:
        print(f"[수집 중지] {refused[0]}. PM에게 알리세요.", file=sys.stderr)
        sys.exit(QUOTA_EXIT)


def mark_stopped(reason: str, url: str) -> None:
    """쿠팡 차단 징후를 기록한다. 로그인 요구는 차단이 아니고, 다른 사이트는 쿠팡 수집을 막지 않는다."""
    if is_coupang(url) and reason in ("access_denied", "captcha", "rate_limited"):
        _update(lambda data: data.update(stopped=reason))


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "use" and sys.argv[2] in DAILY_LIMITS:
        use_quota(sys.argv[2], n=int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    data = _update(lambda _: None)
    print(f"키워드 {data['keyword']}/{DAILY_LIMITS['keyword']} · 상세 {data['detail']}/{DAILY_LIMITS['detail']} · 중지 {data['stopped'] or '없음'}")


if __name__ == "__main__":
    main()
