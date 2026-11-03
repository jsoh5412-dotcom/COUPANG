# shared/collectors — 상세 이미지·리뷰 수집기

LLM이 매번 클릭하지 않는다. **스크롤 → 이미지 URL 수집 → 다운로드**를 고정 스크립트로 한다.
Claude는 스크립트를 실행하고, 결과(`manifest.json`)를 읽고, 막히면 사용자에게 알리는 역할만 한다.

| 스크립트 | 대상 | 결과 |
|---|---|---|
| `coupang_detail.py` | 쿠팡 상품 상세 이미지 전체 | `001.jpg…`, `detail_text.txt`, `manifest.json` |
| `coupang_reviews.py` | 쿠팡 리뷰 여러 페이지 | `reviews.jsonl`, `reviews.md`, `pages/page_XX.txt`, `manifest.json` |
| `supplier_detail.py` | 1688·도매꾹·도매매 상세 이미지 | `001.jpg…`, `spec_text.txt`, `manifest.json` |
| `browser.py` | 공통: 연결, 사람 속도 대기, 차단 감지, 스크롤, 다운로드 | — |
| `quota.py` | 공통: 쿠팡 하루 상한을 모든 팀 합계로 세기, 차단 시 그날 중지 | `~/.cache/coupang-collector/quota_<날짜>.json` |

## 원칙

- **사람 속도로 수집한다.** `browser.py`의 `PACE`에서 대기 시간(초)을 조절한다.
  - 페이지 이동 4~8초
  - 클릭 1~2.5초
  - 이미지 1장당 0.8~2초
  - 스크롤 0.5~1.2초
- **실사이트에서는 빨리 돌리지 않는다.** `COLLECTOR_FAST=1`은 오프라인 테스트 전용이다.
- **차단·로그인·캡차를 만나면 멈춘다** (종료코드 2, `manifest.json`의 `status: blocked`).
  - 우회하거나 자동으로 재시도하지 않는다.
  - 사용자가 크롬 창에서 직접 로그인이나 보안확인을 끝낸 뒤 한 번만 다시 돌리거나, 2순위(직접 업로드)로 전환한다.
- **사이트 구조가 바뀌면 각 스크립트 상단의 선택자 목록만 고친다.**
  - `manifest.json`의 `strategy` / `selectors`를 보면 어떤 선택자가 맞았는지 알 수 있다.
  - `fallback:`으로 시작하면 선택자가 안 맞았다는 뜻이다.
- 수집물은 `pdp/projects/<슬러그>/inputs/` 아래에 둔다. 커밋하지 않는다 (`.gitignore` 처리됨).

## 팀별 프로필과 하루 상한 (결정 43)

| 팀 | `COLLECTOR_TEAM` | 프로필 | 포트 |
|---|---|---|---|
| 상페 (기본) | `pdp` | `~/.coupang-collector-profile` (1688 로그인 보관) | 9222 |
| 시장조사 | `research` | `~/.coupang-collector-research` | 9223 |

- **고르는 법:** `COLLECTOR_TEAM`을 크롬 실행과 수집 스크립트에 똑같이 준다. 포트는 모두 `127.0.0.1`만 연다.
  ```bash
  COLLECTOR_TEAM=research ./shared/collectors/start_chrome.sh
  COLLECTOR_TEAM=research python3 shared/collectors/coupang_detail.py "<쿠팡 URL>" research/raw/<시장>/ref
  ```
- **1688은 기존 프로필에서만.** 다른 팀이 1688을 쓰면 수집기가 멈춘다. 필요하면 상페 팀과 순서를 맞춘 뒤 `COLLECTOR_TEAM=pdp`로 돌린다.
- **같은 프로필은 한 번에 하나만.** `open_page`가 프로필별 잠금을 잡는다. 쓰는 중이면 기다렸다가 시작하고, 30분을 넘기면 멈춘다. 그때는 PM에게 알린다.
- **두 팀이 동시에 수집하면** 페이지 사이 대기가 자동으로 두 배가 된다.
- **쿠팡 하루 상한은 모든 팀 합계다.** 차단이 맥북 IP 단위라서 그렇다. 키워드 30개·상품 상세 150건.
  - `coupang_detail.py`와 `coupang_reviews.py`는 실행할 때마다 상세 1건을 자동으로 센다. 상한을 넘으면 종료코드 3으로 멈춘다.
  - 키워드 검색 스크립트는 페이지를 열기 전에 `use_quota("keyword", url)`을 부른다 (`from quota import use_quota`).
  - 오늘 쓴 건수 보기: `python3 shared/collectors/quota.py`
