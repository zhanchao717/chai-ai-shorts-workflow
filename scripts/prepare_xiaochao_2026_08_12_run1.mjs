#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const root = "/Users/chao/Documents/dailyvideos";
const date = "2026-08-12";
const contentRoot = path.join(root, "content", date);
const outputRoot = path.join(root, "output", "xiaochao", date);

const ensureNew = (target) => {
  if (fs.existsSync(target)) throw new Error(`Refusing to overwrite existing path: ${target}`);
};

const writeNew = (target, body) => {
  if (fs.existsSync(target)) throw new Error(`Refusing to overwrite existing file: ${target}`);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, body.endsWith("\n") ? body : `${body}\n`);
};

const esc = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

const flowSvg = (title, steps) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200">
  <rect width="900" height="1200" fill="#F6F0E4"/>
  <text x="55" y="92" font-family="sans-serif" font-size="44" font-weight="900" fill="#1B1916">${esc(title)}</text>
  ${steps.map((step, index) => {
    const y = 160 + index * 235;
    const fill = ["#B9F227", "#FFD45A", "#FF5A36", "#F6F0E4"][index % 4];
    return `<rect x="55" y="${y}" width="790" height="165" rx="24" fill="${fill}" stroke="#1B1916" stroke-width="8"/>
    <circle cx="125" cy="${y + 82}" r="38" fill="#1B1916"/>
    <text x="125" y="${y + 96}" text-anchor="middle" font-family="monospace" font-size="38" font-weight="900" fill="#F6F0E4">${index + 1}</text>
    <text x="195" y="${y + 96}" font-family="sans-serif" font-size="36" font-weight="900" fill="#1B1916">${esc(step)}</text>
    ${index < steps.length - 1 ? `<path d="M450 ${y + 175}v50" stroke="#1B1916" stroke-width="9"/><path d="m430 ${y + 210} 20 22 20-22" fill="none" stroke="#1B1916" stroke-width="9"/>` : ""}`;
  }).join("\n")}
</svg>`;

const limitsSvg = (title, items) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200">
  <rect width="900" height="1200" fill="#F6F0E4"/>
  <rect x="52" y="54" width="796" height="1092" rx="28" fill="#FFD45A" stroke="#1B1916" stroke-width="9"/>
  <text x="90" y="145" font-family="sans-serif" font-size="48" font-weight="900" fill="#1B1916">${esc(title)}</text>
  ${items.map((item, index) => {
    const y = 245 + index * 270;
    return `<rect x="92" y="${y}" width="716" height="198" rx="22" fill="#F6F0E4" stroke="#1B1916" stroke-width="7"/>
    <circle cx="155" cy="${y + 70}" r="36" fill="#FF5A36" stroke="#1B1916" stroke-width="6"/>
    <text x="155" y="${y + 84}" text-anchor="middle" font-family="monospace" font-size="38" font-weight="900" fill="#1B1916">!</text>
    <foreignObject x="215" y="${y + 35}" width="545" height="140"><div xmlns="http://www.w3.org/1999/xhtml" style="font:900 35px/1.25 sans-serif;color:#1B1916">${esc(item)}</div></foreignObject>`;
  }).join("\n")}
</svg>`;

