# 了不起的小超人｜开源装备雷达 自动化记忆

## 最近运行

- 运行时间：2026-08-11 18:06:11 CST（Asia/Shanghai，UTC+08:00）
- 执行标准：完整读取并严格采用 `workflows/xiaochao-open-source-radar-workflow.md` 与 `workflows/xiaochao-open-source-radar-config.json`。
- 去重范围：核对过去 30 天及当天 008—010；本轮没有重复 WeChat-AI、pi-from-scratch、h3.c 等当天内容。
- 候选：重新核验 18 项，记录在 `content/2026-08-11/xiaochao-radar-candidates-run-2.md`。
- 本轮完成 3 条：
  - 011 JoyAI-Video-Edit，85／100，63.53s。
  - 012 phone-harness，86／100，64.07s。
  - 013 PMB，82／100，60.27s。
- 带 BGM 成片：
  - `output/xiaochao/2026-08-11/videos-with-bgm/11-joyai-video-edit-bgm.mp4`
  - `output/xiaochao/2026-08-11/videos-with-bgm/12-phone-harness-bgm.mp4`
  - `output/xiaochao/2026-08-11/videos-with-bgm/13-pmb-bgm.mp4`
- 30fps 无 BGM 母版与 15fps 渲染中间件均保留在 `output/xiaochao/2026-08-11/videos/`。
- 文案：`output/xiaochao/2026-08-11/copy/11-joyai-video-edit.md`、`12-phone-harness.md`、`13-pmb.md`。
- 来源工程：`content/2026-08-11/xiaochao-011-joyai-video-edit/`、`xiaochao-012-phone-harness/`、`xiaochao-013-pmb/`。
- QA：三条 HyperFrames 0.7.106 检查通过；0 运行错误、0 布局错误、0 动效错误，62／62 对比度通过。最终成片均为 1080×1920、恒定 30fps、H.264/AAC，并通过 ffprobe 与完整 demux／packet 校验。
- 制作修正：发现并修复第 0 帧空白主体；012 首屏标题压缩为“权限你敢给吗”以消除右侧溢出。
- 渲染兼容：工作区新增 `scripts/hyperframes_ffmpeg_wrapper.sh` 与 `scripts/hyperframes_ffprobe_wrapper.sh`，让 Remotion ffmpeg 为 HyperFrames 的 `.m4a` 中间音频显式使用 MP4 容器；三条最终渲染成功。
- 声音：MiniMax `speech-2.8-hd` + `Chinese (Mandarin)_Sincere_Adult`，speed 1.02、volume 1.0、pitch -1、emotion happy；BGM 固定 `assets/music/look-beyond.mp3`，约 10%，首尾各 1 秒淡入淡出，约 -16 LUFS。
- 生产保护：本轮没有生成或修改封面，没有进入任何发布平台，没有创建发布草稿，没有自动发布，也没有覆盖早一轮文件。
- 临时清理：删除失败渲染留下的精确工作目录与 0.5 秒包装器测试音频；不可恢复，正式中间件与 QA 保留。
- 下一期号：014。下一轮仍需重新研究，不能直接沿用本轮未选候选而跳过核验。
- Agent Reach：v1.5.0，已是最新版。

## 追加运行

- 运行时间：2026-08-11 19:05:08 CST（Asia/Shanghai，UTC+08:00）。
- 重新读取两份唯一标准并重新联网核验候选；与过去 30 天及当日 001—013 去重，记录在 `content/2026-08-11/xiaochao-radar-candidates-run-3.md`。
- 完成 014 OpenWorker（92／100，60.10s）、015 QM（89／100，60.80s）、016 GenOffice（94／100，61.10s）。
- 成片：`output/xiaochao/2026-08-11/videos-with-bgm/14-openworker-bgm.mp4`、`15-qm-bgm.mp4`、`16-genoffice-bgm.mp4`。
- 三条均用指定 MiniMax 音色、固定 BGM 和暖色编辑手册版式；正式 HyperFrames check 通过，代表帧目检和最终 demux／packet 校验通过。
- QA：`output/xiaochao/2026-08-11/qa/run-3-report.md`；当日 README 已更新为 9 条。
- 生产保护：未生成或修改封面，未进入发布平台，未创建草稿，未自动发布，未覆盖已有文件。
- 下一期号：017。下一轮仍必须重新研究与去重。

