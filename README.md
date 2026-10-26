# PDP-Converter for COUPANG

잘 팔리는 쿠팡 상세페이지의 **결제 장치**(구조·화법·디자인 어법)를 뽑아서,
내 제품(공급처 상세 + 경쟁 리뷰)으로 새 상세페이지를 만드는 Claude 작업 저장소.

- 봇 규칙·파이프라인: [`CLAUDE.md`](CLAUDE.md)
- 단계별 지침: [`prompts/`](prompts)
- 셋업: [`docs/setup.md`](docs/setup.md)

## 사용법 (Claude에게 이렇게 말하기)
```
새 상품: 무선 미니 청소기
레퍼런스: https://www.coupang.com/vp/products/...
공급처: https://detail.1688.com/offer/....html
리뷰: https://www.coupang.com/vp/products/... (같은 제품 타 판매자)
전체 진행해줘
```
→ 분석 3종 → 카피 원고(검수) → 이미지 제작 → `output/` 에 780px 분할 PNG

## 스크립트
```bash
python3 scripts/remove_bg.py <이미지|폴더> <출력>                       # 누끼
node scripts/gen_image.mjs generate "<prompt>" out.png --size 1024x1536  # 연출컷 생성
node scripts/gen_image.mjs edit "<prompt>" out.png --image nukki.png     # 누끼 + 배경 합성
node scripts/render.mjs projects/<상품>/work/pdp.html projects/<상품>/output  # 렌더·분할
```
