// scripts/gen_gpt_covers.mjs —— 用 GPT 出封面两张（3:4 + 4:3），阿囤囤「产品测评榜单风」
//
// 用法：**必须走 ego-browser 运行时**（taskSpace 等是它注入的全局，直接 node 跑会 ReferenceError）：
//   ~/.local/bin/ego-browser nodejs < scripts/gen_gpt_covers.mjs
//   （脚本读 content/episode-<N>/cover-prompt.json；期号从 /tmp/cover_ep.txt 取，ego 运行时不继承环境变量）
//
// 为什么要有它（2026-09-14 实测固化）：
//   · 封面改为 GPT 出图后，「分两次、两个比例」必须**分别原生生成**（不是裁切）；
//   · **必须把 `assets/brand/chai-editor-avatar-cutout.png` 作为参考图1 上传**，否则模型会自己画一只别的柴犬；
//   · 上传要用 `input[type=file] >> nth=0`（裸选择器会匹配到 5 个 input 而失败）；
//   · 抓生成图的判据必须是**宽高比**（3:4 → 0.70–0.80 / 4:3 → 1.25–1.42），
//     不要用"图片数量 +1"——上传的参考图会被算进去，实测把头像当成了封面存下来；
//   · 提示词里写死两条禁令：不许出现英文/水印、**不许出现我没给的数字**（模型编造过 8 个星数）。
//
// ⚠️ 2026-09-14 EP.182/183 封面连续两轮全废的事故与修复（这段必须留着）：
//   现象——10×20s 轮询全是「候选 无」，两张都没出图。
//   根因（探针实测）：ChatGPT 的 composer 已换成 `data-type="unified-composer"`（ProseMirror 编辑区，
//   **不是 `<textarea>`**）。旧写法 `page.fill()` + 宽选择器点发送，在**编辑器里残留上一次提示词**时
//   （goto 到 chatgpt.com 会载入上次会话！）会出现：文字填进去了、但框架状态没更新 → 发送按钮实际没被点上，
//   而 catch 里的 Enter 退化在 ProseMirror 里只换行 → **提示词一直躺在输入框里没发出去**，
//   脚本却报「已发送」，然后白等 200s 报「未拿到符合比例的生成图」。
//   修复（本文件）：① 每张图前**先开新聊天**；② `fill(..., {clearFirst:true})` 保证替换而不是追加；
//   ③ 发送后**回读用户消息条数 + 输入框是否清空**来确认真的发出去了（最多重试 3 次）；
//   ④ 发送按钮用**实测存在的** `button[data-testid='send-button']`（aria-label「发送提示词」）；
//   ⑤ 失败时把最后一条助手消息与截图落盘，别再只报「候选 无」。
import fs from 'node:fs';
import path from 'node:path';

const ROOT = '/Users/chao/Documents/dailyvideos';
const ep = ((globalThis.process?.env?.COVER_EP) ||
            (fs.existsSync('/tmp/cover_ep.txt') ? fs.readFileSync('/tmp/cover_ep.txt', 'utf8') : '')).trim();
if (!ep) {
  console.error('用法：把期号写进 /tmp/cover_ep.txt（如 `echo 182 > /tmp/cover_ep.txt`）');
  process.exit(2);
}
// ego 运行时不继承环境变量（本文件顶部注释已记），所以调试开关一律走文件
function flag(file, want) {
  try { return fs.readFileSync(file, 'utf8').trim() === want; } catch (e) { return false; }
}

const cfgPath = path.join(ROOT, `content/episode-${ep}/cover-prompt.json`);
if (!fs.existsSync(cfgPath)) {
  console.error(`❌ 缺配置：${cfgPath}`);
  process.exit(2);
}
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
// ⚠️ 2026-09-15 修：`cover-prompt.json` 里的 `proj` 本身就是 `videos/<slug>`，
//    旧写法又拼了一层 'videos' → 变成 `videos/videos/<slug>/...`（**不存在**），
//    于是参考图**一直没真正上传**（`cover-meta.json` 里记的就是这条坏路径）。
//    现在按 proj 原样拼，并在文件不存在时**大声报错**。
const AVATAR = cfg.avatar || path.join(ROOT, cfg.proj || `videos/ep-${ep}`, 'assets/brand', 'chai-editor-avatar-cutout.png');
if (!fs.existsSync(AVATAR)) console.error(`❌ 参考图不存在：${AVATAR}（角色会不一致）`);
const OUTDIR = path.join(ROOT, `content/episode-${ep}/exp-gpt`);

