#!/bin/bash
# 수집 전용 크롬을 원격 디버깅 포트로 띄운다 (mac / linux).
# - 평소 쓰는 크롬과 분리된 전용 프로필을 쓴다 (크롬 136+ 는 기본 프로필에서 디버깅 포트를 막는다).
# - 처음 한 번 이 창에서 쿠팡·1688·도매꾹에 직접 로그인해 두면 이후 수집기가 그 로그인을 쓴다.
# - 다른 크로미움 계열 브라우저를 쓰려면 BROWSER_APP 에 실행 파일 경로를 넣는다.
#   (예: Aside 가 디버깅 포트를 지원하는지는 확인 필요 — README 의 테스트 항목 참고)
set -euo pipefail
PORT="${COLLECTOR_PORT:-9222}"
PROFILE="${COLLECTOR_PROFILE:-$HOME/.coupang-collector-profile}"
if [ -z "${BROWSER_APP:-}" ]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "$(command -v google-chrome || true)" "$(command -v google-chrome-stable || true)" "$(command -v chromium || true)"; do
    [ -n "$c" ] && [ -x "$c" ] && BROWSER_APP="$c" && break
  done
fi
[ -n "${BROWSER_APP:-}" ] || { echo "크롬을 찾지 못했습니다. BROWSER_APP 에 경로를 지정하세요." >&2; exit 1; }
mkdir -p "$PROFILE"
echo "실행: $BROWSER_APP (포트 $PORT, 프로필 $PROFILE)"
"$BROWSER_APP" --remote-debugging-port="$PORT" --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check \
  "https://www.coupang.com" >/dev/null 2>&1 &
sleep 3
curl -s "http://127.0.0.1:$PORT/json/version" | grep -q Browser && echo "연결 준비 완료: http://127.0.0.1:$PORT" \
  || echo "포트 응답 없음. 이미 같은 프로필 창이 떠 있으면 모두 닫고 다시 실행하세요."
