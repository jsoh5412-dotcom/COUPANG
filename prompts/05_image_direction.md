# 05. 이미지 계획·제작

## 소스 우선순위
1. 공급처 원본 → 누끼 (`scripts/remove_bg.py`)
2. 누끼 + AI 배경·연출 합성 (`scripts/gen_image.mjs edit`): 제품 형태·색·로고는 그대로 유지
3. 제품이 없는 컷(감성·문제 상황·사용 장면)은 AI로 생성 (`scripts/gen_image.mjs generate`)
4. 아이콘·인포그래픽은 HTML/CSS·SVG로 직접 그린다

## 생성 프롬프트 규칙 (영어로 작성)
- 공통: `photorealistic commercial product photography, Korean lifestyle, natural soft light, no text, no watermark, no logo`
- 제품이 들어가는 edit: `keep the product exactly as in the input image: same shape, color, proportions, details` 를 반드시 넣는다
- 사람이 나오면 한국인 모델, 자연스러운 손과 표정. 손가락 개수를 확인한다
- 이미지 안에 글자를 넣지 않는다. 글자는 HTML에서 얹는다

## 산출물 `work/05_image_plan.md`
| 섹션 | 컷 | 방식(원본/누끼/합성/생성/CSS) | 소스 파일 | 프롬프트 | 결과 파일 |

생성한 뒤에는 원본 제품과 나란히 놓고 형태·색이 같은지 확인한다. 다르면 다시 생성하거나 누끼 합성으로 바꾼다.
