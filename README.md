# chai-ai-shorts-workflow

**柴主编「只讲一件事」——AI 工具/新闻短视频的端到端生产工作流。**

一套可复用的日更流水线：从选题发现、证据核验、分镜与脚本、配音与合成，到质检、封面、发布包与发布后复盘。
不是模板合集，而是**一套带硬门的流程**——每一步都有可执行的检查脚本，通不过就不进入下一步。

> 本仓库只包含**流程、手册与脚本**，不含任何成片、封面、音频或往期内容。
> 所有账号 ID、路径与凭据均已移除或改为环境变量。

---

## 流程总览（V2.2）

```
选题发现 → 四问筛选 → 证据包 → 分镜 → 脚本 → 三件套检查 → 配音
   → 时间轴 → 合成 → 渲染 → 技术质检 → 封面 → 发布包 → 平台发布 → 发布后核实
```

### 1. 选题发现

- `scripts/chai_news_radar.py` — 带时间戳的官方/媒体线索雷达（OpenAI、Google、Anthropic、量子位、新智元…），输出简报与 JSON
- `scripts/chai_topic_radar.py` — 同赛道创作者选题雷达
- 工作流说明：`workflows/chai-news-radar-workflow.md`，信源配置：`workflows/chai-news-radar-sources.json`

### 2. 选题筛选（四问 + 评分）

每条选题必须答出四问，并在辅助评分中拿到 ≥9/12：

| 四问 | 说明 |
|---|---|
| 谁遇到问题 | 具体人群与具体场景，不是"所有人" |
| 想完成什么 | 观众要完成的任务 |
| 30 秒内能看见什么 | 可拍摄的证据、数字或画面 |
| 看完如何决定 | 可执行动作、适用边界**或放弃理由** |

**证据包先于脚本**：`sources.md` 必须逐条写明「断言 / 来源 / 日期 / 条件 / 证据类型」，并区分
**官方自述 / 实测 / 编辑判断**三种等级。

### 3. 画面与脚本

- 先 `STORYBOARD.md`，再 `SCRIPT.md`
- `scripts/chai_script_pace.py` — 口播语速与时长预估
- `scripts/chai_density_check.py` — 信息密度
- `scripts/chai_hook_check.py` — 开头四项（独立性 / 抓手 / 悬念 / 可信度）
- `scripts/chai_pillar_check.py`、`scripts/chai_rank_series_check.py`

### 4. 三件套检查（定稿门槛）

| 文档 | 检查什么 |
|---|---|
| `dbs-ai-check` | AI 写作指纹（22 项：排比、破折号、"不是 X 是 Y"、无出处强断言…） |
| `dbs-resonate` | 共鸣五维度（沉默解除 / 满足动机 / 立场框架 / 传播入口 / 信念结构） |
| `dbs-hook` | 开头四项与候选对比 |

通过后写 `dbs-gate.json`（含脚本 SHA256），才允许进入配音。

### 5. 配音与合成

- `scripts/minimax_tts.py` — MiniMax TTS，返回**词级时间戳**（用于逐词字幕）
- `workflows/minimax-tts-tuning.md` — 语速/情绪/发音字典调参
- 时间轴、分镜页与字幕由各期的 `build.py` 生成，用 HyperFrames 合成与渲染

### 6. 质检

| 脚本 | 检查 |
|---|---|
| `scripts/chai_caption_boundaries.py` | **字幕断词**：保护词是否被劈开（`--strict` 时非零退出） |
| `scripts/chai_caption_sync_check.py` | 字幕与音频时间轴一致性 |
| `scripts/chai_caption_band_check.py` | 字幕安全区 |
| `scripts/chai_layout_precheck.py` | 版面预检 |
| `scripts/chai_check_motion.py` | 动效规范（只允许 transform/opacity，避免布局属性抖动） |
| `scripts/chai_qa_frames.py` / `chai_visual_review.py` | 抽帧复核 |
| `scripts/chai_cover_check.py` / `chai_cover_margin.py` / `chai_cover_crop_check.py` | 三比例封面与安全边距 |

### 7. 发布包与发布

- `scripts/chai_release_preflight.py` — **离线预检**：文件完整性、哈希、评审绑定、媒体规格
- `workflows/chai-platform-publish-playbook.md` — 三平台发布策略
- `workflows/chai-multipost-desktop-api.md` — MultiPost 桌面端本地 API 的完整手册
- `scripts/chai_publish_mcp.py` — 本地发布器（**凭据只从环境变量或系统钥匙串读**）

### 8. 发布后

- `workflows/episode-tracker.md` — 期次跟踪
- `workflows/chai-editor-performance-template.md` — 数据快照模板
- `scripts/chai_data_report.py` / `chai_published_cover_check.py` — 平台侧核对

**发布后必须做平台侧核实**（作品数 / 笔记数 / 内容管理页），不把任务状态当发布成功。

---

## 目录结构

```
docs/         流程规范（docs/端到端流程.md 是权威版本）与历次升级记录
workflows/    可执行手册、模板与配置
scripts/      检查与生产脚本（97 个）
```

---

## 设计原则

1. **证据先于脚本**。没有可拍摄、可核对的证据，就写不出脚本。
2. **区分证据等级**。官方自述、实测、编辑判断三者在片中必须能被观众分辨。
3. **不宣称未做的事**。没有实测就不出现"我试了"；素材来源在画面里标注。
4. **硬门而非建议**。检查脚本通不过就不进入下一步；`--strict` 用退出码表达。
5. **可复算**。数字标注读取时刻；结论给出计算路径。
6. **诚实记录缺口**。每期的 `sources.md` 都有一节"缺口"，写明没验证的部分。

---

## 运行要求

| 依赖 | 用途 |
|---|---|
| Python 3 | 全部检查与生产脚本 |
| ffmpeg / ffprobe | 音频处理、抽帧、媒体探测 |
| Node.js + [HyperFrames](https://www.npmjs.com/package/hyperframes) | 分镜合成与渲染 |
| MiniMax API Key | 配音（放在系统钥匙串或环境变量） |
| MultiPost 桌面端 | 平台发布（可选） |

**凭据约定**：脚本不硬编码任何密钥。需要的凭据通过环境变量或系统钥匙串读取，例如
`MULTIPOST_MCP_TOKEN`、`DOUYIN_ACCOUNT_ID`。

---

## 说明

- 这套流程是为一个具体账号（AI 工具类短视频）演化出来的，**不保证在其他账号上同样有效**。
- 文档里的经验结论都标了日期与适用范围；平台规则会变，请以当期平台规则为准。
- 不含任何平台密钥、账号 ID 或登录态。
