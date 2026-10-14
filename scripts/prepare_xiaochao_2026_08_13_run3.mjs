#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const root = "<REPO>";
const date = "2026-08-13";
const contentRoot = path.join(root, "content", date);
const outputRoot = path.join(root, "output", "xiaochao", date);
const sourceRoot = "/private/tmp/xiaochao-radar-run3";

const ensureNew = (target) => {
  if (fs.existsSync(target)) throw new Error(`Refusing to overwrite existing path: ${target}`);
};
const writeNew = (target, body) => {
  ensureNew(target);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, body.endsWith("\n") ? body : `${body}\n`);
};
const copyNew = (source, target) => {
  ensureNew(target);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.copyFileSync(source, target);
};
const esc = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
const flowSvg = (title, steps) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200">
<rect width="900" height="1200" fill="#F6F0E4"/><text x="55" y="92" font-family="sans-serif" font-size="44" font-weight="900" fill="#1B1916">${esc(title)}</text>
${steps.map((step,index)=>{const y=160+index*235;const fill=["#B9F227","#FFD45A","#FF5A36","#F6F0E4"][index%4];return `<rect x="55" y="${y}" width="790" height="165" rx="24" fill="${fill}" stroke="#1B1916" stroke-width="8"/><circle cx="125" cy="${y+82}" r="38" fill="#1B1916"/><text x="125" y="${y+96}" text-anchor="middle" font-family="monospace" font-size="38" font-weight="900" fill="#F6F0E4">${index+1}</text><text x="195" y="${y+96}" font-family="sans-serif" font-size="36" font-weight="900" fill="#1B1916">${esc(step)}</text>${index<steps.length-1?`<path d="M450 ${y+175}v50" stroke="#1B1916" stroke-width="9"/><path d="m430 ${y+210} 20 22 20-22" fill="none" stroke="#1B1916" stroke-width="9"/>`:""}`;}).join("\n")}</svg>`;
const limitsSvg = (title, items) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200"><rect width="900" height="1200" fill="#F6F0E4"/><rect x="52" y="54" width="796" height="1092" rx="28" fill="#FFD45A" stroke="#1B1916" stroke-width="9"/><text x="90" y="145" font-family="sans-serif" font-size="48" font-weight="900" fill="#1B1916">${esc(title)}</text>${items.map((item,index)=>{const y=245+index*270;return `<rect x="92" y="${y}" width="716" height="198" rx="22" fill="#F6F0E4" stroke="#1B1916" stroke-width="7"/><circle cx="155" cy="${y+70}" r="36" fill="#FF5A36" stroke="#1B1916" stroke-width="6"/><text x="155" y="${y+84}" text-anchor="middle" font-family="monospace" font-size="38" font-weight="900" fill="#1B1916">!</text><foreignObject x="215" y="${y+35}" width="545" height="140"><div xmlns="http://www.w3.org/1999/xhtml" style="font:900 35px/1.25 sans-serif;color:#1B1916">${esc(item)}</div></foreignObject>`;}).join("\n")}</svg>`;

