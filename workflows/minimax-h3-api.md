# MiniMax H3 / Hailuo 视频生成 API 参考

> 2026-10-14 从 MiniMax 官方文档整理（`platform.minimax.io/docs`）。
> 本文是 **v2.0 AIGC 支线**的技术底稿：把自有的角色与场景素材，用 reference-to-video 生成视频片段。
>
> **证据类型：官方文档转述。** 文档会变，实施前须回原文核对。

---

## 0. 两套接口（别混用）

MiniMax 的视频生成有**两代接口**：

| | 旧版（Hailuo 2.3 时代） | **V2（MiniMax H3）** |
|---|---|---|
| 创建 | `POST /v1/video_generation` | `video-generation-v2-create` |
| 场景 | t2v / i2v / fl2v / s2v 分开的端点 | **一个端点用 `content[]` 组合** |
| 输入 | `prompt` + `first_frame_image` 等字段 | **text / image / video / audio 都可作为参考** |
| 计费 | 常规 API | **必须 Pay-as-you-go** |

**给 v2.0 用 V2**（多模态参考、可传视频与音频参考、参考图最多 9 张）。

---

## 1. V2 / MiniMax H3（推荐）

### 端点

```
POST https://api.minimax.io/v1/video_generation        # create
GET  .../video-generation-v2-query?task_id=<id>        # 查询（保留 7 天）
     .../video-generation-v2-list                      # 列表（分页、可按状态/模型筛）
     .../video-generation-v2-delete                    # 取消排队中的 / 删除已完成的记录
     .../video-generation-v2-h3-context-ir             # 把多模态上下文解读成结构化提示词
     .../video-generation-v2-regeneration              # 把 768P 成片重生成到 2K
```

**认证**：`Authorization: Bearer <API_KEY>` —— 在 **Account Management → API Keys** 取。

### 模型

| 模型 | 能力 | 分辨率 | 时长 |
|---|---|---|---|
| `MiniMax-H3` | t2v / i2v（首帧·尾帧）/ reference-to-video | `768P` · `2K` | **4–15 秒** |
| `MiniMax-H3-Max` | 同上，**更快**；参考支持图/视频/音频 | `480P` · `768P`（不支持 2K） | 5–15 秒（不支持 4 秒） |

### `content[]`：用角色（role）声明每个输入

元素以 `type` 区分：`text` / `image_url` / `video_url` / `audio_url`，并可带 `role`。
**每个请求必须包含至少一个非空 `text`（提示词是必填）。**

| 场景 | 组合 |
|---|---|
| 文生视频 | 仅 1 个 `text` |
| 图生视频（首帧） | `text` + 1 image（`role=first_frame`，或省略 role） |
| 图生视频（尾帧） | `text` + 1 image（`role=last_frame`） |
| 图生视频（首+尾帧） | `text` + 2 images（首帧与尾帧各一） |
| **参考生视频（本期要用）** | `text` + 任意组合：`reference_image`（**≤9**）/ `reference_video`（≤3）/ `reference_audio`（≤3） |

### 输入限制（官方表）

- **请求体总量 ≤ 64 MB**；大文件请用**公网 URL**，避免 Base64
- **图片**：JPG/JPEG/PNG/WEBP/HEIC/HEIF；单文件 ≤30MB；宽高 256–5760px；宽高比 0.4–2.5；首帧 ≤1、尾帧 ≤1、参考图 ≤9
- **参考视频**：MP4/MOV；H.264/AVC 或 H.265/HEVC，音频 AAC/MP3；单文件 ≤50MB；≤3 段；每段 2–15 秒且**总时长 ≤15 秒**；宽高 256–5760px；宽高比 0.4–2.5；帧率 23.976–60
- **参考音频**：WAV/MP3；单文件 ≤15MB；≤3 段；每段 2–15 秒且**总时长 ≤15 秒**

### 其它字段

- `resolution`：按模型（见上表）
- `duration`：整数秒；`MiniMax-H3` 4–15，`MiniMax-H3-Max` 5–15
- `ratio`：`adaptive` / `21:9` / `16:9` / `4:3` / `1:1` / `3:4` / `9:16`
  - **文生视频必须显式指定**，且**不能用 `adaptive`**
  - 图生视频（含首/尾帧）**强制 `adaptive`**（传别的值不报错但被忽略）
  - 参考生视频**可选**，默认 `adaptive`；实际比例从查询接口的 `ratio` 字段读
- `callback_url`：**先做 challenge 校验**——MiniMax 会 POST 一个含 `challenge` 字段的请求，你必须在 **3 秒内原样返回该值**；校验通过后每次状态变化都会推送（结构同查询接口）。状态：`queued` / `running` / `succeeded` / `failed` / `cancelled`

### 创建示例（参考生视频）

```bash
curl -X POST https://api.minimax.io/v1/video_generation \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "MiniMax-H3",
    "resolution": "1080P",
    "duration": 6,
    "ratio": "9:16",
    "content": [
      {"type": "text", "text": "<提示词：identity-preserve + 场景 + 动作 + 镜头>"},
      {"type": "image_url", "role": "reference_image", "image_url": {"url": "<角色图 URL>"}},
      {"type": "image_url", "role": "reference_image", "image_url": {"url": "<场景图 URL>"}}
    ]
  }'
# → {"task_id": "...", "base_resp": {"status_code": 0, "status_msg": "success"}}
```