## 2026-08-12 运行

- 运行时间：2026-08-12 08:05:55 CST（Asia/Shanghai，UTC+08:00）。
- 完整读取两份唯一执行标准，重新联网研究与核验 18 个候选，并与过去 30 天及当日 001—016 去重；候选记录为 `content/2026-08-12/xiaochao-radar-candidates-run-1.md`。
- 完成 017 Qwen-MM-Plugins（90／100，58.27s）、018 Diagram Design（96／100，63.13s）、019 img2threejs（89／100，57.60s）。
- 正式混音成片位于 `output/xiaochao/2026-08-12/videos-with-bgm/`；30fps 无 BGM 母版和 15fps 中间母版位于 `output/xiaochao/2026-08-12/videos/`。
- 三条均沿用暖色编辑手册版式与黄色真人 IP，使用指定 MiniMax `speech-2.8-hd` / `Chinese (Mandarin)_Sincere_Adult` 参数，并固定混入 `assets/music/look-beyond.mp3`。
- QA：HyperFrames 浏览器运行、布局、动效、对比度检查通过；15 张代表帧目检通过；最终文件均为 1080×1920、恒定 30fps、H.264/AAC，完整解码通过，响度为 -15.9／-15.9／-16.2 LUFS，真峰值均 -1.5 dBTP。报告为 `output/xiaochao/2026-08-12/qa/run-1-report.md`。
- 为消除渲染时 CDN 依赖，将 GSAP 3.14.2 冻结到三条工程本地；三条逐帧渲染与封装全部成功。
- 生产保护：未生成或修改封面，未进入发布平台，未创建发布草稿，未自动发布，未覆盖以往文件。
- `animation-map.mjs` 因其辅助依赖未安装而未生成；正式动效检查与逐帧渲染均通过，不构成阻塞。Agent Reach v1.5.0，因 DNS 失败未完成更新检查。
- 下一期号：020。下一轮仍须重新研究和去重。

## 2026-08-13 早轮

- 运行时间：2026-08-13 07:31:56 CST（Asia/Shanghai）。完整读取两份唯一执行标准与自动化记忆，并按 Agent Reach 流程执行 GitHub / Exa 研究通道检查。
- 阻塞：GitHub Search / GitHub API 均无法连接 `api.github.com`；Exa 版本协商因网络 `fetch failed` 失败；Agent Reach 更新检查也因 DNS 失败而未完成。
- 按“关键来源失败即停止”保护规则，没有使用昨天或更早的数据替代本轮核验：未建立候选池、未评分、未制作视频、文案、配音或封面，也未进入任何发布平台。
- 记录：`content/2026-08-13/xiaochao-radar-candidates-run-1.md`、`output/xiaochao/2026-08-13/qa/run-1-blocked.md` 与当日 `README.md`。
- 下一期号仍为 020。网络恢复后须从候选收集、30 天去重和官方来源核验重新开始；不可直接续用本轮。

## 2026-08-13 续跑完成