const episodes = [
  {
    issue:"023", slug:"pireel", project:"Pireel Studio", repo:"github.com/pireel/pireel", category:"AI视频局", score:"91 / 100",
    titleLines:["剪视频不装软件","浏览器里就能做"], kicker:"时间线、字幕、版式和导出，全留在本地浏览器",
    section2TitleLines:["口播视频工作台","Agent 也能直接改"], section3TitleLines:["导入原片后","画布跟着素材走"],
    stats:["浏览器本地编辑","动态字幕 + 主题","WebCodecs 导出"],
    flow:["导入原片写入 OPFS","剪辑字幕和信息卡","套用完整画面主题","浏览器本地导出成片"],
    limits:["自动转写和生成要接 Provider","Agent 控制需安装配套插件","导出依赖 Chromium WebCodecs"],
    verdict:"口播和讲解视频很合适；想要全自动生成的人仍要自己接模型",
    media:["assets/official-hero.png","assets/official-paper-cut.webp","assets/workflow.svg","assets/limits.svg","assets/official-hero.png"],
    flowTitle:"从原片到本地导出", flowSteps:["导入视频","剪辑与字幕","套用主题","浏览器导出"], limitsTitle:"本地编辑，不等于全都离线", limitItems:["转写生成需 Provider","Agent 需配套插件","导出依赖 Chromium"],
    narration:[
      "剪一个口播视频，最折腾的往往不是剪，而是素材、字幕、版式和时间线分在四五个工具里。Pireel 把这些东西放进浏览器，还能让 Agent 直接改时间线。",
      "它面向口播和讲解视频。导入原片后，可以切片、做动态字幕、加信息卡、换整套画面主题，再看实时预览。编辑数据和视频字节都留在本地浏览器，不用账号。",
      "实际链路是先把视频写进浏览器的本地存储，再在多轨时间线上剪辑、排字幕和信息块，最后通过 WebCodecs 本地导出。也可以安装配套 Agent 插件，让 Codex 或 Claude 通过 MCP 驱动编辑器。",
      "但别把本地编辑听成全自动离线。自动转写、内容规划、素材生成和跨设备同步都要接自己的 Provider；开源外壳默认会明确提示不可用。导出还依赖支持 WebCodecs 的 Chromium 浏览器。",
      "如果你常剪口播，又想保留可见时间线和手工控制，Pireel 很值得关注；只想输入一句话等成片，还得自己接模型和服务。你最想让 Agent 帮你剪哪一步？"
    ],
    sources:`# 来源与核验\n\n- 官方仓库：[pireel/pireel](https://github.com/pireel/pireel)，2026-08-13 核验 924 Star、80 Fork，AGPL-3.0-only；创建于 2026-07-20，仓库元数据最近推送为 2026-08-13。\n- 官方 README：面向 talking-head 视频；剪辑、storyboard、信息卡、动态字幕、主题、实时预览、时间线与 WebCodecs 导出均可在浏览器运行，无账号、无服务端。\n- 官方本地路径：编辑草稿保存在 localStorage，视频字节保存在 OPFS；源码通过 pnpm 启动。\n- 官方 Agent 路径：可安装 pireel-agent，通过 MCP 由 Codex 或 Claude 驱动编辑器。\n- 官方边界：自动生成、规划、转写、云端素材与跨设备同步均需注入自己的 Provider；开源外壳默认注册 unavailableProviders。\n- 官方素材：README 的编辑器 hero 与主题示例，冻结在工程 assets。\n\n大陆路径：基础编辑和本地导出无需账号；首次下载源码、依赖与 Agent 插件仍需可访问 GitHub/npm。未安装、未实测。`,
    dbs:`# DBS 门禁\n\n- dbs-ai-check：短视频文稿；首句来自真实多工具切换场景，没有“最强/颠覆”和虚构亲测。只保留一次“本地编辑不等于全自动离线”的必要翻转。通过。\n- dbs-resonate：核心机制是“把口播视频的时间线、字幕、主题和导出留在一个浏览器工作台”；Agent、Provider 与 WebCodecs 都作为工作链或边界支撑，没有另起观点。五个维度有效。通过。\n- dbs-hook：开头独立交代剪口播视频的多工具痛点，给出浏览器工作台与 Agent 控制两层抓手，并把具体链路留到正文。通过。\n- dbs-xhs-title：采用公式 #55“你到底要不要 [话题]”，定稿“你到底要不要让 Agent 剪视频？”，17 字；问题与正文决策边界一致。通过。`,
    copy:`# 发布文案\n\n## 抖音\n\n- 标题：浏览器里怎么剪口播视频？｜Pireel Studio\n- 简介：Pireel 把口播视频的时间线、动态字幕、信息卡、主题、实时预览和 WebCodecs 导出放进浏览器，基础编辑无需账号，素材留在本地。它也能由 Codex 或 Claude 通过 MCP 驱动。注意：自动转写、生成和跨设备同步仍需自己接 Provider。\n- 话题：#开源工具 #AI视频 #视频剪辑 #AIAgent #GitHub\n- 置顶评论：你最想让 Agent 帮你剪字幕、信息卡，还是节奏？\n\n## 小红书\n\n- 标题：你到底要不要让 Agent 剪视频？\n- 正文：Pireel 是一套浏览器里的口播视频工作台：时间线、动态字幕、信息卡、主题和本地导出都放在一起，也能让 Codex 或 Claude 通过 MCP 改项目。适合想保留可见时间线和手工控制的人；自动转写与生成仍要自己接 Provider。\n- 话题：#开源工具 #AI视频 #视频剪辑 #AIAgent #GitHub项目\n- 互动评论：你愿意先把哪一步交给 Agent？\n\n说明：未安装、未实测；内容来自 2026-08-13 核验的官方仓库、README、package.json 与官方素材。`,
    assets:[
      [path.join(sourceRoot,"pireel/hero.png"),"official-hero.png"],
      [path.join(sourceRoot,"pireel/paper-cut.webp"),"official-paper-cut.webp"]
    ]
  },
  {
    issue:"024", slug:"openmausbot", project:"OpenMausBot", repo:"github.com/milind-soni/OpenMausBot", category:"Agent自动化局", score:"93 / 100",
    titleLines:["Agent 开得越多","为什么越容易乱"], kicker:"把 Claude、Codex 和电脑操作，收回一张聊天界面",
    section2TitleLines:["每个 Bot 一套模型","工具和记忆也分开"], section3TitleLines:["消息进入聊天窗","审批卡片原路返回"],
    stats:["Claude / Codex / Grok","本地消息与密钥","命令和写入需审批"],
    flow:["给每个 Bot 选模型与角色","本地 Harness 启动 Agent","工具调用变成审批卡片","结果和截图回到对话"],
    limits:["桌面壳目前只做 macOS","需要 Node 24 和已登录 Agent CLI","云电脑与 500+ App 是可选外部服务"],
    verdict:"同时跑多个本地 Agent 很顺手；Windows 和 Linux 用户先别急着装",
    media:["assets/official-hero.png","assets/official-model-picker.png","assets/workflow.svg","assets/limits.svg","assets/official-approval-card.png"],
    flowTitle:"一个 Bot 的完整工作链", flowSteps:["选择模型","本地启动","审批工具","返回结果"], limitsTitle:"聊天壳之外还有门槛", limitItems:["桌面端目前 macOS","Node 24 + 已登录 CLI","外接服务需单独配置"],
    narration:[
      "同时开三个 Agent 终端，你很快会忘记谁在做什么，哪个命令还等你批准。OpenMausBot 把每个本地 Agent 变成聊天联系人，消息、工具和审批都回到一张界面里。",
      "侧边栏里的每个 Bot 都有自己的角色、模型、线程记忆和工具。底层可以跑已经登录的 Claude、Codex 或 Grok CLI，聊天记录、密钥状态和事件默认放在本机目录。",
      "工作链是先给 Bot 选模型和身份，本地 Harness 再启动对应 Agent。它调用命令、改文件或提出问题时，界面会弹出允许、拒绝和回答卡片；完成后的文字、截图和工具状态继续写回原对话。",
      "限制也很实际：桌面壳目前只做 macOS，需要 Node 二十四和至少一个已登录的 Agent CLI。云电脑与五百多个 App 连接属于可选外部服务；定时任务还是占位，Windows 和 Linux 壳尚未尝试。",
      "如果你经常并行跑多个本地 Agent，又受不了满屏终端，这种聊天联系人思路很顺手；不是 Mac 用户就先观望。你更想把研究、写代码，还是电脑操作分给独立 Bot？"
    ],
    sources:`# 来源与核验\n\n- 官方仓库：[milind-soni/OpenMausBot](https://github.com/milind-soni/OpenMausBot)，2026-08-13 核验 702 Star、121 Fork，MIT；创建于 2026-08-11，最近推送 2026-08-12。\n- 官方版本与维护：package.json 为 0.1.13；最近五次提交均在 2026-08-12，覆盖版本发布、界面和 Bot 间通信。\n- 官方 README：每个 Bot 可拥有独立角色、模型、线程、电脑和 App；底层支持已安装并登录的 Claude、Codex 与 Grok CLI。\n- 官方隐私边界：本地 Harness 监听 127.0.0.1；transcripts、keys 与 events 位于 ~/.openmausbot。命令、文件写入与问题通过审批卡片处理。\n- 官方门槛：macOS、Node >=24、pnpm，以及至少一个已安装并登录的 Agent CLI。云电脑和 Composio App 连接为可选配置。\n- 官方限制：routines 仍是占位；Windows/Linux 桌面壳尚未尝试。\n- 官方素材：仓库 docs/screenshots 的 hero、model picker 与 approval card，冻结在工程 assets。\n\n大陆路径：核心 Harness 和已登录 CLI 可本地运行；外部模型登录、云电脑及 Composio 连接的可用性取决于各自服务。未安装、未实测。`,
    dbs:`# DBS 门禁\n\n- dbs-ai-check：短视频文稿；没有虚构“我同时开过三个 Agent”，把场景改成普遍可验证的界面管理问题。功能、链路和限制节奏有长短变化。通过。\n- dbs-resonate：唯一核心是“多个本地 Agent 需要一张可见、可审批的聊天界面”；模型、Harness、审批和平台限制均服务这个机制。五个维度有效。通过。\n- dbs-hook：开头独立建立多终端混乱与待审批动作丢失的痛点，留下聊天联系人如何接管工具链的悬念。通过。\n- dbs-xhs-title：采用公式 #48“[行动] 是在浪费时间么？”，定稿“同时开三个 Agent，是在浪费时间吗？”，19 字；有数字、争议与决策悬念。通过。`,
    copy:`# 发布文案\n\n## 抖音\n\n- 标题：多个本地 Agent 怎么放进一张聊天界面？｜OpenMausBot\n- 简介：OpenMausBot 把 Claude、Codex 和 Grok CLI 变成聊天联系人，每个 Bot 有独立角色、模型、线程和工具；命令、文件写入与问题会以审批卡片返回。它目前主要面向 macOS，需要 Node 24 和已登录的 Agent CLI，云电脑与 App 连接是可选外部服务。\n- 话题：#开源工具 #AIAgent #Codex #ClaudeCode #GitHub\n- 置顶评论：你会把研究、写代码，还是电脑操作交给独立 Bot？\n\n## 小红书\n\n- 标题：同时开三个 Agent，是在浪费时间吗？\n- 正文：OpenMausBot 把多个本地 Agent 做成聊天联系人：每个 Bot 有独立角色、模型和线程，命令与文件写入会变成审批卡片。适合经常并行跑 Claude、Codex 或 Grok CLI 的 Mac 用户；Windows 和 Linux 桌面壳还没做。\n- 话题：#开源工具 #AIAgent #Codex #ClaudeCode #效率工具\n- 互动评论：如果你建三个 Bot，会怎么分工？\n\n说明：未安装、未实测；内容来自 2026-08-13 核验的官方仓库、README、package.json、提交记录和项目截图。`,
    assets:[
      [path.join(sourceRoot,"openmausbot/hero.png"),"official-hero.png"],
      [path.join(sourceRoot,"openmausbot/model-picker.png"),"official-model-picker.png"],
      [path.join(sourceRoot,"openmausbot/approval-card.png"),"official-approval-card.png"]
    ]
  },
  {
    issue:"025", slug:"md2hd", project:"md2hd", repo:"github.com/evan-steinhilb/md2hd", category:"开源效率局", score:"90 / 100",
    titleLines:["笔记越写越多","关系却越来越乱"], kicker:"Frontmatter 变节点，Wikilink 变连线，还能从图上改原文",
    section2TitleLines:["文件夹直接开地图","不用迁移笔记"], section3TitleLines:["元数据定义节点","链接自动变成边"],
    stats:["本地 127.0.0.1","无账号无遥测","Node 18 以上"],
    flow:["指向 Markdown 文件或目录","解析 frontmatter 与 wikilink","在浏览器聚焦节点和层级","从地图回到原文继续编辑"],
    limits:["关系质量取决于原始笔记结构","复杂图仍需要类型和方向配置","默认面向 Markdown / Wikilink 工作流"],
    verdict:"做研究、知识库和项目关系图很合适；零结构的散文笔记不会自动变清楚",
    media:["assets/official-shell.jpg","assets/official-type.jpg","assets/workflow.svg","assets/limits.svg","assets/official-focus.jpg"],
    flowTitle:"Markdown 变关系地图", flowSteps:["读取文件","识别节点","连接关系","回写原文"], limitsTitle:"图不会替你发明关系", limitItems:["依赖原笔记结构","复杂图要配置方向","主要面向 Markdown"],
    narration:[
      "笔记写得越多，关系反而越看不清。md2hd 不替你总结，它把 frontmatter 直接变成节点，把 wikilink 变成连线，再把整套关系图放进本地浏览器。",
      "你可以把它指向一个 Markdown 文件，也可以直接给一整个笔记目录。页面能按类型看节点、搜索全图、保存拖拽位置；点开某个节点后，还会分左右显示谁指向它、它又指向谁。",
      "链路很简单：npx md2hd 加上文件或目录，程序解析元数据和链接，在一二七点零点零点一启动地图。需要改内容时，打开节点的 Code 面板直接编辑原文件，刷新后关系就重画。",
      "它不会凭空理解一堆散文。节点类型、关系名称和方向仍要来自你的 frontmatter、wikilink 或 rel 配置；图越复杂，越需要先约定命名。运行需要 Node 十八以上，主要面向 Markdown 工作流。",
      "如果你在做研究、知识库、服务地图或人物关系，md2hd 很合适；笔记本身没有结构，它只会把混乱画出来。你最想先把项目、人物，还是知识库画成图？"
    ],
    sources:`# 来源与核验\n\n- 官方仓库：[evan-steinhilb/md2hd](https://github.com/evan-steinhilb/md2hd)，2026-08-13 核验 70 Star、11 Fork，MIT；创建于 2026-08-11，最近推送 2026-08-12。\n- 官方版本与维护：package.json 为 0.3.0，Node >=18；最近提交包含 0.3.0 发布、截图更新与打包修正。\n- 官方 README：文件或目录中的 frontmatter 生成节点，wikilink 与 rel 生成边；支持 Overview、按类型浏览、节点聚焦、关系方向与层级。\n- 官方本地路径：npx md2hd notes/ 或 npx md2hd map.md；服务绑定 127.0.0.1，无账号、无遥测。\n- 官方编辑能力：节点详情中的 Code 面板可编辑源文件，保存后刷新地图。\n- 官方限制：关系图依赖原始笔记中的类型、标识和关系；项目不会替用户发明缺失结构。\n- 官方素材：仓库 media/shell.jpg、focus.jpg、type.jpg，冻结在工程 assets。\n\n大陆路径：安装后可完全本地运行；首次通过 npx/npm 或 GitHub 获取包时需能访问相应源。未安装、未实测。`,
    dbs:`# DBS 门禁\n\n- dbs-ai-check：短视频文稿；没有把“知识图谱”拔高成哲学命题，也没有声称自动理解。保留“只会把混乱画出来”作为真实边界。通过。\n- dbs-resonate：核心机制是“把笔记中已有的结构关系变成可浏览、可回写的地图”；命令、节点浏览和限制都围绕这一机制。五个维度有效。通过。\n- dbs-hook：开头用“笔记越多反而越看不清”的真实矛盾建立话题，明确 frontmatter 与 wikilink 的视觉结果，同时把具体使用链留到正文。通过。\n- dbs-xhs-title：采用公式 #14“[不想要的结果] 的最根本原因”，定稿“笔记越多越乱的根本原因”，13 字；损失感与结构悬念都成立。通过。`,
    copy:`# 发布文案\n\n## 抖音\n\n- 标题：Markdown 笔记怎么直接变成关系图？｜md2hd\n- 简介：md2hd 把 frontmatter 变成节点、wikilink 和 rel 变成连线，在本地浏览器里生成可搜索、可聚焦、可回写原文的地图。它无需账号、无遥测，Node 18 以上即可运行。注意：图的质量取决于笔记本身的类型、标识和关系结构。\n- 话题：#开源工具 #Markdown #知识管理 #效率工具 #GitHub\n- 置顶评论：你最想先把项目、人物，还是知识库画成图？\n\n## 小红书\n\n- 标题：笔记越多越乱的根本原因\n- 正文：md2hd 不替你总结，而是把 Markdown 里已有的 frontmatter 和 wikilink 直接画成关系地图。它在本地浏览器运行，可以搜索、聚焦节点，还能从图上回到原文编辑。适合研究、知识库和项目关系；没有结构的笔记不会自动变清楚。\n- 话题：#开源工具 #Markdown #知识管理 #笔记方法 #GitHub项目\n- 互动评论：你的笔记最缺的是人物关系、项目依赖，还是主题结构？\n\n说明：未安装、未实测；内容来自 2026-08-13 核验的官方仓库、README、package.json、提交记录和项目截图。`,
    assets:[
      [path.join(sourceRoot,"md2hd/shell.jpg"),"official-shell.jpg"],
      [path.join(sourceRoot,"md2hd/focus.jpg"),"official-focus.jpg"],
      [path.join(sourceRoot,"md2hd/type.jpg"),"official-type.jpg"]
    ]
  }
];

