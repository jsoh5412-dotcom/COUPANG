#!/bin/bash
# 클라우드 세션 시작 시 의존성 설치 (로컬에서는 docs/setup.md 대로 한 번만 설치)
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "$CLAUDE_PROJECT_DIR"
pip install -q --break-system-packages -r requirements.txt >/dev/null 2>&1 || echo "rembg 설치 실패" >&2
npm install --no-audit --no-fund --silent >/dev/null 2>&1 || echo "npm install 실패" >&2
# Node 내장 fetch가 클라우드 프록시를 타도록 (gen_image.mjs)
[ -n "${CLAUDE_ENV_FILE:-}" ] && echo 'export NODE_USE_ENV_PROXY=1' >> "$CLAUDE_ENV_FILE"
exit 0
