#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const root = "<REPO>";
const date = "2026-08-14";
const contentRoot = path.join(root, "content", date);
const outputRoot = path.join(root, "output", "xiaochao", date);
const sourceRoot = "/private/tmp/xiaochao-radar-2026-08-14-run1";

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

const esc = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;");

const flowSvg = (title, steps) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200">
<rect width="900" height="1200" fill="#F6F0E4"/><text x="55" y="92" font-family="sans-serif" font-size="44" font-weight="900" fill="#1B1916">${esc(title)}</text>
${steps.map((step, index) => {
  const y = 160 + index * 235;
  const fill = ["#B9F227", "#FFD45A", "#FF5A36", "#F6F0E4"][index % 4];
  return `<rect x="55" y="${y}" width="790" height="165" rx="24" fill="${fill}" stroke="#1B1916" stroke-width="8"/><circle cx="125" cy="${y + 82}" r="38" fill="#1B1916"/><text x="125" y="${y + 96}" text-anchor="middle" font-family="monospace" font-size="38" font-weight="900" fill="#F6F0E4">${index + 1}</text><text x="195" y="${y + 96}" font-family="sans-serif" font-size="36" font-weight="900" fill="#1B1916">${esc(step)}</text>${index < steps.length - 1 ? `<path d="M450 ${y + 175}v50" stroke="#1B1916" stroke-width="9"/><path d="m430 ${y + 210} 20 22 20-22" fill="none" stroke="#1B1916" stroke-width="9"/>` : ""}`;
}).join("\n")}</svg>`;

const limitsSvg = (title, items) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200"><rect width="900" height="1200" fill="#F6F0E4"/><rect x="52" y="54" width="796" height="1092" rx="28" fill="#FFD45A" stroke="#1B1916" stroke-width="9"/><text x="90" y="145" font-family="sans-serif" font-size="48" font-weight="900" fill="#1B1916">${esc(title)}</text>${items.map((item, index) => {
  const y = 245 + index * 270;
  return `<rect x="92" y="${y}" width="716" height="198" rx="22" fill="#F6F0E4" stroke="#1B1916" stroke-width="7"/><circle cx="155" cy="${y + 70}" r="36" fill="#FF5A36" stroke="#1B1916" stroke-width="6"/><text x="155" y="${y + 84}" text-anchor="middle" font-family="monospace" font-size="38" font-weight="900" fill="#1B1916">!</text><foreignObject x="215" y="${y + 35}" width="545" height="140"><div xmlns="http://www.w3.org/1999/xhtml" style="font:900 35px/1.25 sans-serif;color:#1B1916">${esc(item)}</div></foreignObject>`;
}).join("\n")}</svg>`;

