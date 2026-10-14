// 小红书发布页：把封面换成我们的 cover-3x4.png（适配器的封面上传在小红书必然失败，这一步是补课）。
//
// 背景（skill §9.6 固化）：`chai_publish_mcp.py` 在小红书会卡在封面 ——
//   报 `未找到封面上传触发器: div.noCover.uploadCover`、目标状态 failed，
//   但**标题/正文/话题其实都填好了**（自检里能看到 `标题栏已填`）。
//   发布默认留人（用户自己点「发布笔记」），所以这一步的目标是：把封面摆好、页面留在那儿。
//
// 用法（在 `--only xiaohongshu --keep-open` 之后、页面还开着时跑）：
//   echo 205 > /tmp/xhs_ep.txt
//   ~/.local/bin/ego-browser nodejs < scripts/xhs_set_cover.mjs
// 依赖：/tmp/xhs_space.txt（可选，写任务空间名；缺省自动找**名字里带"小红书"或发布时间最近**的空间）

const ep = (fs.existsSync('/tmp/xhs_ep.txt') ? fs.readFileSync('/tmp/xhs_ep.txt', 'utf8') : '').trim();
if (!ep) { console.error('用法：把期号写进 /tmp/xhs_ep.txt'); process.exit(1); }
const cover = `<REPO>/content/episode-${ep}/publish-package-2026-09-22/cover-3x4.png`;
if (!fs.existsSync(cover)) { console.error('❌ 找不到封面 ' + cover); process.exit(1); }
const b64 = fs.readFileSync(cover).toString('base64');
console.log(`封面 ${cover}（${(b64.length * 3 / 4 / 1048576).toFixed(2)}MB base64）`);

// 找任务空间：优先名字里带"小红书"的；否则用最后一个 agent 空间
const spaces = await listTaskSpaces();
const cand = spaces.filter(s => /小红书|xiaohong/i.test(s.name || ''))
  .concat(spaces.filter(s => s.ownership === 'agent' && !/小红书|xiaohong/i.test(s.name || '')));
if (!cand.length) { console.error('❌ 没有可用的任务空间（请先跑 chai_publish_mcp.py --only xiaohongshu --keep-open）'); process.exit(1); }
const task = await takeOverTaskSpace(cand[0].id);
console.log('任务空间:', cand[0].id, cand[0].name);
const page = task.page('p1');

// 1) 找「编辑封面 / 设置封面」入口（小红书文案在不同状态下不一样）
const opened = await page.evaluate(`(() => {
  const want = ['编辑封面', '设置封面', '更换封面', '上传封面'];
  const els = [...document.querySelectorAll('div,span,button,a')].filter(e => {
    const t = (e.innerText || '').trim();
    return want.includes(t) && e.getBoundingClientRect().width > 0;
  });
  if (!els.length) return 'no-entry';
  els[0].scrollIntoView({ block: 'center' }); els[0].click();
  return 'clicked:' + els[0].innerText.trim();
})()`);
console.log('入口 →', opened);
await page.waitForTimeout(3500);

// 2) 在弹窗里上传 cover-3x4.png（base64 → File → DataTransfer）
const up = await page.evaluate(`(() => {
  const inp = [...document.querySelectorAll("input[type=file]")].find(i => (i.accept || '').includes('image'))
           || document.querySelector("input[type=file]");
  if (!inp) return 'no-input';
  const bin = atob("${b64}");
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  const file = new File([arr], 'cover-3x4.png', { type: 'image/png' });
  const dt = new DataTransfer(); dt.items.add(file);
  inp.files = dt.files;
  inp.dispatchEvent(new Event('change', { bubbles: true }));
  inp.dispatchEvent(new Event('input', { bubbles: true }));
  return 'uploaded';
})()`);
console.log('上传 →', up);
await page.waitForTimeout(6000);

// 3) 点「完成 / 确定 / 保存」
const done = await page.evaluate(`(() => {
  const want = ['完成', '确定', '保存', '下一步'];
  const btns = [...document.querySelectorAll('button,div[role=button],span')].filter(e => {
    const t = (e.innerText || '').trim();
    return want.includes(t) && e.getBoundingClientRect().width > 0;
  });
  if (!btns.length) return 'no-done-button';
  btns[btns.length - 1].click();
  return 'clicked:' + btns[btns.length - 1].innerText.trim();
})()`);
console.log('完成 →', done);
await page.waitForTimeout(4000);

// 4) 回读：页面上封面图是否变成 3:4
const back = await page.evaluate(`(() => {
  const imgs = [...document.querySelectorAll('img')].map(i => i.naturalWidth + 'x' + i.naturalHeight)
    .filter(d => d !== '0x0');
  const has34 = imgs.some(d => { const [w, h] = d.split('x').map(Number); return h > w && Math.abs(w / h - 0.75) < 0.06; });
  return JSON.stringify({ has34, imgs: imgs.slice(0, 8) });
})()`);
console.log('回读 →', back);
console.log('👉 页面留在原地：请人工点「发布笔记」。');
