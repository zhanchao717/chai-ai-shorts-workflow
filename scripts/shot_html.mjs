#!/usr/bin/env node
// 通用「HTML → PNG」截图器（复用 render_covers.mjs 的 puppeteer-core / chrome 自动发现逻辑）。
// 用途：给设计样张（如榜单条目卡新版式）出图，不依赖 HyperFrames 工程。
//
// 用法：node scripts/shot_html.mjs <html> <out.png> [--w 1080] [--h 1920] [--wait 1200]
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { globSync } from 'node:fs';
import { createRequire } from 'node:module';

function die(m) { console.error(`❌ ${m}`); process.exit(2); }

function findPuppeteer() {
  const c = [];
  if (process.env.PUPPETEER_CORE_PATH) c.push(process.env.PUPPETEER_CORE_PATH);
  c.push(...globSync(`${os.homedir()}/.npm/_npx/*/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js`));
  c.push(...globSync(`${process.cwd()}/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js`));
  c.sort();
  for (const p of c.reverse()) if (fs.existsSync(p)) return p;
  die('找不到 puppeteer-core');
}

function findChrome() {
  const roots = [`${os.homedir()}/.cache/hyperframes/chrome/chrome-headless-shell`, `${os.homedir()}/.cache/puppeteer`];
  const hits = [];
  for (const r of roots) {
    hits.push(...globSync(`${r}/*/chrome-headless-shell-mac-*/chrome-headless-shell`));
    hits.push(...globSync(`${r}/*/chrome-headless-shell-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`));
  }
  const ok = hits.filter((p) => fs.existsSync(p));
  if (!ok.length) die('找不到 chrome-headless-shell');
  ok.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  return ok[ok.length - 1];
}

const args = process.argv.slice(2);
const pos = args.filter((a) => !a.startsWith('--'));
const opt = (n, d) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
if (pos.length < 2) die('用法：node scripts/shot_html.mjs <html> <out.png> [--w 1080] [--h 1920]');
const [htmlPath, outPath] = pos.map((p) => path.resolve(p));
const W = parseInt(opt('w', '1080'), 10), H = parseInt(opt('h', '1920'), 10);
const wait = parseInt(opt('wait', '1200'), 10);

const require = createRequire(import.meta.url);
const puppeteer = require(findPuppeteer());
const browser = await puppeteer.launch({
  executablePath: findChrome(), headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.goto(`file://${htmlPath}`, { waitUntil: 'load' });
  await new Promise((r) => setTimeout(r, wait));
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await page.screenshot({ path: outPath, clip: { x: 0, y: 0, width: W, height: H } });
  const { size } = fs.statSync(outPath);
  console.log(`✅ ${path.basename(outPath)}  ${W}×${H}  ${(size / 1024).toFixed(0)} KB`);
} finally {
  await browser.close();
}
