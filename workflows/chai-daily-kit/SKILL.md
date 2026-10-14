---
name: daily-ai-shorts
description: 按柴主编流程包制作和检查 AI 热点/工具短视频，交付成片、两种封面、平台文案与复盘记录；用于下一期制作、流程升级或成片检查。
---

# 柴主编流程包 V2.2

以本 SKILL.md 所在目录为包根目录。先读 README.md 确认环境；内容依据 docs/端到端流程.md，尺寸依据 workflows/chai-editor-single-topic-config.json。运行 scripts/validate_chai_editor_contract.py。

只加载当前阶段需要的文件：

- 选题/写稿：先按 workflows/chai-news-radar-workflow.md 运行新闻雷达，读简报和信源健康，核对媒体时间与事件时间；只深读最相关三条。端到端流程 §0–2、workflows/chai-editorial-brief-template.md。先回答具体观众、任务、可见证据、看完决定；公告自述与亲测分开。没有证据的教程不做。口语复审先于 TTS。
- 画面/配音：端到端流程 §3；有 HyperFrames skill 时先读该入口。example/project 只是已完成例子，不规定固定五场。品牌与实际证据优先，示意不得冒充实录。
- 验收/交包：端到端流程 §4、workflows/release-spec-template.json；用包内离线脚本检查，独立评审绑定最终成片。写明实际听音/连续播放/抽帧范围；技术检查不代替内容审查。
- 发布：仅本次用户授权当期后读 workflows/chai-platform-publish-playbook.md。先查原任务与平台作品，再在同一页提交一次；必须核对各封面槽、AI 声明和可见性。离线 PASS 不授权发布。
- 复盘：workflows/chai-editor-performance-template.md；同一作品 24/72 小时快照，未知不补造。

网络调研有 agent-reach 时使用；无连接器则使用可用浏览工具核验一手来源。文案诊断有 dbs-suite 时使用其相关诊断；缺技能时做同等口语、开头、事实与共鸣检查并如实注明。不要默认读取全部技能参考或原始长输出。

每期新目录，不覆盖已发布成片。改脚本重做配音与字幕，改画面重渲染，单改封面或平台文案不重做未改变的视频；任何成片改变都重新绑定评审。缓存尚须由执行者实现，成本实际值记 workflows/chai-stage-cost-template.json，未知为 null。
