#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const root = "<REPO>";
const date = "2026-08-13";
const contentRoot = path.join(root, "content", date);
const outputRoot = path.join(root, "output", "xiaochao", date);
const assetSources = {
  shuohao: "/private/tmp/xiaochao-shuohao-20260813",
  flyingmouse: "/private/tmp/xiaochao-flyingmouse-20260813",
  morphicons: "/private/tmp/xiaochao-morphicons-20260813"
};

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
    issue:"020", slug:"shuohao-skills", project:"shuohao-skills", repo:"github.com/eternityspring/shuohao-skills", category:"AI视频局", score:"93 / 100",
    titleLines:["一本小说","怎么拆成短剧资料"], kicker:"角色、大纲和美术设定，不再混在一个提示词里",
    section2TitleLines:["三套独立 Skill","每套都有质量门"], section3TitleLines:["先定角色和爽点","再生成场景与道具"],
    stats:["角色设定集","短剧大纲五件套","场景 + 道具设定"],
    flow:["小说拆角色与音色","大纲提炼爽点和分集","资产清单预填场景道具","脚本门禁检查结构"],
    limits:["不是直接生成成片","出图仍消耗当前模型额度","只在 macOS + Node 24 实测"],
    verdict:"做 AI 短剧前期资料很实用；只想一句话出成片的人不适合",
    media:["assets/official-characters.webp","assets/official-outline.webp","assets/workflow.svg","assets/limits.svg","assets/official-art.webp"],
    flowTitle:"小说到可开拍资料", flowSteps:["角色设定","大纲五件套","场景与道具","确定性自检"], limitsTitle:"它负责前期，不负责成片", limitItems:["不直接生成视频","出图要模型额度","实测平台范围有限"],
    narration:[
      "一本小说丢给 AI，最容易得到的不是短剧，是一堆互相打架的角色、场景和剧情。shuohao-skills 把前期制作拆成三套独立工作流，先把资料做齐。",
      "第一套拆人物画像、形象和音色；第二套生成改编说明、人物表、爽点表、分集梗概和资产清单；第三套再补场景、道具、光照和状态变体。",
      "实际链路是先跑角色，再用大纲确定每集爽点和资产，最后让美术设定读取 outline.json 预填清单。每套都有自测脚本，大纲十三道门，美术十一道门。",
      "边界也很清楚：它做的是能开拍的前期资料，不是直接生成成片。Node 十八以上即可，脚本零 npm 依赖；出图仍要当前会话的模型额度，而且只在 macOS 和 Node 二十四实测。",
      "如果你在做 AI 短剧，最头疼的是人物和场景前后不一致，这套拆法值得看；只想一句话出成片就不适合。你最想先解决角色、分集，还是美术设定？"
    ],
    sources:`# 来源与核验\n\n- 官方仓库：[eternityspring/shuohao-skills](https://github.com/eternityspring/shuohao-skills)，2026-08-13 核验 1,165 Star、134 Fork，Apache-2.0；创建于 2026-08-06，最近推送 2026-08-11。\n- 官方 README：当前包含 novel-characters、novel-outline、novel-art 三套独立 Skill，分别产出角色设定、大纲五件套和场景/道具设定。\n- 官方门槛：Node ≥18，确定性脚本只用标准库、无 npm 依赖；使用当前 Agent 会话额度，不要求额外 API Key；出图需要 Codex imagegen，否则可跳过。\n- 官方质量门：每个 Skill 均带 selftest；README 明确大纲 13 道质量门、美术 11 道质量门。\n- 官方限制：作者仅在 macOS + Node 24 实测，Linux 和较低 Node 版本仅为理论可用。\n- 官方素材：仓库三套 Skill 的 report.webp，冻结在工程 assets。\n\n大陆路径：仓库与脚本可本地运行；不依赖单独海外 API Key，但仍需能够访问 GitHub 并具备可用的 Codex/Claude 会话。未安装、未实测。`,
    dbs:`# DBS 门禁\n\n- dbs-ai-check：短视频体裁；无虚构亲测、无宣传性“最强/颠覆”，只保留一次具体反差；角色、大纲、美术三项为真实项目结构，不是匀速堆词。通过。\n- dbs-resonate：唯一核心是“把小说改短剧的前期资料拆成三套可检查工作流”；功能、链路和限制均服务一致性问题。沉默解除、满足动机、立场框架、传播入口与信念结构有效。通过。\n- dbs-hook：开头独立建立“小说交给 AI 会得到互相打架资料”的痛点，保留三套工作流如何解决的悬念，正文完整兑现。通过。\n- dbs-xhs-title：采用公式 #14“[不想要的结果] 的最根本原因”，定稿“AI短剧总穿帮的根本原因”，13 字；损失感和悬念同时成立。通过。`,
    copy:`# 发布文案\n\n## 抖音\n\n- 标题：一本小说怎么拆成短剧资料？｜shuohao-skills\n- 简介：shuohao-skills 把 AI 短剧前期拆成角色设定、改编大纲和美术设定三套 Skill。它能生成角色画像与音色、大纲五件套、场景和道具清单，并用确定性脚本做质量门检查。它不直接生成成片，出图仍需模型额度，官方只在 macOS + Node 24 实测。\n- 话题：#开源工具 #AI短剧 #AIAgent #视频制作 #GitHub\n- 置顶评论：你做短剧时最容易穿帮的是角色、分集，还是场景道具？\n\n## 小红书\n\n- 标题：AI短剧总穿帮的根本原因\n- 正文：小说直接丢进一个提示词，角色、剧情和美术很容易互相打架。shuohao-skills 把前期拆成角色设定、大纲五件套、场景与道具设定三套独立 Skill，每套还有确定性自检。适合要认真做前期资料的人；它不负责一键出成片。\n- 话题：#开源工具 #AI短剧 #AIAgent #短剧制作 #GitHub项目\n- 互动评论：角色、分集、美术设定，你最想先补哪一块？\n\n说明：未安装、未实测；内容来自 2026-08-13 核验的官方仓库、README、Skill 说明和示例素材。`,
    assets:[
      [path.join(assetSources.shuohao,"skills/novel-characters/assets/report.webp"),"official-characters.webp"],
      [path.join(assetSources.shuohao,"skills/novel-outline/assets/report.webp"),"official-outline.webp"],
      [path.join(assetSources.shuohao,"skills/novel-art/assets/report.webp"),"official-art.webp"]
    ]
  },
  {
    issue:"021", slug:"flyingmouse-format", project:"FlyingMouse Format", repo:"github.com/LaoFeng-mouse/flyingmouse-format", category:"开源效率局", score:"95 / 100",
    titleLines:["文件格式太乱","一只鼠全在本地转"], kicker:"Office、PDF、图片、音视频和 OCR 放进同一桌面工具",
    section2TitleLines:["转换引擎打包","断网也能继续处理"], section3TitleLines:["拖入文件识别","批量转换保留失败原因"],
    stats:["图片 / Office / PDF","音视频 / OCR / EPUB","批量进度与失败原因"],
    flow:["拖入文件自动识别","按源格式记住目标选项","本地引擎完成转换","单独或批量保存结果"],
    limits:["安装包包含多个引擎，体积不轻","复杂 PDF 不是版式还原","主要面向 Windows 与 macOS"],
    verdict:"经常处理杂格式文件的人很省事；只偶尔转一张图没必要装",
    media:["assets/official-home.png","assets/official-batch.png","assets/workflow.svg","assets/limits.svg","assets/official-success.png"],
    flowTitle:"离线文件转换链路", flowSteps:["识别源格式","选择目标格式","本地引擎转换","批量保存结果"], limitsTitle:"离线不等于没有代价", limitItems:["安装包会比较大","复杂版式可能丢失","长文档处理更慢"],
    narration:[
      "Word、PDF、图片、音频各装一个转换器，最后连自己都记不住文件去了哪。FlyingMouse Format 把常见转换塞进一只桌面鼠里，而且核心处理可以离线完成。",
      "它覆盖图片、Word 和 WPS、表格、PPT、PDF、音视频、ZIP、OCR 和电子书。FFmpeg、LibreOffice、Poppler、Tesseract 都打进应用，批量任务会逐个显示进度和失败原因。",
      "工作链很直白：拖入文件自动识别，选择目标格式；它会按源格式记住上次选项，再调用本地引擎转换。PDF 表格还能结合文字坐标、扫描 OCR 和低置信度批注。",
      "代价也要看见：打包多个引擎，安装体积不会轻。PDF 转 Word 主打内容提取，不保留图片、字体和复杂版式；长文档按一比一处理会更慢。官方主要提供 Windows 和 macOS 路径。",
      "如果你经常收同事发来的杂格式文件，又不想上传云端，这只鼠很实用；一年只转两张图就没必要装。你最常卡住的是 PDF、Office，还是音视频？"
    ],
    sources:`# 来源与核验\n\n- 官方仓库：[LaoFeng-mouse/flyingmouse-format](https://github.com/LaoFeng-mouse/flyingmouse-format)，2026-08-13 核验 943 Star、73 Fork，MIT；创建于 2026-08-06，最近推送 2026-08-12（克隆到的最新提交时间为 2026-08-13 03:14 CST）。\n- 官方 Release：v0.4.1 发布于 2026-08-12；同日连续发布 v0.3.6—v0.4.1，维护活跃。\n- 官方 README：本地集成 FFmpeg、LibreOffice、Poppler、Tesseract；覆盖图片、Office/WPS、PDF、音视频、ZIP、OCR、EPUB 与批量转换。\n- 官方 PDF 边界：PDF→Word 属内容提取，不承诺保留图片、字体、颜色、页眉页脚与复杂版式；长文档加载较慢。\n- 官方平台：README 标记 Windows 与 macOS，仓库同时保留 Win7 构建配置；下载依赖 GitHub Releases。\n- 官方素材：仓库 public/assets/screenshots/home.png 与鼠鼠状态图，冻结在工程 assets。\n\n大陆路径：转换本身可离线运行且无需账号；首次下载和更新需要访问 GitHub Releases。未安装、未实测。`,
    dbs:`# DBS 门禁\n\n- dbs-ai-check：短视频体裁；没有声称亲测，没有用“万能”作无边界承诺，明确 PDF 与安装体积限制。首句为真实场景，不是焦虑三件套。通过。\n- dbs-resonate：唯一核心是“把杂格式文件留在本地统一转换”；引擎、工作链和 PDF 限制都服务隐私与省事。五个共鸣维度有效。通过。\n- dbs-hook：开头用“每种格式装一个转换器”的普遍痛点建立话题，并留下“一只桌面鼠如何离线处理”的悬念，正文兑现。通过。\n- dbs-xhs-title：采用公式 #48“[行动] 是在浪费时间么？”，定稿“为每种格式装软件，值吗？”，14 字，保留决策悬念。通过。`,
    copy:`# 发布文案\n\n## 抖音\n\n- 标题：文件不上传云端，怎么统一转换？｜FlyingMouse Format\n- 简介：FlyingMouse Format 把图片、Office/WPS、PDF、音视频、ZIP、OCR 和电子书转换放进一个桌面工具，内置 FFmpeg、LibreOffice、Poppler 与 Tesseract，可离线处理并显示批量进度和失败原因。注意：安装包不会轻，复杂 PDF 转 Word 属内容提取，不是版式还原。\n- 话题：#开源工具 #文件转换 #PDF工具 #效率工具 #GitHub\n- 置顶评论：你最常需要转换的是 PDF、Office，还是音视频？\n\n## 小红书\n\n- 标题：为每种格式装软件，值吗？\n- 正文：FlyingMouse Format 把图片、Word/WPS、表格、PPT、PDF、音视频、OCR 和电子书转换放进同一只桌面鼠里。核心引擎本地运行，批量任务会显示逐文件进度和失败原因。适合经常处理杂格式文件的人；复杂 PDF 不保证还原版式。\n- 话题：#开源工具 #文件转换 #PDF工具 #效率软件 #GitHub项目\n- 互动评论：哪一种文件格式最折磨你？\n\n说明：未安装、未实测；内容来自 2026-08-13 核验的官方仓库、README、Release 与项目素材。`,
    assets:[
      [path.join(assetSources.flyingmouse,"public/assets/screenshots/home.png"),"official-home.png"],
      [path.join(assetSources.flyingmouse,"public/assets/mouse-format/mouse-batch.png"),"official-batch.png"],
      [path.join(assetSources.flyingmouse,"public/assets/mouse-format/mouse-success.png"),"official-success.png"]
    ]
  },
  {
    issue:"022", slug:"morphicons", project:"morphicons", repo:"github.com/guillermolg00/morphicons", category:"GitHub热榜", score:"90 / 100",
    titleLines:["菜单变关闭","不用手调每对图标"], kicker:"几何对齐和弹簧物理自动算出中间形态",
    section2TitleLines:["任意线性图标","同一套核心跨框架"], section3TitleLines:["先统一路径采样","再对齐旋转与弹簧"],
    stats:["约 7 KB gzip","零运行时依赖","React / Vue / Svelte / RN"],
    flow:["读取图标路径数据","重采样到可比较点集","计算几何对齐与旋转","弹簧插值并支持中途打断"],
    limits:["只适合线性描边图标","ESM only，图标要传 data","减弱动画需显式开启"],
    verdict:"做交互按钮和状态切换很合适；填充图标与静态页面收益有限",
    media:["assets/official-logo.svg","assets/morph-demo.svg","assets/workflow.svg","assets/limits.svg","assets/official-logo.svg"],
    flowTitle:"图标自动变形的四步", flowSteps:["解析路径","统一采样","几何对齐","弹簧插值"], limitsTitle:"不是所有 SVG 都能变", limitItems:["只支持描边图标","ESM 与数据输入","减弱动画要配置"],
    narration:[
      "菜单图标变成关闭按钮，看着只有一下，开发时却常要为每一对图标手调路径。morphicons 想做的，是让任意线性图标都能自动找到一条顺滑的变形路线。",
      "它支持 Lucide、Tabler、Heroicons、Iconoir 和自定义路径，核心大约七 KB gzip、零运行时依赖。React、Vue、Svelte、React Native 和原生 DOM 共用同一套算法。",
      "它先把不同路径重采样成可比较的点，再计算两种形状之间最合适的缩放、旋转和对齐，最后用弹簧插值生成中间帧。动画被打断时，会从当前形状和速度继续，不会突然跳回去。",
      "限制很具体：它只适合描边图标，复杂填充 SVG 会被拒绝；包是 ESM only，Lucide 要传图标数据而不是框架组件。默认仍会播放动画，严格遵循系统减弱动画需要显式设置。",
      "如果你在做菜单、播放、收藏这类状态按钮，morphicons 很值得试；页面里都是静态或填充图标，收益就不大。你最想让哪两个图标互相变形？"
    ],
    sources:`# 来源与核验\n\n- 官方仓库：[guillermolg00/morphicons](https://github.com/guillermolg00/morphicons)，2026-08-13 核验 994 Star、18 Fork，MIT；创建于 2026-08-01，最近推送 2026-08-12。\n- 官方 Release：v1.6.0 发布于 2026-08-08；此前一周连续发布 v1.4.0—v1.6.0。\n- 官方 README：面向线性描边图标，使用重采样、2D Procrustes 与 polar interpolation 自动处理几何对齐和旋转；约 7 KB gzip、零运行时依赖。\n- 官方框架支持：React、Vue、Svelte、React Native、原生 DOM 和纯核心；ESM only，Lucide 输入需要图标 data 而非框架组件。\n- 官方限制：非描边或带不支持结构的 SVG 会在解析时拒绝；reducedMotion 默认 never，严格跟随系统设置需显式传 user。\n- 官方素材：仓库 assets/logo-light.svg，解释图由本工程依据官方算法说明绘制。\n\n大陆路径：可通过 npm/pnpm/bun 安装，核心无运行时依赖；首次安装需可访问包注册表或 GitHub。未安装、未实测。`,
    dbs:`# DBS 门禁\n\n- dbs-ai-check：短视频体裁；没有虚构实测和夸大“任意 SVG”，正文持续限定为线性描边图标。技术名词只保留支撑自动旋转与插值的必要部分。通过。\n- dbs-resonate：唯一核心是“图标对之间不再手调变形路径”；跨框架、算法链和输入限制均服务这一机制。五个共鸣维度有效。通过。\n- dbs-hook：开头从菜单到关闭的可见交互切入，点出“每一对都要手调”的开发痛点，并保留自动路线如何计算的悬念。通过。\n- dbs-xhs-title：采用公式 #55“你到底要不要 [话题]”，定稿“图标切换要不要做动画？”，13 字，适合开发者决策型内容。通过。`,
    copy:`# 发布文案\n\n## 抖音\n\n- 标题：菜单图标怎么自动变成关闭按钮？｜morphicons\n- 简介：morphicons 用路径重采样、几何对齐和弹簧插值，让线性描边图标自动找到变形路线。核心约 7 KB gzip、零运行时依赖，支持 React、Vue、Svelte、React Native 与原生 DOM。注意：复杂填充 SVG 不适用，包为 ESM only，严格跟随系统减弱动画需要显式配置。\n- 话题：#开源工具 #前端开发 #网页动效 #SVG #GitHub\n- 置顶评论：菜单、播放、收藏、下载，你最想先做哪一对图标动画？\n\n## 小红书\n\n- 标题：图标切换要不要做动画？\n- 正文：morphicons 让菜单→关闭、播放→暂停这类线性图标自动计算变形路径，不必为每一对手调。它把路径统一采样，再处理旋转、对齐和弹簧插值，支持多个前端框架。适合状态按钮和微交互；复杂填充 SVG 不适用。\n- 话题：#开源工具 #前端开发 #网页动效 #SVG动画 #GitHub项目\n- 互动评论：你最想让哪两个图标互相变形？\n\n说明：未安装、未实测；内容来自 2026-08-13 核验的官方仓库、README、Release 和源码结构。`,
    assets:[[path.join(assetSources.morphicons,"assets/logo-light.svg"),"official-logo.svg"]]
  }
];

