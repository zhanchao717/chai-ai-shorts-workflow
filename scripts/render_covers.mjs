#!/usr/bin/env node
// 柴主编 · 三比例封面截图（常驻脚本；design-system.md「三比例封面」的落地实现）
//
// 为什么需要它：原来的做法是 /tmp/rc.mjs，里面写死了某个 npx 缓存哈希里的
// puppeteer-core 路径——缓存被清就失效。本脚本**自动发现** puppeteer-core 与
// chrome-headless-shell，任何机器上只要能渲染就能出封面。
//
// 用法：
//   node scripts/render_covers.mjs <project_dir> [--out <dir>]
//   例：node scripts/render_covers.mjs videos/deepseek-v41-flash
//
// 产出：cover-9x16.png(1080×1920) / cover-3x4.png(1080×1440) / cover-4x3.png(1440×1080)
// 默认写到 <project_dir>/covers/（--out 可改，测旧工程时别覆盖原产物）。
// 只用 node 内置模块 + puppeteer-core（npx 缓存或本地 node_modules 均可）。

import { createRequire } from 'node:module';
import { globSync } from 'node:fs';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

// 4:3 is the master. The 3:4 output is the master's centre 810x1080 window scaled by
// 1080/810, so it is rendered on a 1920x1440 viewport (same master canvas, --ms=4/3)
// and screenshotted at 1080x1440 — the layout is generated at full res, no upscaling.
// name, viewportW, viewportH, outW, outH
// The 3:4 output is the master's centre 810x1080 window scaled by 1080/810, so it
// renders on a 1920x1440 viewport (same master canvas at --ms=4/3) and is clipped to
// the visible 1080x1440 — generated at full resolution, never upscaled.
const RATIOS = [
  ['cover-9x16.png', 1080, 1920, 1080, 1920],
  ['cover-4x3.png', 1440, 1080, 1440, 1080],
  // 2026-09-12（用户反馈「4:3 与 3:4 不协调」）：3:4 改为**原生渲染**——
  //   在 1920×1440 视口（= 4:3 母版 × 1.3333）上绘制，cover.html 会选 `.l34` 且 --ms=1.3333，
  //   再截中央 1080×1440（窗左缘 315×1.3333 = 420）。文字是**原生分辨率、不放大**，
  //   而构图仍是「4:3 母版的中央安全窗」→ 协调性不变、清晰度提升。
  //   旧做法（4:3 中心裁 810×1080 → 放大 1.3333×）已弃用，见文件末尾注释。
  ['cover-3x4.png', 1920, 1440, 1080, 1440, { clipX: 420, clipY: 0 }],
];

function die(msg) {
  console.error(`❌ ${msg}`);
  process.exit(2);
}

/** 依次尝试：显式环境变量 → npx 缓存（取最新）→ 本地 node_modules */
function findPuppeteer() {
  const cands = [];
  if (process.env.PUPPETEER_CORE_PATH) cands.push(process.env.PUPPETEER_CORE_PATH);
  cands.push(...globSync(`${os.homedir()}/.npm/_npx/*/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js`));
  cands.push(...globSync(`${process.cwd()}/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js`));
  if (!cands.length) die('找不到 puppeteer-core（试过 $PUPPETEER_CORE_PATH、~/.npm/_npx/*、./node_modules）');
  // 版本目录名排序 → 取最后一个（npx 缓存按哈希命名，无版本语义，取任一可用的）
  cands.sort();
  for (const c of cands.reverse()) {
    if (fs.existsSync(c)) return c;
  }
  die('puppeteer-core 候选路径全部不存在');
}

/** 取 chrome-headless-shell 版本号最大的那个 */
function findChrome() {
  const roots = [`${os.homedir()}/.cache/hyperframes/chrome/chrome-headless-shell`, `${os.homedir()}/.cache/puppeteer`];
  const hits = [];
  for (const r of roots) {
    hits.push(...globSync(`${r}/*/chrome-headless-shell-mac-*/chrome-headless-shell`));
    hits.push(...globSync(`${r}/*/chrome-headless-shell-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`));
    hits.push(...globSync(`${r}/chrome-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`));
  }
  const ok = hits.filter((p) => fs.existsSync(p));
  if (!ok.length) die('找不到 chrome-headless-shell（试过 ~/.cache/hyperframes 与 ~/.cache/puppeteer）');
  // 路径里的 mac_arm-152.0.7977.30 可排序，取最大
  ok.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  return ok[ok.length - 1];
}

const args = process.argv.slice(2);
const projArg = args.find((a) => !a.startsWith('--'));
if (!projArg) die('用法：node scripts/render_covers.mjs <project_dir> [--out <dir>]');
const proj = path.resolve(projArg);
if (!fs.existsSync(path.join(proj, 'cover.html'))) die(`${proj}/cover.html 不存在`);
const outIdx = args.indexOf('--out');
const outDir = path.resolve(outIdx >= 0 ? args[outIdx + 1] : path.join(proj, 'covers'));
fs.mkdirSync(outDir, { recursive: true });

const ppt = findPuppeteer();
const chrome = findChrome();
console.log(`puppeteer-core: ${ppt}`);
console.log(`chrome:         ${chrome}`);
console.log(`output:         ${outDir}`);

const require = createRequire(import.meta.url);
const puppeteer = require(ppt);
const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
});

