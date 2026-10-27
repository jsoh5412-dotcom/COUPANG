# shared/notify — 디스코드 보고 (결정 40 1단계)

팀장이 진행 상황을 디스코드 서버 "쿠팡 본부"의 팀 채널에 올린다. 한 방향(웹후크)이라 봇이 메시지를 받지 않는다.

## 쓰는 법

```bash
python3 shared/notify/discord.py <팀> <종류> "<메시지>" [--file 썸네일.png] [--dry-run]
```

- **팀:** `pm` `기획` `상페` `시장조사` `등록` `물류` `광고` `알림`
- **종류:** `시작` `완료` `막힘` `병합` `요약` `시험`
  - `막힘`은 팀 채널과 `#알림` 둘 다에 올리고 사용자를 멘션한다. 사람이 필요한 일(로그인·캡차·승인 관문)에만 쓴다.
- **첨부:** `--file`은 여러 번 쓸 수 있다. 파일당 10MB를 넘으면 빼고 보낸다.
- 표준 라이브러리만 쓰므로 venv 없이 시스템 `python3`로 돈다. 팀장 워크트리에서도 `.env` 링크로 같은 키를 읽는다.

예)
```bash
python3 shared/notify/discord.py 상페 완료 "발각질제거기-1 상페 완성 · 드라이브 상세페이지/테스트세트1/1_발각질제거기_1_손잡이+양면/" --file thumb.png
python3 shared/notify/discord.py 기획 막힘 "윙 로그인 버튼 눌렀는데 추가 인증이 떠서 멈춤"
```

파이썬에서 부를 때: `from discord import send` 후 `send("상페", "완료", "메시지", files=[...])`. 성공하면 True를 돌려주고, 실패해도 예외를 던지지 않는다.

## 안전장치

- 웹후크 주소는 저장소 루트 `.env`의 `DISCORD_WEBHOOK_PM·PLANNING·PDP·RESEARCH·LISTING·LOGISTICS·ADS·ALERT`, 사용자 멘션은 `DISCORD_USER_ID`. 주소는 출력·로그에 찍지 않는다.
- 실패해도 종료 코드 0, 경고만 낸다. 본 작업을 멈추지 않는다.
- 같은 채널에 같은 내용은 10분 안에 다시 보내지 않고, 채널당 분당 10건까지만 보낸다. 상태는 `~/.cache/coupang-notify/state.json`.
- 멘션은 `DISCORD_USER_ID` 한 명만 허용한다 (`@everyone` 등은 눌리지 않음).
