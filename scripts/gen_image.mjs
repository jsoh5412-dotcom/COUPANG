// OpenAI 이미지 생성/편집
//   생성: node scripts/gen_image.mjs generate "<prompt>" <out.png> [--size 1024x1536] [--model gpt-image-2]
//   편집: node scripts/gen_image.mjs edit "<prompt>" <out.png> --image <누끼.png> [--image <ref2.png>] [--size ...]
// 크기: 1024x1024 | 1536x1024(가로) | 1024x1536(세로) | auto
// OPENAI_API_KEY 환경변수 필요 (클라우드 세션에서는 프록시가 자동 주입)
import { readFileSync, writeFileSync } from 'node:fs';
import { basename } from 'node:path';

const args = process.argv.slice(2);
const [mode, prompt, out] = args;
const multi = (name) => args.flatMap((a, i) => (a === name ? [args[i + 1]] : []));
const opt = (name, def) => multi(name)[0] ?? def;
if (!['generate', 'edit'].includes(mode) || !prompt || !out) {
  console.error('usage: node scripts/gen_image.mjs <generate|edit> "<prompt>" <out.png> [--image f] [--size WxH] [--model m] [--quality high]');
  process.exit(1);
}
const model = opt('--model', process.env.OPENAI_IMAGE_MODEL || 'gpt-image-2');
const size = opt('--size', '1024x1536');
const quality = opt('--quality', 'high');
const headers = process.env.OPENAI_API_KEY ? { Authorization: `Bearer ${process.env.OPENAI_API_KEY}` } : {};

let res;
if (mode === 'generate') {
  res = await fetch('https://api.openai.com/v1/images/generations', {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, prompt, size, quality, n: 1 }),
  });
} else {
  const images = multi('--image');
  if (!images.length) throw new Error('edit 모드는 --image 가 필요합니다');
  const form = new FormData();
  form.append('model', model);
  form.append('prompt', prompt);
  form.append('size', size);
  form.append('quality', quality);
  for (const f of images) form.append('image[]', new Blob([readFileSync(f)], { type: 'image/png' }), basename(f));
  res = await fetch('https://api.openai.com/v1/images/edits', { method: 'POST', headers, body: form });
}
const json = await res.json();
if (!res.ok) {
  console.error(JSON.stringify(json, null, 2));
  process.exit(1);
}
writeFileSync(out, Buffer.from(json.data[0].b64_json, 'base64'));
console.log(`saved ${out} (${model}, ${size})`);