const candidateReport = `# 了不起的小超人｜开源装备雷达候选池（2026-08-13 续跑）\n\n核验时间：2026-08-13（Asia/Shanghai）  \n去重范围：2026-07-14—2026-08-13，核对现有 001—019 期；本轮入选三项均未重复。  \n热度入口：Agent Reach 的 GitHub Search、官方仓库元数据、README、Release、Issue 与项目文件；仓库数据以 2026-08-13 GitHub API 为准。  \n评分顺序：视觉结果 / 用户价值 / 新鲜与增长 / 新手成本 / 维护与许可。\n\n| 候选 | 分类 | 分项 | 总分 | 决策 |\n|---|---|---:|---:|---|\n| LaoFeng-mouse/flyingmouse-format | 开源效率 | 24/24/19/13/15 | 95 | 制作 021 |\n| eternityspring/shuohao-skills | AI 视频 | 24/23/19/12/15 | 93 | 制作 020 |\n| guillermolg00/morphicons | GitHub 热榜 | 24/20/18/13/15 | 90 | 制作 022 |\n| Zeejay0/gathered-scenes-zine-skill | AI 视觉 | 25/21/19/12/7 | 84 | 仅个人非商业许可，不选 |\n| DannyMac180/sol-advisor | Agent 自动化 | 15/21/18/12/15 | 81 | 与近期 Agent 编排内容邻近 |\n| magicrew/doc7 | 开源效率 | 19/22/17/10/15 | 83 | 与 003 AnyDoc 主题邻近 |\n| Flaminis/Dalaran | GitHub 热榜 | 24/18/18/5/15 | 80 | 机器人门槛高 |\n| FareedKhan-dev/kimi-k3-in-c | GitHub 热榜 | 16/18/19/4/15 | 72 | 内存与模型题材邻近 010 |\n| google-gemma/gemma-translator | 开源效率 | 15/18/17/9/15 | 74 | 视觉结果弱 |\n| pathwayout/arc-task-gen | Agent 自动化 | 14/16/18/5/15 | 68 | 低于门槛 |\n| Accio-org/RealReplicaBench | Agent 自动化 | 18/17/18/4/15 | 72 | 普通用户路径弱 |\n| openTrinity/mycontext | 开源效率 | 20/22/16/10/7 | 75 | 许可证非标准，未选 |\n| thebuggeddev/anatomy | GitHub 热榜 | 25/18/18/10/0 | 71 | 未识别许可证 |\n| Binaryify/open-kimi-ppt-skill | 开源效率 | 23/22/18/12/0 | 75 | 未识别许可证 |\n| imsai-sh/zhuzhiliao | GitHub 热榜 | 23/15/17/15/3 | 73 | 许可证不明确 |\n| photo-abstract-editorial | AI 视觉 | 24/18/18/11/3 | 74 | 许可证不明确 |\n| watermarks-remover | 开源效率 | 16/14/20/11/15 | 76 | 涉及来源标记移除，不选 |\n| awesome-growth-hacking-skills | Agent 自动化 | 12/15/16/10/0 | 53 | 未识别许可证、视觉弱 |\n\n## 入选核验摘要\n\n- shuohao-skills：Apache-2.0，三套独立 Skill、确定性自测和清晰的模型/平台边界；中文用户有直接使用路径。\n- FlyingMouse Format：MIT，v0.4.1 于 2026-08-12 发布，核心可离线转换，功能、平台和 PDF 还原边界明确。\n- morphicons：MIT，v1.6.0，约 7 KB gzip、零运行时依赖，线性图标输入和 reduced-motion 边界明确。\n`;