- 运行时间：2026-08-13 12:12 CST（Asia/Shanghai）。按用户“继续”指令重新完整读取工作流、配置与自动化记忆；恢复联网核验和 MiniMax 配音后，从候选研究重新执行。
- 候选：重新研究 18 项，并与过去 30 天及当日 001—019 去重；记录为 `content/2026-08-13/xiaochao-radar-candidates-run-2.md`。
- 完成 020 shuohao-skills（93／100，60.5s）、021 FlyingMouse Format（95／100，64.3s）、022 morphicons（90／100，60.4s）。
- 正式混音成片：`output/xiaochao/2026-08-13/videos-with-bgm/20-shuohao-skills-bgm.mp4`、`21-flyingmouse-format-bgm.mp4`、`22-morphicons-bgm.mp4`；无 BGM 母版保存在同日 `videos/`。
- 配音：MiniMax `speech-2.8-hd` + `Chinese (Mandarin)_Sincere_Adult`，speed 1.02、volume 1.0、pitch -1、emotion happy。原始较长配音保留在 `voice/`，DBS 缩时复审后的最终配音保存在 `voice-final/`，未覆盖原文件。
- 视觉与音乐：暖色编辑手册版式、黄色真人 IP；固定混入 `assets/music/look-beyond.mp3`，音乐约 10%，首尾各 1 秒淡入淡出，目标 -16 LUFS／-1.5 dBTP。
- QA：三条 HyperFrames 0.7.107 检查均为 0 runtime errors、0 layout issues、0 motion errors/warnings、62／62 contrast；最终成片均为 1080×1920、30fps、H.264/AAC，完整解码和 15 张抽帧目检通过。响度 -16.29／-16.02／-15.89 LUFS，真峰值 -1.41／-1.29／-1.43 dBTP。报告：`output/xiaochao/2026-08-13/qa/run-2-report.md`。
- 同日 `run-1-blocked.md` 和 `run-2-blocked.md` 为历史阻塞记录；续跑后均已解除，不代表最终状态。
- 生产保护：未生成或修改封面，未进入任何发布平台，未创建发布草稿，未自动发布，未覆盖已有文件。
- 下一期号：023。下一轮仍须重新研究、核验并去重，不能直接沿用本轮未选候选。

## 2026-08-13 晚轮完成

- 运行时间：2026-08-13 19:08:55 CST（Asia/Shanghai）。完整读取两份唯一执行标准与自动化记忆，重新执行联网研究、官方来源核验、30 天及当日 001—022 去重。
- 候选：重新研究 18 项，记录为 `content/2026-08-13/xiaochao-radar-candidates-run-3.md`；未为凑数降低 70 分门槛。
- 完成 023 Pireel Studio（91／100，61.1s）、024 OpenMausBot（93／100，63.0s）、025 md2hd（90／100，63.2s）。
- 正式混音成片：`output/xiaochao/2026-08-13/videos-with-bgm/23-pireel-bgm.mp4`、`24-openmausbot-bgm.mp4`、`25-md2hd-bgm.mp4`；无 BGM 母版保存在同日 `videos/`。
- 文案：`output/xiaochao/2026-08-13/copy/23-pireel.md`、`24-openmausbot.md`、`25-md2hd.md`；每条均完成 DBS hook、共鸣、标题和 AI 痕迹审查。
- 配音：MiniMax `speech-2.8-hd` + `Chinese (Mandarin)_Sincere_Adult`，speed 1.02、volume 1.0、pitch -1、emotion happy。023 与 025 使用 `voice-final-v2/`，024 使用 `voice-final/`；原始较长配音保留，未覆盖。
- 视觉与音乐：暖色编辑手册版式、黄色真人 IP；固定混入 `assets/music/look-beyond.mp3`，10%，首尾各 1 秒淡入淡出，目标 -16 LUFS／-1.5 dBTP。
- QA：三条 HyperFrames 0.7.107 检查均为 0 runtime errors、0 layout issues、0 motion errors/warnings、62／62 contrast；最终成片均为 1080×1920、恒定 30fps、H.264/AAC stereo，完整画面与音频解码、15 张抽帧目检通过。响度 -15.73／-15.64／-16.69 LUFS，真峰值 -1.29／-1.33／-1.22 dBTP。报告：`output/xiaochao/2026-08-13/qa/run-3-report.md`。
- 附加 `animation-map.mjs` 因辅助依赖未安装而未生成；正式 motion 检查、快照与最终抽帧均通过，不构成阻塞。Agent Reach v1.5.0，已是最新版。
- 生产保护：未生成或修改封面，未进入发布平台，未创建发布草稿，未自动发布，所有文件均以新名称写入、未覆盖已有产物。
- 下一期号：026。下一轮仍须重新研究、核验并去重，不能直接沿用本轮未选候选。