const episodes = [
  {
    issue: "026",
    slug: "needle2",
    project: "Needle 2",
    repo: "github.com/cactus-compute/needle",
    category: "Agent自动化局",
    score: "95 / 100",
    titleLines: ["能调用工具的模型", "竟然只有 14MB"],
    kicker: "45M 参数、约 28MB 内存，把工具判断放进小设备",
    section2TitleLines: ["不是陪聊模型", "专门判断该调什么"],
    section3TitleLines: ["描述工具以后", "直接拿结构化调用"],
    stats: ["单文件 14MB", "约 28MB 内存", "MIT 许可证"],
    flow: ["pip 安装并缓存引擎", "用函数或 Schema 描述工具", "本地模型选择工具与参数", "返回结果和置信度"],
    limits: ["上下文窗口只有 256 token", "首次仍要下载引擎和权重", "微调与复杂任务需要开发能力"],
    verdict: "端侧工具路由很有意思；拿它替代通用大模型就想错了",
    media: ["assets/official-banner.png", "assets/official-frontier.png", "assets/workflow.svg", "assets/limits.svg", "assets/official-architecture.png"],
    flowTitle: "让小模型做工具路由",
    flowSteps: ["安装引擎", "声明工具", "本地判断", "返回 JSON"],
    limitsTitle: "小，来自明确取舍",
    limitItems: ["256 token 窗口", "首次需要下载", "面向开发者集成"],
    narration: [
      "一个能调用工具的模型，竟然只有十四兆。Needle 2 想做的不是陪你长聊，而是让手机、穿戴设备和小机器人在本地判断：现在该调用哪个工具。",
      "它有四千五百万参数，量化后打进一个十四兆的引擎，完整会话大约占二十八兆内存。输入文字，输出受 Schema 约束的 JSON；每次结果还带置信度，低于阈值就可以交给更大的模型。",
      "实际链路是先 pip 安装，首次从模型仓库缓存引擎；再用 Python 函数、类型和说明声明工具。Needle 在本机选出工具、填写参数、执行函数，再把结果送回循环。工具很多时，它只把最相关的五个放进当前提示。",
      "小也意味着边界很硬。它的滑动窗口只有二百五十六个 token，适合工具路由和结构化抽取，不适合长文推理。首次下载仍依赖 GitHub 和模型托管站；自己微调还要准备数据、JAX 和可用加速设备。",
      "如果你在做端侧控制、离线表单抽取或小机器人，Needle 2 很值得研究；想把它当通用聊天大模型，就用错地方了。你会先把哪个工具判断放到本地？"
    ],
    sources: `# 来源与核验\n\n- 官方仓库：[cactus-compute/needle](https://github.com/cactus-compute/needle)，2026-08-14 核验 4,933 Star、333 Fork，MIT；创建于 2026-02-24，最近推送 2026-08-14。\n- GitHub Trending：2026-08-14 位于日榜，页面显示当日新增 768 Star。\n- 官方 README：Needle 2 为 45M 参数工具调用与结构化抽取模型；CQ2 量化后的单文件引擎为 14MB，完整会话约占 28MB RAM。\n- 官方工作链：pip install cactus-needle；用函数签名、docstring、Pydantic 或 JSON Schema 声明工具；返回结构化调用、结果与置信度。\n- 官方边界：256-token 滑动窗口；首次从 Hugging Face 下载并缓存引擎；LoRA 微调使用 JAX，可选 CUDA 或 Apple Silicon Metal。\n- 官方许可：仓库 LICENSE 为 MIT。\n- 官方素材：README 的 banner、size-quality frontier 与架构图，冻结在工程 assets。\n\n大陆路径：安装后推理不需要网络；首次访问 GitHub、PyPI 与 Hugging Face 的可用性取决于用户网络和镜像配置。未安装、未实测。`,
    dbs: `# DBS 门禁\n\n## dbs-ai-check\n- 体裁：短视频文稿。\n- 未命中虚构亲测、夸大“最强/颠覆”或哲学升维。\n- “不是陪你长聊”只出现一次，用来界定模型任务，不构成高密度否定翻转。\n- 长短句有变化，数据均来自官方 README。通过。\n\n## dbs-resonate\n- 核心机制：把工具选择与结构化参数填写压到端侧小模型，而不是让小模型承担通用对话。\n- 沉默解除：有效，回应“端侧 Agent 一定要塞大模型”的默认假设。\n- 满足动机：有效，给开发者一条低内存、本地运行的工具路由路径。\n- 立场框架：有效，站在需要隐私、低延迟和小设备部署的人一边。\n- 传播入口：有效，端侧 AI、IoT 与 Agent 开发者会因 14MB 数据转发。\n- 信念结构：有效，用 256 token 和首次下载边界阻止错误期待。\n- 骨架：14MB 结果 → 为什么能小 → 工具调用链 → 明确取舍 → 适用人群。通过。\n\n## dbs-hook\n- 素材：14MB、28MB RAM、45M 参数三项可核数据，内容超过 200 字。\n- 开头独立交代对象、反差和用途；没有假设观众看过标题，也没有虚构使用经历。\n- 选用“数据冲击”方案：“一个能调用工具的模型，竟然只有十四兆。”通过。\n\n## dbs-xhs-title\n- 采用公式 #55“你到底要不要 [话题]”。\n- 定稿：“你到底要不要让 Agent 离线跑？”共 17 字；有端侧与云端反差，也保留是否值得装的悬念。通过。`,
    copy: `# 发布文案\n\n## 抖音\n\n- 标题：14MB 的模型怎么在本地调用工具？｜Needle 2\n- 简介：Needle 2 是一个 45M 参数的端侧工具调用模型：量化引擎只有 14MB，完整会话约占 28MB 内存，能按函数或 Schema 返回结构化调用和置信度。它适合工具路由与抽取，不适合长文推理；首次仍需下载引擎和权重。\n- 话题：#开源工具 #端侧AI #AIAgent #本地模型 #GitHub\n- 置顶评论：你最想把哪一个工具判断放到本地？\n\n## 小红书\n\n- 标题：你到底要不要让 Agent 离线跑？\n- 正文：Needle 2 把工具选择和参数填写压进一个 14MB 的本地模型，完整会话约占 28MB 内存，还能返回置信度。它更像端侧路由器，不是通用聊天模型：窗口只有 256 token，首次也要下载引擎和权重。\n- 话题：#开源工具 #端侧AI #AIAgent #本地模型 #GitHub项目\n- 互动评论：如果只选一个，你会先离线化哪个工具？\n\n说明：未安装、未实测；内容来自 2026-08-14 核验的官方仓库、README、许可证和官方素材。`,
    assets: [
      [path.join(sourceRoot, "needle/banner.png"), "official-banner.png"],
      [path.join(sourceRoot, "needle/frontier.png"), "official-frontier.png"],
      [path.join(sourceRoot, "needle/architecture.png"), "official-architecture.png"]
    ]
  },
  {
    issue: "027",
    slug: "fluidvoice",
    project: "FluidVoice",
    repo: "github.com/altic-dev/FluidVoice",
    category: "开源效率局",
    score: "94 / 100",
    titleLines: ["语音输入还要上云", "这次可以留在 Mac"],
    kicker: "听写、改写和命令模式，直接写进当前应用",
    section2TitleLines: ["按一下快捷键", "文字直接进光标位置"],
    section3TitleLines: ["选模型和模式", "说完就回到当前应用"],
    stats: ["macOS 15 以上", "Whisper 支持中文", "核心 GPLv3"],
    flow: ["安装并授权麦克风与辅助功能", "选择本地语音模型和模式", "全局快捷键开始听写", "转写或处理后写入当前应用"],
    limits: ["当前正式版只支持 macOS", "中文不走最快的 Parakeet 方案", "Fluid Intelligence 增强模型不开放源码"],
    verdict: "Mac 上的本地听写很完整；别把闭源增强层也算成全开源",
    media: ["assets/official-command.png", "assets/official-local-ai.png", "assets/workflow.svg", "assets/limits.svg", "assets/official-history.png"],
    flowTitle: "从说话到当前光标",
    flowSteps: ["安装授权", "选择模型", "按键说话", "自动写入"],
    limitsTitle: "本地优先，也有边界",
    limitItems: ["目前只做 macOS", "中文模型速度不同", "增强层单独闭源"],
    narration: [
      "语音输入经常要在速度、隐私和格式整理里三选一。FluidVoice 把听写、改写和命令模式放回 Mac 本地，按一下快捷键，说完的文字就能直接进当前应用。",
      "它能用 Apple Speech、Whisper、Nemotron、Parakeet 和 Cohere 等模型。写作模式可以把结果插进任意文本框；命令模式还能启动应用或触发系统操作。音频历史、每日统计和每个应用的提示词都集中在一个界面。",
      "链路是先用 Homebrew 或 Release 安装，授权麦克风和辅助功能，再选语言、模型与快捷键。开始说话后，转写结果先出现在悬浮层；需要时做格式整理，最后通过系统辅助功能写回光标位置。",
      "边界要分开说。正式版目前只有 macOS 十五以上；中文可走 Apple Speech、Whisper 或 Cohere，但主打低延迟的 Parakeet 方案目前不含中文。FluidVoice 核心是 GPLv3，不过本地增强层 Fluid Intelligence 由作者单独闭源维护。",
      "如果你用 Mac 写邮件、笔记或长提示词，又在意语音不离机，FluidVoice 很值得试；Windows 和 iOS 还要等。你更想用它听写，还是直接发系统命令？"
    ],
    sources: `# 来源与核验\n\n- 官方仓库：[altic-dev/FluidVoice](https://github.com/altic-dev/FluidVoice)，2026-08-14 核验 9,837 Star、663 Fork，GPL-3.0；创建于 2025-09-22，最近推送 2026-08-14。\n- GitHub Trending：2026-08-14 位于日榜，页面显示当日新增 187 Star。\n- 最新 Release：[v1.6.8](https://github.com/altic-dev/FluidVoice/releases/tag/v1.6.8)，发布于 2026-08-11，提供 DMG 与 ZIP。\n- 官方 README：支持 Write Mode、Command Mode、全局快捷键、悬浮预览、音频历史、每应用配置，以及 Apple Speech、Whisper、Nemotron、Parakeet、Cohere 等语音模型。\n- 官方门槛：macOS 15+；Apple Silicon 支持全部模型，Intel 通过 Whisper；需要麦克风和辅助功能权限。\n- 中文路径：Whisper 支持多语言，Apple Speech 取决于系统语言，Cohere 列明支持 Mandarin；README 当前列出的 Parakeet 语言不含中文。\n- 许可边界：应用核心从 2026-02-23 起为 GPLv3；Fluid Intelligence 是单独维护且暂不公开源码的本地增强运行时。\n- 官方素材：仓库 assets 的命令模式、本地增强与历史界面截图，冻结在工程 assets。\n\n大陆路径：应用可本地运行；首次访问 GitHub Release、Homebrew 与模型下载源的可用性取决于用户网络。未安装、未实测。`,
    dbs: `# DBS 门禁\n\n## dbs-ai-check\n+- 体裁：短视频文稿。\n+- 没有把“本地优先”写成绝对隐私承诺；闭源增强层、平台和中文模型差异均明确。\n+- 句式节奏有长有短，未堆连接词或连续排比。通过。\n+\n+## dbs-resonate\n+- 核心机制：让听写结果从本地语音模型直接回到当前应用，而不是只做一个转写窗口。\n+- 沉默解除：有效，点出速度、隐私和整理经常互相牺牲。\n+- 满足动机：有效，给 Mac 用户一条少切应用、少上传语音的输入路径。\n+- 立场框架：有效，站在高频写字但不想被云端流程打断的人一边。\n+- 传播入口：有效，Mac 效率工具与本地 AI 用户会因“直接写回光标”转发。\n+- 信念结构：有效，承认核心开源而增强层闭源，避免信任透支。\n+- 骨架：输入痛点 → 直接写回结果 → 四步链路 → 中文与开源边界 → 人群结论。通过。\n+\n+## dbs-hook\n+- 文稿超过 200 字，包含直接写回、模型选择、平台和许可四类素材。\n+- 开头不依赖标题，先给“三选一”痛点，再给本地写回结果；没有自问自答。通过。\n+\n+## dbs-xhs-title\n+- 采用公式 #55“你到底要不要 [话题]”。\n+- 定稿：“你到底要不要本地语音输入？”共 14 字；在云端与本地之间保留决策悬念。通过。`,
    copy: `# 发布文案\n\n## 抖音\n\n- 标题：Mac 怎么把本地听写直接写进任意应用？｜FluidVoice\n- 简介：FluidVoice 把听写、写作模式和系统命令放进 Mac 本地流程：按全局快捷键说话，结果通过辅助功能写回当前光标。它支持 Apple Speech、Whisper 等模型。注意：目前只支持 macOS 15+；核心是 GPLv3，但 Fluid Intelligence 增强层单独闭源。\n- 话题：#开源工具 #Mac效率 #语音输入 #本地AI #GitHub\n- 置顶评论：你会先用它听写、改写，还是发系统命令？\n\n## 小红书\n\n- 标题：你到底要不要本地语音输入？\n- 正文：FluidVoice 不只把语音转成文字，还能把结果直接写回当前应用，并提供写作和命令模式。中文可选 Apple Speech、Whisper 或 Cohere；主打低延迟的 Parakeet 当前不含中文。核心 GPLv3，本地增强层 Fluid Intelligence 单独闭源。\n- 话题：#开源工具 #Mac效率 #语音输入 #本地AI #效率工具\n- 互动评论：你最想把哪一种输入场景改成说话完成？\n\n说明：未安装、未实测；内容来自 2026-08-14 核验的官方仓库、README、Release、许可证和官方截图。`,
    assets: [
      [path.join(sourceRoot, "fluidvoice/cmd-mode.png"), "official-command.png"],
      [path.join(sourceRoot, "fluidvoice/local-ai.png"), "official-local-ai.png"],
      [path.join(sourceRoot, "fluidvoice/history.png"), "official-history.png"]
    ]
  },
  {
    issue: "028",
    slug: "modly",
    project: "Modly",
    repo: "github.com/lightningpixel/modly",
    category: "GitHub热榜",
    score: "92 / 100",
    titleLines: ["不会建模", "也能把图片变成 3D"],
    kicker: "模型、工作流和导出都留在一张本地桌面界面",
    section2TitleLines: ["导入一张图片", "流程节点自己接"],
    section3TitleLines: ["图片进入工作流", "网格结果回到场景"],
    stats: ["Windows / Linux", "Apple Silicon Mac", "本地 GPU 推理"],
    flow: ["安装桌面端与模型扩展", "把图片接到生成网格节点", "本地模型生成并加入场景", "平滑减面后导出 GLB"],
    limits: ["需要本地 GPU 和模型文件", "不同扩展门槛与显存不同", "许可证文本附带可见署名要求"],
    verdict: "本地图片转 3D 很直观；没有合适显卡就别只看界面心动",
    media: ["assets/official-app.png", "assets/official-install-models.png", "assets/workflow.svg", "assets/limits.svg", "assets/official-app.png"],
    flowTitle: "一张图变成可导出网格",
    flowSteps: ["安装扩展", "连接节点", "本地生成", "优化导出"],
    limitsTitle: "离线生成仍然吃硬件",
    limitItems: ["需要本地 GPU", "扩展门槛不同", "分发需保留署名"],
    narration: [
      "不会建模，也能把一张图片变成三维网格。Modly 把本地 AI 模型、节点工作流和三维预览放进桌面应用，生成后还能直接平滑、减面和导出。",
      "它支持 Windows、Linux 和 Apple Silicon Mac。模型通过扩展安装，目前官方列出 Hunyuan3D Mini、TripoSG 和 Trellis 2 GGUF 等方案。界面里能导入图片、切换工作流、查看内存，再把网格放进三维场景。",
      "真实链路是先安装桌面端和一个模型扩展，再把 Image 节点接到 Generate Mesh，选中工作流后开始生成。结果回到场景，可以继续平滑和减面，最后导出模型。脚本或 Agent 也能通过本地 CLI 提交图片、轮询任务并拿到 GLB。",
      "它不等于零门槛。所有推理都在本机，显卡、内存和模型文件必须自己准备；不同扩展的硬件要求也不一样。macOS 只支持 Apple Silicon。仓库使用 MIT 文本，但 LICENSE 后面还写了衍生应用要保留 Modly 与作者署名。",
      "如果你做游戏原型、电商展示或三维草模，又有可用 GPU，Modly 的流程很直观；只想在普通办公本上点一下就出模型，先别急。你会先拿什么图片试三维化？"
    ],
    sources: `# 来源与核验\n\n- 官方仓库：[lightningpixel/modly](https://github.com/lightningpixel/modly)，2026-08-14 核验 5,386 Star、574 Fork；创建于 2026-03-18，最近推送 2026-08-13。\n- GitHub Trending：2026-08-14 位于日榜，页面显示当日新增 221 Star。\n- 最新 Release：[v0.4.1](https://github.com/lightningpixel/modly/releases/tag/v0.4.1)，发布于 2026-07-17，提供 Windows、Linux 与 Apple Silicon macOS 安装包。\n- 官方 README：桌面端在本地 GPU 上运行图片转 3D；支持扩展系统、节点工作流、三维预览、平滑、减面与导出。\n- 官方扩展：列出 Hunyuan3D 2 Mini、TripoSG、Trellis2 GGUF 等官方扩展；具体硬件和模型下载门槛随扩展变化。\n- 官方自动化路径：stdlib-only Modly CLI 可提交图片、查询 workflow-run、导出最终网格；README 明确要求桌面桥接状态可用。\n- 平台边界：Windows、Linux 与 Apple Silicon Mac；本地推理需要可用 GPU、内存和模型文件。\n- 许可边界：仓库标注 MIT，LICENSE 文本后另附衍生应用需在 UI 或文档显示 Modly 与作者署名的要求。\n- 官方素材：README 的主界面、模型安装与扩展安装截图，冻结在工程 assets。\n\n大陆路径：安装后可本地推理；首次获取 GitHub Release、扩展仓库与模型文件的可用性取决于用户网络。未安装、未实测。`,
    dbs: `# DBS 门禁\n\n## dbs-ai-check\n+- 体裁：短视频文稿。\n+- 没有虚构生成速度、显存数字或亲测效果；“不会建模”只描述产品入口，不承诺专业成品质量。\n+- 功能、链路和门槛各只保留一个重点，未堆成产品清单。通过。\n+\n+## dbs-resonate\n+- 核心机制：把图片转 3D 的模型选择、工作流、预览和导出集中到本地桌面端。\n+- 沉默解除：有效，说出“本地运行并不等于办公本无门槛”。\n+- 满足动机：有效，给原型、电商与三维草模用户一条可见流程。\n+- 立场框架：有效，站在想掌控模型与文件、又不想先学复杂节点系统的人一边。\n+- 传播入口：有效，3D、游戏原型与本地 AI 用户会因结果画面转发。\n+- 信念结构：有效，用 GPU、扩展差异和署名条款约束安装冲动。\n+- 骨架：一图转 3D 结果 → 桌面能力 → 四步链路 → 硬件许可边界 → 人群结论。通过。\n+\n+## dbs-hook\n+- 文稿超过 200 字，包含明确输入输出、官方模型扩展和硬件边界。\n+- 开头直接给“不会建模也能得到三维网格”的结果，但不声称一键成品；后文仍保留如何实现和适不适合的悬念。通过。\n+\n+## dbs-xhs-title\n+- 采用公式 #55“你到底要不要 [话题]”。\n+- 定稿：“你到底要不要在本地做 3D？”共 16 字；本地与硬件成本形成决策张力。通过。`,
    copy: `# 发布文案\n\n## 抖音\n\n- 标题：一张图片怎么在本地变成 3D 模型？｜Modly\n- 简介：Modly 把图片转 3D 的模型扩展、节点工作流、三维预览、平滑减面和导出放进一个桌面端，支持 Windows、Linux 与 Apple Silicon Mac，也提供本地 CLI 给脚本和 Agent 调用。注意：推理需要本地 GPU 和模型文件，不同扩展门槛不同。\n- 话题：#开源工具 #AI3D #本地AI #三维建模 #GitHub\n- 置顶评论：你会先拿人物、商品，还是游戏概念图试三维化？\n\n## 小红书\n\n- 标题：你到底要不要在本地做 3D？\n- 正文：Modly 把图片、模型扩展、节点工作流和三维预览放进一个桌面端，生成网格后还能平滑、减面和导出。它支持 Windows、Linux 与 Apple Silicon Mac，但需要自己的 GPU、内存和模型文件；不同扩展的门槛并不一样。\n- 话题：#开源工具 #AI3D #本地AI #三维建模 #GitHub项目\n- 互动评论：如果只能试一张图，你会选什么？\n\n说明：未安装、未实测；内容来自 2026-08-14 核验的官方仓库、README、Release、许可证和官方截图。`,
    assets: [
      [path.join(sourceRoot, "modly/app.png"), "official-app.png"],
      [path.join(sourceRoot, "modly/install-extension.png"), "official-install-extension.png"],
      [path.join(sourceRoot, "modly/install-models.png"), "official-install-models.png"]
    ]
  }
];