const episodes = [
  {
    issue: "017",
    slug: "qwen-mm-plugins",
    project: "Qwen-MM-Plugins",
    repo: "github.com/QwenLM/Qwen-MM-Plugins",
    category: "Agent自动化局",
    score: "90 / 100",
    titleLines: ["Agent 终于", "能看懂视频了"],
    kicker: "多模态能力拆成八个模块，按需安装",
    section2TitleLines: ["本地读取打底", "云端能力按需叠加"],
    section3TitleLines: ["先装 core", "再补识别、搜索和创作"],
    stats: ["图片 / 视频 / PDF / 3D", "8 个独立能力模块", "Codex / Claude / Qwen Code"],
    flow: ["core 本地读取与抽帧", "api 接视觉与音视频理解", "search 负责网页和反向搜图", "创作模块连接视频与 3D"],
    limits: ["云端理解与生成需要 DashScope", "搜索模块另需 Serper API Key", "Windows 当前只验证 WSL2"],
    verdict: "多模态重度用户值得装 core；纯文本任务不用加链路",
    media: ["assets/official-core.png", "assets/architecture.svg", "assets/workflow.svg", "assets/limits.svg", "assets/official-codex.png"],
    narration: [
      "让 Agent 看懂一张图，不该先把它硬塞进提示词。Qwen 这套开源插件，把图片、视频、PDF，甚至三维模型，直接变成可调用的工具。",
      "它把能力拆成独立模块：本地读取、云端视觉理解、网页与反向搜图、长视频记忆、视频编辑，还有 Blender 和 FreeCAD。按需装，不必一次全上。",
      "先装 core，Agent 就能动态分辨率读图、抽帧、标注和可视化文件；需要识别、转写或生成时，再接 DashScope；查网页和反搜图则要 Serper。",
      "边界很明确：本地读取不需要 API Key，但云端视觉和生成要 DashScope，搜索要 Serper；Windows 目前只验证 WSL2，三维软件还得先开着。",
      "如果你经常让 Codex 或 Claude 处理图片、长视频和三维文件，这套插件值得从 core 开始看；只做纯文本任务就别增加工具链。你最想先补哪种视觉能力？"
    ],
    sources: `# 来源与核验

- 官方仓库：[QwenLM/Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins)，2026-08-12 核验 1,960 Star，Apache-2.0，创建于 2026-07-29，最近推送 2026-08-11。
- 官方 README：八个独立能力模块；core 可本地读取图片、视频、文档和 3D 文件，云端 API、搜索、视频记忆、视频编辑、Blender、FreeCAD 和教育视频按需叠加。
- 官方安装说明：支持 Claude Code、Codex、Qoder、OpenClaw、Qwen Code 与 Gemini CLI；Windows x64 当前只验证 WSL2。
- 官方配置说明：本地读取无需 API Key；云端视觉/音视频理解和生成需 DashScope，网页与反向搜图需 Serper。
- 官方素材：仓库 \`cookbooks/core/assets\` 截图与 \`docs/assets/architecture.svg\`，冻结在工程 \`assets/\`。

大陆路径：core 可在本地使用；DashScope 为国内可获得的云端路径，具体账号、额度和网络状况由用户自行确认。未安装、未实测。`,
    dbs: `# DBS 门禁

- dbs-ai-check：短视频体裁；无虚构亲测、无“最强/第一”、无日报腔或匀速排比。首句反差用于建立真实问题，不属于高密度翻转。通过。
- dbs-resonate：唯一核心是“把多模态能力拆成可按需安装的 Agent 工具”；模块清单、工作链和 API 边界均服务这一机制。沉默解除、满足动机、立场框架、传播入口、信念结构均有效。通过。
- dbs-hook：开头独立建立“Agent 看图不能只塞提示词”的话题，给出图片、视频、PDF、3D 的可见结果，并保留工具如何做到的悬念；正文能够兑现。通过。
- dbs-xhs-title：采用公式 #55“你到底要不要 [话题]”，定稿“你到底要不要给Agent装眼睛？”，16 字，含具体对象与决策张力。通过。`,
    copy: `# 发布文案

## 抖音

- 标题：Agent 看不懂视频怎么办？｜Qwen-MM-Plugins
- 简介：Qwen-MM-Plugins 把多模态能力拆成八个独立模块。core 可在本地读图片、视频、PDF 和 3D 文件；云端识别、长视频记忆、搜索、视频编辑、Blender 与 FreeCAD 按需叠加。注意：云端能力与搜索需要各自 API Key，Windows 当前只验证 WSL2。
- 话题：#开源工具 #AIAgent #多模态 #Qwen #GitHub
- 置顶评论：你最想先让 Agent 看懂图片、长视频，还是三维文件？

## 小红书

- 标题：你到底要不要给Agent装眼睛？
- 正文：Qwen-MM-Plugins 不是把所有功能塞成一坨，而是把本地读取、云端视觉、搜索、长视频记忆、视频编辑、Blender 和 FreeCAD 拆开安装。先装 core 就能让 Agent 处理图片、视频、PDF 与 3D；需要云端理解和搜索时再配 Key。适合多模态重度用户，纯文本任务不用增加链路。
- 话题：#开源工具 #AIAgent #多模态AI #Qwen #GitHub项目
- 互动评论：图片、长视频、PDF、3D，你最想先补哪一种能力？

说明：未安装、未实测；内容来自 2026-08-12 核验的官方仓库、README、安装和配置说明。`,
    flowTitle: "能力按需叠加",
    flowSteps: ["core 本地读取", "api 云端理解", "search 事实核验", "创作与 3D 工具"],
    limitsTitle: "安装前先看边界",
    limitItems: ["本地 core 不要 Key", "云端与搜索要 Key", "Windows 走 WSL2"]
  },
  {
    issue: "018",
    slug: "diagram-design",
    project: "Diagram Design",
    repo: "github.com/cathrynlavery/diagram-design",
    category: "开源效率局",
    score: "96 / 100",
    titleLines: ["AI 画流程图", "别再像默认模板"],
    kicker: "27 种编辑式图表，还能重画旧 draw.io",
    section2TitleLines: ["图形类型够全", "输出仍是开放文件"],
    section3TitleLines: ["先读品牌", "再选尺寸、细节和受众"],
    stats: ["27 种图表类型", "亮色 / 暗色 / 编辑版", "HTML / SVG / PNG"],
    flow: ["读取品牌颜色与字体", "匹配合适图形类型", "按尺寸与受众简化", "输出文件与删改台账"],
    limits: ["它是 Agent skill，不是拖拽软件", "品牌抓取结果要人工确认", "旧图简化可能合并或删除节点"],
    verdict: "文章、方案与演示作者很实用；只想拖拽的人未必适合",
    media: ["assets/official-architecture.png", "assets/official-gallery.png", "assets/workflow.svg", "assets/limits.svg", "assets/official-import.png"],
    narration: [
      "AI 画流程图最常见的问题，不是画不出来，是一眼就像默认模板。Diagram Design 做了二十七种编辑式图表，还能把旧 draw.io 重新排得更像设计稿。",
      "它覆盖架构图、流程图、时序、象限、甘特、雷达、组织图和数据流。每种都有亮色、暗色和完整编辑版，直接在浏览器打开，不需要构建。",
      "使用时先让它读你的品牌颜色和字体，再选择图形类型、尺寸、细节和受众。输入现成 draw.io 时，它会记录哪些节点合并、折叠或删掉，不是只换皮。",
      "门槛不高：Codex 用一条 npx skills add 安装，结果是 HTML、SVG 或 PNG。但它是 Agent skill，不是拖拽软件；品牌抓取和内容简化仍要你确认。",
      "写文章、做方案、做演示，又受够了圆角框的人，这个项目很实用；只想鼠标拖两下的人不一定合适。你最想先把哪张旧图重画？"
    ],
    sources: `# 来源与核验

- 官方仓库：[cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design)，2026-08-12 核验 6,770 Star，MIT，创建于 2026-04-16，最近推送 2026-08-11。
- 官方 README：27 种图表类型，每种提供 minimal light、minimal dark 与 full-editorial 三种变体；结果可直接在浏览器打开，无构建步骤与外部图片依赖。
- 官方安装说明：Codex 可用 \`npx skills add https://github.com/cathrynlavery/diagram-design --skill diagram-design\` 安装。
- 官方 draw.io 说明：支持 drawio/xml/png/svg 容器，可按格式、尺寸、细节和受众重画，并输出 fidelity ledger 记录合并、折叠与删除。
- 官方素材：仓库 \`docs/screenshots\` 中的架构图、循环图和 draw.io 导入结果，冻结在工程 \`assets/\`。

大陆路径：核心产物是本地 HTML/SVG/PNG；安装与品牌抓取需要可访问 GitHub/目标网站。未安装、未实测。`,
    dbs: `# DBS 门禁

- dbs-ai-check：短视频体裁；没有虚构使用体验、夸大收益、连续金句或宣传词。开头的“不是画不出来”仅一次，用于具体反差。通过。
- dbs-resonate：唯一核心是“AI 图表要按品牌、受众和信息密度重画，而非套默认样式”；类型、工作链和 draw.io 台账均为支撑。五个共鸣维度有效。通过。
- dbs-hook：开头独立说清 AI 流程图的可见痛点，并用“27 种 + 重画旧 draw.io”给出可信素材；正文兑现类型、品牌和简化机制。通过。
- dbs-xhs-title：采用公式 #48“[行动] 是在浪费时间么？”，定稿“AI画流程图是在浪费时间吗？”，15 字，留有结果悬念。通过。`,
    copy: `# 发布文案

## 抖音

- 标题：AI 画流程图别再像默认模板｜Diagram Design
- 简介：Diagram Design 提供 27 种编辑式图表，支持亮色、暗色和完整编辑版，还能按尺寸、细节与受众重画 draw.io，并记录哪些节点被合并或删除。Codex 可直接安装 skill，输出 HTML、SVG 或 PNG；它不是拖拽软件，品牌抓取和内容简化仍需确认。
- 话题：#开源工具 #流程图 #信息设计 #AI效率 #GitHub
- 置顶评论：你手里最想重画的是架构图、流程图，还是甘特图？

## 小红书

- 标题：AI画流程图是在浪费时间吗？
- 正文：问题通常不在“能不能画”，而在一眼就像默认模板。Diagram Design 把架构、流程、时序、象限、甘特、雷达等 27 种图表做成 Agent skill，还能读取品牌颜色和字体，并按受众重画旧 draw.io。输出仍是 HTML、SVG 或 PNG，适合写文章、做方案和演示的人。
- 话题：#开源工具 #流程图设计 #信息可视化 #AI效率 #GitHub项目
- 互动评论：你最想先重画哪一张旧图？

说明：未安装、未实测；内容来自 2026-08-12 核验的官方仓库、README、安装和 draw.io 导入说明。`,
    flowTitle: "从内容到编辑式图表",
    flowSteps: ["读取品牌 tokens", "选图形类型", "按受众做减法", "导出 + fidelity ledger"],
    limitsTitle: "它不是一键美化",
    limitItems: ["不是鼠标拖拽软件", "品牌映射需要确认", "简化会改动节点"]
  },
  {
    issue: "019",
    slug: "img2threejs",
    project: "img2threejs",
    repo: "github.com/img2threejs/img2threejs",
    category: "AI视频局",
    score: "89 / 100",
    titleLines: ["一张照片", "变成可动画 3D"],
    kicker: "不用网格下载，Agent 用 Three.js 重新搭建",
    section2TitleLines: ["产物是代码", "不是一块不可编辑网格"],
    section3TitleLines: ["逐关搭建", "每一步都和参考图对比"],
    stats: ["TypeScript 工厂", "8 段生成与质检", "Python 3.10+ 标准库"],
    flow: ["列出轮廓与关键细节", "白模到结构逐层搭建", "材质灯光逐关校验", "输出层级、转轴和碰撞区"],
    limits: ["单图看不到背面与隐藏结构", "人物目前偏风格化重建", "需要 Agent 看图与浏览器能力"],
    verdict: "网页 3D 与游戏原型值得看；精密工业模型不适合",
    media: ["assets/official-gallery.png", "assets/official-doraemon.png", "assets/workflow.svg", "assets/limits.svg", "assets/official-sony.png"],
    narration: [
      "给 AI 一张物体照片，直接变成能旋转的三维模型？img2threejs 的答案有点反常识：它不做照片测量，而是让 Agent 用代码把物体重新搭出来。",
      "最终产物不是下载来的网格，而是一个 Three.js 工厂：几何体、材质、层级、转轴和碰撞区都写进 TypeScript，方便继续动画和版本管理。",
      "流程先列出轮廓和关键细节，再按白模、结构、形体、材质、表面、灯光逐关生成。每一关都把参考图和渲染放在一张对比表里，不合格就停。",
      "限制必须说清：单张图看不到背面，所以项目会标低置信度，不承诺百分之百还原。它擅长硬表面物体；人物目前偏风格化，还要 Agent 的看图与浏览器能力。",
      "做网页三维展示、游戏原型，又想保留可编辑代码的人值得关注；要一键得到精确工业模型就不适合。你会先拿什么物体照片测试？"
    ],
    sources: `# 来源与核验

- 官方仓库：[img2threejs/img2threejs](https://github.com/img2threejs/img2threejs)，2026-08-12 核验 10,960 Star，Apache-2.0，创建于 2026-07-15，最近推送 2026-08-11。
- 官方 README 与 v1.5 beta：输入单张参考图，输出由 primitives、程序化材质和生成几何组成的 Three.js TypeScript 工厂，并保留层级、转轴、socket 与 collider。
- 官方流程：detail inventory 后按 blockout、structural、form、material、surface、lighting、interaction、optimization 推进；每关使用参考图与渲染的对比表，严格门禁失败即停止。
- 官方限制：单图无法看到隐藏面，项目记录低置信度；硬表面物体更强，人物当前是风格化重建，不能承诺精确人物相似度。
- 官方素材：[img2threejs showcase](https://img2threejs.github.io/img2threejs-showcase/) 仓库的 hero gallery、多啦 A 梦小屋与 Sony 耳机示例，冻结在工程 \`assets/\`。

大陆路径：核心脚本为 Python 3.10+ 标准库，无 pip 依赖；仍需可看图、可运行浏览器预览的 Agent 环境。未安装、未实测。`,
    dbs: `# DBS 门禁

- dbs-ai-check：短视频体裁；不声称亲测、不承诺“一键精确还原”，主动写出单图盲区。一次“不是网格”反差服务机制，没有高密度翻转。通过。
- dbs-resonate：唯一核心是“用可编辑 Three.js 代码重建物体，并用逐关对比门禁控制质量”；产物、工作链和限制统一服务这一机制。五个共鸣维度有效。通过。
- dbs-hook：开头给出“一张图变可旋转 3D”的可见结果，再用“不做照片测量”留下方法悬念；正文有流程与限制兑现。通过。
- dbs-xhs-title：采用公式 #55“你到底要不要 [话题]”，定稿“你到底要不要用照片做3D？”，15 字，符合决策型内容且保留悬念。通过。`,
    copy: `# 发布文案

## 抖音

- 标题：一张照片能变成可动画 3D 吗？｜img2threejs
- 简介：img2threejs 不做照片测量或下载网格，而是让 Agent 用 primitives、程序化材质和生成几何重建 Three.js 模型。结果是可编辑的 TypeScript 工厂，保留层级、转轴和碰撞区；每个阶段都要过参考图对比门禁。单图看不到背面，人物目前也偏风格化，不能当精密工业建模。
- 话题：#开源工具 #ThreeJS #三维建模 #AI工具 #GitHub
- 置顶评论：你会先拿耳机、家具，还是一件游戏道具来测试？

## 小红书

- 标题：你到底要不要用照片做3D？
- 正文：img2threejs 的路线很特别：输入一张物体图，不做传统照片测量，而是让 Agent 用 Three.js 代码重新搭建。流程从白模、结构、材质一路过门禁，输出可继续动画和版本管理的 TypeScript 工厂。它更适合硬表面物体与网页/游戏原型；单图盲区和人物相似度要诚实看待。
- 话题：#开源工具 #ThreeJS #3D建模 #AI工具 #GitHub项目
- 互动评论：你会先用什么物体照片测试？

说明：未安装、未实测；内容来自 2026-08-12 核验的官方仓库、README、版本说明与官方 showcase。`,
    flowTitle: "一张图到可动画代码",
    flowSteps: ["轮廓与细节清单", "白模与结构", "材质灯光门禁", "层级与动画接口"],
    limitsTitle: "单张图有天然盲区",
    limitItems: ["背面结构只能推断", "人物仍偏风格化", "精密建模不适合"]
  }
];