## 2026-08-14 第 1 轮完成

- 运行时间：2026-08-14 08:40:38 CST（Asia/Shanghai）。完整读取工作流、配置与自动化记忆，重新执行研究、官方来源核验及 2026-07-16—2026-08-14 / 001—025 去重。
- 候选：重新研究 18 项，记录为 `content/2026-08-14/xiaochao-radar-candidates-run-1.md`；未为凑数降低 70 分门槛。
- 完成 026 Needle 2（95／100，60.5s）、027 FluidVoice（94／100，63.3s）、028 Modly（92／100，62.3s）。
- 正式混音成片：`output/xiaochao/2026-08-14/videos-with-bgm/26-needle2-bgm.mp4`、`27-fluidvoice-bgm.mp4`、`28-modly-bgm.mp4`；正式交付只认这三条。
- 文案：`output/xiaochao/2026-08-14/copy/26-needle2.md`、`27-fluidvoice.md`、`28-modly.md`；每条均完成 DBS hook、共鸣、标题公式与 AI 写作痕迹审查。
- 配音：MiniMax `speech-2.8-hd` + `Chinese (Mandarin)_Sincere_Adult`，speed 1.02、volume 1.0、pitch -1、emotion happy；最终段落保存在各工程 `voice-final/`，原始较长版本未覆盖。
- 视觉与音乐：暖色编辑手册版式、黄色真人 IP；固定混入 `assets/music/look-beyond.mp3`，10%，首尾各 1 秒淡入淡出，目标 -16 LUFS／-1.5 dBTP。
- QA：三条正式 HyperFrames check 均为 0 runtime errors、0 阻断 layout issues、0 motion errors/warnings，contrast 61/61 或 62/62；最终成片均为 1080×1920、恒定 30fps、H.264/AAC，完整画面/音频解码与 15 张抽帧目检通过。响度 -16.16／-16.33／-16.04 LUFS，真峰值 -1.29／-1.01／-1.23 dBTP。报告：`output/xiaochao/2026-08-14/qa/run-1-report.md`。
- 渲染说明：HyperFrames CLI 在当前受限环境进入 file-server/frame-capture 后子进程被回收；改用同一 HTML、GSAP 时间线与 HyperFrames 管理 Chrome 做 15fps 确定性逐帧渲染，再编码 30fps。`videos/26-needle2.mp4` 是 30.6 秒帧率诊断文件，不是交付成片；因不覆盖规则保留并已在 QA/README 明示。
- 附加动画地图脚本因辅助包未安装而未执行；正式 motion/快照/最终抽帧通过。Agent Reach 更新检查因 DNS 失败，重试 3 次后停止；不影响已保存关键来源。
- 生产保护：未生成或修改封面，未进入任何发布平台，未创建发布草稿，未自动发布，未覆盖已有文件。
- 下一期号：029。下一轮仍须重新研究、核验并去重，不能直接沿用本轮未选候选。

## 2026-08-14 第 2 轮阻塞

