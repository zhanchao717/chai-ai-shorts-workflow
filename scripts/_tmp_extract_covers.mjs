import fs from 'node:fs';
const URL_C = 'https://chatgpt.com/c/6ab72943-d3e0-83ee-a234-5c6ddecf93c1';
const OUT = '/Users/chao/Documents/dailyvideos/content/episode-214/exp-gpt';
const task = await taskSpace('GPT 封面 · probe');
const page = task.page('p1');
await page.goto(URL_C, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(12000);
await page.evaluate(() => { const m = document.querySelector('main'); if (m) m.scrollTop = m.scrollHeight; });
await page.waitForTimeout(5000);
const cand = await page.evaluate(() => [...document.querySelectorAll('img')]
  .filter(i => (i.alt || '') === '已生成图像 1' && i.naturalWidth > 500)
  .map(i => ({ src: i.src, w: i.naturalWidth, h: i.naturalHeight })));
console.log('候选：', JSON.stringify(cand.map(c => `${c.w}x${c.h} ${c.src.slice(0,30)}`)));
const want = { '3x4': [0.70, 0.80], '4x3': [1.25, 1.42] };
const got = {};
for (const [ratio, [lo, hi]] of Object.entries(want)) {
  const hit = cand.find(c => { const r = c.w / c.h; return r > lo && r < hi && !Object.values(got).includes(c.src); });
  if (!hit) { console.log(`❌ ${ratio} 无候选`); continue; }
  const dataUrl = await page.evaluate(async (src) => {
    const b = await (await fetch(src)).blob();
    return await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = rej; fr.readAsDataURL(b); });
  }, hit.src);
  const b64 = dataUrl.split(',')[1];
  const buf = Buffer.from(b64, 'base64');
  const p = `${OUT}/cover-${ratio}.png`;
  fs.writeFileSync(p, buf);
  got[ratio] = hit.src;
  console.log(`✅ ${ratio} ${hit.w}x${hit.h} (${(hit.w/hit.h).toFixed(3)}) → ${p} ${(buf.length/1048576).toFixed(2)}MB`);
}