const candidateReport = `# 了不起的小超人｜开源装备雷达候选池（2026-08-13 晚轮）\n\n核验时间：2026-08-13 17:xx（Asia/Shanghai）  \n去重范围：2026-07-15—2026-08-13，核对现有 001—022 期；本轮入选三项均未重复。  \n热度入口：Agent Reach 的 GitHub Search 与 Exa，补充官方仓库、README、package.json、提交记录、官网与演示素材；数据以本轮 GitHub API 为准。  \n评分顺序：视觉结果 / 用户价值 / 新鲜与增长 / 新手成本 / 维护与许可。\n\n| 候选 | 分类 | 分项 | 总分 | 决策 |\n|---|---|---:|---:|---|\n| milind-soni/OpenMausBot | Agent 自动化 | 25/24/20/10/14 | 93 | 制作 024 |\n| pireel/pireel | AI 视频 | 25/25/17/11/13 | 91 | 制作 023 |\n| evan-steinhilb/md2hd | 开源效率 | 25/22/18/14/11 | 90 | 制作 025 |\n| shadcn-labs/pdfcn | 开源效率 | 24/22/20/12/12 | 90 | 三条上限，受众更窄 |\n| wzchav/tokentab | 开源效率 | 22/24/20/13/9 | 88 | 价格表需人工维护 |\n| CureJe/sedentary-reminder | GitHub 热榜 | 25/20/18/14/11 | 88 | 三条上限 |\n| dengzi008/DramaLens | AI 视频 | 22/23/19/8/14 | 86 | Windows 与版权使用边界较重 |\n| dmmulroy/anti-slop | Agent 自动化 | 13/21/20/13/14 | 81 | 视觉结果弱 |\n| lyc403223157-source/knowledge-inbox | Agent 自动化 | 19/23/18/7/13 | 80 | 安装链较长 |\n| Yixuan-Wu39/bandminton | GitHub 热榜 | 23/20/19/4/14 | 80 | 指定手环与侧载门槛高 |\n| OpenLabs-so/openanalytics | 开源效率 | 22/22/18/4/13 | 79 | 自托管门槛高 |\n| guillaumemeyer/watermarks-remover | 开源效率 | 16/14/20/11/15 | 76 | 涉及来源标记移除，不选 |\n| shadcn-ui/chatbot-template | Agent 自动化 | 18/19/18/12/9 | 76 | 模板同质化明显 |\n| RadishXN/run-abroad | 开源效率 | 18/22/19/14/2 | 75 | 法律时效与维护风险高 |\n| sohaibdevv/youtube-music | GitHub 热榜 | 20/18/18/12/6 | 74 | 逆向接口与平台条款风险 |\n| lilvli/portable-vna | GitHub 热榜 | 23/18/18/4/10 | 73 | 硬件门槛高 |\n| ndu99911/repo-context-mcp | Agent 自动化 | 14/19/19/12/8 | 72 | 视觉结果弱、体量小 |\n| aletheics/zeno | Agent 自动化 | 20/18/18/10/5 | 71 | 项目早期、受众较窄 |\n\n## 入选核验摘要\n\n- OpenMausBot：MIT，0.1.13，最近提交活跃；macOS + Node 24 + 已登录 Agent CLI，审批与本地数据边界清楚。\n- Pireel Studio：AGPL-3.0-only，浏览器本地时间线、字幕、主题与 WebCodecs 导出；生成与转写 Provider 边界清楚。\n- md2hd：MIT，0.3.0，Node 18+；本地 127.0.0.1、无账号无遥测，输入结构与图质量的边界清楚。\n`;