- 运行时间：2026-08-14 17:49:13 CST（Asia/Shanghai）。完整读取工作流、配置与自动化记忆；按 Agent Reach 重新研究 GitHub Trending、GitHub API、Exa、官方仓库、README、Release、npm / PyPI 和许可证，并与 2026-07-16—2026-08-14 / 001—028 去重。
- 候选：重新研究并评分 18 项，记录为 `content/2026-08-14/xiaochao-radar-candidates-run-2.md`；未为凑数降低 70 分门槛。
- 入选准备：029 DeepSeek Harness（96／100）与 030 book-to-skill（90／100）通过来源核验和 DBS AI 痕迹、共鸣、开头、标题四项门禁；口播、文案、来源、说明图与工程准备材料已用新路径写入。
- 来源淘汰：Dalaran 官方 README 所列 `dalaran-sdk` 在 PyPI 官方 JSON 返回 HTTP 404；Waku 的 Release 安装包核验因外部联网权限审查停止；两条均未制作。
- 关键阻塞：MiniMax 首段在沙箱内无法读取 macOS 钥匙串；按正规授权路径重试时，外部权限额度审查拒绝。两条 `voice/` 目录为空，因此按保护规则同时停止 029／030，没有换音色、其他 TTS、旧音频或占位内容。
- 未执行：没有生成 HyperFrames `index.html`，没有渲染、混音或 029／030 视频；固定 `look-beyond.mp3` 未用于未完成条目。
- 记录：`output/xiaochao/2026-08-14/qa/run-2-blocked.md` 与 `output/xiaochao/2026-08-14/README-run-2.md`。
- 生产保护：未生成或修改封面，未进入发布平台，未创建发布草稿，未自动发布，未覆盖 026—028 或更早文件。
- Agent Reach：v1.5.0；更新检查因 DNS 失败，重试 3 次后停止。
- 下一期号仍为 029。MiniMax 权限恢复后须先重新确认来源时效，再从指定音色配音继续；不得把本轮准备稿当成完成视频。

## 2026-08-14 第 2 轮续做完成（08-15 恢复）

- 运行时间：2026-08-15（Asia/Shanghai）。MiniMax 钥匙串读取恢复后，从 029／030 已备口播与文案续做，未覆盖任何已备材料。
- 来源重核：029 deepseek-harness Star 82,878 → 103,086；030 book-to-skill Star 21,390 → 21,649；MIT／版本／关键事实不变，成片统计与 evidence.svg 已同步更新。
- DBS 缩时复审：首轮五段 029 74.16s、030 69.80s 均超 65s；缩时后 029 60.01s、030 60.19s，保留全部核验事实、钩子与适用人群。narration-final／voice-final 保存定稿，narration／voice 保留原始版。
- 完成 029 DeepSeek Harness（96／100，62.2s）、030 book-to-skill（90／100，62.4s）。
- 正式混音成片：`output/xiaochao/2026-08-14/videos-with-bgm/29-deepseek-harness-bgm.mp4`、`30-book-to-skill-bgm.mp4`；无 BGM 母版与中间件在 `videos/`。
- QA：两条 HyperFrames 0.7.109 check 通过（motion 0 错、contrast 62／62）；成片 1080×1920、恒定 30fps、H.264／AAC，完整解码、黑帧与静音检测通过；响度 -16.20／-1.38 与 -15.56／-1.43 LUFS／dBTP。报告 `output/xiaochao/2026-08-14/qa/run-2-report.md`。
- 生产保护：未生成或修改封面，未进入发布平台，未创建草稿，未自动发布，未覆盖 026—028 及更早文件。
- 下一期号：031。下一轮仍须重新研究、核验并去重，不能直接沿用本轮未选候选。

## 2026-08-15 第 1 轮完成（新标准）

- 运行时间：2026-08-15（Asia/Shanghai）。按新标准（零铺垫开头 + 干货前置 + 缩短时长 + hook 封面）生产。
- 完成 031 Headroom（96／100，48.3s）、032 OpenMontage（92／100，47.1s）、033 CC Switch（90／100，44.1s）。
- 正式混音成片：`output/xiaochao/2026-08-15/videos-with-bgm/31-headroom-bgm.mp4`、`32-openmontage-bgm.mp4`、`33-cc-switch-bgm.mp4`。
- 新增 hook 封面：`31/32/33-*-cover-9x16.png`（暖色编辑手册风格，9:16，发布时手动选）。
- 时长从 50—65s 压到 44—48s（观众均播放约 7s，短利于完播）。
- 生产保护：未进入发布平台，未自动发布，未覆盖旧文件；本轮未生成 3:4/4:3 封面。
- 下一期号：034。下一轮仍须重新研究、核验并去重。

- 追加 034 Deep Whale 昼夜主题（87／100，46.0s）：DSH 网页端鲸鱼娘昼夜角色 UI 皮肤，CC BY-NC-SA 非商用；成片 `output/xiaochao/2026-08-15/videos-with-bgm/34-deepwhale-theme-bgm.mp4`。下一期号：035。

