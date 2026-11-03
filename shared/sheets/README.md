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

## 만들기가 막힐 때

서비스 계정은 자기 저장 공간이 없어 새 파일 만들기가 막힐 수 있다. 그때는 사용자 계정 소유의 시트를 먼저 만들고 공유한 뒤 ID로 쓴다: `test --sheet <시트ID>`

## 상태

2026-11-03 기준 Sheets API 연결과 키 인증은 확인했다. 쓰기·읽기 시험은 Drive API와 폴더 공유가 끝난 뒤 한다.