---

## 2. 旧版接口（Hailuo 2.3 时代，仍可用）

### 文生视频 `POST /v1/video_generation`

```json
{"model":"MiniMax-Hailuo-2.3","prompt":"...","duration":6,"resolution":"1080P"}
```

**`prompt` ≤ 2000 字符。** 对 `MiniMax-Hailuo-2.3` / `MiniMax-Hailuo-02` / `T2V-01-Director`，可用 `[命令]` 语法控制镜头。

**支持的 15 个镜头命令**（本期最有价值的可复用知识）：

| 类别 | 命令 |
|---|---|
| 平移 Truck | `[Truck left]` `[Truck right]` |
| 摇 Pan | `[Pan left]` `[Pan right]` |
| 推拉 Push | `[Push in]` `[Pull out]` |
| 升降 Pedestal | `[Pedestal up]` `[Pedestal down]` |
| 俯仰 Tilt | `[Tilt up]` `[Tilt down]` |
| 变焦 Zoom | `[Zoom in]` `[Zoom out]` |
| 晃动 Shake | `[Shake]` |
| 跟随 Follow | `[Tracking shot]` |
| 固定 Static | `[Static shot]` |

**用法规则**
- **组合**：一个 `[]` 里写多个命令表示**同时生效**，如 `[Pan left,Pedestal up]`；**建议最多 3 个**
- **顺序**：命令按出现顺序执行，如 `"...[Push in], then...[Pull out]"`
- **自然语言**也能用，但**显式命令更准**

**其它参数**
- `prompt_optimizer`（默认 `true`）：是否自动优化提示词；**要精确控制就设 `false`**
- `fast_pretreatment`（默认 `false`）：开了优化器时减少优化耗时（仅 Hailuo-2.3 / 02）
- `duration`：默认 6。Hailuo-2.3：`768P` → 6 或 10；`1080P` → 6
- `resolution`：`720P` / `768P` / `1080P`（依模型与时长；Hailuo-2.3 默认 768P，6 秒可选 1080P）
- `callback_url`：**校验方式不同**——同上 challenge 回显；状态值为 `processing` / `success` / `failed`

### 图生视频 `POST /v1/video_generation`（i2v）

在 t2v 的字段基础上增加：
- `first_frame_image`：**公网 URL 或 Base64 Data URL**（`data:image/jpeg;base64,...`）
- 另有首+尾帧（fl2v）与**主体参考**（s2v）两个变体

### 查询与下载（两代通用思路）

```
GET /v1/query/video_generation?task_id=<id>
→ {"task_id":"...","status":"Success","file_id":"...","video_width":1920,"video_height":1080}

GET /v1/files/retrieve?file_id=<id>
→ 取下载地址
```

**状态值**：旧版 `Preparing` / `Queueing` / `Processing` / `Success` / `Fail`；V2 为 `queued` / `running` / `succeeded` / `failed` / `cancelled`。

---

## 3. 计费：网页额度 ≠ API 额度

官方原文：

> To use MiniMax H3 or MiniMax H3 Max, please select the **Pay-as-you-go API**.

**H3 在 API 侧需要按量付费方案**；`hailuoai.video` 网页版的积分与它是两套。

**因此 v2.0 的路线是两步**：
1. **先用网页版验证质量和提示词**（用已有积分，零新增成本）
2. **验证通过后再开 API 建线**（脚本化、可无人值守）

---

## 4. 本项目的用法（v2.0 计划）

**目标**：用「高性价比人生指南」项目里已有的素材生成 AIGC 片段。

**可用素材**（`videos/chai-life-guide-comedy-v1/`）：

| 素材 | 路径 | 用途 |
|---|---|---|
| 柴犬角色表情表（4 表情） | `assets/character/chai-shiba-sprites.png` | `reference_image`（裁单张） |
| 场景插画 4 张 | `assets/scenes/{office,reader,magician,sunkcost}.png` | `reference_image` |
| 角色设定表（含浣熊搭档） | `~/.codex/generated_images/01a10157-…/` 中的角色排排站图 | `reference_image` |
| 配音 | `assets/voice/{v1,v2,v3,v5}` | 可作为 `reference_audio` |

**第一次验证的参数建议**
- `model: MiniMax-H3` · `resolution: 768P` · `duration: 6` · `ratio: 9:16`（与账号一致）
- `content`：1 段 text（identity-preserve 写法，沿用项目 `IMAGE-PROMPTS.md` 的风格）+ 1–2 张 `reference_image`
- **评估维度**（按 `docs/端到端流程.md` 的硬门）：① 角色像不像 ② 动作/口型能不能用 ③ 能不能直接剪进成片

**为什么用 reference-to-video 而不是 first-frame**：我们要的是**角色一致 + 场景可控**，不是让一张静止图动起来。
参考图模式最多 9 张，正好够「角色表 + 场景 + 道具」。

---

## 5. 未做的事（如实记录）

- **未调用过 API**（没有 Pay-as-you-go 的 Key）
- **未在网页版生成过**（浏览器自动化受限于页签/地址栏合成输入）
- 镜头的 15 个命令**未实测**在 H3 上的效果与旧版是否一致（文档只对 Hailuo-2.3 / 02 / T2V-01-Director 承诺）
- 定价数字未取（文档只写了需要按量付费，具体单价见其 Pricing 页）