writeNew(path.join(contentRoot,"xiaochao-radar-candidates-run-2.md"),candidateReport);
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
  writeNew(path.join(projectDir,"STORYBOARD.md"),`# STORYBOARD\n\n1. 官方结果或品牌画面 + “${episode.titleLines.join(" / ")}”问题。\n2. 三个核心能力与官方素材。\n3. 一条真实工作链路和步骤图。\n4. 安装、平台或输入限制。\n5. ${episode.score} 与适用人群结论。`);
  writeNew(path.join(projectDir,"video-spec.json"),JSON.stringify({slug:`xiaochao-${episode.issue}-${episode.slug}`,issue:episode.issue,category:episode.category,kicker:episode.kicker,titleLines:episode.titleLines,section2TitleLines:episode.section2TitleLines,section3TitleLines:episode.section3TitleLines,project:episode.project,repo:episode.repo,score:episode.score,verdict:episode.verdict,stats:episode.stats,flow:episode.flow,limits:episode.limits,media:episode.media,durationsMs:[]},null,2));
  writeNew(path.join(projectDir,"assets","workflow.svg"),flowSvg(episode.flowTitle,episode.flowSteps));
  writeNew(path.join(projectDir,"assets","limits.svg"),limitsSvg(episode.limitsTitle,episode.limitItems));
  for (const [source,name] of episode.assets) copyNew(source,path.join(projectDir,"assets",name));
  copyNew(path.join(root,"assets/brand/xiaochao/avatar-yellow-800.png"),path.join(projectDir,"assets/ip.png"));
  copyNew(path.join(root,"content/2026-08-12/xiaochao-018-diagram-design/assets/Hiragino-Sans-GB.ttc"),path.join(projectDir,"assets/Hiragino-Sans-GB.ttc"));
  copyNew(path.join(root,"content/2026-08-12/xiaochao-018-diagram-design/assets/CobaltMono.ttf"),path.join(projectDir,"assets/CobaltMono.ttf"));
  copyNew(path.join(root,"content/2026-08-12/xiaochao-018-diagram-design/assets/gsap-3.14.2.min.js"),path.join(projectDir,"assets/gsap-3.14.2.min.js"));
}

