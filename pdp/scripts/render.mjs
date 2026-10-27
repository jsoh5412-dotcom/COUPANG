// HTML 상세페이지 → 가로 780px 이미지로 렌더링하고 세로로 분할 저장
// 사용법: node pdp/scripts/render.mjs <pdp.html> <outDir> [--slice 3000] [--jpg] [--width 780]
import { chromium } from 'playwright';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : def;
};
const valued = new Set(['--slice', '--width']);
const [htmlPath, outDir] = args.filter((a, i) => !a.startsWith('--') && !valued.has(args[i - 1]));
if (!htmlPath || !outDir) {
  console.error('usage: node pdp/scripts/render.mjs <pdp.html> <outDir> [--slice 3000] [--jpg] [--width 780]');
  process.exit(1);
}
const width = Number(opt('--width', 780));
const sliceH = Number(opt('--slice', 3000));
const ext = args.includes('--jpg') ? 'jpg' : 'png';

mkdirSync(outDir, { recursive: true });
// 클라우드 세션에는 브라우저가 /opt/pw-browsers 에 미리 설치돼 있다
const exe = process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined);
const browser = await chromium.launch(exe ? { executablePath: exe } : {});
const page = await browser.newPage({ viewport: { width, height: 1200 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(resolve(htmlPath)).href, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);

// 제품 슬롯 좌표 기록: [data-slot] 요소의 페이지 기준 좌표·크기 (누끼 교체·합성용)
const slots = await page.evaluate(() =>
  [...document.querySelectorAll('[data-slot]')].map((e) => {
    const r = e.getBoundingClientRect();
    return { name: e.dataset.slot, src: e.getAttribute('src'), x: Math.round(r.left + window.scrollX), y: Math.round(r.top + window.scrollY), w: Math.round(r.width), h: Math.round(r.height) };
  }),
);
writeFileSync(join(outDir, 'slots.json'), JSON.stringify({ width, slots }, null, 2));

// 섹션 경계에서 자르기: [data-slice-break] 요소 직전, 또는 sliceH 초과 시 섹션 경계로
const total = await page.evaluate(() => document.documentElement.scrollHeight);
const sectionTops = await page.evaluate(() =>
  [...document.querySelectorAll('section')].map((s) => Math.round(s.getBoundingClientRect().top + window.scrollY)),
);
const cuts = [0];
for (const top of sectionTops) {
  const last = cuts[cuts.length - 1];
  if (top - last > sliceH) {
    const prev = sectionTops.filter((t) => t > last && t < top).pop();
    cuts.push(prev && prev - last > sliceH * 0.4 ? prev : last + sliceH);
  }
}
while (total - cuts[cuts.length - 1] > sliceH) cuts.push(cuts[cuts.length - 1] + sliceH);
cuts.push(total);

const files = [];
for (let i = 0; i < cuts.length - 1; i++) {
  const y = cuts[i];
  const h = cuts[i + 1] - y;
  if (h <= 0) continue;
  const file = join(outDir, `pdp_${String(files.length + 1).padStart(2, '0')}.${ext}`);
  await page.screenshot({ path: file, fullPage: true, clip: { x: 0, y, width, height: h }, ...(ext === 'jpg' ? { type: 'jpeg', quality: 92 } : {}) });
  files.push(`${file} (${width}x${h})`);
}
await page.screenshot({ path: join(outDir, `pdp_full.${ext}`), fullPage: true, ...(ext === 'jpg' ? { type: 'jpeg', quality: 85 } : {}) });
await browser.close();
console.log(`total height ${total}px →\n` + files.join('\n'));
