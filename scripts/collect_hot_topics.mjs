// 热点采集器（浏览器侧）：把**没有 API 的榜单页**读回来，落成候选 JSON，喂给 chai_topic_radar.py。
//
// 为什么要浏览器而不是 curl（2026-09-22 用户选了「B：加浏览器智能体采集」）：
//   · 抖音热榜 / 微博热搜 / 知乎热榜 / Product Hunt 这些页面要么纯前端渲染、要么对无头请求不友好，
//     curl 拿不到内容（GitHub trending 的 HTML 结构也常改）。
//   · 本机已有的 ego-browser 就是一个**可被 Agent 驱动的 Chromium**（封面出图那条链路一直在用它），
//     它跟 jev 属于同一类东西 —— jev 的卖点是"用决策模型挑操作和元素、更快更便宜"，
//     但我们这一步只需要"把榜单读回来"，用不着为此接一套 API。
//   · 真要换成 jev/browser-use 驱动，只需把本文件里的 page.goto/evaluate 换成它们的调用：
//     jev 需要 TypeSafe 的 API key（docs.typesafe.ai），browser-use 云是按小时计费（官方 $0.02/小时）。
//
// 站点名单（只需要浏览器的那些）：HackerNews / GitHubTrending / 知乎热榜
//
// 运行（必须走 ego 运行时，taskSpace 等是它注入的全局）：
//   ~/.local/bin/ego-browser nodejs < scripts/collect_hot_topics.mjs
// 输出：/tmp/hot-candidates.json（{source, title, url, extra} 数组）

const OUT = '/tmp/hot-candidates.json';
// 只用想跑的那几个站：ego-browser nodejs < scripts/collect_hot_topics.mjs -- HackerNews,GitHubTrending
// （有些站会弹通知/登录权限框，弹了就**整个任务空间被接管**、本次采集直接中断 —— 所以：
//   ① 每读完一个站就落一次盘（下面 writeOut()），中断也不丢已采到的；② 名单可裁剪。）

const TARGETS = [
  {
    source: 'HackerNews',
    url: 'https://news.ycombinator.com/',
    // 每条：标题 + 链接 + 分数（HN 的 DOM 很稳）
    js: `(() => [...document.querySelectorAll('tr.athing')].slice(0, 25).map(tr => {
      const a = tr.querySelector('.titleline > a');
      const sub = tr.nextElementSibling;
      const score = sub ? (sub.querySelector('.score') || {}).textContent || '' : '';
      return { title: a ? a.innerText.trim() : '', url: a ? a.href : '', extra: score };
    }).filter(x => x.title))()`,
  },
  {
    source: 'GitHubTrending',
    url: 'https://github.com/trending?since=daily',
    js: `(() => [...document.querySelectorAll('article.Box-row')].slice(0, 25).map(el => {
      const a = el.querySelector('h2 a');
      const desc = el.querySelector('p');
      const stars = el.querySelector('a[href$="/stargazers"]');
      return {
        title: a ? a.innerText.replace(/\\s+/g, ' ').trim() : '',
        url: a ? 'https://github.com' + a.getAttribute('href') : '',
        extra: [desc ? desc.innerText.trim().slice(0, 90) : '', stars ? stars.innerText.replace(/\\s+/g, '') : ''].filter(Boolean).join(' · '),
      };
    }).filter(x => x.title))()`,
  },
  // Product Hunt **故意不放这里**：它的首页会弹通知权限框，一弹任务空间就被浏览器收回给用户
  // （2026-09-22 实测），而它另有公开 Atom feed —— 用 curl 就能拿，见 chai_topic_radar.py 的 ph_feed()。
  {
    // 机器之心：官网是 JS 壳，curl 拿不到列表 → 走浏览器渲染。
    source: '机器之心',
    // ⚠️ 首页是付费墙/pro 版壳（2026-09-28 实测：DOM 里只有 pro.jiqizhixin.com 的推广卡），
    //    改走公开的文章列表页；仍读不到就说明它又改版了，这条会在报告里显示 0 条。
    url: 'https://www.jiqizhixin.com/articles',
    js: `(() => [...document.querySelectorAll('a[href*="/articles/"]')].slice(0, 40).map(a => {
      const h = a.getAttribute('href') || '';
      return { title: (a.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 100),
               url: h.startsWith('http') ? h : 'https://www.jiqizhixin.com' + h, extra: '' };
    }).filter(r => r.title.length > 10))()`,
  },
  {
    // 新智元：官网不可达，主战场是公众号；这里用它的**搜狐号**（ID 473283）当可抓镜像。
    // ⚠️ 同样只当线索源 —— 事实仍须回官方一手源核。
    source: '新智元·搜狐号',
    url: 'https://mp.sohu.com/profile?xpt=473283',
    js: `(() => [...document.querySelectorAll('a[href*="/a/"]')].slice(0, 30).map(a => {
      const t = (a.innerText || '').replace(/\\s+/g, ' ').trim();
      return { title: t.slice(0, 100), url: a.href, extra: '' };
    }).filter(r => r.title.length > 10))()`,
  },
  {
    source: '知乎热榜',
    url: 'https://www.zhihu.com/hot',
    js: `(() => [...document.querySelectorAll('.HotItem, .HotList-item')].slice(0, 25).map(el => {
      const a = el.querySelector('a');
      return { title: (el.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 90), url: a ? a.href : '', extra: '' };
    }).filter(x => x.title))()`,
  },
];

