#!/usr/bin/env python3
"""구글 시트 읽기·쓰기 공용 도구 (결정 46). 사람이 보는 표(시장조사 아카이브 등)에 쓴다.

사용법:
  .venv/bin/python shared/sheets/sheets.py email                     서비스 계정 이메일 보기
  .venv/bin/python shared/sheets/sheets.py test --folder <폴더ID>     시험 시트를 만들어 읽기·쓰기 확인
  .venv/bin/python shared/sheets/sheets.py test --sheet <시트ID>      시험 전용 시트로 읽기·쓰기 확인 (첫 칸부터 덮어쓰니 실제 시트에 쓰지 않는다)

코드에서는:
  from sheets import create, read, write, append, upsert
  upsert(sheet_id, "전체", key="시장명", rows=[{"시장명": "손난로", "상태": "신규"}], protected=["관심", "메모"])

- 키 파일 경로는 저장소 루트 `.env`의 GOOGLE_SERVICE_ACCOUNT_JSON에서 읽는다. 키 내용은 출력하지 않는다.
- `protected` 열(사용자 소유)은 어떤 경우에도 쓰지 않는다. 사용자의 체크·메모를 덮어쓰지 않기 위해서다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEET_MIME = "application/vnd.google-apps.spreadsheet"


def key_path() -> Path:
    env = ROOT / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        if line.startswith("GOOGLE_SERVICE_ACCOUNT_JSON="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return Path(value).expanduser()
    sys.exit("[키 없음] .env의 GOOGLE_SERVICE_ACCOUNT_JSON이 비어 있습니다.")


def service_email() -> str:
    return json.loads(key_path().read_text(encoding="utf-8"))["client_email"]


def _services():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(str(key_path()), scopes=SCOPES)
    return (
        build("sheets", "v4", credentials=creds, cache_discovery=False),
        build("drive", "v3", credentials=creds, cache_discovery=False),
    )


def create(title: str, folder_id: str | None = None) -> str:
    """새 시트를 만들고 ID를 돌려준다. 공유 드라이브 폴더에서만 된다.

    서비스 계정은 저장 공간이 없어 개인 드라이브에는 파일을 만들 수 없다 (README 참고).
    """
    from googleapiclient.errors import HttpError

    _, drive = _services()
    body = {"name": title, "mimeType": SHEET_MIME}
    if folder_id:
        body["parents"] = [folder_id]
    try:
        return drive.files().create(body=body, fields="id", supportsAllDrives=True).execute()["id"]
    except HttpError as e:
        if "storage quota" in str(e):
            sys.exit("[만들기 불가] 서비스 계정은 개인 드라이브에 파일을 만들 수 없습니다. 사용자 계정 소유 시트를 공유 폴더에 먼저 만들고 ID로 쓰세요.")
        raise


def read(sheet_id: str, range_: str) -> list[list[str]]:
    sheets, _ = _services()
    return sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_).execute().get("values", [])


def write(sheet_id: str, range_: str, rows: list[list]) -> None:
    sheets, _ = _services()
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_, valueInputOption="USER_ENTERED", body={"values": rows}
    ).execute()


def append(sheet_id: str, range_: str, rows: list[list]) -> None:
    sheets, _ = _services()
    sheets.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=range_, valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body={"values": rows}
    ).execute()


def _column(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def upsert(sheet_id: str, tab: str, key: str, rows: list[dict], protected: list[str] | tuple[str, ...] = ()) -> dict:
    """key 열 값으로 행을 찾아 갱신하고, 없으면 맨 아래에 추가한다. protected 열은 셀 단위로 건너뛴다.

    첫 행은 머리글이다. 머리글에 없는 열이 rows에 있으면 잘못 쓰지 않도록 멈춘다.
    """
    sheets, _ = _services()
    grid = read(sheet_id, f"'{tab}'")
    if not grid:
        sys.exit(f"[머리글 없음] '{tab}' 탭 첫 행에 머리글이 필요합니다.")
    header = grid[0]
    if key not in header:
        sys.exit(f"[열 없음] 머리글에 '{key}' 열이 없습니다.")
    key_at = header.index(key)
    row_of = {r[key_at]: i + 1 for i, r in enumerate(grid) if i and len(r) > key_at and r[key_at]}
    next_row = len(grid) + 1
    data = []
    counts = {"updated": 0, "added": 0}
    for row in rows:
        unknown = [c for c in row if c not in header]
        if unknown:
            sys.exit(f"[열 없음] 머리글에 없는 열: {unknown}")
        value = str(row[key])
        if value in row_of:
            number = row_of[value]
            counts["updated"] += 1
        else:
            number = next_row
            row_of[value] = number
            next_row += 1
            counts["added"] += 1
        for column, cell in row.items():
            if column in protected:
                continue
            letter = _column(header.index(column))
            data.append({"range": f"'{tab}'!{letter}{number}", "values": [[cell]]})
    if data:
        sheets.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
        ).execute()
    return counts


def self_test(folder_id: str | None, sheet_id: str | None = None) -> None:
    """시험 시트에 쓰기·읽기·추가·사용자 열 보호를 확인한다. sheet_id가 없으면 새로 만든다."""
    if not sheet_id:
        sheet_id = create("_시험_shared_sheets", folder_id)
        print(f"만들기 성공: https://docs.google.com/spreadsheets/d/{sheet_id}")
    sheets, _ = _services()
    tab = sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()["sheets"][0]["properties"]["title"]
    write(sheet_id, f"'{tab}'!A1", [["시장명", "상태", "메모"], ["손난로", "신규", "사용자 메모"]])
    assert read(sheet_id, f"'{tab}'")[1] == ["손난로", "신규", "사용자 메모"]
    print("쓰기·읽기 성공")
    counts = upsert(
        sheet_id, tab, key="시장명",
        rows=[{"시장명": "손난로", "상태": "추천", "메모": "봇이 덮어쓰면 안 됨"}, {"시장명": "윷놀이", "상태": "신규"}],
        protected=["메모"],
    )
    after = read(sheet_id, f"'{tab}'")
    assert counts["updated"] + counts["added"] == 2, counts  # 같은 시트로 다시 돌리면 추가 대신 갱신이 된다
    assert after[1] == ["손난로", "추천", "사용자 메모"], after
    assert after[2][:2] == ["윷놀이", "신규"], after
    print("갱신·추가 성공, 사용자 열 보호 확인")


def main() -> None:
    parser = argparse.ArgumentParser(description="구글 시트 공용 도구")
    parser.add_argument("command", choices=["email", "test"])
    parser.add_argument("--folder", help="시험 시트를 만들 드라이브 폴더 ID")
    parser.add_argument("--sheet", help="시험에 쓸 기존 빈 시트 ID")
    args = parser.parse_args()
    if args.command == "email":
        print(service_email())
    else:
        self_test(args.folder, args.sheet)


if __name__ == "__main__":
    main()