const candidateReport = `# 了不起的小超人｜开源装备雷达候选池（2026-08-12 早轮）

核验时间：2026-08-12（Asia/Shanghai）  
去重范围：2026-07-13—2026-08-12，核对现有 001—016 期；本轮三项均未重复。  
热度入口：GitHub Trending、RepoRadar、Trendshift；仓库数据以 2026-08-12 GitHub API 为准。  
评分顺序：视觉结果 / 用户价值 / 新鲜与增长 / 新手成本 / 维护与许可。

| 候选 | 分类 | 分项 | 总分 | 决策 |
|---|---|---:|---:|---|
| cathrynlavery/diagram-design | 开源效率 | 25/24/18/14/15 | 96 | 制作 018 |
| QwenLM/Qwen-MM-Plugins | Agent 自动化 | 22/23/19/11/15 | 90 | 制作 017 |
| img2threejs/img2threejs | AI 视觉/3D | 25/20/19/11/14 | 89 | 制作 019 |
| paperclipai/paperclip | Agent 自动化 | 22/24/18/10/14 | 88 | 与本轮多模态 Agent 题撞类型 |
| pingdotgg/t3code | Agent 自动化 | 22/22/17/13/14 | 88 | 与 017 撞类型 |
| stablyai/orca | Agent 自动化 | 22/21/18/10/14 | 85 | 与 017 撞类型 |
| calesthio/OpenMontage | AI 视频 | 25/22/15/6/13 | 81 | 门槛偏高，且与近 30 天视频工具内容邻近 |
| vercel-labs/scriptc | 开源效率 | 16/18/20/8/15 | 77 | 视觉结果弱于 018 |
| holaboss-ai/holaOS | Agent 自动化 | 22/21/16/11/3 | 73 | GitHub 未识别许可证，未选 |
| 1ay1/agentty | Agent 自动化 | 13/17/18/11/14 | 73 | 视觉结果偏弱 |
| PrimeIntellect-ai/prime-agent | Agent 自动化 | 15/18/20/5/14 | 72 | 新手门槛高 |
| vitali87/code-graph-rag | 开源效率 | 17/20/13/7/14 | 71 | 勉强过线，留待重新核验 |
| danielmiessler/LifeOS | Agent 自动化 | 16/20/12/8/14 | 70 | 勉强过线，主题边界偏大 |
| org2AI/ORG2 | Agent 自动化 | 12/15/19/5/13 | 64 | 不制作 |
| google-deepmind/weathernext | GitHub 热榜 | 20/15/11/2/15 | 63 | 计算门槛太高 |
| Sidiora-Labs/centra-llm-agents（原候选重定向） | Agent 自动化 | 18/15/19/8/2 | 62 | 许可证不明确 |
| harveyai/harvey-labs | GitHub 热榜 | 10/13/18/4/14 | 59 | 普通用户价值与视觉结果不足 |
| aklivity/zilla | GitHub 热榜 | 10/15/8/4/4 | 41 | 主题过于基础设施化，许可未识别 |

## 入选核验摘要

- Diagram Design：MIT，2026-08-11 最近推送；27 种图表、三种视觉变体、draw.io 导入与删改台账，普通创作者有明确本地输出路径。
- Qwen-MM-Plugins：Apache-2.0，创建于 2026-07-29、2026-08-11 最近推送；core 本地可用，云端与搜索 Key 边界明确，支持 Codex。
- img2threejs：Apache-2.0，创建于 2026-07-15、2026-08-11 最近推送；官方 showcase 可核验，标准库脚本、逐关门禁和单图盲区说明明确。
`;