// ⚠️ ego 的 CLI **只接受一个 source 参数**（实测：`ego-cli nodejs` accepts at most one source argument），
//    所以"只跑某几个站"用**文件**传：/tmp/hot_targets.txt（逗号或换行分隔站名）。
const wantFile = '/tmp/hot_targets.txt';
let want = null;
try {
  const raw = fs.readFileSync(wantFile, 'utf8').trim();
  if (raw) want = raw.split(/[,\n]/).map(s => s.trim()).filter(Boolean);
} catch (e) { want = null; }
const list = want ? TARGETS.filter(t => want.includes(t.source)) : TARGETS;

// ⚠️ 任务空间名**每次运行都换**（带时间戳）：空间一旦被浏览器权限弹窗接管
//    （ownership 变成 agentDelegatedToUser），按名字复用就会一直撞在同一个卡住的空间上。
const RUN_ID = (process.env.HOT_RUN_ID || new Date().toISOString().slice(11, 19).replace(/:/g, ''));
const task = await taskSpace(`选题雷达 · 采集 ${RUN_ID}`);
const page = task.page('p1');
const out = [];
// 多次调用（每站一次）要能**累积**：先读盘上已有的，再追加
let prev = [];
try { prev = JSON.parse(fs.readFileSync(OUT, 'utf8')); } catch (e) { prev = []; }
const writeOut = () => {
  const names = new Set(list.map(t => t.source));
  const keep = (prev || []).filter(r => !names.has(r.source));
  fs.writeFileSync(OUT, JSON.stringify(keep.concat(out), null, 1));
};

for (const t of list) {
  console.log(`===== ${t.source} ${t.url}`);
  try {
    await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(4000);
    // 有些榜单是懒加载的：先滚一下再读
    await page.evaluate('window.scrollTo(0, 800)');
    await page.waitForTimeout(2500);
    const rows = await page.evaluate(t.js);
    const n = Array.isArray(rows) ? rows.length : 0;
    console.log(`  读到 ${n} 条`);
    for (const r of (rows || [])) out.push({ ...r, source: t.source });
    if (n) console.log('  例：', (rows[0].title || '').slice(0, 60), '|', (rows[0].extra || '').slice(0, 40));
    writeOut();          // 每个站读完就落盘：后面某站弹权限框中断也不丢前面的
  } catch (e) {
    const msg = String(e);
    console.log(`  ⚠️ 失败：${msg.slice(0, 160)}`);
    // 浏览器自带的权限弹窗（通知/摄像头/…）只有人点得掉：空间被接管后继续跑只会连撞，
    // 直接收工，让已经采到的数据先落地。
    if (/permission prompt|user now controls|takeOverTaskSpace/i.test(msg)) {
      console.log('  ⛔ 浏览器弹了权限框、任务空间已交给用户 —— 本次采集到此为止（已采部分已落盘）');
      console.log('     → 在浏览器窗口里点掉那个框（点「阻止」即可），然后重跑本脚本。');
      break;
    }
  }
}

writeOut();   // ego 运行时里 fs.writeFile 需要回调，用同步版最稳
console.log(`\n📝 写入 ${OUT}（共 ${out.length} 条）`);
try { await task.finish({ keep: [] }); } catch (e) { console.log(`（收尾跳过：${String(e).slice(0, 80)}）`); }