## 2026-08-16 第 1 轮（6 条）

- 完成 035 ECC(95)、036 Hermes Agent(93)、037 Open WebUI(90)、038 scrcpy(93)、039 Dify(91)、040 Firecrawl(92)。
- 本轮回正确使用官方截图做 hero/evidence 展示图（此前几轮误用 SVG 示意图）。
- 成片：`output/xiaochao/2026-08-16/videos-with-bgm/{35..40}-*-bgm.mp4`。
- 下一期号：041。

## 2026-08-17 第 1 轮（行业 × AI 改版首条）

- 栏目改版：小超人从「开源装备雷达」改为「行业 × AI」——仍按 GitHub 热榜抓工具，但每个工具绑定一个真实行业场景讲（先打电商/带货 + 开店实体）。人设、视觉、头像、BGM、配音参数不变。工作流已更新：`dailyvideos/workflows/xiaochao-open-source-radar-workflow.md`。
- 完成 041 rembg（93/100，63.2s 音频 / 65.4s 成片）：商品图抠背景/换白底，电商向。真实素材：官方 examples before/after 对比图（car-1、girl-1）。
- 新增行业版能力：video-spec.json 支持 `seriesName`（header 系列名）与 `chipText`（场景1钩子标签）字段，build 脚本已兼容，缺省保持旧值。
- 成片：`output/xiaochao/2026-08-16/videos-with-bgm/41-rembg-bgm.mp4`；封面 3:4/4:3；桌面 `~/Desktop/小超人发布-041/`。
- 生产保护：未自动发布；口播全程说人话（禁开源/Prompt/Agent 等黑话）。
- 下一期号：042。下一轮仍须重新研究、核验并去重，行业匹配门必过（工具必须能在真实行业解决具体烦人事）。

## 2026-08-18 041 文案修订（v4 终版）

- 用户反馈：电商选题 OK，但文案不行。重写要点：
  - 钩子带具体数字（一张 5 块，一个月 300 张就是 1500）制造"对号入座"感。
  - **全链路（口播/封面/发布文案/话题标签）禁用"钱"字**（用户明确要求），改用"开销/花了多少/省下 1500"。
  - 删掉"听我说"废话铺垫；"GitHub 上"改为"国外"。
- 视觉模型已配置：modlens + Gemini API（gemini-3-flash-preview，key 存 Keychain `dailyvideos-gemini-api-key`）。首次实战抓到 SVG 文字溢出（"可上架"被裁、绿框"免"字缺失），修复：before/after SVG 内容收进中央安全区 x∈[95,665]（容器 390×610 contain 适配会左右各裁 62px）。
- 041 终版：`41-rembg-v4-bgm.mp4`（61.2s，1080×1920/30fps/H.264/AAC 48kHz），桌面 `~/Desktop/小超人发布-041/`。

## 2026-08-18 041 模板升级（v5 终版，60fps）

- 用户反馈：模板不丝滑 + 内容少、节奏感弱。
- 修复 1（丝滑）：渲染从 15fps 截帧升到 **60fps 截帧 + 60fps 输出**（真 60fps，之前 15→30 只是重复帧）。render_xiaochao_frames.mjs 传 fps=60。
- 修复 2（节奏）：build 模板动画升级——
  - 场景内卡片（stats/flow/limit）逐个弹入（back.out，每 ~0.7s 一个）
  - 字幕改为上滑+弹出入场/退场（替代原地淡入）
  - 钩子场景 h1 分 span 弹跳入场 + kicker/corner-note 依次入场
- 视觉模型复验：12s 只见卡片 01、13.5s 三个全出（逐个入场生效），文字无截断。
- 041 终版：`41-rembg-v5-bgm.mp4`（61.2s，1080×1920/**60fps**/H.264/AAC 48kHz，14MB）。

## 2026-08-18 帧率决策（30fps 定案）