- **쿠팡 차단 징후(접근 거부·캡차·요청 제한)가 나오면** 그날 쿠팡 수집이 모든 팀에서 멈춘다. `run()`이 자동으로 표시한다. 먼저 만난 세션이 PM에게 알린다. 해제하려고 기록 파일을 고치지 않는다.

## PC 준비 (한 번만)

패키지는 저장소 가상환경(`.venv`)에만 설치한다 (전역 설치 금지, 루트 `CLAUDE.md`).

```bash
python3 -m venv .venv                      # 저장소 루트에서, 처음 한 번
source .venv/bin/activate                  # 이후 수집기를 돌릴 때마다
pip install -r shared/collectors/requirements.txt
python3 -m playwright install chromium     # launch 모드용. cdp 모드만 쓰면 생략 가능
```

### 1) 수집 전용 크롬 띄우기 (기본 방식: cdp)

```bash
./shared/collectors/start_chrome.sh                                       # mac / linux
powershell -ExecutionPolicy Bypass -File shared/collectors/start_chrome.ps1   # windows
```

- 평소 쓰는 크롬과 분리된 **쿠팡 수집 전용 프로필**로 디버깅 포트를 열고 실행한다 (결정 25). 기본은 상페용 `~/.coupang-collector-profile`:9222이고, 시장조사는 `COLLECTOR_TEAM=research`를 붙인다 (결정 43).
  - 크롬 136부터는 기본 프로필에서 디버깅 포트를 막기 때문에 전용 프로필이 필요하다.
  - 이 프로필은 쿠팡 수집에만 쓴다. 당근 등 다른 사업은 이 프로필과 포트를 쓰지 않는다.
  - 디버깅 포트는 `127.0.0.1`에만 열린다 (같은 맥북 안에서만 접속 가능). 크롬 156에서 확인.
- **로그인은 1688만** 사용자가 이 창에서 직접 해 둔다 (결정 21). 쿠팡 상품·리뷰는 로그인 없이 공개 페이지로 수집하고, 도매꾹·도매매는 OpenAPI로 처리한다.
  - 봇은 비밀번호를 입력해 로그인하지 않는다. 로그인 만료를 만나면 멈추고 사용자에게 알린다.
- 수집기는 이 창에 **새 탭을 하나 열고, 끝나면 그 탭만 닫는다.**

### 2) 실행

```bash
source .venv/bin/activate
S=pdp/projects/test/inputs
python3 shared/collectors/coupang_detail.py  "<쿠팡 URL>"   $S/ref
python3 shared/collectors/coupang_reviews.py "<쿠팡 URL>"   $S/reviews --pages 10 --sort recent
python3 shared/collectors/supplier_detail.py "<공급처 URL>" $S/source
```

### 다른 방식
- **launch 모드** (`--mode launch`): cdp 연결이 안 될 때만 쓴다. 플레이라이트가 전용 프로필로 크롬을 직접 띄운다.
  - 자동화 표식이 붙어서 cdp보다 차단될 가능성이 높다.
- **다른 크로미움 계열 브라우저**: `BROWSER_APP=<실행파일 경로> ./start_chrome.sh`
  - 원격 디버깅 포트를 지원해야 붙을 수 있다. 기본은 크롬이다 (결정 20·25).

## 테스트

```bash
python3 shared/collectors/tests/test_offline.py   # 로컬 가짜 페이지로 동작 원리 확인 (어디서나 실행 가능)
```

실사이트 테스트 절차와 결과는 [`TEST_REPORT.md`](TEST_REPORT.md)에 기록한다.
