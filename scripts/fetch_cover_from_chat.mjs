// 从**同一个 GPT 会话**里把某比例的封面补取回来。
//
// 为什么需要（2026-09-22 EP.205 实测）：封面提示词发出去、用户消息也进了会话，但出图**排队慢**，
//   gen_gpt_covers.mjs 的轮询窗口（首发 15 轮 + 续跑 12 轮 + 补扫 12 轮，约 13 分钟）过了图才到，
//   于是那一张被记成 false。图本身是好的 —— 回到 /tmp/cover_chat_url.txt 指的会话就能取。
//   本脚本还会先发一句「续跑」提示（实测这一句能让排队中的那轮立刻开工），再轮询新图。
//
// 用法：
//   echo 205 > /tmp/cover_ep.txt; echo 3x4 > /tmp/cover_ratio.txt
//   ~/.local/bin/ego-browser nodejs < scripts/fetch_cover_from_chat.mjs
// 依赖：/tmp/cover_chat_url.txt（gen_gpt_covers.mjs 每次跑完都会写）
// 产出：content/episode-<N>/exp-gpt/cover-<ratio>.png（只认**本轮新出现**的图，避免拿错旧图）

const ep = (fs.existsSync('/tmp/cover_ep.txt') ? fs.readFileSync('/tmp/cover_ep.txt', 'utf8') : '').trim();
const ratio = (fs.existsSync('/tmp/cover_ratio.txt') ? fs.readFileSync('/tmp/cover_ratio.txt', 'utf8') : '3x4').trim();
if (!ep) { console.error('用法：把期号写进 /tmp/cover_ep.txt'); process.exit(1); }
const url = (fs.existsSync('/tmp/cover_chat_url.txt') ? fs.readFileSync('/tmp/cover_chat_url.txt', 'utf8') : '').trim();
if (!/chatgpt\.com\/c\//.test(url)) { console.error('❌ /tmp/cover_chat_url.txt 里没有会话 URL'); process.exit(1); }
const want = ratio === '3x4' ? [0.70, 0.80] : [1.25, 1.42];
const out = `/Users/chao/Documents/dailyvideos/content/episode-${ep}/exp-gpt/cover-${ratio}.png`;

const IMGS = `(() => [...document.querySelectorAll('img')]
  .filter(x => /estuary\\/content|oaidalleapi|oaiusercontent|backend-api\\/files/.test(x.src||'') && x.naturalWidth > 500)
  .map(x => ({ src: x.src, w: x.naturalWidth, h: x.naturalHeight })))()`;

const task = await taskSpace(`封面补取 · EP.${ep} · ${ratio}`);
const page = task.page('p1');
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(12000);
const base = new Set((await page.evaluate(IMGS)).map(x => x.src));
console.log(`会话已有 ${base.size} 张图（本轮只认新图）`);

// 先发一句续跑提示：实测排队中的那轮会立刻开工
await page.evaluate(() => { const t = document.querySelector('#prompt-textarea'); if (t) { t.scrollIntoView({ block: 'center' }); t.focus(); } });
await page.waitForTimeout(400);
await page.keyboard.press('Meta+a'); await page.waitForTimeout(150); await page.keyboard.press('Delete');
await page.keyboard.insertText(`请按我上一条消息里的完整提示词直接出图（${ratio === '3x4' ? '竖版 3:4' : '横版 4:3'}封面，画面文字只能出现我列出的那些，一字不增不减）。`);
await page.waitForTimeout(1200);
try { await page.press('#prompt-textarea', 'Enter'); console.log('已发续跑提示'); }
catch (e) { console.log('续跑提示发送失败：' + String(e).slice(0, 80)); }

let got = false;
for (let i = 1; i <= 40; i++) {
  await page.waitForTimeout(20000);
  const fresh = (await page.evaluate(IMGS)).filter(x => !base.has(x.src));
  const hit = fresh.filter(x => { const r = x.w / x.h; return r > want[0] && r < want[1]; }).pop();
  const busy = await page.evaluate(() => !!document.querySelector("[data-testid*='stop'], button[aria-label*='Stop']"));
  console.log(`第${i}轮 busy=${busy} 新图 ${fresh.map(x => x.w + 'x' + x.h).join(',') || '无'}`);
  if (hit) {
    const r = await page.fetch(hit.src, { saveAs: out, timeout: 60000 });
    const st = fs.statSync(out);
    console.log(`✅ 命中 ${hit.w}x${hit.h} → ${out}（${(st.size / 1048576).toFixed(2)}MB, ok=${r.ok}）`);
    got = true;
    break;
  }
}
if (!got) {
  // 兜底：有时候那张图在**本脚本启动之前**就已经出现在会话里了（生成器轮询窗口过了才回来），
  // 于是它落在基线里、被当"旧图"过滤掉。此时按「会话里该比例的最后一张」取回，并如实标注。
  const all = (await page.evaluate(IMGS)).filter(x => { const r = x.w / x.h; return r > want[0] && r < want[1]; });
  if (all.length) {
    const pick = all[all.length - 1];
    const r = await page.fetch(pick.src, { saveAs: out, timeout: 60000 });
    const st = fs.statSync(out);
    console.log(`✅（会话内已有，非本轮新出）取回 ${pick.w}x${pick.h} → ${out}（${(st.size / 1048576).toFixed(2)}MB, ok=${r.ok}）`);
    got = true;
  }
}
if (!got) console.log('⚠️ 本次没拿到新图（会话里可能仍是旧的；可用 COVER_ONLY 重跑生成器）');
await task.finish({ keep: [] });
