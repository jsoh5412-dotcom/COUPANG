# shared/sheets — 구글 시트 공용 도구 (결정 46)

사람이 보고 체크·메모하는 표는 엑셀 대신 구글 시트로 만든다. 설명과 함수는 `sheets.py` 머리말에 있다.

## 준비 (한 번만)

```bash
python3 -m venv .venv
.venv/bin/pip install -r shared/sheets/requirements.txt
```

- 키 파일은 맥북 `~/.secrets/coupang-sheets.json`에만 둔다. `.env`의 `GOOGLE_SERVICE_ACCOUNT_JSON`에 경로를 적는다. 저장소에 넣지 않고 내용을 출력하지 않는다.
- 구글 클라우드 프로젝트에 **Google Sheets API와 Google Drive API**가 모두 켜져 있어야 한다.
- 봇이 쓸 드라이브 폴더나 시트를 서비스 계정 이메일에 편집자로 공유한다. 이메일 확인: `.venv/bin/python shared/sheets/sheets.py email`

## 사용자 열 보호

`upsert(..., protected=["관심", "메모"])`는 그 열을 셀 단위로 건너뛴다. 사용자 소유 열은 이 함수로만 다룬다. `write`로 그 열을 포함한 범위를 쓰지 않는다.

## 새 시트 만들기

서비스 계정은 저장 공간이 없어 개인 드라이브에 새 파일을 만들 수 없다 (`create`가 멈춘다). 새 시트는 **사용자 계정 소유로 먼저 만들고** ID로 쓴다.

- 만드는 법: 공유된 폴더 안에 드라이브 커넥터로 빈 구글 시트를 만든다. 커넥터가 없으면 PM에게 요청한다.
- 공유: `쿠팡/research` 폴더(ID `11DaVls9IKByvoknVaJsZv8Bm7Lphqvbp`)는 서비스 계정에 편집자로 공유돼 있어, 안에 만든 시트는 권한을 물려받는다.

## 상태

2026-11-03 `_시험_shared_sheets`(research 폴더)로 쓰기·읽기·행 추가·사용자 열 보호를 확인했다. `create`는 공유 드라이브에서 시험하지 않았다.