for (const episode of episodes) ensureNew(path.join(contentRoot, `xiaochao-${episode.issue}-${episode.slug}`));
for (const episode of episodes) ensureNew(path.join(outputRoot, "copy", `${Number(episode.issue)}-${episode.slug}.md`));

fs.mkdirSync(contentRoot, {recursive: true});
fs.mkdirSync(path.join(outputRoot, "videos-with-bgm"), {recursive: true});
fs.mkdirSync(path.join(outputRoot, "videos"), {recursive: true});
fs.mkdirSync(path.join(outputRoot, "copy"), {recursive: true});
fs.mkdirSync(path.join(outputRoot, "qa"), {recursive: true});
writeNew(path.join(contentRoot, "xiaochao-radar-candidates-run-1.md"), candidateReport);

for (const episode of episodes) {
  const projectDir = path.join(contentRoot, `xiaochao-${episode.issue}-${episode.slug}`);
  for (const subdir of ["assets", "narration", "voice", "snapshots"]) fs.mkdirSync(path.join(projectDir, subdir), {recursive: true});
  episode.narration.forEach((line, index) => writeNew(path.join(projectDir, "narration", `${String(index + 1).padStart(2, "0")}-${["hook", "what", "workflow", "limit", "verdict"][index]}.txt`), line));
  writeNew(path.join(projectDir, "sources.md"), episode.sources);
  writeNew(path.join(projectDir, "dbs-review.md"), episode.dbs);
  writeNew(path.join(projectDir, "package.md"), episode.copy);
  writeNew(path.join(outputRoot, "copy", `${Number(episode.issue)}-${episode.slug}.md`), episode.copy);
  writeNew(path.join(projectDir, "BRIEF.md"), `# BRIEF

- flow: automation
- authoring_skill: general-video
- format: 1080×1920 vertical
- duration: 50—65 seconds, five narrated scenes
- visual: current warm editorial manual and yellow portrait IP
- audio: exact MiniMax voice and fixed look-beyond.mp3 mix
- constraints: no cover, platform, draft, publish, or unverifiable hands-on claim`);
  writeNew(path.join(projectDir, "STORYBOARD.md"), `# STORYBOARD

1. 官方结果画面 + “${episode.titleLines.join(" / ")}”问题。
2. 三个核心能力与官方素材。
3. 一条真实工作链路和步骤图。
4. 账号、工具或输入限制。
5. ${episode.score} 与适用人群结论。`);
  writeNew(path.join(projectDir, "video-spec.json"), JSON.stringify({
    slug: `xiaochao-${episode.issue}-${episode.slug}`,
    issue: episode.issue,
    category: episode.category,
    kicker: episode.kicker,
    titleLines: episode.titleLines,
    section2TitleLines: episode.section2TitleLines,
    section3TitleLines: episode.section3TitleLines,
    project: episode.project,
    repo: episode.repo,
    score: episode.score,
    verdict: episode.verdict,
    stats: episode.stats,
    flow: episode.flow,
    limits: episode.limits,
    media: episode.media,
    durationsMs: []
  }, null, 2));
  writeNew(path.join(projectDir, "assets", "workflow.svg"), flowSvg(episode.flowTitle, episode.flowSteps));
  writeNew(path.join(projectDir, "assets", "limits.svg"), limitsSvg(episode.limitsTitle, episode.limitItems));
}

console.log(JSON.stringify({date, episodes: episodes.map(({issue, slug, score}) => ({issue, slug, score}))}, null, 2));
