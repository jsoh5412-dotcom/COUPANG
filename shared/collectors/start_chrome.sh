#!/bin/bash
# 수집 전용 크롬을 원격 디버깅 포트로 띄운다 (mac / linux).
# - 평소 쓰는 크롬과 분리된 쿠팡 수집 전용 프로필을 쓴다 (크롬 136+ 는 기본 프로필에서 디버깅 포트를 막는다).
# - 로그인은 1688만 사용자가 이 창에서 직접 해 둔다 (쿠팡은 비로그인 수집, 도매꾹·도매매는 API — 결정 21).
# - 디버깅 포트는 127.0.0.1 에만 열려야 한다. 다른 주소로 열리면 크롬을 닫고 멈춘다.
# - 다른 크로미움 계열 브라우저를 쓰려면 BROWSER_APP 에 실행 파일 경로를 넣는다.
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
PID=$!
# 크롬이 뜨는 데 몇 초 걸린다 (맥북 M1에서 약 5초). 최대 20초 기다린다.
for _ in $(seq 1 20); do
  curl -s -m 1 "http://127.0.0.1:$PORT/json/version" | grep -q Browser && break
  sleep 1
done
if ! curl -s -m 1 "http://127.0.0.1:$PORT/json/version" | grep -q Browser; then
  echo "포트 응답 없음. 이미 같은 프로필 창이 떠 있으면 모두 닫고 다시 실행하세요." >&2
  exit 1
fi
# 127.0.0.1 이 아닌 주소로 열려 있으면 외부에서 브라우저를 조종할 수 있으므로 닫는다.
if command -v lsof >/dev/null && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN | awk 'NR>1 {print $9}' | grep -vqE '^(127\.0\.0\.1|\[::1\]):'; then
  echo "디버깅 포트가 127.0.0.1 밖으로 열려 있어 크롬을 닫습니다." >&2
  kill "$PID" 2>/dev/null || true
  exit 1
fi
echo "연결 준비 완료: http://127.0.0.1:$PORT (127.0.0.1 전용)"