- 用户判断 60fps 性价比低：文件大、渲染慢，平台播放按 30fps 处理，观众看不出差别。
- 定案：**真 30fps**（30fps 截帧 + 30fps 输出）。此前"不丝滑"根源是 15fps 截帧冒充 30fps，不是帧率不够高。
- HyperFrames 模板/工程默认即 30fps（组件 data-fps="30"），无需改动；手搓渲染脚本以 30fps 截帧为准。

## 2026-08-18 视觉改版定案：苹果设计风（v5/最终）

- 用户试过：暖米白编辑风（嫌亮）、暗色工坊（嫌土）、大图杂志/奶油杂志（嫌普通）→ 最终选定「苹果设计风」。
- 苹果风要素：深黑底 #000 + 三色极光光斑（橙/蓝/紫，blur 110px 慢漂移）+ 毛玻璃卡片（backdrop-filter:blur 30px）+ 大圆角（24-32px）+ 超大粗体标题（第二行橙→琥珀渐变）+ 底部 300px 平台安全区（虚线标注）。
- 新 build 脚本：`scripts/build_xiaochao_video_apple.mjs`（5 场景：钩子/证据对比/用法/限制/结论；卡片逐个 back.out 弹入；字幕上滑弹入）。
- HyperFrames 管线渲染：`npx hyperframes render --quality high`（30fps 定案，勿用 60fps），ffmpeg wrapper 在 /tmp/hf-bin（remotion 自带 ffmpeg + DYLD）。
- 041 苹果版成片：`41-rembg-apple-bgm.mp4`（61.2s，1080×1920/30fps，13.9MB）。
- 教训：Gemini 免费额度每分钟 15 次、每日有上限——视觉质检每次只抽 2-3 关键帧，别每场景都查；429 后等几分钟再试。
- 待办：视觉模型额度恢复后补一轮苹果版全场景精查；封面（3:4/4:3）也需按苹果风重做。

## 2026-08-18 041 改版：单工具 → 三工具（最终）

- 用户反馈：单工具版内容少、全是互动、节奏慢；第二页（汽车对比图）设计不行。
- 改版：一条讲 3 个工具——rembg（24k⭐/MIT，功能全/批量）+ background-removal-js（7.3k⭐/AGPL，浏览器嵌入）+ bg-remove（1k⭐/MIT，网页免装）。均已核验官方仓库。
- 结构：钩子（3 免费工具）→ 工具卡逐个（场景2）→ 怎么选（场景3）→ 结尾互动。音频从 59s 压到 50.9s，全片 53.1s。
- 场景2 由「数据卡+汽车对比图」改为「3 个毛玻璃工具卡」（编号+名字+适合谁）。
- 成片：`41-rembg-apple3-bgm.mp4`（53.1s/30fps/12.5MB）。桌面 `小超人发布-041/041-电商抠图-3工具版.mp4`。
- 用户待确认：三工具版节奏/内容密度是否达标；苹果风封面（3:4/4:3）仍待做。

## 2026-08-19 041 终稿交付（三工具版 + 苹果风封面）

- 用户确认三工具版节奏/内容 OK，要求做今天的内容收尾。
- 苹果风封面（3:4 + 4:3）已生成：`output/xiaochao/2026-08-16/41-rembg-cover-{3x4,4x3}.png`（深黑+极光+毛玻璃+大字标题）。
- 最终交付包：`~/Desktop/小超人发布-041/`（`041-电商抠图-3工具版.mp4` + 竖/横封面 + 文案）。
- 041 定稿：53.1s / 1080×1920 / 30fps / H.264 / AAC 48kHz。
- 下一期：042。行业版流程 + 苹果风模板已固化，下一轮直接用 `build_xiaochao_video_apple.mjs`。

## 2026-08-19 042/043 完成（开店向，苹果风）

