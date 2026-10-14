#!/usr/bin/env node
/* Measure the cover's real geometry so the seat solver can work from facts.

  Reads a request JSON:
    { cover, ratios: { "l916": [1080,1920], ... }, stickerTexts: [...] }
  Writes a response JSON:
    { "l916": { "zones": { ".kicker": [x0,y0,x1,y1], ... },
                "stickers": [[w,h], ...] }, ... }

  Zones are measured with all stickers hidden, so a stale seat can never pollute a
  keep-out rectangle. This is what makes the seat computation correct by
  construction instead of by hand-tuning.

  usage: node scripts/measure_cover_geometry.mjs <request.json> <out.json>
          (also accepts: --project <dir> for a one-off dump)
*/
import { createRequire } from 'node:module';
import { globSync } from 'node:fs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function findPuppeteer() {
  const c = [];
  if (process.env.PUPPETEER_CORE_PATH) c.push(process.env.PUPPETEER_CORE_PATH);
  c.push(`${process.cwd()}/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js`);
  c.push(...globSync(`${os.homedir()}/.npm/_npx/*/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js`));
  c.sort();
  for (const x of c.reverse()) if (fs.existsSync(x)) return x;
  throw new Error('puppeteer-core not found');
}
function findChrome() {
  const hits = [];
  for (const r of [`${os.homedir()}/.cache/hyperframes/chrome/chrome-headless-shell`,
                   `${os.homedir()}/.cache/puppeteer`]) {
    hits.push(...globSync(`${r}/*/chrome-headless-shell-mac-*/chrome-headless-shell`));
    hits.push(...globSync(`${r}/*/chrome-headless-shell-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`));
  }
  const ok = hits.filter((p) => fs.existsSync(p));
  ok.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  return ok[ok.length - 1];
}

const req = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const outPath = process.argv[3];
const require = createRequire(import.meta.url);
const puppeteer = require(findPuppeteer());
const browser = await puppeteer.launch({
  executablePath: findChrome(), headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
});

const PROTECT = ['.kicker', '.hero', '.act', '.cap', '.brand', '.idx', '.ava'];
const res = {};
for (const [ratio, [W, H]] of Object.entries(req.ratios)) {
  const p = await browser.newPage();
  await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await p.goto(`file://${req.cover}?cb=${Date.now()}-${ratio}`, { waitUntil: 'networkidle0' });
  await p.evaluate(() => document.fonts.ready);
  await p.waitForFunction(() => Array.isArray(window.__coverLayoutErrors), { timeout: 5000 }).catch(() => {});
  // freeze animations so measurements are stable
  await p.evaluate(() => {
    const st = document.createElement('style');
    st.textContent = '*,*::before,*::after{animation:none !important;transition:none !important}';
    document.head.appendChild(st);
    document.querySelectorAll('.sun').forEach((e) => { e.style.animation = 'none'; e.style.transform = 'none'; });
  });
  // hide stickers, then measure everything
  await p.evaluate(() => { document.querySelectorAll('.st').forEach((e) => { e.style.visibility = 'hidden'; }); });
  await new Promise((r) => setTimeout(r, 120));
  const zones = await p.evaluate((PROTECT) => {
    const o = {};
    for (const sel of PROTECT) {
      const el = document.querySelector(sel);
      if (!el || getComputedStyle(el).display === 'none') continue;
      const r = el.getBoundingClientRect();
      o[sel] = [r.left, r.top, r.right, r.bottom];
    }
    return o;
  }, PROTECT);
  // measure each sticker's own size (unhide one at a time, no transform)
  const sizes = [];
  const n = await p.evaluate(() => document.querySelectorAll('.st').length);
  for (let i = 0; i < n; i++) {
    const s = await p.evaluate((i) => {
      const el = document.getElementById('st' + i);
      if (!el || getComputedStyle(el).display === 'none') return null;
      const prevTransform = el.style.transform, prevLeft = el.style.left, prevTop = el.style.top;
      el.style.visibility = 'visible';
      el.style.transform = 'none';
      el.style.left = '-10000px';
      el.style.top = '0px';
      const r = el.getBoundingClientRect();
      const out = { w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10,
                    text: el.textContent, on: el.getAttribute('data-on') };
      el.style.visibility = 'hidden';
      el.style.transform = prevTransform;
      el.style.left = prevLeft;
      el.style.top = prevTop;
      return out;
    }, i);
    sizes.push(s);
  }
  // Resolved box: unhide the stickers, let the page's own placement run, then
  // report the rotated bounding box each sticker actually occupies at its
  // intended anchor. This is the only fully reliable feedback — modelling the
  // post-rotation box in Python kept drifting by a few px (which is exactly how a
  // right-rail seat ended up 15px past the safe margin).
  await p.evaluate(() => { document.querySelectorAll('.st').forEach((e) => { e.style.visibility = 'visible'; }); });
  await new Promise((r) => setTimeout(r, 250));
  const rotOffset = await p.evaluate(() => {
    const out = [];
    document.querySelectorAll('.st').forEach((el) => {
      if (getComputedStyle(el).display === 'none') { out.push(null); return; }
      const r = el.getBoundingClientRect();
      out.push({ ax: parseFloat(el.style.left), ay: parseFloat(el.style.top),
                 x: r.left, y: r.top, bw: r.width, bh: r.height,
                 w: el.offsetWidth, h: el.offsetHeight, text: el.textContent });
    });
    return out;
  });
  res[ratio] = { zones, stickers: sizes, resolved: rotOffset };
  await p.close();
}
await browser.close();
fs.writeFileSync(outPath, JSON.stringify(res, null, 1));
console.log(`measured ${Object.keys(res).length} ratios -> ${outPath}`);
