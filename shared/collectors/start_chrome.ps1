# 수집 전용 크롬을 원격 디버깅 포트로 띄운다 (windows PowerShell).
# 로그인은 1688만 사용자가 이 창에서 직접 해 둔다 (쿠팡은 비로그인 수집, 도매꾹·도매매는 API — 결정 21).
$Port = if ($env:COLLECTOR_PORT) { $env:COLLECTOR_PORT } else { 9222 }
$Profile = if ($env:COLLECTOR_PROFILE) { $env:COLLECTOR_PROFILE } else { "$env:USERPROFILE\.coupang-collector-profile" }
$App = $env:BROWSER_APP
if (-not $App) {
  $App = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
           "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
           "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $App) { Write-Error "크롬을 찾지 못했습니다. BROWSER_APP 환경변수에 경로를 지정하세요."; exit 1 }
New-Item -ItemType Directory -Force -Path $Profile | Out-Null
Start-Process $App "--remote-debugging-port=$Port", "--user-data-dir=$Profile", "--no-first-run", "--no-default-browser-check", "https://www.coupang.com"
Start-Sleep 3
try { Invoke-RestMethod "http://127.0.0.1:$Port/json/version" | Out-Null; "연결 준비 완료: http://127.0.0.1:$Port" }
catch { "포트 응답 없음. 같은 프로필 창을 모두 닫고 다시 실행하세요." }