let failed = 0;
const titleByRatio = {};
for (const [name, w, h, outW, outH, opt] of RATIOS) {
  const page = await browser.newPage();
  // 封面页里的落座校验是**硬门禁**：脚本通过 window.__coverLayoutErrors 报错，
  // 这里读到非空就必须失败退出（2026-09-11 修 P0 —— 原来自检只 console.warn，
  // 报了红照样出图，导致贴纸压主标题的封面被放行）。
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(`pageerror: ${e.message}`));
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  await page.goto(`file://${proj}/cover.html`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  // 2026-09-13（复核轮次 1 的 P2）：封面里 `.sun` 是**无限旋转**动画 → 同一份 cover.html
  //   两次渲染的 md5 不同（差异像素严格落在 sun 盒内），封面哈希不可复算。
  //   → 截图前**冻结所有动画**（把播放位置钉死在 0），保证出图可复算。
  await page.addStyleTag({ content: '*,*::before,*::after{animation-play-state:paused !important;animation-delay:0s !important;}' });
  await page.evaluate(() => {
    document.getAnimations?.().forEach(a => { try { a.pause(); a.currentTime = 0; } catch (e) {} });
  });
  // 落座校验挂在 fonts.ready 的 then 里，等它跑完再取值
  await page.waitForFunction(() => Array.isArray(window.__coverLayoutErrors), { timeout: 5000 })
    .catch(() => {});
  let layoutErrors = await page.evaluate(() => window.__coverLayoutErrors || null);
  // 母版还要过「窗四边 4px 带内有无墨迹」这一关。cover.html 是静态文件拿不到位图，
  // 所以由这里用 CDP 抓一张母版画布原尺寸的截图喂回去，再重跑一次门禁。
  // 抓之前把纯氛围层藏掉：光晕/斜纹/点阵/网格/光芒允许出窗，不该算越缘。
  if (name === 'cover-4x3.png' || name === 'cover-9x16.png') {
    // 藏掉纯氛围层（它们允许出窗），再抓一张原尺寸截图
    await page.evaluate((AMB) => {
      window.__ambHidden = [];
      for (const sel of AMB) {
        const e = document.querySelector(sel);
        if (e && e.style.visibility !== 'hidden') { e.style.visibility = 'hidden'; window.__ambHidden.push(e); }
      }
    }, ['.stripes', '.grid', '.vig', '.sun', '.glow']);
    const cdp = await page.createCDPSession();
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
    await cdp.detach();
    await page.evaluate(() => {
      (window.__ambHidden || []).forEach((e) => { e.style.visibility = ''; });
      window.__ambHidden = [];
    });
    const shot = await page.evaluate(async (b64) => {
      const img = new Image();
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = 'data:image/png;base64,' + b64; });
      const cv = document.createElement('canvas');
      cv.width = img.width; cv.height = img.height;
      const cx = cv.getContext('2d');
      cx.drawImage(img, 0, 0);
      return { data: Array.from(cx.getImageData(0, 0, cv.width, cv.height).data), width: cv.width, height: cv.height };
    }, data);
    const reErr = await page.evaluate((shot) => {
      window.__coverRecheck(shot);
      return window.__coverLayoutErrors || null;
    }, shot);
    if (reErr) layoutErrors = reErr;
  }
  if (layoutErrors === null) {
    console.error(`  ❌ ${name}: 页面没有报告落座校验结果（window.__coverLayoutErrors 未定义）`);
    failed++;
  } else if (layoutErrors.length) {
    console.error(`  ❌ ${name}: 封面落座校验失败 ${layoutErrors.length} 项：`);
    for (const e of layoutErrors) console.error(`       ${e}`);
    failed++;
  } else {
    console.log(`  ✅ ${name} 落座校验通过（贴纸不压文案、不出安全区）`);
  }
  for (const e of pageErrors) { console.error(`  ❌ ${name}: ${e}`); failed++; }
  const out = path.join(outDir, name);
  await page.screenshot({ path: out, type: 'png',
    clip: { x: (opt && opt.clipX) || 0, y: (opt && opt.clipY) || 0, width: outW, height: outH } });
  // 取真实主标题文本：三比例是互斥显隐布局，innerText 对隐藏元素返回空 → 用 textContent
  titleByRatio[name] = await page.evaluate(() => {
    const el = document.querySelector('.hero') || document.querySelector('#f5-hero');
    return el ? (el.textContent || '').replace(/\s+/g, '') : null;
  });
  // 3:4 现在由 4:3 主版裁切派生，没有自己的渲染页；它的标题就是主版的标题
  if (name === 'cover-4x3.png') titleByRatio['cover-3x4.png'] = titleByRatio[name];
  await page.close();
  const kb = (fs.statSync(out).size / 1024).toFixed(0);
  console.log(`  ✅ ${name}  ${w}×${h}  ${kb} KB`);
}
await browser.close();

// ── 3:4 已由上方 RATIOS 原生渲染（1920×1440 视口 + 中央 1080×1440 截取）──────────
// 历史：原实现是「4:3 中心裁 810×1080 再放大 1080/810」——构图安全但**文字被放大 1.333× 发虚**
//（实测 OCR 会把底注读错，如把「vs 媒体标题」读成「棋休蒜肠」）。2026-09-12 用户反馈
//「4:3 与 3:4 不协调」后改为原生渲染：同一套布局、同一个中央安全窗，只是**按目标尺寸直接绘制**。

// ② 文件存在且非空（含派生的 3:4）
for (const [name] of [...RATIOS, ['cover-3x4.png']]) {
  const f = path.join(outDir, name);
  if (!fs.existsSync(f) || fs.statSync(f).size < 5000) {
    console.error(`  ❌ ${name} 缺失或过小`);
    failed++;
  }
}
console.log(failed ? `\n结论：FAIL（${failed} 张异常）` : '\n结论：PASS（三比例封面已生成）');
process.exit(failed ? 1 : 0);