const candidateReport = `# 了不起的小超人｜开源装备雷达候选池（2026-08-14 早轮）

核验时间：2026-08-14（Asia/Shanghai）  
去重范围：2026-07-16—2026-08-14，核对现有 001—025 期；入选三项均未重复。  
热度入口：Agent Reach 的 GitHub Trending、GitHub API、官方 README、Release 与许可证；Exa 本轮版本协商失败，未把其失败结果作为事实来源。  
评分顺序：视觉结果 / 用户价值 / 新鲜与增长 / 新手成本 / 维护与许可。

| 候选 | 分类 | 分项 | 总分 | 决策 |
|---|---|---:|---:|---|
| cactus-compute/needle | Agent 自动化 | 24/24/20/12/15 | 95 | 制作 026 |
| altic-dev/FluidVoice | 开源效率 | 25/24/19/14/12 | 94 | 制作 027 |
| lightningpixel/modly | GitHub 热榜 | 25/23/19/12/13 | 92 | 制作 028 |
| macro-inc/macro | 开源效率 | 25/24/19/6/14 | 88 | 本轮上限；自托管链路重 |
| cloudflare/computer | Agent 自动化 | 18/23/20/8/15 | 84 | Preview，账号与平台门槛高 |
| PrimeIntellect-ai/prime-agent | Agent 自动化 | 18/23/20/8/15 | 84 | 视觉结果弱，执行权限风险高 |
| unslothai/unsloth | Agent 自动化 | 20/23/16/7/15 | 81 | 成熟项目，新鲜度较低 |
| kepano/obsidian-skills | 开源效率 | 20/22/10/14/15 | 81 | 当轮增长强但项目并不新 |
| NVIDIA-NeMo/Switchyard | Agent 自动化 | 14/22/20/8/15 | 79 | 受众偏开发者，视觉弱 |
| infiniflow/ragflow | Agent 自动化 | 20/23/16/5/15 | 79 | 部署重、成熟项目 |
| semantica-agi/semantica | Agent 自动化 | 17/20/19/9/14 | 79 | 概念密度高，50 秒难讲清 |
| holaboss-ai/holaOS | Agent 自动化 | 24/22/19/8/5 | 78 | 仓库许可元数据不明确 |
| Lightricks/LTX-2 | AI 视频 | 25/22/17/4/9 | 77 | 社区许可与硬件门槛重 |
| msitarzewski/agency-agents | Agent 自动化 | 18/21/10/13/15 | 77 | 新鲜度不足、同类内容多 |
| 3b1b/manim | GitHub 热榜 | 25/20/8/5/15 | 73 | 成熟工具，本轮新鲜度不足 |
| smicallef/spiderfoot | GitHub 热榜 | 20/18/8/11/15 | 72 | 安全题材且项目较老 |
| anthropics/skills | Agent 自动化 | 14/23/17/14/2 | 70 | 许可证无法从仓库元数据确认，不制作 |
| megadose/holehe | GitHub 热榜 | 12/12/2/10/11 | 47 | 最近推送停在 2024，不制作 |

## 入选核验摘要

- Needle 2：MIT，14MB / 约 28MB RAM 的端侧工具调用模型；日榜新增 768 Star，256-token 窗口与首次下载边界清楚。
- FluidVoice：核心 GPLv3，v1.6.8；日榜新增 187 Star，macOS 15+，中文模型路径与闭源增强层边界清楚。
- Modly：仓库标注 MIT 且附可见署名要求，v0.4.1；日榜新增 221 Star，Windows/Linux/Apple Silicon Mac 与本地 GPU 门槛清楚。
`;

