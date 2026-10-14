#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = path.resolve("<REPO>");
const TEMPLATE = path.join(ROOT, "videos/grok-image-2-editing");
const DATE = "2026-08-11";
const CHECKED = "2026-08-11 08:15 CST";
const CONFIG = JSON.parse(fs.readFileSync(path.join(ROOT, "workflows/chai-editor-single-topic-config.json"), "utf8"));
const BLUE = "#1f2be0";
const PAPER = "#f0ebde";
const RED = "#e33b2e";

const episodes = [
  {
    issue: "015",
    speed: 1.08,
    slug: "ai-job-targeting",
    series: "AI 帮你找工作 01",
    title: "先别让 AI 推荐岗位",
    coverTitle: ["AI 找工作", "先做这张表"],
    coverSub: "3 份真实 JD → 1 张职位证据表",
    core: "AI 找工作的第一步不是凭空推荐岗位，而是把真实职位要求和你的证据做成可比较的表。",
    why: "这是求职链路的起点。OpenAI 的求职指南把简历、目标职位、真实成果和不能让步的条件列为高杠杆输入，适合被翻译成中国求职者能立刻照做的职位证据表。",
    score: "84/100（常青实用题：热度 10/20、大陆影响 24/25、一句判断 19/20、证据 14/15、60 秒解释 12/15、风险 5/5）",
    segments: [
      "AI 找工作，第一步不是让它推荐岗位。先把你的经历、限制和三份真实招聘信息摆在一起。",
      "OpenAI 的求职指南建议，先整理当前简历、两到五份目标职位、八到十二条真实成果，再补上地点、薪资和行业等不能让步的条件。",
      "让 AI 把每份职位拆成四栏：每天做什么、必须会什么、加分项、你能拿什么证明。再比较三份，重复出现的要求才值得优先准备。",
      "别让它凭空判断你适合谁，更别上传身份证号、手机号和住址。岗位和公司信息，要回原链接核对。",
      "柴主编的判断：先做职位证据表，再决定投不投。AI 负责整理，你负责选择。"
    ],
    captions: [
      ["AI 找工作，第一步不是让它推荐岗位。", "先把你的经历、限制", "和三份真实招聘信息摆在一起。"],
      ["OpenAI 的求职指南建议，", "先整理当前简历、两到五份目标职位、", "八到十二条真实成果，", "再补上地点、薪资和行业等", "不能让步的条件。"],
      ["让 AI 把每份职位拆成四栏：", "每天做什么、必须会什么、", "加分项、你能拿什么证明。", "再比较三份，", "重复出现的要求才值得优先准备。"],
      ["别让它凭空判断你适合谁，", "更别上传身份证号、手机号和住址。", "岗位和公司信息，要回原链接核对。"],
      ["柴主编的判断：", "先做职位证据表，再决定投不投。", "AI 负责整理，你负责选择。"]
    ],
    frames: [
      { kind: "hook", title: "别先问 AI\n你适合什么", kicker: "AI JOB SEARCH · 01", badge: "先看证据", source: "SOURCE · OPENAI JOB SEARCH PLAYBOOK", items: ["经历", "限制", "真实岗位"] },
      { kind: "evidence", title: "先备齐 4 份输入", kicker: "OFFICIAL PLAYBOOK", source: "SOURCE · OPENAI · FEB 07 2026", items: ["当前简历", "2–5 份目标职位", "8–12 条真实成果", "不能让步的条件"] },
      { kind: "mechanism", title: "职位证据表", kicker: "ONE TABLE · FOUR COLUMNS", source: "METHOD · VERIFIED JOB DESCRIPTIONS", items: ["每天做什么", "必须会什么", "加分项", "我的证据"] },
      { kind: "action", title: "只比较 3 份", kicker: "REPEAT = PRIORITY", source: "ACTION · OPEN ORIGINAL LINKS", items: ["找重复要求", "标出证据空白", "决定先投谁"] },
      { kind: "verdict", title: "AI 负责整理\n你负责选择", kicker: "柴主编判断", source: "LIMIT · REMOVE PERSONAL IDENTIFIERS", items: ["不上传证件号", "不上传住址", "岗位信息回原站核对"] }
    ],
    sources: [
      ["OpenAI Forum｜ChatGPT Job Search Playbook", "https://forum.openai.com/en/public/blogs/chatgpt-job-search-playbook-2026-02-06", "2026-02-07", "建议集中整理当前简历、2–5 份目标职位、8–12 条真实成果和不可妥协条件；职位建议必须能回到真实成果证据。", "这是官方实践指南，不是就业结果保证。"],
      ["OpenAI Academy｜How to Use ChatGPT to Land Your Dream Job", "https://academy.openai.com/en/public/clubs/higher-education-05x4z/blogs/how-to-use-chatgpt-to-land-your-dream-job-2026-04-22", "2026-04-23", "建议先让 ChatGPT 提问，再把职位描述翻译成日常工作、必需能力、加分项和可突出经历。", "示例主要面向学生和英语语境，国内岗位名称与招聘规则需回原站核对。"],
      ["OpenAI Help｜Data Controls FAQ", "https://help.openai.com/en/articles/7730893-data-controls-faq", "持续更新", "可关闭‘Improve the model for everyone’；Temporary Chat 不进历史、不创建记忆，也不用于训练，并在 30 天后删除。", "关闭训练不等于可以上传身份证号、住址等不必要的敏感信息。"]
    ],
    douyinTitle: "AI 找工作，先别让它推荐岗位｜求职01",
    xhsTitle: "AI 找工作，先做这张职位证据表",
    xhsFormula: "#28 数字 + 结果（方法型）",
    pinned: "复制提示词：把这 3 份 JD 拆成‘日常工作/必须会/加分项/我的证据’四栏；没有证据请标空，不要替我补。"
  },
  {
    issue: "016",
    speed: 1.05,
    slug: "ai-resume-evidence",
    series: "AI 帮你找工作 02",
    title: "别让 AI 代写整份简历",
    coverTitle: ["AI 改简历", "只改 3 件事"],
    coverSub: "证据前移 · 空话删掉 · 结果写清",
    core: "AI 改简历的正确用法是把真实证据摆对位置，不是代写一份看起来漂亮的经历。",
    why: "求职者最容易把 AI 当代笔，导致内容泛化甚至失真。哈佛职业中心明确建议从本人草稿出发，让 AI 做编辑而非主笔，能形成一条清晰、可执行又低风险的判断。",
    score: "87/100（常青实用题：热度 12/20、大陆影响 25/25、一句判断 20/20、证据 14/15、60 秒解释 12/15、风险 4/5）",
    segments: [
      "让 AI 写完整简历，通常只会得到一份很顺、也很像假的文本。",
      "哈佛职业中心建议，从你自己的草稿开始；AI 适合改措辞、找职位关键词，不该成为主笔。",
      "最实用的做法，是做一张证据对照表：左边放职位要求，右边只放你真实做过的项目、动作和结果。没有数字就标待补，禁止猜。",
      "再让 AI 只改三件事：把最相关经历前移，删掉空话，把任务写成动作和结果。每一行你都必须能在面试里讲清。",
      "柴主编的判断：简历不是让 AI 代写，是让它帮你把证据摆对位置。编出来的亮点，迟早会在追问里露馅。"
    ],
    captions: [
      ["让 AI 写完整简历，", "通常只会得到一份很顺、", "也很像假的文本。"],
      ["哈佛职业中心建议，", "从你自己的草稿开始；", "AI 适合改措辞、找职位关键词，", "不该成为主笔。"],
      ["最实用的做法，是做一张证据对照表：", "左边放职位要求，", "右边只放你真实做过的项目、动作和结果。", "没有数字就标待补，禁止猜。"],
      ["再让 AI 只改三件事：", "把最相关经历前移，删掉空话，", "把任务写成动作和结果。", "每一行你都必须能在面试里讲清。"],
      ["柴主编的判断：", "简历不是让 AI 代写，", "是让它帮你把证据摆对位置。", "编出来的亮点，迟早会在追问里露馅。"]
    ],
    frames: [
      { kind: "hook", title: "整份代写\n最像模板", kicker: "AI JOB SEARCH · 02", badge: "很顺 ≠ 可信", source: "SOURCE · HARVARD CAREER SERVICES", items: ["漂亮", "泛化", "难追问"] },
      { kind: "evidence", title: "AI 只能当编辑", kicker: "START WITH YOUR DRAFT", source: "SOURCE · HARVARD FAS · DEC 11 2023", items: ["本人草稿", "职位关键词", "建议修改", "逐行核对"] },
      { kind: "mechanism", title: "职位要求 ↔ 我的证据", kicker: "EVIDENCE MATRIX", source: "METHOD · NO INVENTED METRICS", items: ["真实项目", "具体动作", "可见结果", "缺失标待补"] },
      { kind: "action", title: "只改 3 件事", kicker: "EDIT · DO NOT GHOSTWRITE", source: "ACTION · EVERY LINE MUST BE DEFENSIBLE", items: ["相关经历前移", "空话删掉", "动作 + 结果"] },
      { kind: "verdict", title: "把证据\n摆对位置", kicker: "柴主编判断", source: "LIMIT · REMOVE PERSONAL / PROPRIETARY DATA", items: ["不编数字", "不编职位", "不编项目范围"] }
    ],
    sources: [
      ["Harvard FAS MCS｜AI for Resumes and Cover Letters", "https://careerservices.fas.harvard.edu/ai-resumes-and-cover-letters/", "2023-12-11", "生成式 AI 可用于编辑、提炼职位关键词和改进已有内容，但不应成为主要作者；应从本人草稿开始，逐行确认真实与可讲述。", "哈佛学生指南可提供原则，但不同单位的 AI 使用规则仍需单独查看。"],
      ["OpenAI Academy｜How to Use ChatGPT to Land Your Dream Job", "https://academy.openai.com/en/public/clubs/higher-education-05x4z/blogs/how-to-use-chatgpt-to-land-your-dream-job-2026-04-22", "2026-04-23", "建议缺少指标时标记‘ADD DETAIL’，而不是虚构；强调本人提供真实经历，AI 负责澄清和对齐。", "这是方法建议，不代表使用 AI 会提升面试率。"],
      ["Indeed Career Guide｜How To Tailor Your Resume To a Job Description", "https://www.indeed.com/career-advice/resumes-cover-letters/tailoring-resume", "持续更新", "建议按职位描述的优先级组织简历，把最相关的能力和经历放在前面，并在语境中使用职位关键词。", "招聘流程与 ATS 实现各异，不宣称关键词能保证通过。"],
      ["OpenAI Help｜Data Controls FAQ", "https://help.openai.com/en/articles/7730893-data-controls-faq", "持续更新", "说明训练开关与 Temporary Chat；支持用户降低数据留存与训练风险。", "职业中心仍建议不要分享个人或专有数据。"]
    ],
    douyinTitle: "AI 改简历，只让它改这 3 件事｜求职02",
    xhsTitle: "AI 改简历，只改这 3 件事",
    xhsFormula: "#28 数字 + 结果（方法型）",
    pinned: "复制提示词：按这份 JD 审阅我的简历，只做‘相关经历前移/删空话/任务改成动作+结果’；事实不变，缺信息标待补。"
  },
  {
    issue: "017",
    speed: 1.00,
    slug: "ai-interview-practice",
    series: "AI 帮你找工作 03",
    title: "把 AI 当面试陪练",
    coverTitle: ["AI 练面试", "别背标准答案"],
    coverSub: "一次一题 · 连续追问 · 只看证据",
    core: "AI 最适合当高频面试陪练，通过连续追问暴露证据漏洞，而不是提供逐字标准答案。",
    why: "面试准备是 AI 最能提供低成本、高频重复帮助的场景。哈佛和伯克利职业中心都支持用 AI 生成问题、模拟面试和反馈，同时明确反对背逐字稿。",
    score: "89/100（常青实用题：热度 13/20、大陆影响 25/25、一句判断 20/20、证据 15/15、60 秒解释 12/15、风险 4/5）",
    segments: [
      "面试前最没用的，是让 AI 给你一份标准答案，然后背下来。",
      "哈佛职业中心建议，用 AI 生成可能的问题、模拟追问，再按 STAR 检查答案；但别背逐字稿。",
      "先整理六个真实故事：一次解决难题、一次协作、一次冲突、一次失败、一次赶进度、一次学会新东西。",
      "让 AI 一次只问一题，连续追问为什么、你具体做了什么、结果怎么证明。答完只让它评价清楚、简洁、证据三个维度。",
      "柴主编的判断：AI 最适合当陪练，不适合当替身。练到换个问法，你也能说清同一段经历，才算准备好。"
    ],
    captions: [
      ["面试前最没用的，", "是让 AI 给你一份标准答案，", "然后背下来。"],
      ["哈佛职业中心建议，", "用 AI 生成可能的问题、模拟追问，", "再按 STAR 检查答案；", "但别背逐字稿。"],
      ["先整理六个真实故事：", "一次解决难题、一次协作、一次冲突、", "一次失败、一次赶进度、", "一次学会新东西。"],
      ["让 AI 一次只问一题，", "连续追问为什么、你具体做了什么、", "结果怎么证明。", "答完只让它评价清楚、简洁、证据三个维度。"],
      ["柴主编的判断：", "AI 最适合当陪练，不适合当替身。", "练到换个问法，你也能说清同一段经历，", "才算准备好。"]
    ],
    frames: [
      { kind: "hook", title: "标准答案\n最经不起追问", kicker: "AI JOB SEARCH · 03", badge: "别背逐字稿", source: "SOURCE · HARVARD CAREER SERVICES", items: ["背稿", "换题", "卡住"] },
      { kind: "evidence", title: "AI 适合做陪练", kicker: "GENERATE · FOLLOW UP · FEEDBACK", source: "SOURCE · HARVARD FAS · BERKELEY", items: ["生成问题", "模拟追问", "STAR 复盘", "不要背稿"] },
      { kind: "mechanism", title: "6 个真实故事", kicker: "YOUR STORY BANK", source: "METHOD · REAL EXPERIENCE ONLY", items: ["难题 / 协作", "冲突 / 失败", "赶工 / 学习"] },
      { kind: "action", title: "一次只问一题", kicker: "FOLLOW-UP LOOP", source: "ACTION · CLARITY / CONCISION / EVIDENCE", items: ["为什么？", "你做了什么？", "怎么证明结果？"] },
      { kind: "verdict", title: "换个问法\n也能说清", kicker: "柴主编判断", source: "LIMIT · VERIFY COMPANY FACTS", items: ["不背逐字稿", "不用 AI 替答", "事实回官方核对"] }
    ],
    sources: [
      ["Harvard FAS MCS｜AI for Interviews and Offers", "https://careerservices.fas.harvard.edu/ai-interviews-and-offers/", "2023-12-11", "建议用 AI 做背景初查、生成问题、模拟追问，并用 STAR 结构评估答案；明确提醒不要背逐字稿，答案要保持本人声音。", "生成式 AI 可能给出错误公司信息，需用可信来源复核。"],
      ["UC Berkeley Career Engagement｜Utilizing Generative AI", "https://career.berkeley.edu/prepare-for-success/utilizing-generative-ai/", "2023-07-24", "AI 可生成特定岗位常见问题、测试回答并提供反馈；求职者仍应独立判断，不能在招聘过程中违规使用实时辅助。", "雇主对 AI 使用有不同规则，面试现场不得默认可用。"],
      ["OpenAI Forum｜ChatGPT Job Search Playbook", "https://forum.openai.com/en/public/blogs/chatgpt-job-search-playbook-2026-02-06", "2026-02-07", "建议建立 STAR 故事库，语音模拟真实面试节奏，一次一题，并从清晰、简洁和影响证据上复盘。", "官方指南是练习方法，不是面试成功率承诺。"],
      ["OpenAI Academy｜How to Use ChatGPT to Land Your Dream Job", "https://academy.openai.com/en/public/clubs/higher-education-05x4z/blogs/how-to-use-chatgpt-to-land-your-dream-job-2026-04-22", "2026-04-23", "建议按招聘者、用人经理等不同角色做模拟，跟随回答追问，口头练习比只看文本更接近真实面试。", "示例偏英语与学生招聘，国内岗位需结合真实流程。"]
    ],
    douyinTitle: "AI 练面试，别再背标准答案｜求职03",
    xhsTitle: "AI 练面试，别背标准答案",
    xhsFormula: "#17 警告 + 努力白费（纠错型）",
    pinned: "复制提示词：按这份 JD 面试我，一次只问一题；我的回答含糊时追问‘我做了什么/为什么/结果如何证明’，最后只评清楚、简洁、证据。"
  }
];