writeNew(path.join(contentRoot,"xiaochao-022-morphicons/assets/morph-demo.svg"),`<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200"><rect width="900" height="1200" fill="#F6F0E4"/><text x="70" y="105" font-family="sans-serif" font-size="48" font-weight="900" fill="#1B1916">一次状态变化，三段几何计算</text><g fill="none" stroke="#1B1916" stroke-width="25" stroke-linecap="round"><path d="M150 310h220M150 390h220M150 470h220"/><path d="M665 310L815 460M815 310L665 460"/></g><path d="M420 390h160" stroke="#FF5A36" stroke-width="18"/><path d="m545 350 45 40-45 40" fill="none" stroke="#FF5A36" stroke-width="18"/><rect x="70" y="620" width="760" height="390" rx="34" fill="#B9F227" stroke="#1B1916" stroke-width="9"/><text x="115" y="720" font-family="sans-serif" font-size="42" font-weight="900" fill="#1B1916">路径重采样</text><text x="115" y="810" font-family="sans-serif" font-size="42" font-weight="900" fill="#1B1916">几何对齐与旋转</text><text x="115" y="900" font-family="sans-serif" font-size="42" font-weight="900" fill="#1B1916">弹簧插值，可中途打断</text></svg>`);

console.log(JSON.stringify({date,episodes:episodes.map(({issue,slug,score})=>({issue,slug,score}))},null,2));