writeNew(path.join(contentRoot, "xiaochao-radar-candidates-run-1.md"), candidateReport);

for (const episode of episodes) {
  const projectDir = path.join(contentRoot, `xiaochao-${episode.issue}-${episode.slug}`);
  ensureNew(projectDir);
  for (const sub of ["assets", "narration", "voice", "snapshots"]) {
    fs.mkdirSync(path.join(projectDir, sub), {recursive: true});
  }
  episode.narration.forEach((line, index) => {
    const labels = ["hook", "what", "workflow", "limit", "verdict"];
    writeNew(path.join(projectDir, "narration", `${String(index + 1).padStart(2, "0")}-${labels[index]}.txt`), line);
  });
  writeNew(path.join(projectDir, "sources.md"), episode.sources);
  writeNew(path.join(projectDir, "dbs-review.md"), episode.dbs);
  writeNew(path.join(projectDir, "package.md"), episode.copy);
  writeNew(path.join(outputRoot, "copy", `${Number(episode.issue)}-${episode.slug}.md`), episode.copy);
  writeNew(path.join(projectDir, "BRIEF.md"), `# BRIEF

- workflow: general-video
- flow: automation
- storyboard: no
- message: explain one verified open-source tool, its workflow, threshold, and boundary
- audience: Chinese creators and practical tool users
- destination: 1080×1920 vertical short video
- duration: 50—65 seconds, five narrated scenes
- visual: current warm editorial manual and yellow portrait IP
- audio: exact MiniMax voice and fixed look-beyond.mp3 mix
- constraints: no cover, platform, draft, publish, or unverifiable hands-on claim`);
  writeNew(path.join(projectDir, "STORYBOARD.md"), `# STORYBOARD

## Frame 1
- status: outline
- src: index.html#scene-1
- rules: staggered-reveal, slow-push
- beat: 官方结果画面 + “${episode.titleLines.join(" / ")}”问题。

## Frame 2
- status: outline
- src: index.html#scene-2
- rules: staggered-reveal, slow-push
- beat: 三个核心能力与官方素材。

## Frame 3
- status: outline
- src: index.html#scene-3
- rules: staggered-reveal, slow-push
- beat: 一条真实工作链路和步骤图。

## Frame 4
- status: outline
- src: index.html#scene-4
- rules: staggered-reveal, slow-push
- beat: 安装、平台、硬件或许可限制。

## Frame 5
- status: outline
- src: index.html#scene-5
- rules: staggered-reveal, slow-push
- beat: ${episode.score} 与适用人群结论。

Rhythm: hook-hold-explain-boundary-verdict。真实口播时长决定每一帧的停留时间。`);
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
  for (const [source, name] of episode.assets) copyNew(source, path.join(projectDir, "assets", name));
  copyNew(path.join(root, "assets/brand/xiaochao/avatar-yellow-800.png"), path.join(projectDir, "assets/ip.png"));
  copyNew(path.join(root, "content/2026-08-12/xiaochao-018-diagram-design/assets/Hiragino-Sans-GB.ttc"), path.join(projectDir, "assets/Hiragino-Sans-GB.ttc"));
  copyNew(path.join(root, "content/2026-08-12/xiaochao-018-diagram-design/assets/CobaltMono.ttf"), path.join(projectDir, "assets/CobaltMono.ttf"));
  copyNew(path.join(root, "content/2026-08-12/xiaochao-018-diagram-design/assets/gsap-3.14.2.min.js"), path.join(projectDir, "assets/gsap-3.14.2.min.js"));
}

console.log(JSON.stringify({date, episodes: episodes.map(({issue, slug, score}) => ({issue, slug, score}))}, null, 2));
