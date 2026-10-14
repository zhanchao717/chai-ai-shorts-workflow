# 柴主编日更流程包 V2.2

版本：2026-10-01。目标：把这次实际跑通的制作、复核、发布经验变成可复用流程。

## 包里有什么

- `SKILL.md`：短入口，按阶段读取资料。
- `docs/端到端流程.md`：内容、证据、文案、画面、验收与复盘规则。
- `workflows/`：编辑简报、平台文案、发布状态、成本记录、24/72 小时复盘模板与尺寸配置。
- `scripts/`：公开官方消息/中文媒体新闻雷达，以及离线契约检查、文案检查、字幕断词诊断、成片和评审绑定检查。
- `example/project/`：EP.227 可编辑 HyperFrames 工程及原配音、品牌和证据素材。
- `example/release/`：已交付成片、两种封面、文案、来源及评审报告；作为参考，不是下一期默认题材或场景数。
- `manifest.json`：包内每个文件的 SHA-256；`verify-kit.py` 验证解压后是否完整。

本包不包含浏览器登录态、账号密钥、旧带认证的发布脚本或 macOS 二进制软链。制作依赖 MiniMax/其他配音服务、HyperFrames 和平台浏览器会话，迁移后分别配置；这不是无账号零配置的一键自动发布软件。

## 使用

1. 解压到任意目录。离线检查需要 Python 3.9+；成片检查另需 `ffprobe`。
2. 在包根目录执行：

```bash
python3 verify-kit.py
python3 scripts/validate_chai_editor_contract.py
# 联网拉取公开新闻元数据（不登录、不写稿、不发布）：
python3 scripts/chai_news_radar.py --hours 48 --limit 12
python3 scripts/chai_xhs_copy_check.py example/release/publish-copy.md
python3 scripts/chai_release_preflight.py example/release --ffprobe /你的/ffprobe
python3 scripts/chai_caption_boundaries.py example/project/caption_groups.json
```

示例字幕保留原已发布版本，其中“Ultra用户”被拆开；诊断会报出。它是留存的 P1 样例，不是已修好的新成片。预检 PASS 仅限文件、规格、文案与评审哈希绑定；示例报告明确未听音、未连续观看。

3. 下一期先复制模板到新的期目录，完成观众任务、证据、脚本、分镜、口语复审再做配音。复制工程时换掉题材、原句、期号、配音、字幕、封面；每个生成文件对应本期输入。
4. 在新发布包内参照 `workflows/release-spec-template.json` 填实际文件路径、哈希和真实评审范围。哈希是绑定已审文件，不是自动给内容背书；渲染变化须重新验收，不能只刷新哈希。
5. 用户授权这期发布后，读 `workflows/chai-platform-publish-playbook.md`，使用当前 MultiPost/浏览器在同一任务提交一次，按平台侧状态留痕。

工程复用需要 Node.js/npm 和 HyperFrames。示例固定 `0.8.102`（原制作版本）；`cd example/project` 后 `npm run check`、`npm run render` 可进入框架检查/渲染。首次会获取 npm 依赖，所需浏览器、渲染环境按 HyperFrames 提示配置。本次仅验证工程资源完整与可本地重建 HTML，没有在新机器重渲染；不能承诺跨机器像素完全一致。

## 给 Codex / DSH 的入口

在当前包目录告诉助手：“按 SKILL.md 做下一期，先给三个与观众有关且证据充分的选题；不要发布。”
使用现有工作区时调用现行 `daily-ai-shorts` 即可。迁移若要安装为 skill，复制**整个包目录**到技能根下的 `daily-ai-shorts`；已有同名技能先备份/合并，不能只复制 SKILL.md 而漏掉脚本和参考。包内 skill 不自带所有框架/调研连接器，缺失时先说明可用能力。

## 本轮改进

1. 文案硬门禁聚焦缺失、链接、标题预算和平台间复制；固定 emoji、正文长度和标签配额改为编辑提示。
2. 旧发布入口只建草稿，禁用绕过封面核对的自动提交；封面缺失不回退另一比例，封面异常停止该平台准备。
3. 两种封面按槽位明确路由；登录过期、失败状态和审核中均在原任务恢复，避免重复发布。
4. 评审绑定最终视频哈希，明确抽帧/听音/连续观看范围；增加字幕拆词诊断。
5. 原始大文件留磁盘，分阶段加载 skill；加耗时和 token 留痕模板。实际节省比例需后续测量。

## 还要做什么

优先补上可执行的听审/连续观看，再用 6–8 条相近作品的 24/72 小时数据检验选题、开头和包装。下一步实现自动阶段缓存和发布任务锁；现有模板本身不执行缓存或锁。先提高证据、文案和画面增量，再考虑换整套渲染框架。

## V2.2 新闻入口

已实测接入新智元官网公开 JSON、量子位公开 RSS、OpenAI RSS、Google AI RSS 和 Anthropic Newsroom。机器之心、智东西和 AI科技评论为搜索/分享链接补充，不声称已自动采集原生微信内容。只把短字段交给编导，每源配额，真正过滤时间，媒体稿与事件时间分别核对；先深读三条再选题。细节见 `workflows/chai-news-radar-workflow.md` 和 `docs/AI公众号与一手信源调研-2026-10-01.md`。

新闻脚本使用 Python 3.9+ 的 zoneinfo，目标环境需要 IANA 时区数据。原始缓存留用户的 `.agent-reach` 目录，不放便携包。雷达运行命令不会创建定时任务；默认 10 分钟内可复用缓存，`--refresh` 即时重新读取。


### 生产路线确认 · 2026-10-03

用户在看过EP.233 ChatCut试验后决定：日更恢复原 MiniMax + 词级时间轴 + HyperFrames + MultiPost 路线。ChatCut 单独做数字人介绍等业务，不改动日更生产线。迁移和复用本包时按此边界处理。