writeNew(path.join(contentRoot,"xiaochao-radar-candidates-run-3.md"),candidateReport);
for (const episode of episodes) {
  const projectDir = path.join(contentRoot,`xiaochao-${episode.issue}-${episode.slug}`);
  ensureNew(projectDir);
  for (const sub of ["assets","narration","voice","snapshots"]) fs.mkdirSync(path.join(projectDir,sub),{recursive:true});
  episode.narration.forEach((line,index)=>writeNew(path.join(projectDir,"narration",`${String(index+1).padStart(2,"0")}-${["hook","what","workflow","limit","verdict"][index]}.txt`),line));
  writeNew(path.join(projectDir,"sources.md"),episode.sources);
  writeNew(path.join(projectDir,"dbs-review.md"),episode.dbs);
  writeNew(path.join(projectDir,"package.md"),episode.copy);
  writeNew(path.join(outputRoot,"copy",`${Number(episode.issue)}-${episode.slug}.md`),episode.copy);
  writeNew(path.join(projectDir,"BRIEF.md"),`# BRIEF\n\n- workflow: general-video\n- flow: automation\n- storyboard: no\n- message: explain one verified open-source tool, its workflow, threshold, and boundary\n- audience: Chinese creators and practical tool users\n- destination: 1080×1920 vertical short video\n- duration: 50—65 seconds, five narrated scenes\n- visual: current warm editorial manual and yellow portrait IP\n- audio: exact MiniMax voice and fixed look-beyond.mp3 mix\n- constraints: no cover, platform, draft, publish, or unverifiable hands-on claim`);
  writeNew(path.join(projectDir,"STORYBOARD.md"),`# STORYBOARD\n\n1. 官方结果画面 + “${episode.titleLines.join(" / ")}”问题。\n2. 三个核心能力与官方素材。\n3. 一条真实工作链路和步骤图。\n4. 安装、平台或 Provider 限制。\n5. ${episode.score} 与适用人群结论。`);
  writeNew(path.join(projectDir,"video-spec.json"),JSON.stringify({slug:`xiaochao-${episode.issue}-${episode.slug}`,issue:episode.issue,category:episode.category,kicker:episode.kicker,titleLines:episode.titleLines,section2TitleLines:episode.section2TitleLines,section3TitleLines:episode.section3TitleLines,project:episode.project,repo:episode.repo,score:episode.score,verdict:episode.verdict,stats:episode.stats,flow:episode.flow,limits:episode.limits,media:episode.media,durationsMs:[]},null,2));
  writeNew(path.join(projectDir,"assets","workflow.svg"),flowSvg(episode.flowTitle,episode.flowSteps));
  writeNew(path.join(projectDir,"assets","limits.svg"),limitsSvg(episode.limitsTitle,episode.limitItems));
  for (const [source,name] of episode.assets) copyNew(source,path.join(projectDir,"assets",name));
  copyNew(path.join(root,"assets/brand/xiaochao/avatar-yellow-800.png"),path.join(projectDir,"assets/ip.png"));
  copyNew(path.join(root,"content/2026-08-12/xiaochao-018-diagram-design/assets/Hiragino-Sans-GB.ttc"),path.join(projectDir,"assets/Hiragino-Sans-GB.ttc"));
  copyNew(path.join(root,"content/2026-08-12/xiaochao-018-diagram-design/assets/CobaltMono.ttf"),path.join(projectDir,"assets/CobaltMono.ttf"));
  copyNew(path.join(root,"content/2026-08-12/xiaochao-018-diagram-design/assets/gsap-3.14.2.min.js"),path.join(projectDir,"assets/gsap-3.14.2.min.js"));
}

console.log(JSON.stringify({date,episodes:episodes.map(({issue,slug,score})=>({issue,slug,score}))},null,2));