function write(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, value.endsWith("\n") ? value : `${value}\n`);
}

function clean(text) { return text.replace(/\s+/gu, ""); }
function esc(text) { return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"); }

function sourcesMd(ep) {
  const blocks = ep.sources.map((s, i) => `### ${i + 1}. ${s[0]}\n\n- 链接：${s[1]}\n- 发布/更新：${s[2]}\n- 确认事实：${s[3]}\n- 限制：${s[4]}\n- 核验时间：${CHECKED}`).join("\n\n");
  return `# episode-${ep.issue}｜${ep.title}｜来源与核验\n\n- 节目日期：${DATE}（Asia/Shanghai）\n- 选题类型：常青实用方法，不做新闻播报\n- 系列：${ep.series}\n- 核心判断：${ep.core}\n- 评分：${ep.score}\n\n## 选题理由\n\n${ep.why}\n\n## 主要来源\n\n${blocks}\n\n## 事实与判断边界\n\n- 不声称 AI 能保证获得面试、通过 ATS 或拿到 offer。\n- 不声称使用过求职者的真实账号或代替用户申请职位。\n- 职位、公司、薪资和招聘流程信息必须回到原始招聘页面与雇主官网核对。\n- 简历和面试内容只使用本人真实经历；缺失数字、职位、工具、日期或项目范围时明确标记待补。\n- 不上传身份证号、住址、手机号、银行卡、他人信息或雇主专有资料。\n\n## 调研通道\n\n- agent-reach Doctor：Exa 配置存在但沙箱内离线；经授权联网后 Exa 与 Jina Reader 成功。\n- 小红书、B站、Reddit、Twitter、LinkedIn 登录后端在本次环境不可用，因此没有据此虚构平台热度。\n- 选题依据以 OpenAI 官方指南、大学职业中心和招聘平台公开指南为主。\n`;
}

function scriptMd(ep) {
  return `# SCRIPT｜${ep.title}\n\n**Series:** ${ep.series}  \n**Voice:** MiniMax \`male-qn-qingse\`  \n**Voice settings:** \`speech-2.8-hd\` · speed ${ep.speed.toFixed(2)} · calm  \n**Voice direction:** 冷静、直接、像认真帮人改方案的科技主编；不喊口号，不承诺求职结果。\n\n${ep.segments.map((s, i) => `## Line ${i + 1}\n\n${s}`).join("\n\n")}\n`;
}

function storyboardMd(ep) {
  const frames = ep.frames.map((f, i) => `## Frame ${i + 1} — ${f.title.replace("\n", " / ")}\n\n- type: ${f.kind}\n- voiceover: "${ep.segments[i]}"\n- duration: pending MiniMax audio\n- transition_in: ${i === 0 ? "cut" : i === 4 ? "blur-crossfade" : "push-slide LEFT"}\n- status: animated\n- src: compositions/frames/${String(i + 1).padStart(2, "0")}-${f.kind}.html\n- focal: ${f.title.replace("\n", " / ")}\n- roles: ${f.items.join(" · ")}\n- source: ${f.source}\n\nnarrativeRole: ${["用反常识判断否定常见误用。", "用公开指南建立方法事实底座。", "把方法翻译成一张可照做的流程图。", "给出普通求职者今天就能执行的动作。", "补齐隐私、真实性与核验边界，并给出柴主编判词。"][i]}\nkeyMessage: ${i === 4 ? ep.core : ep.segments[i]}\n`).join("\n");
  return `---\nformat: 1080x1920\nduration: pending\nmessage: "${ep.core}"\narc: how-to\naudience: "正在找工作、转岗或准备面试的中国大陆普通用户"\nmode: autonomous\nmusic: none\n---\n\n## Video direction\n\n复用 Cobalt Grid 柴主编编辑部视觉：奶油网格纸、钴蓝主色、红色批注章。画面只展示自制证据卡和流程图，不伪造产品界面。正文保持在 y=1380 以上，SOURCE 固定在 y=1388；柴犬头像与逐句字幕严格按配置放置。\n\n${frames}`;
}

function dbsMd(ep) {
  const hook = ep.segments[0];
  return `# 文案门禁｜episode-${ep.issue}\n\n## dbs-hook\n\n- 体裁：45–60 秒实用型短视频口播。\n- 内容完整性：${clean(ep.segments.join("")).length} 个非空白字符；有公开指南锚点、单一机制、可执行动作和限制。\n- 当前开头：\`${hook}\`\n- 诊断：独立建立“AI 帮你找工作”的话题，用常见误用制造反差；没有用虚构数据或夸张结果做钩子，正文能够兑现。\n- 结论：通过。\n\n## dbs-resonate\n\n- 所有主张：AI 能整理求职材料；真实经历必须由本人提供；公开信息要回原站核对；${ep.core}\n- 唯一核心机制：${ep.core}\n- 沉默解除：有效。说出求职者最容易做错的那一步，而不是制造“AI 一键上岸”的幻觉。\n- 满足动机：有效。观众能直接复制一个表格、三步编辑法或陪练提示词。\n- 立场框架：有效。站在普通求职者的时间、隐私和真实性一边。\n- 传播入口：有效。正在求职、转岗或帮朋友改材料的人有明确转发动机。\n- 信念结构：有效。确认“AI 帮整理，人负责事实与选择”。\n- 结论：核心明确，没有被工具介绍、行业新闻或产品宣传稀释。\n\n## dbs-ai-check\n\n- 体裁识别：短视频口播。\n- 弱信号：首句有一次反差判断，属于体裁需要，未重复滥用。\n- 未命中：日报腔、连接词堆叠、虚假权威、匀速排比、三段式空话、逐段金句、伪亲测、营销绝对化。\n- 结论：没有阻断生产的 AI 写作指纹。\n\n## humanizer-zh\n\n- 保留口语短句，删除“赋能、精准匹配、全面提升、求职效率革命”等宣传词。\n- 把抽象的“人岗匹配”改成可见的表、证据和追问。\n- 事实、建议和限制分开，不把职业中心建议写成必然结果。\n- 评分：直接性 10/10；节奏 9/10；信任度 10/10；真实性 9/10；精炼度 9/10；总分 47/50。\n\n## dbs-xhs-title\n\n- 采用：\`${ep.xhsTitle}\`\n- 公式：${ep.xhsFormula}\n- 张力：含明确对象“AI/求职步骤”和行动缺口；不承诺面试率、offer 或薪资。\n- 字数：${clean(ep.xhsTitle).length}，不超过 20 字。\n\n## 最终门禁\n\n通过。脚本只讲一个机制，不声称亲测，不虚构求职结果；可以进入 MiniMax 配音。\n`;
}

function publishMd(ep) {
  return `# 发布文案｜episode-${ep.issue}\n\n## 抖音\n\n**标题**  \n${ep.douyinTitle}\n\n**简介**  \n${ep.core} 这期只给一个能立刻照做的方法，并保留真实性、隐私和原链接核验边界。\n\n**话题**  \n#人工智能 #AI求职 #找工作 #职场 #效率工具 #柴主编\n\n**置顶评论**  \n${ep.pinned}\n\n## 小红书\n\n**标题**  \n${ep.xhsTitle}\n\n**正文**  \nAI 真能帮你找工作，但最有用的地方不是“替你做决定”，而是把真实材料整理清楚，再陪你反复检查。\n\n这期的方法：${ep.core}\n\n可以直接从置顶评论复制提示词。记得删掉身份证号、手机号、住址和不该外传的公司资料；职位、公司和薪资信息回原链接核对。\n\n**话题**  \n#AI工具 #AI求职 #简历 #面试 #职场成长 #柴主编\n\n**置顶评论**  \n${ep.pinned}\n\n## AI 内容声明\n\n部分画面及配音由 AI 辅助生成；方法与限制依据 OpenAI 官方资料、大学职业中心和公开求职指南核验。视频不保证获得面试或 offer，不代替职业顾问、雇主规则与个人判断。\n\n## 发布前检查清单\n\n- [ ] 视频为 1080×1920、45–60 秒、H.264 + AAC。\n- [ ] 逐句字幕、口播、柴犬嘴型同步，停顿闭嘴。\n- [ ] 每个方法与限制都能在 sources.md 找到来源。\n- [ ] 无身份证号、手机号、住址、公司专有资料或伪造经历。\n- [ ] 三种封面尺寸正确、独立排版、标题逐字准确。\n- [ ] 勾选平台“内容由 AI 生成”。\n- [ ] 不自动发布；发布前人工最终确认。\n`;
}

function coverPromptsMd(ep) {
  return `# 封面设计说明｜episode-${ep.issue}\n\n- 参考主体：复用项目柴犬 IP \`chai-editor-avatar.png\`，不生成陌生真人。\n- 风格：阿囤囤“黑底效率工作流风”与“教程清单风”的确定性代码排版版本。\n- 主标题：\`${ep.coverTitle.join(" / ")}\`\n- 副标题：\`${ep.coverSub}\`\n- 标题配色：奶油白 #F0EBDE，关键词浅黄 #FDFFA7，深海军蓝描边；绿色勾选只用于行动清单。\n- 说明：为保证中文逐字准确和三比例安全区，本期采用 HTML/CSS 原生排版，不调用生成式位图模型；三种比例分别重排，不裁切、不拉伸。\n\n## 9:16\n\n柴犬位于中下部，标题占上半屏；右侧三张求职卡片纵向错位，底部保留抖音安全区。\n\n## 3:4\n\n柴犬位于右下，主标题左上两行；三条绿色勾选清单在左下，适配小红书缩略图。\n\n## 4:3\n\n柴犬位于右侧，主标题左侧两行；流程卡横向展开，标题与角色均在横版安全区。\n\n## 负面约束\n\n不使用平台 Logo、水印、陌生真人、多手、伪产品截图、错误中文、拉伸头像或裁切移植。\n`;
}

function projectBrief(ep) {
  return `---\nworkflow: faceless-explainer\nflow: automation\nstoryboard: no\nmessage: "${ep.core}"\ndestination: douyin\naspect: 1080x1920\nlanguage: zh-CN\naudience: "正在找工作、转岗或准备面试的中国大陆普通用户"\nlength: 54s\nangle: how-to\nnarration: yes\nvoice: male-qn-qingse\nstyle_preset: cobalt-grid\n---\n\n## Intent\n\n制作“${ep.series}”第 ${ep.issue} 期。${ep.core}\n\n## Customizations\n\n- MiniMax 国内 API 普通话男声，冷静实用的科技编辑语气。\n- 复用 Cobalt Grid 视觉和固定柴犬口播栏。\n- 五段视觉：反常识判断、公开指南证据、方法机制、行动清单、限制与判词。\n- 不生成伪产品界面，不声称替用户申请职位。\n\n## Notes\n\n- 不承诺面试、offer、薪资或 ATS 通过率。\n- 不上传个人敏感信息与公司专有信息。\n- 自动化已明确要求高质量 MP4，无需再次等待渲染确认；不得自动发布。\n`;
}

function frameHtml(ep, f, index) {
  const id = `${String(index + 1).padStart(2, "0")}-${f.kind}`;
  const p = `f${id}`;
  const items = f.items.map((item, n) => `<div id="${p}-item-${n}" class="item"><span>${String(n + 1).padStart(2, "0")}</span><b>${esc(item)}</b></div>`).join("");
  const splitTitle = f.title.split("\n").map(x => `<div>${esc(x)}</div>`).join("");
  const duration = 20;
  const kindCss = {
    evidence: `.hero{font-size:105px}.items{grid-template-columns:1fr 1fr}.item{grid-template-columns:76px 1fr}.item b{font-size:33px}`,
    mechanism: `.hero{font-size:122px}.items{grid-template-columns:1fr 1fr}.item{height:150px;grid-template-columns:80px 1fr}.item b{font-size:35px}.item:nth-child(odd){margin-right:22px}.item:nth-child(even){margin-left:22px}`,
    action: `.hero{font-size:132px}.item{height:124px}.item b{font-size:45px}.stamp{top:1170px}`,
    verdict: `.hero{font-size:120px}.items{grid-template-columns:repeat(3,1fr)}.item{height:170px;display:flex;flex-direction:column;justify-content:center;gap:12px;padding:22px}.item span{display:block;height:auto;background:none;color:#c63328;font-size:26px;font-weight:800}.item b{padding:0;font-size:30px;text-align:center}.stamp{top:1120px}`
  }[f.kind] || "";
  return `<template>
  <div id="root" data-composition-id="${id}" data-start="0" data-width="1080" data-height="1920" data-duration="${duration}">
    <div id="${p}-ground" class="clip ground" data-start="0" data-duration="${duration}" data-track-index="0"></div>
    <div id="${p}-stage" class="clip stage" data-start="0" data-duration="${duration}" data-track-index="1">
      <header><span>柴主编｜只讲一件事</span><b>${esc(ep.series)}</b></header>
      <div id="${p}-kicker" class="kicker">${esc(f.kicker)}</div>
      <section id="${p}-hero" class="hero">${splitTitle}</section>
      <div id="${p}-rule" class="rule"></div>
      <section id="${p}-items" class="items" data-layout-allow-overlap>${items}</section>
      ${f.badge ? `<div id="${p}-badge" class="badge">${esc(f.badge)}</div>` : ""}
      <div id="${p}-stamp" class="stamp">${index === 4 ? "DO IT YOURSELF" : ["QUESTION", "EVIDENCE", "METHOD", "ACTION"][index]}</div>
      <footer><span>${esc(f.source)}</span><span>${String(index + 1).padStart(2, "0")}</span></footer>
    </div>
  </div>
  <style>
    @font-face{font-family:CobaltSans;src:url("assets/fonts/CobaltSans.ttc") format("truetype")}
    @font-face{font-family:CobaltSerif;src:url("assets/fonts/CobaltSerif.ttc") format("truetype")}
    @font-face{font-family:CobaltMono;src:url("assets/fonts/CobaltMono.ttf") format("truetype")}
    *{box-sizing:border-box}#root{position:relative;width:1080px;height:1920px;overflow:hidden;color:${BLUE};font-family:CobaltSans,sans-serif}
    .ground{position:absolute;inset:0;background-color:${PAPER};background-image:linear-gradient(rgba(31,43,224,.09) 1px,transparent 1px),linear-gradient(90deg,rgba(31,43,224,.09) 1px,transparent 1px);background-size:38px 38px}
    .stage{position:absolute;inset:0;padding:58px 64px 430px;overflow:hidden}.stage:after{content:"";position:absolute;right:0;top:200px;width:180px;height:780px;background:repeating-linear-gradient(90deg,${BLUE} 0 8px,transparent 8px 28px);opacity:.08;z-index:0}
    header,footer{position:relative;z-index:3;height:62px;border-top:2px solid ${BLUE};border-bottom:2px solid ${BLUE};display:flex;align-items:center;justify-content:space-between;font:24px CobaltMono;letter-spacing:.05em}header b{font-size:19px}
    .kicker{position:relative;z-index:3;margin-top:84px;font:25px CobaltMono;letter-spacing:.14em}.hero{position:relative;z-index:3;margin-top:36px;max-width:900px;font:112px/1.08 CobaltSerif;letter-spacing:-.04em}.hero>div+div{margin-left:66px;margin-top:10px}
    .rule{position:relative;z-index:3;margin-top:70px;height:9px;width:88%;background:${BLUE};transform-origin:left center}.items{position:relative;z-index:3;margin-top:48px;display:grid;gap:18px;max-width:870px}.item{height:104px;border:3px solid ${BLUE};background:${PAPER};display:grid;grid-template-columns:106px 1fr;align-items:center}.item span{height:100%;display:grid;place-items:center;background:${BLUE};color:${PAPER};font:25px CobaltMono}.item b{padding:0 30px;font-size:42px;font-weight:700}.badge{position:absolute;z-index:5;right:64px;top:420px;background:${RED};color:white;padding:18px 24px;font-size:34px;font-weight:800;transform:rotate(-4deg)}
    .stamp{position:absolute;z-index:4;right:92px;top:1150px;border:7px solid ${RED};color:${RED};padding:16px 22px;font:30px CobaltMono;letter-spacing:.1em;transform:rotate(-6deg)}
    footer{position:absolute;z-index:6;left:64px;right:64px;bottom:470px;height:64px;font-size:18px;background:${PAPER}}footer span:first-child{max-width:830px;white-space:nowrap;overflow:hidden}
    ${kindCss}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    (()=>{window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});window.__timelines["${id}"]=tl;
      tl.fromTo("#${p}-kicker",{x:-120,opacity:0},{x:0,opacity:1,duration:.55,ease:"power3.out"},.15)
        .fromTo("#${p}-hero>div",{y:90,opacity:0},{y:0,opacity:1,duration:.7,stagger:.28,ease:"power4.out"},.6)
        .fromTo("#${p}-rule",{scaleX:0},{scaleX:1,duration:.65,ease:"power3.inOut"},1.55)
        .fromTo("#${p}-items .item",{x:(i)=>i%2?-120:120},{x:0,duration:.62,stagger:.42,ease:"power3.out"},2.15)
        .fromTo("#${p}-stamp",{scale:0,rotation:-18,opacity:0},{scale:1,rotation:-6,opacity:1,duration:.55,ease:"back.out(1.8)"},4.2)
        ${f.badge ? `.fromTo("#${p}-badge",{y:-70,opacity:0},{y:0,opacity:1,duration:.45,ease:"power3.out"},5.1)` : ""};
    })();
  </script>
</template>`;
}

function coverHtml(ep, width, height, ratioName) {
  const vertical = height > width;
  const is34 = ratioName === "xiaohongshu-3x4";
  const titleSize = vertical ? (is34 ? 132 : 150) : 116;
  const avatar = vertical ? (is34 ? 420 : 470) : 420;
  const avatarLeft = vertical ? width - avatar - 40 : width - avatar - 85;
  const avatarTop = vertical ? (is34 ? 760 : 1110) : 500;
  const cards = ep.frames[3].items.slice(0,3).map((x,i)=>`<div class="cover-card"><i>✓</i><b>${esc(x)}</b></div>`).join("");
  return `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
  @font-face{font-family:CobaltSans;src:url("../assets/fonts/CobaltSans.ttc")}@font-face{font-family:CobaltSerif;src:url("../assets/fonts/CobaltSerif.ttc")}
  *{box-sizing:border-box}html,body{margin:0;width:${width}px;height:${height}px;overflow:hidden}body{background:#071337;color:${PAPER};font-family:CobaltSans,"PingFang SC",sans-serif}
  .grid{position:absolute;inset:0;background-image:linear-gradient(rgba(96,165,250,.11) 1px,transparent 1px),linear-gradient(90deg,rgba(96,165,250,.11) 1px,transparent 1px);background-size:46px 46px}.glow{position:absolute;inset:0;background:radial-gradient(circle at 82% 62%,rgba(31,43,224,.6),transparent 36%),linear-gradient(135deg,transparent 60%,rgba(253,255,167,.12))}
  .series{position:absolute;left:${vertical?58:70}px;top:${vertical?60:52}px;padding:12px 18px;background:${BLUE};border:3px solid ${PAPER};font-size:${vertical?28:26}px;font-weight:900;letter-spacing:.06em}.issue{position:absolute;right:${vertical?52:64}px;top:${vertical?58:50}px;font:800 ${vertical?34:30}px CobaltSans}
  .title{position:absolute;left:${vertical?54:68}px;top:${vertical?170:154}px;z-index:8;width:${vertical?width-108:760}px;font:900 ${titleSize}px/.9 CobaltSans;letter-spacing:-.07em;text-shadow:0 8px 0 #000,5px 0 0 #000,-5px 0 0 #000,0 -5px 0 #000}.title .accent{color:#fdffa7}.title div+div{margin-top:18px}
  .sub{position:absolute;z-index:8;left:${vertical?58:72}px;top:${vertical?(is34?535:615):430}px;max-width:${vertical?730:720}px;padding:14px 20px;background:#e33b2e;border:4px solid #000;font-size:${vertical?34:31}px;font-weight:900;transform:rotate(-2deg)}
  .avatar-ring{position:absolute;z-index:6;left:${avatarLeft}px;top:${avatarTop}px;width:${avatar}px;height:${avatar}px;border:12px solid #fdffa7;border-radius:50%;background:${BLUE};box-shadow:0 0 0 10px #000;overflow:hidden}.avatar-ring img{width:100%;height:100%;object-fit:cover}
  .cards{position:absolute;z-index:9;left:${vertical?58:72}px;top:${vertical?(is34?850:1120):590}px;width:${vertical?(is34?560:610):740}px;display:grid;gap:${vertical?18:16}px}.cover-card{min-height:${vertical?94:86}px;display:flex;align-items:center;gap:20px;background:${PAPER};border:5px solid #000;color:#071337;padding:16px 22px;font-size:${vertical?34:31}px;font-weight:900;box-shadow:9px 9px 0 ${BLUE}}.cover-card i{display:grid;place-items:center;flex:none;width:50px;height:50px;background:#29a86b;color:white;border:4px solid #000;font-style:normal;font-size:33px}
  .arrow{position:absolute;z-index:10;right:${vertical?280:420}px;top:${vertical?(is34?1040:1410):700}px;color:#fdffa7;font-size:${vertical?130:120}px;font-weight:900;transform:rotate(18deg)}.footer{position:absolute;z-index:10;left:${vertical?58:72}px;right:${vertical?58:72}px;bottom:${vertical?(is34?54:190):54}px;border-top:4px solid ${PAPER};padding-top:16px;display:flex;justify-content:space-between;font-size:${vertical?26:25}px;font-weight:800;letter-spacing:.08em}
  </style></head><body><div class="grid"></div><div class="glow"></div><div class="series">柴主编｜AI 帮你找工作</div><div class="issue">EP.${ep.issue}</div><div class="title"><div>${esc(ep.coverTitle[0])}</div><div class="accent">${esc(ep.coverTitle[1])}</div></div><div class="sub">${esc(ep.coverSub)}</div><div class="avatar-ring"><img src="../assets/brand/chai-editor-avatar.png"></div><div class="cards">${cards}</div><div class="arrow">↘</div><div class="footer"><span>只讲一件事</span><span>不代投 · 不编经历</span></div></body></html>`;
}

function prepare(ep) {
  const content = path.join(ROOT, `content/episode-${ep.issue}`);
  const project = path.join(ROOT, `videos/${ep.slug}`);
  if (fs.existsSync(content) || fs.existsSync(project)) throw new Error(`Refusing to overwrite episode ${ep.issue}`);
  fs.mkdirSync(content, { recursive: false });
  fs.mkdirSync(project, { recursive: false });
  for (const dir of ["assets/fonts", "assets/brand", "assets/voice", "compositions/frames", "covers", "bin", "renders", "snapshots"]) fs.mkdirSync(path.join(project, dir), { recursive: true });
  for (const file of fs.readdirSync(path.join(TEMPLATE, "assets/fonts"))) fs.copyFileSync(path.join(TEMPLATE, "assets/fonts", file), path.join(project, "assets/fonts", file));
  fs.copyFileSync(path.join(TEMPLATE, "assets/brand/chai-editor-avatar.png"), path.join(project, "assets/brand/chai-editor-avatar.png"));
  fs.copyFileSync(path.join(TEMPLATE, "bin/ffmpeg"), path.join(project, "bin/ffmpeg"));
  fs.copyFileSync(path.join(TEMPLATE, "bin/ffprobe"), path.join(project, "bin/ffprobe"));
  fs.chmodSync(path.join(project, "bin/ffmpeg"), 0o755); fs.chmodSync(path.join(project, "bin/ffprobe"), 0o755);
  fs.copyFileSync(path.join(TEMPLATE, "AGENTS.md"), path.join(project, "AGENTS.md"));
  write(path.join(content, "sources.md"), sourcesMd(ep));
  write(path.join(content, "SCRIPT.md"), scriptMd(ep));
  write(path.join(content, "narration.txt"), ep.segments.join("\n\n"));
  write(path.join(content, "STORYBOARD.md"), storyboardMd(ep));
  write(path.join(content, "dbs-review.md"), dbsMd(ep));
  write(path.join(content, "publish-copy.md"), publishMd(ep));
  write(path.join(content, "cover-prompts.md"), coverPromptsMd(ep));
  write(path.join(project, "BRIEF.md"), projectBrief(ep));
  write(path.join(project, "SCRIPT.md"), scriptMd(ep));
  write(path.join(project, "STORYBOARD.md"), storyboardMd(ep));
  write(path.join(project, "frame.md"), fs.readFileSync(path.join(TEMPLATE, "frame.md"), "utf8"));
  write(path.join(project, "package.json"), JSON.stringify({name: ep.slug, private:true, type:"module", scripts:{dev:"npx --yes hyperframes@0.7.105 preview",check:"npx --yes hyperframes@0.7.105 check",render:"npx --yes hyperframes@0.7.105 render"}}, null, 2));
  write(path.join(project, "hyperframes.json"), JSON.stringify({name:ep.slug,skill:"faceless-explainer",resolution:{width:1080,height:1920},fps:30}, null, 2));
  write(path.join(project, "caption-overrides.json"), "{}");
  write(path.join(project, "meta.json"), JSON.stringify({id:ep.slug,name:`${ep.series}｜${ep.title}`}, null, 2));
  ep.segments.forEach((text, i) => write(path.join(project, "audio-text", `${String(i+1).padStart(2,"0")}.txt`), text));
  ep.frames.forEach((f, i) => write(path.join(project, "compositions/frames", `${String(i+1).padStart(2,"0")}-${f.kind}.html`), frameHtml(ep, f, i)));
  for (const cover of CONFIG.covers) write(path.join(project, "covers", `${cover.name}.html`), coverHtml(ep, cover.width, cover.height, cover.name));
}

function probe(file, project) {
  return Number(execFileSync(path.join(project, "bin/ffprobe"), ["-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",file], {encoding:"utf8"}).trim());
}

function repairFrames(ep) {
  const project = path.join(ROOT, `videos/${ep.slug}`);
  ep.frames.forEach((f, i) => write(path.join(project, "compositions/frames", `${String(i + 1).padStart(2, "0")}-${f.kind}.html`), frameHtml(ep, f, i)));
  write(path.join(project, "caption-overrides.json"), "{}");
}

function finalize(ep) {
  const project = path.join(ROOT, `videos/${ep.slug}`);
  const content = path.join(ROOT, `content/episode-${ep.issue}`);
  const durations = ep.segments.map((_,i)=>probe(path.join(project,"assets/voice",`${String(i+1).padStart(2,"0")}.mp3`), project));
  const starts = durations.map((_,i)=>durations.slice(0,i).reduce((a,b)=>a+b,0));
  const total = durations.reduce((a,b)=>a+b,0);
  const groups=[]; const allWords=[]; const voices=[]; const speechWords=[];
  const isPunc = value => /^[\s，。；：、“”‘’！？,.!?:;()（）\-]+$/u.test(value);
  for(let si=0;si<durations.length;si++){
    const sid=String(si+1).padStart(2,"0");
    const raw=JSON.parse(fs.readFileSync(path.join(project,"assets/voice",`${sid}-words.json`),"utf8"))[0];
    const collapsed=[];
    for(const entry of raw.timestamped_words){const prev=collapsed.at(-1);if(prev&&prev.word_begin===entry.word_begin&&prev.word_end===entry.word_end){prev.time_end=entry.time_end}else collapsed.push({...entry});}
    const words=collapsed.map((e,wi)=>({id:`w${si}-${wi}`,text:e.word,start:starts[si]+e.time_begin/1000,end:starts[si]+e.time_end/1000,local_start:e.time_begin/1000,local_end:e.time_end/1000}));
    voices.push({id:sid,path:`assets/voice/${sid}.mp3`,duration_s:durations[si],words}); allWords.push(...words); speechWords.push(...words.filter(w=>!isPunc(w.text)));
    let cursor=0;
    for(const phrase of ep.captions[si]){
      const target=clean(phrase); const phraseWords=[]; let assembled="";
      while(cursor<words.length&&clean(assembled).length<target.length){phraseWords.push(words[cursor]);assembled+=words[cursor].text;cursor++;}
      if(clean(assembled)!==target) throw new Error(`Caption mismatch ep${ep.issue} seg${sid}: expected ${target}, got ${clean(assembled)}`);
      const compact=[]; for(const word of phraseWords){if(isPunc(word.text)&&compact.length){compact.at(-1).text+=word.text;compact.at(-1).end=word.end}else compact.push({...word});}
      const gi=groups.length; groups.push({id:`caption-group-${gi}`,frame:si+1,start:phraseWords[0].start,end:phraseWords.at(-1).end+.12,text:phrase,words:compact.map((w,j)=>({id:`caption-word-${gi}-${j}`,text:w.text,start:w.start,end:w.end}))});
    }
    if(cursor!==words.length) throw new Error(`Unused timings ep${ep.issue} seg${sid}: ${words.length-cursor}`);
  }
  const speechWindows=[]; for(const word of speechWords){const prev=speechWindows.at(-1);if(prev&&word.start-prev[1]<=.045)prev[1]=Math.max(prev[1],word.end);else speechWindows.push([word.start,word.end]);}
  const capTemplate=fs.readFileSync(path.join(ROOT,"videos/qwen38-max-explained/compositions/captions.html"),"utf8");
  let captions=capTemplate.replaceAll("53.172",total.toFixed(3)).replace(/var GROUPS = \[[\s\S]*?\];\n  var DURATION = [\d.]+;/,`var GROUPS = ${JSON.stringify(groups)};\n  var DURATION = ${total.toFixed(3)};`).replace(/\n    \/\/ full-span anchor[\s\S]*?tl\.to\(\{\}, \{ duration: DURATION \}, 0\);/, "");
  write(path.join(project,"compositions/captions.html"),captions);
  write(path.join(project,"audio_meta.json"),JSON.stringify({provider:"minimax",model:"speech-2.8-hd",voice_id:"male-qn-qingse",total_duration_s:total,voices,bgm:null,sfx:[]},null,2));
  write(path.join(project,"word_timeline.json"),JSON.stringify({total_duration_s:total,words:allWords,speech_windows:speechWindows},null,2));
  write(path.join(project,"sentence_timeline.json"),JSON.stringify({total_duration_s:total,sentences:groups.map(({id,frame,start,end,text})=>({id,frame,start,end,text}))},null,2));
  write(path.join(project,"caption_groups.json"),JSON.stringify({total_duration_s:total,width:1080,height:1920,groups},null,2));
  const scenes=ep.frames.map((f,i)=>({id:`${String(i+1).padStart(2,"0")}-${f.kind}`,file:`${String(i+1).padStart(2,"0")}-${f.kind}.html`}));
  const sceneMarkup=scenes.map((s,i)=>`<div id="scene-${ep.issue}-${i+1}" class="clip scene" data-composition-id="${s.id}" data-composition-src="compositions/frames/${s.file}" data-start="${starts[i].toFixed(3)}" data-duration="${(i<4?durations[i]+.5:durations[i]).toFixed(3)}" data-track-index="${i%2}"></div>\n<audio id="audio-${ep.issue}-${i+1}" src="assets/voice/${String(i+1).padStart(2,"0")}.mp3" data-start="${starts[i].toFixed(3)}" data-duration="${durations[i].toFixed(3)}" data-track-index="10" data-volume="1"></audio>`).join("\n");
  const transitions=scenes.slice(1).map((s,i)=>{const prev=scenes[i];const at=starts[i+1].toFixed(3);return i===3?`tl.to("#scene-${ep.issue}-${i+1}",{filter:"blur(10px)",scale:1.03,opacity:0,duration:.6,ease:"power2.inOut"},${at});tl.fromTo("#scene-${ep.issue}-${i+2}",{filter:"blur(10px)",scale:.97,opacity:0},{filter:"blur(0px)",scale:1,opacity:1,duration:.6,ease:"power2.inOut"},${at});`:`tl.to("#scene-${ep.issue}-${i+1}",{x:-1080,duration:.5,ease:"power3.inOut"},${at});tl.fromTo("#scene-${ep.issue}-${i+2}",{x:1080},{x:0,duration:.5,ease:"power3.inOut"},${at});`;}).join("\n");
  const index=`<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080,height=1920"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;background:#000}#root{position:relative;width:1080px;height:1920px;overflow:hidden;background:${PAPER}}.scene{position:absolute;inset:0}.chai{position:absolute;z-index:40;left:${CONFIG.speechBar.avatar.left}px;top:${CONFIG.speechBar.avatar.top}px;width:${CONFIG.speechBar.avatar.width}px;height:${CONFIG.speechBar.avatar.height}px;border:3px solid ${BLUE};border-radius:50%;background:#06143f;box-shadow:0 0 0 5px rgba(240,235,222,.94);overflow:visible}.crop{position:absolute;inset:0;overflow:hidden;border-radius:50%}.crop img{width:100%;height:100%;object-fit:cover}.mouth{position:absolute;left:50%;top:66.2%;width:34px;height:20px;margin-left:-17px;margin-top:-10px;border-radius:48% 48% 54% 54%;background:radial-gradient(ellipse at 50% 76%,#d65a68 0 20%,#521e2a 22% 48%,#160b12 52% 100%);opacity:0}.name{position:absolute;left:50%;bottom:-23px;min-width:84px;margin-left:-42px;padding:4px 8px;border:2px solid ${BLUE};background:${PAPER};color:${BLUE};font:700 14px sans-serif;text-align:center;white-space:nowrap}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="${total.toFixed(3)}" data-width="1080" data-height="1920">${sceneMarkup}<div id="captions-${ep.issue}" class="clip scene" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="${total.toFixed(3)}" data-track-index="2"></div><div id="chai-${ep.issue}" class="chai"><div class="crop"><img src="assets/brand/chai-editor-avatar.png"><div id="mouth-${ep.issue}" class="mouth"></div></div><div class="name">柴主编</div></div></div><script>window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});window.__timelines.main=tl;${transitions}tl.fromTo("#chai-${ep.issue}",{scale:0,opacity:0},{scale:1,opacity:1,duration:.55,ease:"back.out(1.7)"},.18);const windows=${JSON.stringify(speechWindows)};const jaw={progress:0};tl.to(jaw,{progress:1,duration:${total.toFixed(3)},ease:"none",onUpdate:()=>{const t=jaw.progress*${total.toFixed(3)};let active=null;for(const w of windows){if(t>=w[0]&&t<=w[1]){active=w;break}}let open=0;if(active){const local=t-active[0];open=(.34+.66*Math.abs(Math.sin(local*18.5)))*Math.max(0,Math.min(1,local/.07,(active[1]-t)/.09))}gsap.set("#mouth-${ep.issue}",{scaleX:.82+open*.22,scaleY:.12+open*.94,opacity:open>.04?.98:0});gsap.set("#chai-${ep.issue}",{y:active?-2.5*Math.sin(t*5.4):0,rotation:active?.7*Math.sin(t*2.7):0})}},0);</script></body></html>`;
  write(path.join(project,"index.html"),index);
  for(const file of fs.readdirSync(path.join(project,"compositions/frames"))){const fp=path.join(project,"compositions/frames",file);let t=fs.readFileSync(fp,"utf8");t=t.replaceAll('data-duration="20"',`data-duration="${durations[Number(file.slice(0,2))-1].toFixed(3)}"`);write(fp,t);}
  let sb=storyboardMd(ep).replace("duration: pending",`duration: ${total.toFixed(3)}s`);durations.forEach((d,i)=>{sb=sb.replace("- duration: pending MiniMax audio",`- duration: ${d.toFixed(3)}s`)});write(path.join(project,"STORYBOARD.md"),sb);write(path.join(content,"STORYBOARD.md"),sb);
  write(path.join(content,"production-report.md"),`# 生产报告｜episode-${ep.issue}\n\n- 日期：${DATE}\n- 选题：${ep.series}｜${ep.title}\n- 核心判断：${ep.core}\n- MiniMax：speech-2.8-hd / male-qn-qingse / calm / speed ${ep.speed.toFixed(2)}\n- 口播时长：${total.toFixed(3)} 秒\n- 逐句字幕：${groups.length} 组\n- 词级时间戳：${allWords.length} 条\n- 嘴型窗口：${speechWindows.length} 段\n- 自动发布：否\n`);
  console.log(JSON.stringify({issue:ep.issue,project,total,durations,groups:groups.length,words:allWords.length}));
}

const mode=process.argv[2]||"prepare";const issue=process.argv[3];const selected=issue?episodes.filter(e=>e.issue===issue):episodes;if(!selected.length)throw new Error(`Unknown issue ${issue}`);
for (const ep of selected) {
  ep.segments.forEach((segment, index) => {
    const captionText = ep.captions[index].join("");
    if (clean(segment) !== clean(captionText)) throw new Error(`Caption plan does not match episode ${ep.issue} segment ${index + 1}`);
  });
}
if(mode==="prepare")selected.forEach(prepare);else if(mode==="repair")selected.forEach(repairFrames);else if(mode==="finalize")selected.forEach(finalize);else if(mode==="summary")console.log(JSON.stringify(episodes.map(e=>({issue:e.issue,slug:e.slug,chars:clean(e.segments.join("")).length,title:e.title})),null,2));else throw new Error(`Unknown mode ${mode}`);