(async () => {
  const fs2 = await import('node:fs/promises');
  await fs2.mkdir(OUTDIR, { recursive: true });

  const task = await taskSpace(`GPT 封面 · EP.${ep}`);
  const page = task.page('p1');
  await page.goto('https://chatgpt.com/', { waitUntil: 'domcontentloaded' });
  // ⚠️ 2026-09-26：ChatGPT 前端改版后 composer **不再有 `#prompt-textarea` 这个 id**
  //   （页面上只剩 `.ProseMirror[contenteditable=true]`），旧选择器会 waitForSelector 超时 40s → 整条出图链路挂掉。
  //   → 先等 ProseMirror，再**在运行时给它补上 id**，后面所有沿用 `#prompt-textarea` 的老代码就不用改。
  await page.waitForSelector('.ProseMirror[contenteditable="true"], #prompt-textarea', { timeout: 60000 });
  await ensureComposerId();
  await page.waitForTimeout(2500);

  /** ⚠️ 2026-09-26 事故（EP.214）：ChatGPT 前端又改版了 —— 消息容器**不再有 `data-message-author-role`**
   *  （也没有 `article` / `[data-testid^=conversation-turn]`）。于是：
   *    `userCount()` 恒为 0 → `sendPrompt()` 的「回读确认」永远判失败（其实消息发出去了）；
   *    `lastAssistant()` 恒为空 → `waitAssistantIdle()` 每次都空等到 150s 超时。
   *  实测（探针）新 DOM 的消息判据是**无障碍标题 `<h4 class="sr-only">`**：
   *    用户消息的 h4 文本 = 「你说：<正文>」，助手消息 = 「ChatGPT 说：<正文>」。
   *  这里做成**兼容层**：优先老选择器，老选择器为空时走 h4 判据；返回值结构统一。 */
  const MSGS_JS = () => {
    const legacy = [...document.querySelectorAll('[data-message-author-role]')]
      .map(e => ({ role: e.getAttribute('data-message-author-role'), text: (e.innerText || '').trim() }));
    if (legacy.length) return legacy;
    const h4s = [...document.querySelectorAll('h4')].filter(h => {
      const t = (h.textContent || '').trim();
      return /^(你说[:：]|You said|ChatGPT 说[:：]|ChatGPT said)/.test(t);
    });
    return h4s.map(h => {
      const head = (h.textContent || '').trim();
      const role = /^(你说[:：]|You said)/.test(head) ? 'user' : 'assistant';
      // 往上爬到「只含这一个 h4」的最大祖先 = 恰好这一条消息的容器
      let box = h.parentElement, best = h;
      for (let i = 0; i < 5 && box; i++) {
        if (box.querySelectorAll('h4').length > 1) break;
        best = box; box = box.parentElement;
      }
      const text = ((best && best.innerText) || head).trim();
      return { role, text };
    });
  };

  const userCount = async () => (await page.evaluate(MSGS_JS)).filter(m => m.role === 'user').length;
  const composerEmpty = () => page.evaluate(() => {
    const t = document.querySelector('#prompt-textarea');
    return !!t && (t.innerText || '').trim() === '';
  });

  /** 给 composer 补上 `#prompt-textarea` 这个 id（新版前端不带了），返回是否成功。 */
  async function ensureComposerId() {
    try {
      return await page.evaluate(() => {
        const cand = document.querySelector('#prompt-textarea')
          || document.querySelector('.ProseMirror[contenteditable="true"]')
          || document.querySelector('[contenteditable="true"]');
        if (!cand) return false;
        if (cand.id !== 'prompt-textarea') cand.id = 'prompt-textarea';
        return true;
      });
    } catch (e) { return false; }
  }

  async function newChat() {
    try {
      await page.click("button[aria-label*='新聊天'], button[aria-label*='New chat'], a[data-testid='create-new-chat-button']",
        { timeout: 5000 });
      await page.waitForTimeout(2500);
    } catch (e) {
      console.log('  （没找到「新聊天」按钮，改用清空输入框）');
    }
  }

  /** ⚠️ 实测（探针 6 / bash-94 / bash-95 三组对照）：**必须等固定的一段时间**再输入文字。
   *  · 探针 6：setInputFiles 后**固定等 12s** → 输入 → 点发送 = **成功**；
   *  · bash-93（轮询缩略图出现就往下走）→ **失败**；
   *  · bash-94/95（轮询「缩略图 >0 且按钮 aria-disabled=false」，结果第 0 秒就成立）→ **失败**。
   *  即「缩略图出现」**不等于**「上传完成」；缩略图是乐观渲染的。这里老老实实等 20s。
   *  （发送按钮在上传中会变成转圈 spinner，看 `aria-disabled` 也不可靠——它 0s 就是 false。）
   */
  async function attachAvatar() {
    // 对照实验开关（2026-09-16）：把 `no_avatar` 写进 /tmp/cover_no_avatar.txt 就跳过参考图。
    if (fs.existsSync('/tmp/cover_no_avatar.txt') && fs.readFileSync('/tmp/cover_no_avatar.txt','utf8').trim() === 'no_avatar') {
      console.log('  （对照：跳过参考图）');
      return false;
    }
    try {
      await page.setInputFiles('input[type=file] >> nth=0', [AVATAR]);
      console.log('  …参考图已投喂，固定等 20s 让上传跑完');
      await page.waitForTimeout(20000);
      const n = await page.evaluate(() => document.querySelectorAll("#prompt-textarea img, form img").length);
      console.log(`  ✅ 参考图等待结束（输入框内图片元素 ${n} 个）`);
      return true;
    } catch (e) {
      console.log('  ⚠️ 参考图上传失败（角色可能不一致）：', String(e).slice(0, 90));
      return false;
    }
  }

  /** 清空 composer。
   *  ⚠️ 实测（探针 4）：点了「新聊天」之后输入框里**仍留着上一次会话的 951 个字符**
   *  （goto chatgpt.com 会载入上次会话），必须显式 Meta+A → Delete 才算干净。
   *  ⚠️ 实测（探针 5 vs 6）：清空**必须发生在附参考图之前**——附了附件再 Meta+A/Delete
   *  会让后续发送彻底不生效（按钮 aria-disabled=true、文字留在框里、消息数不动）。 */
  /** 聚焦输入框：**优先真实点击，失败就退回 DOM focus()**。
   *  ⚠️ 2026-09-15 实测：ego 的点击在「元素不在视口内」时会直接抛
   *  `page.click timed out: element is not visible in the viewport`（新开的 ChatGPT 页
   *  布局还没稳定时会出现），旧写法会让整个脚本崩掉。 */
  async function focusComposer() {
    await ensureComposerId();
    try {
      await page.click('#prompt-textarea', { timeout: 6000 });
    } catch (e) {
      await page.evaluate(() => {
        const t = document.querySelector('#prompt-textarea');
        if (t) { t.scrollIntoView({ block: 'center' }); t.focus(); }
      });
    }
    await page.waitForTimeout(200);
  }

  /** 发送：**优先回车**。
   *  ⚠️ 2026-09-15 实测（探针 12）：ego 给这个标签页的 viewport 是 **0×0**
   *  （`window.innerWidth === 0`），于是 `page.click()` 一律报
   *  「element is not visible in the viewport」；而 `page.press(Enter)` 不依赖几何，
   *  实测能把消息发出去（用户消息 0→1）。所以**回车是主路径，点按钮只是兜底**。 */
  async function submit() {
    await ensureComposerId();
    let how = '回车';
    try {
      await page.press('#prompt-textarea', 'Enter');
    } catch (e) {
      how = '点按钮';
      try { await page.click("button[data-testid='send-button']", { timeout: 8000 }); }
      catch (e2) { how = '无手段'; }
    }
    return how;
  }

  async function clearComposer() {
    await ensureComposerId();
    await focusComposer();
    await page.waitForTimeout(250);
    await page.keyboard.press('Meta+a');
    await page.waitForTimeout(150);
    await page.keyboard.press('Delete');
    await page.waitForTimeout(300);
    return page.evaluate(() => {
      const t = document.querySelector('#prompt-textarea');
      return t ? (t.innerText || '').length : -1;
    });
  }

  async function typePrompt(text) {
    await ensureComposerId();
    await focusComposer();
    await page.keyboard.insertText(text);
    await page.waitForTimeout(1500);
    return page.evaluate(() => {
      const t = document.querySelector('#prompt-textarea');
      return t ? (t.innerText || '').length : -1;
    });
  }

  /** 发一条文字提示词（**不带附件**），并**用回读确认真的发出去了**（不是靠 catch 不报错）。
   *  ⚠️ 实测（探针 4）：`page.fill()` 对 unified-composer（ProseMirror）**直接报错**
   *  「page.fill did not accept the text. Click the editor and use page.keyboard」——
   *  工具自己就给了正解：点编辑区 + page.keyboard。这里用 `keyboard.insertText`（CDP
   *  insertText，会触发 input 事件），实测可以真正把消息发出去。
   *  ⚠️ 2026-09-14 晚定案：**长文字 + 附件同一条消息，发送按钮点不动**（探针 8 对照：
   *  无附件 951 字能发；带附件 951 字点发送无反应；先后顺序无关）。所以参考图**单独发一条**。 */
  async function sendPrompt(text) {
    for (let attempt = 1; attempt <= 3; attempt++) {
      if (attempt > 1) {
        await clearComposer();
      }
      const len = await typePrompt(text);
      const n0 = await userCount();
      const how = await submit();
      await page.waitForTimeout(8000);
      const n1 = await userCount();
      const empty = await composerEmpty();
      console.log(`  发送尝试 ${attempt}（${how}）：输入 ${len} 字 · 用户消息 ${n0}→${n1} · 输入框已清空=${empty}`);
      if (n1 > n0 || (empty && len > 0)) return true;
    }
    return false;
  }

  /** 参考图**单独发一条消息**（不带任何文字）。
   *  ⚠️ 2026-09-14 晚实测（探针 9）：`纯附件` 可以发出去（用户消息 0→1）；
   *  一旦在同一个 composer 里再加上文字，发送按钮就点不动了。
   *  ⚠️ 另一个坑（bash-97 实测）：附件**发出前**不要再点输入框 / 再按一次 Meta+A+Delete ——
   *  那会把编辑器留在"刚被清过"的状态，随后纯附件也发不出去。发附件前只允许**已经**清过一次。 */
  async function sendAvatarOnly() {
    for (let attempt = 1; attempt <= 3; attempt++) {
      await attachAvatar();
      const n0 = await userCount();
      const how = await submit();
      await page.waitForTimeout(8000);
      const n1 = await userCount();
      console.log(`  参考图发送尝试 ${attempt}（${how}）：用户消息 ${n0}→${n1}`);
      if (n1 > n0) return true;
    }
    return false;
  }

  /** 兜底：**复用最近一个已经带过参考图的会话**（探针 9 那条成功了）。
   *  点侧栏第一条历史 → 确认会话里确实有图片 → 直接在这条会话里发提示词（纯文字可发）。 */
  async function reuseRecentConversation() {
    // ⚠️ 2026-09-15 实测：这个标签页 viewport 是 0×0、侧栏默认收起 → `a[href*='/c/']` 抓不到；
    //    而「带附件的消息」在当前状态下又发不出去（头像发不出去 → 会话里没有角色参考图）。
    //    所以这里①先打开侧栏 ②再读状态文件里上次成功的会话 URL ③最后才读页面链接；
    //    成功一次就把 URL 存进 /tmp/cover_chat_url.txt 供下次直接用。
    const STATE = '/tmp/cover_chat_url.txt';
    const candidates = [];
    try {
      if (fs.existsSync(STATE)) {
        const u = fs.readFileSync(STATE, 'utf8').trim();
        if (u) candidates.push(u);
      }
    } catch (e) {}
    try {
      await page.click("button[aria-label*='打开侧边栏'], button[aria-label*='Open sidebar']", { timeout: 4000 });
      await page.waitForTimeout(2500);
    } catch (e) {}
    try {
      const links = await page.evaluate(() => [...document.querySelectorAll("a[href*='/c/']")]
        .map(a => 'https://chatgpt.com' + a.getAttribute('href').split('?')[0]).slice(0, 8));
      console.log('  侧栏会话候选：', JSON.stringify(links).slice(0, 240));
      candidates.push(...links);
    } catch (e) {}
    for (const url of [...new Set(candidates)]) {
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(9000);
        const imgs = await page.evaluate(() => [...document.querySelectorAll('img')]
          .filter(x => /estuary\/content|oaiusercontent|backend-api\/files/.test(x.src || '') && x.naturalWidth > 200)
          .map(x => x.naturalWidth + 'x' + x.naturalHeight));
        console.log(`  ${url.slice(-12)} 里的图片：`, JSON.stringify(imgs).slice(0, 120));
        if (imgs.length > 0) {
          fs.writeFileSync(STATE, url);
          return true;
        }
      } catch (e) {
        console.log('  打开会话失败：', String(e).slice(0, 80));
      }
    }
    return false;
  }

  const common = [
    '**参考图1是我账号的角色**：一只**柴犬主编**（毛绒玩具质感、颜色与参考图一致）。请严格按参考图1的长相、配色、毛绒质感来画，不要换品种、不要改成真人；姿态按下面要求摆。',
    '硬规矩：① **画面里绝对不要出现任何英文单词、字母、水印**（工具本身的品牌名如 LM Studio / Ollama / llama.cpp 除外）；',
    '② **绝对不要出现任何我没有给你的数字**；③ **画面里只允许出现下面列出的这些文字，一个字都不许增删**，不要自己加标签/关键词/口号；④ 所有中文逐字正确。',
    '⑥ **品牌色必须真的用足（这条也会被量）**：画面里的浅黄绿 **#FDFFA7** 是频道识别色，**主标题本身必须是 #FDFFA7（不是白色、不是灰色）**，且**浅黄绿的总面积要占整张画面的 8%–14%**（靠主标题的字面 + 底部横幅 + 一条粗色带凑够；只有细描边不够，会被判成「不是本频道的封面」）。',
    '⑤ **安全边距是硬要求（会拿尺子量，量的是画面百分比）**：',
    '   · 把整张画布想象成**中间一个 84% 宽的安全框**：所有文字必须完整落在框内，框外那 8% 的四周只能是背景（场景、光效、装饰物可以延伸出去，但**一个字都不能进**）。',
    '   · **主标题刻意排成两行**（例如「修照片」/「不用买软件」这样断行），**任何一行都不许超过画面宽度的 62%** —— 排不下就缩小字号，绝不许拉宽到接近画面两边。',
    '   · 除主标题外，其它文字也都不许越过 8%–92% 的范围。',
    '   · 平台会裁封面，贴边的字会被切掉（2026-09-16 抖音竖封面就是这么被切掉字的），**所以这条规则比「好看」优先**。',
    '⑤ **背景装饰性词里绝对不要出现任何与钱有关的词**（省钱 / 更便宜 / 划算 / 免费额度 / 收益 / 回本 / 性价比 等一律不要），也不要用「更省钱」这类话术 —— 封面不放任何金钱暗示。',
  ].join('\n');

  const items = (cfg.items || []).map((t) => `「**${t}**」`).join('、');
  /** 4:3 背景装饰词的**白名单**（名词）。
   *  ⚠️ 2026-09-26 事故：这份清单原来**写死在脚本里**（安卓 / 手机 / 开源 / 工具 / 播客 / 视频 / 终端 /
   *  命令行 / 手册 / 屏幕），于是**每一期**的 4:3 封面都长着同一批装饰词 —— 做工具清单期还算贴题，
   *  做**新闻汇总期**（EP.214 讲三家闭源模型）就变成「封面背景写着『开源』」：正是 EP.211 评审判过 P0
   *  的那类错误（最显眼的面说错，正文再自我更正也没用）。
   *  → 改成**按期刊可配**：`cover-prompt.json` 里给 `decor`（本期相关名词），没给才回退旧清单。
   *  纪律：`decor` 必须和本期主题同一件事，且只能是名词。 */
  const decorList = (Array.isArray(cfg.decor) && cfg.decor.length
    ? cfg.decor
    : ['安卓', '手机', '开源', '工具', '播客', '视频', '终端', '命令行', '手册', '屏幕']).join(' / ');
  const allowlist = [
    `角标/系列行（**必须逐字出现**）：「${cfg.kicker}」`,
    `主标题（最大）：「${cfg.hero}」`,
    `副标题：「${cfg.sub}」`,
    `三条勾选清单：${items}`,
    `底部横幅：「${cfg.banner}」`,
    '以及背景里淡淡的、**与本期主题相关**的装饰性词（可不出现；必须和角标/主标题讲的是同一件事，不要掺别的主题的词；**装饰词只允许是名词**——工具名 / 文件格式名 / 技术名词；**绝对不要任何形容词、口号或承诺类词**：更安心 / 更省心 / 更自由 / 更轻松 / 更简单 / 安全 / 隐私 / 免费 / 最强 / 最好 / 放心 / 自由 等一律不许出现 —— 它们会被当成我们对效果的承诺）',
  ].join('\n    ');

  function promptFor(ratio) {
    if (ratio === '3x4') {
      return [
        '用**阿囤囤「产品测评榜单风」**出一张小红书封面（**3:4 竖版**）。',
        common,
        '',
        '**允许出现的全部文字（逐字，不许增删）**：',
        '    ' + allowlist,
        '',
        '构图：',
        '- 柴犬主编位于画面**右下**，占画面约 40%，一只手指向中间的巨大文字；边缘有柔和浅黄 **#FDFFA7** 描边（抠图感）。',
        `- **顶部**中文标题「**${cfg.hero}**」：柔和浅黄 #FDFFA7 超粗黑体、粗黑描边。`,
        `- 标题下方一行白色粗体小字：「**${cfg.sub}**」，右上角放一个小胶囊写「**${cfg.ep_label}**」。`,
        `- 画面**中部**三条**绿色勾选**清单（白色粗体、黑描边）：${items}。`,
        `- **底部**一条 #FDFFA7 横幅写「**${cfg.banner}**」（黑色粗体）。`,
        '- 背景：**深蓝黑科技工具墙**（深色卡片、模糊界面块），局部暗角，**不抢标题**。',
        '',
        '3:4 竖版，高对比高密度，一眼能读懂。',
      ].join('\n');
    }
    return [
      '再来**同一套设计的横版 4:3**（抖音/头条主投放位）。**配色、元素、角色、文案与上一张保持同一套**，版式针对横版**重新编排**（不是竖版裁切/拉伸）。',
      common,
      '',
      '横版构图：',
      `- **左侧文字区**：顶部小胶囊「**${cfg.kicker}**」；其下巨大标题「**${cfg.hero}**」（#FDFFA7、粗黑描边、字号最大）；标题下一行白色小字「**${cfg.sub}**」；再下三条绿色勾选（${items}）；最底部 #FDFFA7 横幅「**${cfg.banner}**」。`,
      '- **右侧**柴犬主编半身，占画面高约 60%，手指向左侧标题，边缘 #FDFFA7 描边。',
      '- 背景同为深蓝黑科技工具墙 + 暗角。',
      `**背景装饰词只能用这些名词**：${decorList}；`
        + '**绝对不要**出现：隐私 / 自由 / 安全 / 免费 / 效率 / 生活 / 探索 / 创意 / 更好的 / 更省 / 更安心 —— '
        + '这些是评价词或口号，会被当成我们对效果的承诺（2026-09-20 实测：不加这句，模型必写「隐私 / 自由 / 探索」）。',
      '',
      '4:3 横版，高对比高密度。',
    ].join('\n');
  }

  /** 生成图候选。
   *  ⚠️ 2026-09-26 事故（EP.214）：新前端的成图**不再是 `estuary/content` 之类 HTTP 地址，而是 `blob:`
   *  对象 URL**，`alt` 固定为「已生成图像 N」。旧白名单把它全滤掉 → 连续 30+ 轮「候选 无」，
   *  日志里助手却一路在报进度（「布置场景 62%」「即将完成 83%」）——**图早就出来了，是我们没看见**。
   *  → 白名单加 `blob:`，并用 `alt` 排除用户自己上传的参考图（`用户附件`）。 */
  const IMG_JS = () => [...document.querySelectorAll('img')]
    .filter(x => /estuary\/content|oaidalleapi|oaiusercontent|backend-api\/files|^blob:/.test(x.src || '')
      && (x.alt || '') !== '用户附件' && x.naturalWidth > 500)
    .map(x => ({ src: x.src, w: x.naturalWidth, h: x.naturalHeight, alt: x.alt || '' }));

  /** 助手最后一条消息（新老两套 DOM 都认，见上面 MSGS_JS 的注释）。 */
  const lastAssistant = async () => {
    const msgs = await page.evaluate(MSGS_JS);
    const a = msgs.filter(m => m.role === 'assistant');
    const e = a[a.length - 1];
    return e ? (e.text || '').trim().slice(0, 600) : '';
  };

  /** 一个会话里出两张：**参考图单独发一条**（纯附件），再发第 1 张的提示词，
   *  第 2 张沿用同一会话（提示词里自带「再来同一套设计的横版 4:3」，与既有做法一致）。 */
  /** 轮询捞某个比例的**新**成图。
   *  ⚠️ 2026-09-14 晚实测（第二次事故）：复用会话（`reuseRecentConversation`）时，
   *  上一轮生成的封面**还挂在会话里**，`collect` 会把它当成本轮成图存下来 ——
   *  EP.183 就这样存到了 EP.182 的封面（OCR 里出现「182 / 2000 / 20GB」才发现）。
   *  → 发提示词**之前**先快照所有图片 src，之后**只认 src 不在快照里的新图**。 */
  const IMG_SRCS = () => [...document.querySelectorAll('img')]
    .filter(x => /estuary\/content|oaidalleapi|oaiusercontent|backend-api\/files|^blob:/.test(x.src || '')
      && (x.alt || '') !== '用户附件')
    .map(x => x.src);

  /** 把一张成图写盘。⚠️ `blob:` URL 是**页面作用域**的，`page.fetch` 拿不到（会 404/报错），
   *  必须在页面里 `fetch()` → `FileReader` 转 data URL 再落盘（2026-09-26 起 blob 是新常态）。 */
  async function saveImg(src, out) {
    if (!/^blob:/.test(src)) {
      const r = await page.fetch(src, { saveAs: out, timeout: 60000 });
      const st = await fs2.stat(out);
      return { ok: r.ok, mb: st.size / 1048576 };
    }
    const dataUrl = await page.evaluate(async (s) => {
      const b = await (await fetch(s)).blob();
      return await new Promise((res, rej) => {
        const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = rej; fr.readAsDataURL(b);
      });
    }, src);
    const buf = Buffer.from(String(dataUrl).split(',')[1], 'base64');
    await fs2.writeFile(out, buf);
    return { ok: true, mb: buf.length / 1048576 };
  }

  async function collect(ratio, out, rounds, tag, seenBefore) {
    const want = ratio === '3x4' ? [0.70, 0.80] : [1.25, 1.42];
    for (let i = 1; i <= rounds; i++) {
      await page.waitForTimeout(20000);
      const cand = await page.evaluate(IMG_JS);
      const fresh = cand.filter(c => !seenBefore.has(c.src));
      const hit = fresh.filter(c => { const r = c.w / c.h; return r > want[0] && r < want[1]; }).pop();
      if (hit) {
        const r = await saveImg(hit.src, out);
        console.log(`  ✅ ${tag} ${ratio} 新图命中 ${hit.w}x${hit.h}（比例 ${(hit.w / hit.h).toFixed(3)}）存盘 ok=${r.ok} ${r.mb.toFixed(2)}MB`);
        return true;
      }
      console.log(`  ${tag} ${ratio} 第${i}轮：候选 ${cand.map(c => `${c.w}x${c.h}${seenBefore.has(c.src) ? '(旧)' : ''}`).join(',') || '无'}`);
      // 诊断开关（2026-09-22）：3:4 连续 3 次"提示词发出去了但不出图"时加的 —— 每轮把助手最后一条
      // 消息打出来，能立刻分辨"模型还在生成 / 模型反问了 / 被拒了"三种情况。
      if (flag('/tmp/cover_debug.txt', '1')) {
        const t = await lastAssistant();
        console.log(`     ↳ 助手最后一条：${(t || '(空)').replace(/\s+/g, ' ').slice(0, 200)}`);
      }
    }
    return false;
  }

  /** 等助手停下（没有正在生成的消息）。参考图的确认语是流式的，还没写完就发提示词，
   *  实测（2026-09-22 EP.205）三次都出现「提示词已发出、用户消息 +1、但助手永远不回复」→ 不出图。 */
  /** 正在生成中？（新老前端兼容：老版有 stop 按钮；新版实测有「停止」按钮 / result-streaming 类） */
  const assistantBusy = () => page.evaluate(() =>
    !!(document.querySelector("[data-testid*='stop'], button[aria-label*='Stop'], button[aria-label*='停止']")
       || document.querySelector('.result-streaming')
       || /正在(生成|思考|回答)/.test(document.body.innerText.slice(-400))));

  async function waitAssistantIdle(maxMs = 150000) {
    const t0 = Date.now();
    let last = '', stable = 0;
    while (Date.now() - t0 < maxMs) {
      await page.waitForTimeout(6000);
      const cur = await lastAssistant();
      const busy = await assistantBusy();
      if (!busy && cur === last) { stable++; if (stable >= 2) return true; }
      else stable = 0;
      last = cur;
    }
    console.log('  ⚠️ 等待助手停下超时，继续发提示词');
    return false;
  }

  async function gen(ratio, out) {
    // ⚠️ 2026-09-16 事故：基线快照取太早 —— 会话里的旧图还没渲染完，
    //   上一期那张封面在快照之后才出现，于是被当成本轮"新图"存了下来
    //   （EP.189 的封面 = EP.188 的封面，md5 完全相同）。
    //   → 导航进会话后先等稳，再**连拍两次**取并集当基线。
    await page.waitForTimeout(12000);
    const b1 = await page.evaluate(IMG_SRCS);
    await page.waitForTimeout(5000);
    const b2 = await page.evaluate(IMG_SRCS);
    const seenBefore = new Set([...b1, ...b2]);
    await waitAssistantIdle();          // ← 先确认上一句写完了（见上面注释）
    console.log(`  基线（连拍并集）${seenBefore.size} 张`);
    console.log(`  发送前会话里已有 ${seenBefore.size} 张图（本轮只认新图）`);
    const ok = await sendPrompt(promptFor(ratio));
    if (!ok) {
      console.log(`  ❌ ${ratio} 提示词没发出去，跳过`);
      return false;
    }
    let got = await collect(ratio, out, 15, '首发', seenBefore);
    if (!got) {
      // ── 追一句"续跑"提示（2026-09-22 EP.205 起固定动作）──────────────────────────
      //  实测：全新会话里，参考图的确认语（模型还会反问一句"先做竖版还是横版？"）还没写完时
      //  发出去的第一条提示词**会被吞掉** —— 用户消息在会话里，但助手永远不回复（等满 15 轮 + 12 轮
      //  补扫都不出图，`busy=false`）。此时只要再发一句"请按上一条提示词直接出图"，模型立刻开工
      //  （实测 15 秒内 busy=true 并出图）。所以这里把它做成**兜底重试**，而不是人工救场。
      console.log(`  ↻ ${ratio} 首发被吞（助手没回复上一条），补一句续跑提示…`);
      const nudge = `请按我上一条消息里的完整提示词直接出图（${ratio === '3x4' ? '竖版 3:4' : '横版 4:3'}封面，`
        + '画面文字只能出现我列出的那些，一字不增不减）。';
      if (await sendPrompt(nudge)) {
        await page.waitForTimeout(5000);
        const b3 = await page.evaluate(IMG_SRCS);
        await page.waitForTimeout(4000);
        const b4 = await page.evaluate(IMG_SRCS);
        const seen2 = new Set([...seenBefore, ...b3, ...b4]);
        got = await collect(ratio, out, 12, '续跑', seen2);
      }
    }
    if (!got) {
      const txt = await lastAssistant();
      console.log(`  ⚠️ ${ratio} 首发轮询未见新成图；助手最后一条消息：${txt || '(空)'}`);
      try { await page.screenshot({ path: path.join(OUTDIR, `fail-${ratio}.png`) }); } catch (e) {}
    }
    return got;
  }

  const only = ((globalThis.process?.env?.COVER_ONLY) ||
                (fs.existsSync('/tmp/cover_only.txt') ? fs.readFileSync('/tmp/cover_only.txt', 'utf8') : '')).trim();
  // ── 会话初始化：新聊天 → 清空 → **参考图单独发一条**；不行就复用最近带图会话 ──
  await newChat();
  const left = await clearComposer();
  console.log(`  新聊天后输入框残留 ${left} 字（已清空）`);
  const NO_AVATAR = fs.existsSync('/tmp/cover_no_avatar.txt') &&
                    fs.readFileSync('/tmp/cover_no_avatar.txt', 'utf8').trim() === 'no_avatar';
  let avatarOk = false;
  if (NO_AVATAR) {
    // ⚠️ 对照模式：不附参考图 → **必须留在全新会话**。
    //   复用旧会话会踩两个坑：① 上一期的封面还在里面（长会话的图是懒加载的，
    //   基线快照抓不到它，它稍后出现就被当成本轮新图 —— EP.189 两次存成了别人的封面）；
    //   ② 会话太长也会让模型跑偏。全新会话里只有本轮的图。
    console.log('  （对照模式：不附参考图，使用全新会话）');
  } else {
    avatarOk = await sendAvatarOnly();
    console.log(avatarOk ? '  ✅ 角色参考图已作为独立消息发出' : '  ⚠️ 参考图没发出去，尝试复用最近带图会话…');
    if (!avatarOk) avatarOk = await reuseRecentConversation();
  }
  console.log(avatarOk ? '  ✅ 会话里已有角色参考图' : '  ❌ 会话里没有参考图（角色可能不一致，仍继续出图）');
  await page.waitForTimeout(4000);

  let okCount = 0;
  const results = {};
  if (!only || only === '3x4') { results['3x4'] = await gen('3x4', path.join(OUTDIR, 'cover-3x4.png')); }
  if (!only || only === '4x3') { results['4x3'] = await gen('4x3', path.join(OUTDIR, 'cover-4x3.png')); }
  // ── 补扫：两张提示词都发完之后，再把没拿到的比例捞一遍（图一直在会话里） ──
  //    注意：补扫的基线取「两张都发完」时的快照，避免又把上一轮会话里的旧图当新图。
  const sweepBase = new Set(await page.evaluate(IMG_SRCS));
  for (const ratio of ['3x4', '4x3']) {
    if (results[ratio] === false || (!results[ratio] && (!only || only === ratio))) {
      const out = path.join(OUTDIR, `cover-${ratio}.png`);
      if (!fs.existsSync(out)) {
        console.log(`  ↻ 补扫 ${ratio} …`);
        results[ratio] = await collect(ratio, out, 12, '补扫', sweepBase);
      }
    }
  }
  okCount = Object.values(results).filter(Boolean).length;
  console.log(`EP.${ep} 封面完成 ${okCount}/${Object.keys(results).length}（${JSON.stringify(results)}）`);

  // ── 封面出处凭证（2026-09-14 事故后新增） ─────────────────────────────────
  // 事故：EP.182/183 的封面临时改用了工程内 cover.html 渲的版本，风格与 EP.181（GPT 阿囤囤版）
  // 明显不同，包照样过门禁、照样发出去，**没有任何闸门拦住"封面换了个来源"这件事**。
  // 现在：本脚本每跑一次就写一份 cover-meta.json；门禁F 只认 generator="gpt-atutun"。
  const crypto = await import('node:crypto');
  const sizes = {};
  for (const f of ['cover-3x4.png', 'cover-4x3.png']) {
    const p = path.join(OUTDIR, f);
    if (fs.existsSync(p)) {
      const buf = fs.readFileSync(p);
      sizes[f] = { bytes: buf.length, md5: crypto.createHash('md5').update(buf).digest('hex') };
    }
  }
  const meta = {
    generator: 'gpt-atutun',
    generator_script: 'scripts/gen_gpt_covers.mjs',
    prompt_file: `content/episode-${ep}/cover-prompt.json`,
    prompt_sha1: crypto.createHash('sha1').update(fs.readFileSync(cfgPath)).digest('hex'),
    // 2026-09-17 复评 P2-5：只记 cover-prompt.json 的 sha1，证明不了这张图出自**哪一版提示词模板**；
    // 于是出现过「改了模板、图还是旧规则出的」而这种错配没有任何凭证能查。把模板自己也记上。
    generator_script_sha1: crypto.createHash('sha1')
      .update(fs.readFileSync(path.join(ROOT, 'scripts/gen_gpt_covers.mjs'))).digest('hex'),
    avatar: NO_AVATAR ? null : path.relative(ROOT, AVATAR),
    avatar_attached: NO_AVATAR ? false : avatarOk,
    no_avatar_mode: NO_AVATAR,
    generated_at: new Date().toISOString(),
    files: sizes,
    note: '工程内 cover.html 渲的版本（render_covers.mjs）不是这个 generator，禁止入包 —— 门禁F 会拦。',
  };
  // 2026-09-20 复评 P0：这里原来**从零重写** cover-meta.json，每重出一次图就把
  // `safe_margin_postprocess` / `unverifiable_postprocess` / 各种注记全抹掉（EP.195/198 都因此丢过凭证）。
  // 现在改成**合并**：新字段覆盖，旧的后处理凭证与注记保留。
  const metaPath = path.join(OUTDIR, 'cover-meta.json');
  try {
    const prev = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
    for (const k of ['safe_margin_postprocess', 'unverifiable_postprocess', 'no_postprocess',
                     'generator_script_sha1_note', 'generated_at_note', 'note_cover_3x4_roll']) {
      if (prev[k] !== undefined && meta[k] === undefined) meta[k] = prev[k];
    }
  } catch (e) { /* 首次生成，没有旧文件 */ }
  fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2));
  console.log(`  📝 已写 ${path.join(OUTDIR, 'cover-meta.json')}`);
  // 把本轮会话 URL 落盘：某张图"提示词发出去了但排队慢、轮询窗口内没回来"时，
  // 后续可以直接回到同一个会话把图取回来（2026-09-22 EP.205 的 3:4 就是这么救回来的）。
  try {
    const chatUrl = await page.evaluate(() => location.href);
    if (/chatgpt\.com\/c\//.test(chatUrl)) {
      fs.writeFileSync('/tmp/cover_chat_url.txt', chatUrl);
      console.log(`  📝 会话 URL 落盘：${chatUrl}`);
    }
  } catch (e) {}
  if (flag('/tmp/cover_keep.txt', '1')) {
  console.log('  （COVER_KEEP=1：保留任务空间，供人工查看会话）');
} else {
  await task.finish({ keep: [] });
}
})();