- 042 NocoBase（23.7k⭐/MIT，无代码建业务系统）：58.6s 成片。钩子"开店的，进货库存客户名单别记本子了"。
- 043 teable（21.7k⭐，AI 电子表格）：56.7s 成片。钩子"表格变聪明了，用大白话问"。
- 素材：官网真实截图（headless Chrome 截 nocobase.com / teable.io）+ NocoBase 官方文档图。
- 成片：`output/xiaochao/2026-08-16/videos-with-bgm/{42,43}-*-bgm.mp4`；桌面 `~/Desktop/小超人发布-04{2,3}/`。
- 流程完全复用 041 苹果模板：build_xiaochao_video_apple.mjs + HyperFrames 30fps 渲染 + BGM 混音。
- 下一期：044。

## 2026-08-20 042/043 修复（图片比例 + 布局重叠）

- 用户反馈 042：图片 404 感 + 比例不行 + 压住后面的字。
- 根因 1：官网截图是竖屏 1080×1920，塞进横图片卡（~952px 宽）比例怪。
- 根因 2（真 bug）：标题区（top:240，h1 112px 两行高 477px → 到 717）和图片卡（top:660）重叠 57-64px → "压住字"。
- 修复（build_xiaochao_video_apple.mjs）：标题上移 top:210 + 字号 104px + kicker 收紧；图片卡下移 top:780/bottom:400；img 改 height:100%+contain；官网截图重截为横屏 1280×800。
- 用 puppeteer getBoundingClientRect 验证：标题(210→532) < 图片卡(780) < 字幕条(1536)，无重叠。
- 只有场景 1 有图片卡，其余场景纯卡片布局，不受影响。
- 042/043 已重新渲染混音替换：桌面 `小超人发布-04{2,3}/`。30fps 验证通过。

## 2026-08-20 044 完成 + 安全区布局调整

- 044 ChatGPT-On-CS（4.3k⭐/AGPL，多平台客服自动回：微信/抖音/拼多多/小红书）：51.7s 成片。钩子"三个平台消息回不过来？免费工具自动回"。
- 素材：GitHub 仓库页真实截图（1280×800 横屏）。
- 布局调整（用户要求）：最下行安全区提示上移（bottom 60→110）且左右留白（left/right 64→120），给抖音/小红书平台信息留白。布局实测：safe top=1760，底部留 160px；标题/图片/字幕三层无重叠。
- 成片：`output/xiaochao/2026-08-16/videos-with-bgm/44-chatgptoncs-bgm.mp4`；桌面 `~/Desktop/小超人发布-044/`。
- 下一期：045。

## 2026-08-21 045-047 完成（自媒体向，苹果风）

- 用户要求"做 3 期自媒体的 AI 工具"。
- 045 Whisper（10.7万⭐/MIT，语音转文字）：53.6s。钩子"录完视频还要敲文字稿？语音一键变文字"。
- 046 VideoCaptioner（1.57万⭐/GPL，卡卡字幕助手：字幕生成/断句/翻译）：48.5s。钩子"加字幕别手动对了"。
- 047 video-subtitle-remover（1.24万⭐/Apache，去硬字幕/水印）：48.5s。钩子"素材带字幕水印？一键抹掉"。
- 素材：GitHub 仓库页横屏截图（1280×800）。
- 成片：`output/xiaochao/2026-08-16/videos-with-bgm/{45,46,47}-*-bgm.mp4`；桌面 `~/Desktop/小超人发布-04{5,6,7}/`。
- 下一期：048。

## 2026-08-22 048 完成（自媒体向，苹果风）

- 048 GPT-SoVITS（6.1万⭐/MIT，声音克隆：1 分钟语音训练专属配音）：52.7s 成片。钩子"录一分钟，AI 就能用你的声音念任何稿子"。
- 素材：GitHub 仓库页横屏截图。
- 成片：`output/xiaochao/2026-08-16/videos-with-bgm/48-gptsovits-bgm.mp4`；桌面 `~/Desktop/小超人发布-048/`。
- 下一期：049。自媒体工具线已做 5 期（Whisper/字幕/去水印/声音克隆），可换行业或继续补充（如视频翻译配音 VideoLingo）。
