# 셋업 가이드

## 운영 구조
- **주 작업 환경: 사장님 PC의 Claude 데스크톱 앱 + Claude in Chrome**
  - 쿠팡·1688·도매꾹 링크를 사장님의 실제 크롬(로그인 상태)으로 열어 수집한다.
  - PC에서 돌리므로 네트워크 차단이 없다.
- 보조: 클라우드 세션 (claude.ai/code)
  - 이미지를 직접 첨부해서 분석·카피·제작하는 용도.
  - 쇼핑몰 도메인이 막혀 있어서 링크 수집은 안 된다.

## 1. PC 준비 (한 번만)
1. **Claude 데스크톱 앱** 설치 → 로그인
2. **Claude in Chrome** 확장 설치 → 데스크톱 앱과 연결
3. 쿠팡·1688·도매꾹에 크롬으로 로그인해 둔다 (1688은 로그인해야 상세가 보이는 경우가 많다)
4. 저장소 받기
   ```bash
   git clone https://github.com/jsoh5412-dotcom/PDP-Converter_forCOUPANG.git
   cd PDP-Converter_forCOUPANG
   ```
5. 도구 설치 (Python 3.10+, Node.js 22+)
   ```bash
   pip install -r requirements.txt     # 누끼(rembg). 첫 실행 때 모델 약 180MB 자동 다운로드
   npm install                         # 렌더러(playwright)
   npx playwright install chromium
   ```
6. **OpenAI API 키**: https://platform.openai.com/api-keys 에서 발급받는다.
   - 환경변수 `OPENAI_API_KEY` 에 등록한다.
   - 클라우드 세션은 이미 연결돼 있어서 필요 없다. PC에서만 필요하다.
   - mac: `~/.zshrc` 에 `export OPENAI_API_KEY=sk-...` 추가
   - windows: 시스템 환경변수에 추가
7. 데스크톱 앱에서 이 폴더를 열고 시작한다.

## 2. 선택 사항
| 도구 | 용도 | 필요할 때 |
|---|---|---|
| remove.bg / Photoroom API | 고난도 누끼 (머리카락, 투명 소재) | rembg 결과가 부족할 때 |
| 도매꾹 Open API 키 | 공급처 정보 안정 수집 | 도매꾹·도매매 상품이 많을 때 |
| 쿠팡 Wing Open API | 상품 등록 자동화 | 나중에 |
| GoFullPage (크롬 확장) | 상세페이지 전체 캡처 | 링크 수집이 실패했을 때의 대안 |

## 3. 비용 감각 (OpenAI 이미지)
- 상세페이지 1개에 연출컷 5~10장 정도 필요하다.
- 시안은 `--quality low`, 확정 컷만 `high`로 뽑는다.
- 요금은 OpenAI 가격 페이지 기준으로 확인한다.
