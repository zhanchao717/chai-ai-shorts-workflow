# 深度版（60–90 秒 / 7 场景）＋ 长视频（3–5 分钟 / 20–30 场景 / 分章节）改造说明

> 2026-09-11 深度版改造；2026-09-12 扩到**长视频档**（20–30 场景 + 章节结构 + 5 个新模板）。
> **日更 5 场景与深度版 7 场景路径零变化**：`gen_chai_frames.py` / `gen_chai_index.py`
> 在既有 spec（`specs/165.json` / `specs/168.json`）下的输出与改造前**逐字节相同**
> （回归证明见 §5 与 §9）。
> 相关脚本与本文档已同步到镜像 `~/.agents/skills/daily-ai-shorts/scripts/`。

## 0. 三种形态一览（先看这张表）

| 形态 | 总时长档 | 场景数 | 章节 | 走的模板 |
|---|---|---|---|---|
| 日更 | 25–45s | 5 | 无 | 01-hook / 02-facts / 03-mechanism / 04-action / 05-verdict |
| 深度版 | 60–90s | 7 | 无 | 上面 5 个 + 05-config / 06-verify（末场顺延到 07-verdict） |
| **长视频（新）** | **180–300s** | **20–30** | **3–5 章** | 深度版全部 + **chapter / quote / table / flow / case**（中间槽位按字段选） |

长视频的两个开关（都**缺省关闭**，所以老形态零变化）：

```bash
# ① 章节页之间用更长的转场（缺省 = --trans，即与场内转场一致）
python3 scripts/gen_chai_index.py /tmp/long-proj content/episode-900 "LONG FORM / 900" \
    --scenes=auto --spec /tmp/long/spec24.json --chapter-trans 1.2

# ② 章节进度指示（缺省不渲染；开了才会改动 index.html）
python3 scripts/gen_chai_index.py ... --chapter-progress

# ③ 写稿阶段的长档节奏门禁（阈值规则不变，档位换成 180–300）
python3 scripts/chai_script_pace.py content/episode-900 --min-duration 180 --max-duration 300
```

---

## 1. 核心约定：1 段音频 = 1 个场景，场景键 = composition id = 帧文件名

| 场景槽位 | 日更 5 场景 | 深度版 7 场景 | 模板 |
|---|---|---|---|
| 01 | `01-hook` | `01-hook` | 钩子（既有） |
| 02 | `02-facts` | `02-facts` | 事实（既有） |
| 03 | `03-mechanism` | `03-mechanism` | 机制三节点（既有） |
| 04 | `04-action` | `04-action` | 行动两口井（既有） |
| 05 | `05-verdict` | **`05-config`** | **配置逐行（新）** |
| 06 | — | **`06-verify`** | **三步验证（新）** |
| 07 | — | `07-verdict` | 判词（既有模板，槽位顺延） |

- spec 的 `scenes` 键**必须以两位序号开头**：写纯数字 `"01".."05"`（既有各期的写法）或
  写 `"05-config"` 都吃；两种写法归一到同一套帧文件名，**既有 spec 一个字不用改**。
- 序号必须从 `01` 连续；`audio_meta.voices` 段数必须等于场景数，不等就**显式报错**（不静默）。
- `05-config` / `06-verify` 各自独立可选：spec 里 `05` 带 `lines` 才启用配置模板，
  `06` 带 `checks` 才启用验证模板。两个都缺 = 老 5 场景行为。

---

## 2. `gen_chai_frames.py` 新增模板的 spec 契约

### 2.1 `05-config`（配置逐行，一屏讲完一份 YAML）

```json
"scenes": {
  "05-config": {
    "hero_l1": "配置文件按行抄",              // 顶部小标题（30px，≤34 个中文字）
    "hero_em": "environments",               // 可选；{em} 占位符的强调串（#D1FF00）
    "lines": [
      {"t": "name: proxy-fix",               // 代码正文（等宽 CobaltMono，22→19px 自适应）
       "hl": true,                           // 本行高亮：强调色 + 淡底 + 左侧 3px 竖条
       "c": "名字只给模型看"},                // 可选：右侧注释列
      {"t": "environments:", "i": 1, "c": "这一段是环境变量入口"},
      {"t": "HTTPS_PROXY: http://127.0.0.1:7890", "i": 2, "hl": true, "c": "写本机代理端口"},
      {"t": "NO_PROXY: 127.0.0.1,localhost", "i": 2, "c": "本机与内网直连"},
      {"t": "PATH: ${PATH}", "i": 2, "c": "保留原路径"}
    ],
    "note": "SOURCE · DSH 官方文档《网络代理》＋本期实测"
  }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `lines` | ✅ | 1–12 项；不足 6 项按 6 行留白；每项 `{t, i?, hl?, c?}` |
| `lines[].t` | ✅ | 代码正文。**不换行**：超宽时先用 `chai_layout_precheck.width_px` 同一宽度模型把字号 22→21→20→19 逐档降；19px 仍放不下就**显式报错**并给出「拆行 / 降 i / 缩 c」三条改法 |
| `lines[].i` | ❌ | 缩进层级（整数，1 级 = 2 个半角空格），建议 0–2 |
| `lines[].hl` | ❌ | `true` = 高亮该行 |
| `lines[].c` | ❌ | 右侧注释；注释列宽度按**最长注释**统一，所以一条长注释会抬高全局预算 |
| `hero_l1` | ❌ | 缺省 `"配置逐行读"`；可写 `{em}` |
| `note` | ✅ | 底部来源行 |

宽度预算（1080×1920 安全区，左右各 110px，内容宽 860px）：
`860 − 卡片内边距 34×2 − 计数器列 − 间距 36 − 注释列`；缩进每级另占 11.5px。

### 2.2 `06-verify`（三步验证清单）

```json
"scenes": {
  "06-verify": {
    "title": "三步确认它{em}真的生效",        // 卡头标题（38px，可含 {em}）
    "sub": "照做一遍，别靠感觉",              // 可选；卡头副标题（23px 等宽）
    "checks": [                              // 必须正好 3 步
      {"t": "重启一次终端",
       "s": "环境变量只在进程启动时读取，不重启就不会生效",
       "tag": "第一步"},
      {"t": "打印代理变量",
       "s": "确认 HTTPS_PROXY 指的就是你本机的代理端口",
       "tag": "echo $HTTPS_PROXY"},
      {"t": "再请求一次接口",
       "s": "还是连不上就回头看 NO_PROXY 有没有把目标写成直连",
       "tag": "最后复查"}
    ],
    "num_style": "circled",                  // 可选：circled ①②③（默认）/ ascii 123 / cjk 一二三
    "note": "SOURCE · DSH 官方文档《网络代理》· 本期验证步骤"
  }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `checks` | ✅ | **必须正好 3 项**，多/少都显式报错（版式按 3 步设计） |
| `checks[].t` | ✅ | 步骤主文案（38px，≤17 个中文字；不用 nowrap，超了换行） |
| `checks[].s` | ✅ | 步骤说明（22px，≤34 个中文字，正常折行不溢出） |
| `checks[].tag` | ❌ | 右侧小标签（19px 等宽，≤14 个字符），缺省不渲染 |
| `title` / `sub` / `note` | title+note 必填 | `sub` 缺省整行不渲染 |

版式：**竖向编号徽章 + 左侧虚线导轨 + 横排步骤**，与既有 `03-mechanism`
（横向 3 节点卡 + 箭头 + 底部断言条）刻意区分：不同轴、不同构图、无箭头、有回勾感。
卡片 `min-height:720px`、随内容长高，**不使用 `white-space:nowrap`**——
不重蹈 `.fnode .t`（26px + nowrap 无回退，被 flex 压到 ~191px）的覆辙。

---

## 2A. 长视频 5 个新模板的 spec 字段契约（2026-09-12）

> 全部**按字段启用**：spec 里没有对应字段就完全不启用（老 spec 一个字不用改）。
> 排片规则：槽位 **01–04 固定用既有模板**，**末场固定是判词卡**（`NN-verdict`），
> **中间槽位**按字段选：`lines` → 05-config、`checks` → 06-verify、
> 其余按 `no+title` → chapter、`quote` → quote、`table` → table、
> `steps` → flow、`chain` → case。中间槽位一个字段都对不上会**显式报错并列出全部契约**
> （不静默生成空白帧）。
>
> 皮肤全部沿用同一套常量：深色底（`#1F1F1F→#101010`）、酸柠强调 `#D1FF00`、
> `CobaltMono` + `Noto Sans SC`/`PingFang SC`、底部 `.note` 来源行、
> `DECOR`（`.slash` 光斑 / `.rline` 酸柠条 / `.dash` 上下虚线 / `.cross` 四角准星）、
> `.idx` 场号水印。
>
> **宽度自检**：每个模板在**生成期**用 `_estw()`（与 `chai_layout_precheck.width_px`
> 同一套字宽模型）逐档降字号并断言放得下；降到底还放不下就 `SystemExit` 并给出改法
> ——**绝不静默截断、绝不静默溢出**。全部新模板**不使用 `white-space:nowrap`**
> （历史事故：`.fnode .t` 被 flex 压到 191px 折出孤字）。
> 竖向：卡片底边硬上限 **y1290**（`.note` 在 y1408），内容区 0..1290。

### 2A.1 `chapter`（章节页）

```jsonc
"06-chapter": {
  "no": 1,                                  // 章节序号：1–30 会转汉字（1→一、12→十二）；
                                            //   想要阿拉伯数字就传字符串 "12"
  "title": "长视频为什么要分章",              // 章节标题（60px 起逐档降到 40px，最多折 2 行）
  "tag": "PART 1",                          // 可选；缺省 "CHAPTER"
  "steps": ["看一份真实长片的场景表",          // 可选；**最多 3 条**，每条 1 行（>3 条或放不下=报错）
            "认出章节页与内容页的分工",
            "把总时长拆成可控的段落"],
  "note": "SOURCE · 内部创作规范《长视频形态》· 第 1 章"
}
```

版式：**超大号酸柠章节序号（268px，左列出血小）+ 橙色 PART 标签 + 一条 860px title bar
（左侧 14px 酸柠条）+ 至多三条编号预览行**。
**与 `01-hook` 的刻意区分**：01 是「顶部 warn 条 + 118px 双行大字 + 底部 52px 大数字卡」，
chapter 没有大数字卡、没有双行大字，靠**序号 + 章节标题条**立住。

### 2A.2 `quote`（官方原文引用页）

```jsonc
"07-quote": {
  "quote": "缓存只在同一段长前缀被反复提问时才有价值，短前缀加标记只是多花一次写入。",
                                            // 引文：68px 起逐档降到 36px，**最多折 6 行**
                                            //   显式断行用 \n（模板按行渲染）
  "head": "成本口径",                        // 可选；引文下面的小标题
  "source": "官方文档《Context Cache》· 使用建议",   // **必填**：来源角标（文档名 + 小节）
  "note": "SOURCE · 官方文档《Context Cache》· 使用建议"
}
```

版式：**巨大酸柠引号（印刷件，深色字形 + 酸柠底，不参与对比度门禁）+ 大字引文 +
底部虚线分隔 + 右侧酸柠来源角标**。引文含 HTML 标签会显式报错（只做转义输出）。

### 2A.3 `table`（2 列 × 4–6 行对照）

```jsonc
"10-table": {
  "title": "本地代理的三种写法",              // 可选；缺省整块不渲染
  "sub": "PROXY CONFIG",                    // 可选；等宽副标题
  "table": {
    "head": ["写在哪", "作用范围"],           // 可选；必须正好 2 列
    "rows": [                               // **必须是 3–6 行**（含表头共 4–6 行）
      ["环境变量", "当前进程及其子进程"],
      {"k": "配置文件", "v": "当前仓库的所有命令", "hl": true},   // hl=true 整行高亮
      ["命令行参数", "只有这一次调用"],
      ["全局默认", "所有项目都吃"]
    ]
  },
  "note": "SOURCE · PROXY CONFIG 对照表"
}
```

版式：**圆角栅格表，首行等宽表头（酸柠）+ 分隔行；行高按内容自适应；`hl` 行整行高亮
（酸柠淡底 + 左侧 3px 酸柠条 + 文字转酸柠）**。
⚠️ **不用 nowrap 赌宽度**：单元格正常折行，换行数由生成期宽度模型把住
（行名列可用宽 = 内容宽 18% − 内边距；数值列 82% − 内边距；
最小档 20px 下任一格要折 3 行以上即**报错**并给出改法）。

### 2A.4 `flow`（横向步骤条 3–5 步）

```jsonc
"09-flow": {
  "title": "一次请求里，缓存是这样被读到的",   // 可选
  "sub": "READ → MATCH → HIT → BILL",       // 可选
  "steps": [                                // **必须 3–5 步**
    {"t": "先看标记", "s": "cache_control"},  //   t = 步骤标题（24px→18px，172px 内最多 2 行）
    {"t": "往前找前缀", "s": "最多 20 块"},    //   s = 可选说明（17px→15px）
    {"t": "命中就直接用", "s": "不再重算"},
    {"t": "最后按一成计费", "s": "输入原价"}
  ],
  "note": "SOURCE · 官方文档《Context Cache》· 命中流程"
}
```

版式（**轴向刻意区别于既有两块**，这是设计约束不是审美偏好）：

| 模板 | 结构 | 轴向 |
|---|---|---|
| `03-mechanism`（既有） | 横向 3 个 248×200 节点卡 + 卡间大箭头 | 离散卡片，**无连续轴** |
| `06-verify`（既有） | 竖向三步 + 左侧虚线导轨 | 竖向，无连续轴 |
| **`flow`（新）** | **贯穿全宽的一条连续进度条 + 轴上圆点 + 已走过段酸柠填充 + 时间刻度** | **横向时间线** |
| **`case`（新）** | 竖向三张因果卡 + 向下小箭头 | 竖向，**带因果标记** |

### 2A.5 `case`（现象 → 机制 → 结果 因果链）

```jsonc
"05-case": {
  "kicker": "CASE 01",                      // 可选；橙色小标签
  "title": "为什么长片剪完反而更平",           // 可选；36px，≤23 个中文字
  "chain": [                                // **必须正好 3 段**，每段都要 hd
    {"hd": "现象", "t": "24 个场景逐段都合格，连起来看却一直平到底"},
    {"hd": "机制", "t": "每段都是同一种版式，眼睛找不到章节边界"},
    {"hd": "结果", "t": "每 4–6 场插一个章节页，节奏靠版式差异撑住"}
  ],
  "note": "SOURCE · 本期实测 · 长片节奏记录"
}
```

版式：**竖向三张因果卡 + 卡间向下小箭头（CSS 画的竖线 + 三角，不是字形）+ 左侧竖向
rail + 每卡左上编号徽章（首段酸柠）**。正文 32px 起降到 24px，最多折 2 行。

---

## 2A.0 槽位路由：**长片按字段、扁平按槽位**（2026-09-12 修 EP.170 的 KeyError）

> **症状**：`python3 scripts/gen_chai_frames.py specs/170.json` →
> `KeyError: 'mm'`（03 槽是 `table` 而代码去读 `s["mm"]`）。

**根因**：路由规则原先只有一半 ——

| | 01–04 | 中间槽位 | 末场 |
|---|---|---|---|
| 旧行为 | **写死模板**（01 读 `warn_a`、03 读 `mm`…） | 按字段（`lines`/`checks`/`chapter`…） | 写死判词 |

`specs/170.json` 是长片，把 `table` 放在 03、`flow` 放在 04、`facts` 放在 05、`action` 放在 08
—— 于是 03 先崩；就算绕过 03，04 也会因为取不到 `w1_t` 再崩一次。
更糟的是 `chai_layout_precheck.py` 是**按字段**扫模板的，所以它对同一份 spec 报 ✅，
**两条口径不一致**，问题没能被提前拦下。

**新规则（两条路径严格分开）**：

| spec 形态 | 路由方式 |
|---|---|
| **带 `chapters`**（长片） | **每一槽都按字段路由**（含 01–04 与末场）。槽位号只决定顺序，不决定模板 |
| **不带 `chapters`**（扁平，既有 5/7 场景各期） | **行为完全不变**：01–04 固定模板、末场判词卡、config 第 5 槽、verify 第 6 槽 |

**判别表**（`ROLE_REQUIRED`，顺序 = 判别性从强到弱；用**判别性字段**而不是「该模板用到的全部
字段」，否则会互相抢 —— 例如 `chapter` 也有 `steps`）：

| 顺序 | 模板 | 必需字段 |
|---:|---|---|
| 1 | `chapter` 章节页 | `no` |
| 2 | `table` 对照表 | `table` |
| 3 | `case` 因果链 | `chain` |
| 4 | `quote` 引用页 | `quote` |
| 5 | `flow` 流程条 | `steps` |
| 6 | `config` 配置逐行 | `lines` |
| 7 | `verify` 三步验证 | `checks` |
| 8 | `action` 行动两口井 | `w1_t` + `w2_t` |
| 9 | `mechanism` 机制三节点 | `n1_t` + `n2_t` + `n3_t` |
| 10 | `facts` 事实卡 | `repo_big` |
| 11 | `hook` 首帧钩子 | `warn_a` + `warn_b` + `card_big` |
| 12 | `verdict` 判词卡（兜底） | `hero_l1` + `note` |

**长片的两条硬校验**（不静默放行）：

1. **第 1 槽必须是 `hook`** —— 首帧契约门禁（`chai_hook_check.py`）比的是 spec 的 `01` 槽
   文字与封面文字，01 槽不是钩子那件常驻门禁就失效了；
2. **末槽必须是 `verdict`** —— 收尾卡且 `#f5-hero` 只认 `hero_l1/hero_l2_pre/em/tail`。

**「帧名 ↔ index 场景表」一致性**：`gen_chai_frames.py` 的 `_canon_frame_name()` 与
`gen_chai_index.py` 的 `_canon()` 是**同一张表**（两处注释都标注了「必须逐字一致」）。
扁平路径两张表都是老表（零回归的前提）；长片路径纯数字键时按**该槽位的实际角色**起名。

**两个文件都吃 `chapters`**：`scenes_from_spec()` 也认 `chapters`（章内键仍是全局槽位号），
所以 `--scenes=auto` 对长片 spec 直接可用。

**预检已同步**：`chai_layout_precheck.py` 现在
① 用**同一个 `ROLE_REQUIRED` 顺序**扫描**全部槽位**（不再是「按字段粗筛」），
② 启用情况按角色打印（含既有角色命中数），
③ 在**写稿阶段**就报出「槽位/模板不匹配」「01 槽不是 hook」「末槽不是判词」并 **exit 1**。
反例实测（三个都对）：

```
❌ 槽位 / 模板不匹配 1 处（**写稿阶段就能拦下**，不用等生成期崩）：
  ❌ 首槽 01-hook：判定为「flow」，不是首帧钩子（hook） —— 首帧契约门禁比的是 01 槽文字与封面文字
  ❌ 末槽 24-verdict：判定为「case」，不是收尾判词（verdict） —— 末槽固定是收尾卡
  ❌ 场景 14-flow：字段对不上任何模板（生成期会直接报错中止）
```

### 2A.1 哪些脚本吃 `chapters`（2026-09-12 补齐）

长片 spec 顶层**没有 `scenes`、只有 `chapters`**。任何直接读 `spec["scenes"]` 的门禁都会
拿到空字典 —— 表现为「读不到场景」而不是报错，**比崩更危险**（EP.170 的
`❌ [首帧结论字] spec 场景 01 没有任何 hero* 大字` 就是这么来的）。

| 脚本 | 读 spec？ | 状态 | 说明 |
|---|---|---|---|
| `gen_chai_frames.py` | ✅ 读 | ✅ 已支持 | `_flat_scenes()`：无 `scenes` 时按章顺序展平；两者都给以 `scenes` 为准 |
| `gen_chai_index.py` | ✅ 读 | ✅ 已支持 | `scenes_from_spec()` 同样展平；`--scenes=auto` 对长片直接可用 |
| `chai_layout_precheck.py` | ✅ 读 | ✅ 已支持 | 展平 + 按字段扫**全部槽位**（§2A.0） |
| `chai_script_pace.py` | ✅ 读 | ✅ 已支持 | `--spec` 用于显示槽位真名；段数本就来自 `audio/NN.txt` |
| **`chai_hook_check.py`** | ✅ 读 | ✅ **本次修** | 原实现只读 `scenes` → 长片报 ❌。现按章展平（与上面三处**同一口径**），并新增一条 `[spec 形态]` 自证行 |
| **`chai_pipeline.py`** | ❌ 不读 | ✅ **无需改** | 场景表来自 `index.html`（`index_scenes()`），配音口径来自 `audio_meta.json` —— 与 spec 形态无关。**门禁A 本次另修一处**：长片稿的段落标记是「按章 + 块内每场一行 `NN.txt：`」，旧解析只认 `## Line N` / `## Scene NN`，对 EP.170 解析出 **0 句**（靠既有的空转守卫报 FAIL）；现先按 `NN.txt：` 行解析，解析不到才回退老规则（六期解析逐字不变） |
| `chai_check_motion.py` | ❌ 不读 | ✅ 无需改 | 只看成片 mp4（其 `specs` 变量是「视频规格」，与 spec.json 无关） |
| `chai_title_check.py` | ❌ 不读 | ✅ 无需改 | 只读发布包 `publish-copy.md` |
| `chai_qa_frames.py` | ❌ 不读 | ✅ 无需改 | 只读工程 `index.html` / 帧文件 |
| `chai_visual_review.py` | ❌ 不读 | ✅ 无需改 | 其 `scenes` 是**帧分组**的局部变量，不是 spec 场景 |

**新增规则（写脚本时照抄）**：读 spec 场景表的脚本一律这样取 ——

```python
scenes = (spec or {}).get("scenes") or {}
if not scenes:                       # 长片：章节形态（章内键仍是全局槽位号）
    for c in (spec or {}).get("chapters") or []:
        scenes.update(c.get("scenes") or {})
```

### 2A.2 `SCRIPT.md` 的三种写法都要认（门禁侧）

| 写法 | 长什么样 | 谁在用 |
|---|---|---|
| ① `## Line N` + 缩进口播 | `## Line 1 — 对比钩子` | 日更 165–167 |
| ② `## Scene NN` + 缩进口播 | `## Scene 01 — …` | 深度版 / 长片 167D–169 |
| ③ **按章写稿** | `## 第一章｜…（001–006）` + 一章一段、块内每场一行 `01.txt：…` | 长片 EP.170 起 |

`chai_hook_check.py` 的 `script_line1()` 与 `chai_pipeline.py` 门禁A 的解析都已按
「① → ③（仅在**没有** `## Line/Scene` 标题时）→ ②」的顺序补齐；**③ 必须排在 ② 之前、
但只在没有 ①② 标题时才启用** —— 因为 167D/168/169 也有 `01.txt：` 行，
让 ③ 抢在 ② 前面会把它们的第一句判定改掉（实测会误伤）。

**期号目录解析**（`chai_hook_check.py`）：spec 的 `ep` 字段**不一定等于目录名**
（EP.167D 的 `ep="167D"`，目录却是 `content/episode-167-deep/`）。查找顺序为
`episode-{eps}` → `episode-{eps}-*` → `episode-<数字前缀>*`（取名字最长者）→
纯数字目录；**最后才**退到「最大期号目录」，且退回时**必须打印警告**
（原实现静默退到最新一期，导致 EP.167D 一直在用 **EP.170 的稿子**判「第一句」）。

---

## 2B. 章节结构（`chapters`）与长视频 spec 形态

两种写法**都能吃**，扁平路径行为不变：

```jsonc
// B) 分章（长视频新增）——章节内的场景键仍是**全局槽位号**（01…N 连续）
{
  "ep": "900",
  "proj": "/tmp/long-proj",
  "chapters": [
    { "id": 1, "title": "长视频为什么要分章",
      "scenes": { "01-chapter": {…}, "02-quote": {…}, "03-flow": {…},
                  "04-table": {…}, "05-case": {…}, "06-chapter": {…} } },
    { "id": 2, "title": "代理与缓存踩过的坑", "scenes": { "07-quote": {…}, … } }
  ],
  "chapter_progress": true,          // 可选；缺省关闭
  "cover": { … }                     // 封面契约不变
}
```

- `chapters` 与 `scenes` **二选一**；两个都给时以 `scenes` 为准，并校验 chapters 的键都在 scenes 里。
- 一个场景键只能出现在一章里（重复 → 显式报错）。
- `chapter_progress`（**缺省关闭**）：`true` 或 `{"mode":"chapter"|"slot"}` —— ⚠️ **2026-09-12（EP.171）更正：这个字段只管「帧内」的章节页角标，不管底部那行进度条。**
  两处是**两套开关**，此前文档把二者混为一谈（「文档有、代码无」的悬空说法）：

  | 开关 | 谁读 | 控制什么 | 形态 |
  |---|---|---|---|
  | spec 顶层 `chapter_progress` | **`gen_chai_frames.py`**（`_long_progress_html`） | **只有 `chapter` 模板帧内的右上角小角标** `#ch-prog`（如 `02 / 04`） | `true`（= `mode:"chapter"`）或 `{"mode":"chapter"\|"slot"}`；`slot` 模式显示「当前槽位 / 总槽位」 |
  | 命令行 `--chapter-progress` | **`gen_chai_index.py`** | 底部那行 `CHAPTER 02/04 · SCENE 07/24` | **只有布尔开关，没有 `mode`**（`gen_chai_index.py` 里不存在 `mode` 这个键——此前文档写成 `{"mode":…}` 属**悬空说明**，已改正） |

  也就是说：**想要底部进度条，必须给 `gen_chai_index.py` 传 `--chapter-progress`**；
  只写 spec 的 `chapter_progress` 只在章节页里多一个角标。
  **不传 `--chapter-progress` 时 index.html 与改造前逐字节相同**（`prog_html` 为空串）。
- **底部进度条是「逐场递增」的**（2026-09-12 EP.171 修）：EP.170 的实现**只在章节边界打点**，
  同一章内 5 场都停在章首编号（实测 12 场显示 `SCENE 07/24`）→ 现在**每一场都写一次**
  `CHAPTER NN/04 · SCENE MM/24`（24 场 = 24 条 `tl.set`，行数比旧实现多 `场景数 − 章节数`）。
- `--chapter-trans <秒>`：章节页之间的转场时长，**缺省 = `--trans`**（即老行为）。
  只有同时给 `--spec` 且 spec 带 `chapters` 时才知道哪几处是章节边界；
  传了比 `--trans` 更短的值会**显式报错**（章节转场就是要比场内转场更长）。
  24 场景 4 章实测：23 处交接 → 6 条 tween 用 1.2s（3 个边界 × 出/入）、40 条用 0.5s。

---

## 3. `gen_chai_index.py`：任意场景数

```bash
# 日更 5 场景（默认，行为不变）
python3 scripts/gen_chai_index.py videos/<slug> content/episode-NNN "<FURNITURE>"

# 深度版 7 场景：显式给场景表
python3 scripts/gen_chai_index.py /tmp/deep-proj content/episode-190 "DEEP / 190" \
    --scenes=01-hook,02-facts,03-mechanism,04-action,05-config,06-verify,07-verdict

# 深度版 7 场景：由 spec 自动推导（推荐，避免两处写岔）
python3 scripts/gen_chai_index.py /tmp/deep-proj content/episode-190 "DEEP / 190" \
    --scenes=auto --spec specs/190.json

# 交接动画时长（秒）可调，缺省 0.5 = 历史值
python3 scripts/gen_chai_index.py ... --trans 0.7

# 长视频 24 场景 / 4 章：章节转场 1.2s + 章节进度指示（两个开关都缺省关闭）
python3 scripts/gen_chai_index.py /tmp/long-proj /tmp/long/ep "LONG FORM / 900" \
    --scenes=auto --spec /tmp/long/spec24.json --chapter-trans 1.2 --chapter-progress
# → proj: index rebuilt, 24 scenes, total 240.0s, 4 chapters, 3 处章节转场用 1.2s, 章节进度指示 ON
```

- 过渡动画数 = 场景数 − 1（7 场景 = 12 条 tween；**24 场景 = 23 次交接 = 46 条 tween**）。
- 场景数 ≠ `audio_meta.voices` 段数 → 显式报错退 1，不会生成残缺 index。
- **注意**：逗号分隔值请写成 `--scenes=a,b` 或加引号。
- `--scenes=auto` 现在**也吃 `chapters` 形态**（章内键仍是全局槽位号，展平后按序取）；
  纯数字键按槽位归一到角色名（`_canon`），带角色名的键原样用 —— 与
  `gen_chai_frames.py` 的 `_fid` 归一表**必须逐字一致**（两处都在注释里标了）。
- `--chapter-trans` / `--chapter-progress` / `--chapters none` 三个开关见 §2B。

---

## 4. 深度版门禁调用方式

```bash
SPEC=specs/190.json
PROJ=videos/<slug>
EP=content/episode-190

# ① 时长档位门禁：深度版 60–90s（默认仍是 25–45，日更行为不变）
python3 scripts/chai_hook_check.py --project $PROJ --spec $SPEC \
    --min-duration 60 --max-duration 90

# ② 版面宽度预检（含 05-config 逐行预算 + 06-verify 步骤预算）
python3 scripts/chai_layout_precheck.py $SPEC

# ③ 三平台标题门禁
python3 scripts/chai_title_check.py $EP/publish-package-*/publish-copy.md

# ④ 工程体检（门禁A 配音↔脚本、成品流等长、收尾余量）
python3 scripts/chai_pipeline.py verify --episode 190 --project <slug>

# ⑤ 帧数 / 时长一致性（7 场景 = 7 帧 + 12 条转场）
npx --yes hyperframes@0.7.102 check --at 2,8,14,22,32,42,51
```

### 4.1 长视频（20–30 场景 / 180–300s）的门禁调用

```bash
SPEC=/tmp/long/spec24.json
PROJ=/tmp/long-proj
EP=/tmp/long/ep

# ① 版面宽度预检（含 5 个新模板的逐项预算 + **每种模板的启用情况**）
python3 scripts/chai_layout_precheck.py $SPEC
#   末段会打印：
#     ℹ️ 长视频模板启用情况（chapter / quote / table / flow / case）：
#        ✅ chapter  3 场：06-chapter、11-chapter、16-chapter
#        ✅ quote    3 场：07-quote、12-quote、17-quote
#        ✅ table    3 场：10-table、13-table、18-table
#        ✅ flow     4 场：09-flow、15-flow、20-flow、23-flow
#        ✅ case     4 场：05-case、08-case、14-case、19-case

# ② 写稿阶段长档节奏门禁（**阈值规则不变**，只换档位；另加「相邻段字数差」检查）
python3 scripts/chai_script_pace.py $EP --min-duration 180 --max-duration 300 --spec $SPEC
#   加 --spec 后槽位列会显示 05-case / 06-chapter 这类真名（不再是 01? … 24?）

# ③ 时长档位门禁（成片后）
python3 scripts/chai_hook_check.py --project $PROJ --spec $SPEC \
    --min-duration 180 --max-duration 300     # 已支持，无需改代码

# ④ 成片自动验收（规格/静帧/黑帧/静音）
python3 scripts/chai_check_motion.py $PROJ/renders/xxx.mp4 \
    --min-duration 180 --max-duration 300     # 已支持，无需改代码

# ⑤ 工程体检：0 error 才能渲染（**每场一个采样点**，24 场 = 24 个 --at）
AT=$(python3 -c "print(','.join(f'{5+10.5*i:g}' for i in range(24)))")
cd $PROJ && npx --yes hyperframes@0.7.102 check --at "$AT" --timeout=30000
```

`chai_hook_check.py` 另有 N 场景容忍：① 首帧场景键 `"01"` / `"01-hook"` 都认；
② `NUMERIC_RE` 量词表已补 **遍/趟/回/番/遭/圈**（EP.165「口头交代十遍」原被漏判为无数字信号）。

`chai_pipeline.py` 的场景表不再写死 5：`stage_sync` 按 `audio/` 实际段数同步、
`stage_gates` 按 index 实际场景数校验（5 场景路径输出与改造前逐字相同）。

---

## 5. 回归证明命令清单（可复跑）

```bash
# ── A. 既有 5 场景零回归：改前脚本 vs 改后脚本，逐字节 diff ────────────────
cp -R videos/agent-skills-standard /tmp/ep165/proj && rm -rf /tmp/ep165/proj/renders
python3 - <<'PY'
import json
d = json.load(open("specs/165.json")); d["proj"] = "/tmp/ep165/proj"
json.dump(d, open("/tmp/ep165/spec.json","w"), ensure_ascii=False, indent=2)
PY
pip3 install --quiet --target /tmp/chai-orig/pylib 2>/dev/null || true
# 改前脚本：取 git 历史或备份（本次用备份 scripts/gen_chai_frames.py.bak-20260911d 的同源副本）
python3 <改前>/gen_chai_frames.py /tmp/ep165/spec.json     # → /tmp/ep165/before/
python3 scripts/gen_chai_frames.py      /tmp/ep165/spec.json     # → /tmp/ep165/after/
diff -r /tmp/ep165/before/compositions/frames /tmp/ep165/after/compositions/frames && echo "帧逐字节相同"

# ── B. 5 场景 index 零回归 ────────────────────────────────────────────
python3 scripts/gen_chai_index.py /tmp/ep165/proj content/episode-165 "AGENT SKILLS / 165"
diff videos/agent-skills-standard/index.html /tmp/ep165/proj/index.html && echo "index 逐字节相同"

# ── C. 门禁零回归（EP.165/166/167 各跑四件，改前改后 diff）──────────────
for n in 165 166 167; do
  python3 scripts/chai_hook_check.py --project <proj-$n> --spec specs/$n.json
  python3 scripts/chai_layout_precheck.py specs/$n.json
  python3 scripts/chai_title_check.py content/episode-$n/publish-package-*/publish-copy.md
  python3 scripts/chai_pipeline.py verify --episode $n --project <slug-$n>
done

# ── D. 新路径可用：/tmp 下 7 场景测试工程 ─────────────────────────────
python3 scripts/gen_chai_frames.py /tmp/deep7/spec7.json          # 7 帧
python3 scripts/gen_chai_index.py /tmp/deep7/proj /tmp/deep7/ep "DEEP / 800" \
    --scenes=auto --spec /tmp/deep7/spec7.json                    # 7 场景 / 12 条转场
cd /tmp/deep7/proj && npx --yes hyperframes@0.7.102 check \
    --at 2.5,7.5,13,22,32,42,51 --timeout=30000                   # 0 error
npx --yes hyperframes@0.7.102 snapshot --at 32,42 --no-end -o /tmp/deep7/shots
swift /tmp/ocr.swift /tmp/deep7/shots/frame-00-at-32s.png         # 文字完整、无溢出
swift /tmp/ocr.swift /tmp/deep7/shots/frame-01-at-42s.png

# ── E. build_chai_timeline 吃 7 段音频 ────────────────────────────────
python3 scripts/build_chai_timeline.py /tmp/tl7                   # → clips 7
```

> ⚠️ 本节的 `<改前>` 指**改前脚本的逐字节副本**。2026-09-12 的长视频改造里，
> 那份副本放在 `/tmp/chai24/scripts/gen_chai_frames.baseline.py`
> （sha256 `15aaedb4242a3e26552e3b1a104344c395e8542e57b63ef34cb9e31cbcefa47b`），
> 完整做法与结果见 **§9.1**。注意**不要**拿 `scripts/gen_chai_frames.py.bak-*` 当基线：
> 那几个备份里有更早一版**封面**（第一版左右分栏构图），与当前脚本的产出本来就不同，
> 拿来对拍会误判成回归。

### 2026-09-11 实测结论（本机复跑）

- A：`01-hook … 05-verdict` 五帧 + `cover.html` + `captions.html` 与改前**逐字节相同**。
- B：`index.html` 与 `videos/agent-skills-standard/index.html` **逐字节相同**。
- C：EP.165/166/167 × 4 件门禁，**改前改后输出逐字相同**，全部 PASS（❌ 0）。
- D：7 帧全部生成、`--scenes=auto` 推出 7 场景、12 条交接 tween、
      `hyperframes check` = **0 error(s)**（8 warning / 8 info 均为既有皮肤特征：
      Google Fonts import、`.slash` pointer-events、深色底对比度提示）。
- E：`clips 7 · frames [1..7]`。
- OCR：`06-config` 六行代码 + 右侧注释列 + `06` 场号全部完整可读；
      `07-verify` 三个 ①②③ 徽章 + 步骤/说明/小标签 + `07` 场号完整，无裁切、无孤字。

---

## 6. 已知边界 / 待决策

1. **`05-config` 只吃第 5 槽、`06-verify` 只吃第 6 槽**（槽位即序号 = 音频段号）。
   若想换位置（例如配置放第 4 段），改 `gen_chai_frames.py` 里 `_fid[5] / _fid[6]`
   这两处映射即可 —— 没有做成 `--role-map` 参数，是因为「1 段音频 = 1 场景」的口播顺序
   本来就是作者定的，多一个参数反而更容易写岔。需要的话我可以补。
2. **`gen_chai_frames.py` 的 `durs` 口径与 `gen_chai_index.py` 的 `TAIL_PAD` 是两处常量**，
   改一处必须改两处（都已有注释标注）。建议后续合并成一个共享模块。
3. **一条超长注释会抬高整块代码列的预算**（注释列按最长注释统一宽度）。若某行注释很长，
   优先缩短注释而不是缩短代码。
4. `chai_check_motion.py` / `chai_visual_review.py` 未改：它们的时长档位已经是
   `--min-duration/--max-duration` 参数（默认 25/45），深度版渲染后用
   `--min-duration 60 --max-duration 90` 即可，无需改代码。

---

## 7. 封面：阿囤囤风格 + 三比例契约

> 2026-09-11 重做。旧封面是「克制的深色玻璃卡」（小字号 kicker chip、`#7A7A7A` 小字、
> 低对比），信息流里不抢眼，4:3 只是把竖版缩排。新封面改成**高对比大字 + 贴纸徽章 +
> 发光斜纹背景 + 柴主编抠图**，三比例各自排版。

### 7.1 三个比例各自设计（不是缩放）

| 比例 | 尺寸 | 构图 |
|---|---|---|
| **9:16**（同时是视频首帧） | 1080×1920 | 顶角 lime 胶囊 + 集数；主标题 2 行在 y426 起；行动条；柴主编抠图右下（含 lime 环 + 太阳光芒）；3 张贴纸绕场 |
| **3:4** | 1080×1440 | 同一套元素的**重新排布**：标题上移、人物右下、贴纸三个落点重算（不是等比缩小） |
| **4:3**（横版） | 1440×1080 | **标题在左、人物在右、贴纸绕场**：左栏 x70 起宽 648px 放标题+行动条，右栏是人物盘（x816 起 520px）+ 暖光 + 光芒；4 张贴纸分列右上/左中/右下/最右 |

**4:3 的构图决策与理由**

1. **左文右图对半分**（左栏 648px / 右盘从 x816 起）——横版信息流常被裁成 1:1，
   把标题压在左半、人物压右半，裁成方形时两边都还留得住主体。
2. **标题只占左栏宽度的 77%**（实测墨迹最宽 601px / 栏宽 648px），**右边缘 x671，
   与人物盘左边缘 x816 之间留 145px 净空**——标题永远不会压到人物身上（见 §7.5）。
3. **贴纸绕场而不是堆在标题旁**：4 个落点刻意避开三处会打架的区域——顶角胶囊
   （x70–~610）、集数（x≥1099）、左下小注（x74–394）。落座后页内自检，越界只 `console.warn`。
4. **贴纸按右边缘对齐**（`SEAT` 里的 `'r'`）：长文案（如「永久记忆（深度版）」）从右侧
   往左量宽度，不会溢出画布右边。

### 7.2 spec 契约（向后兼容；新增字段全部可选）

既有字段**全部继续可用**，且**旧 spec 一个字节都不用改**：

| 字段 | 必填 | 缺省回退 |
|---|---|---|
| `cover.kicker` | ❌ | `""` → 整个胶囊不渲染 |
| `cover.hero_l1` / `hero_pre` / `hero_em` / `hero_tail` | ✅ | 见下方「首帧契约」 |
| `cover.act` | ❌ | `""` → 行动条不渲染 |
| `cover.cap43` | ❌ | `""` → 左下小注不渲染 |
| `cover.font` | ❌ | `96`。**只当整体档位**（夹到 ×0.90–×1.15），真实字号由宽度收敛决定 |

新增可选字段：

```jsonc
"cover": {
  "stickers": [                        // ≤6 条；缺省 = 由 kicker/act 自动派生
    "支持字符串简写",
    {"t": "三份配置", "icon": "db", "bg": "cyan", "on": ["l916","l34","l43"]}
  ],
  //   icon ∈ db | bolt | shield | gear | plug | spark   （内联 SVG，几何图形，无第三方标识）
  //   bg   ∈ lime | cyan | orange | cream | white
  //   on   = 只在这些比例显示；缺省三比例都显示
  "avatar": true,                      // 缺省 true；false = 不渲染人物
  "avatar_src": "assets/brand/chai-editor-avatar-cutout.png"   // 缺省即此路径
}
```

**`stickers` 缺省时的派生规则**（保证 165–167 这类旧 spec 也有系列一致的贴纸）：
`kicker` 按 `·` 切分，逐段配 `db/bolt/shield` 图标；再把 `act` 的 `·` 前段配 `gear` 图标。每条截断到 14 字。

**首帧契约不破**：主标题文本**始终**由 `hero_l1 + hero_pre + hero_em + hero_tail`
拼成（`em` 只换颜色，不换字），所以 `chai_hook_check.py` 的「封面文字 ↔ 正片首帧大字」
比对口径完全不变。`render_covers.mjs` 里「三比例主标题逐字一致」的校验也照旧生效。

### 7.3 人物抠图：`gen_chai_cover_avatar.py`

`assets/brand/chai-editor-avatar.png` 是 **RGB 无 alpha**（柴主编坐在深蓝渐变背景上），
本机没有 `hyperframes` CLI，所以用脚本**确定性**抠图：

```bash
python3 scripts/gen_chai_cover_avatar.py \
  videos/<slug>/assets/brand/chai-editor-avatar.png \
  videos/<slug>/assets/brand/chai-editor-avatar-cutout.png
```

1. 背景 = 蓝色主导且偏暗的像素；取**最大 4-连通域**丢掉青色角弧；
2. **补内部空洞**（眼睛/鼻子/嘴）——不然脸会镂空；
3. **边缘去污染**：跨边界的像素带背景色，若直接用会让羽化出「脏边/白边」。
   用 16px 网格加速的最近内部像素查找把这些像素的 RGB 换成纯主体色；
4. 羽化 + 紧裁剪输出 RGBA。

**换头像素材后要重跑这一步。** 没跑也不会崩：模板检测到缺文件会打印告警并回退成色块占位。

### 7.4 贴纸落座：两道关（2026-09-11 修 P0）

> **背景**：首版模板的贴纸把 9:16／3:4 的**主标题压住了**（`#st0`「AI 账单」盖在
> 酸柠色强调字「10 倍」上，同色叠加等于看不见），而且是**模板级**缺陷——坐标是硬编码的，
> 任何「强调字落在第二行右段」的选题都会复发。评审给的定级是 P0，理由是这个数字是
> `chai_hook_check` 依赖的首帧契约数字。

**第一关：生成期求解（正确性靠构造，不靠调参）**

`_derive_anchor_table()` 不再手写坐标，而是从**真实几何**求空位：

1. `scripts/measure_cover_geometry.mjs` 用 headless Chromium 1:1 渲染一张草稿封面，
   量出每个文案元素的真实盒（kicker / hero / act / cap / brand / idx / ava）、
   每个贴纸的真实尺寸，以及**旋转后**包围盒相对未旋转盒的位移。
2. `gen_chai_frames.py` 把这些数字喂给求解器：在画布上按 6px 网格枚举候选位置，
   逐一排除
   - 越安全区（`COVER_SAFE_MARGIN = 60`，按**旋转后**盒判）
   - 与文案/人物盘相交（避让区外扩 `COVER_ST_CLEAR = 24`）
   - 与已放贴纸太近（`COVER_ST_CARD_GAP = 26`）
   然后按「靠上优先、左右交替、离标题尽量远」打分选最优。
3. **两轮量测**：第一轮量 → 解 → 第二轮带上解好的锚点再量一次，把残余误差学回来。
   纯数学建模旋转包围盒总会差几像素（实测 dy 偏差到 17.8px，足够把贴纸挪到标题上），
   一轮反馈比继续推公式可靠。
4. **锚点 = 旋转包围盒的中心**。中心对旋转不变（`transform-origin: 50% 50%`），
   所以渲染期只要 `left = cx − w/2`、`top = cy − h/2` 就能精确落在算好的盒上。
   早期版本用左/右边缘当锚点，旋转会把盒挪走 `(rw−w)/2` —— 正是贴纸漫进标题的原因。

**为什么 `COVER_ST_CLEAR` 是 24 而不是 6**：贴纸要 `rotate(-7°..7°)`，旋转会让
包围盒位移十几像素；求解期不模拟这个位移，就靠这条净空把误差吃进去
（24 = 12px 位移 + 12px 视觉间隙）。

**第二关：渲染期硬门禁（这条比修坐标更重要）**

`cover.html` 内联 JS 在 `document.fonts.ready` 之后按**实测盒**逐个复核贴纸：
- 用 `getBoundingClientRect()`（**含 rotate 变换**）——旧版用 `offsetWidth/offsetHeight`
  的未旋转盒，旋转后左边缘实测 55.2px 已越 60px 安全线却报不出来；
- 避让区**从真实元素量**——旧版是手写常数，9:16 标题区底写 670 而实际 672–711，
  贴纸正落在那写小的 41px 里；
- 判「压字」要求**净空**而不是「不相交」——出货版贴纸旋转后与标题只差 **0.05px**，
  浏览器算的盒比手算的还小一点，于是「差一点点」被判成没压；视觉上描边+阴影已经贴到字了。
- **失败即抛错**：错误写进 `window.__coverLayoutErrors`，`render_covers.mjs` 读到非空就
  **非零退出**。旧版只 `console.warn`——评审明确指出「自检报了红却照样出图」是这次放行的直接原因。

锚点被占时求解器会先就近搜空位；搜不到才失败。**宁可少放一张贴纸，也不许压字。**

### 7.4.1 本次改动速查（口径与数值）

**一、贴纸永不压文案 / 不出安全区 —— 规则**

- 硬规则：贴纸盒**永远**不许与主标题（两行）、行动条、顶角胶囊、集数、左下小注、
  品牌字、人物盘相交（要求**净空**，不是「不相交」，见下）；**永远**不许出 60px 安全区。
- 放不下就**少放一张贴纸**，绝不压字。

**二、旧的 `SEAT` / `AVOID` 手写常数已删除**

首版是两张手写表（`SEAT.l916 = [[772,596,-7,'r'],[58,1252,6,'l'],[96,1614,-5,'l']]` +
`AVOID.l916 = [[88,96,700,202],[88,426,908,670],[92,1032,606,1094],[92,1768,440,1848]]` …）。
删掉的原因有两个，都是 P0 的成因：`AVOID` 比真实盒小（9:16 标题区底写 **670**，实际
**672–711**，贴纸正落在那写小的 41px 里），而 `SEAT` 是手调的，换个更长的标题就失效。

现在是**从真实几何算**，三个常数（都在 `gen_chai_frames.py`）：

| 常数 | 值 | 含义 |
|---|---|---|
| `COVER_SAFE_MARGIN` | `60` | 贴纸到画布边缘的最小留边；按**旋转后**盒判 |
| `COVER_ST_CLEAR` | `24` | 贴纸与任何文案/人物盘的最小净空（含旋转位移余量） |
| `COVER_ST_CARD_GAP` | `26` | 贴纸与贴纸之间的最小净空（阴影不互压） |

三比例各自的避让区边界（`_COVER_CSS` 同源，改 CSS 必须同步改 `COVER_KEEPOUT`）：

| 比例 | 画布 | 避让区 |
|---|---|---|
| 9:16 | 1080×1920 | 胶囊 y96–202 / 标题 y426–711 / 行动条 y1032–1094 / 小注 y1768–1804 / 品牌 y1812–1850 / 集数 x632–1000 y56–294 / 人物盘 x544–1032 y1282–1770 |
| 3:4 | 1080×1440 | 胶囊 y80–176 / 标题 y368–651 / 行动条 y840–896 / 小注 y1307–1340 / 品牌 y1345–1382 / 集数 x684–1004 y44–251 / 人物盘 x604–1032 y886–1314 |
| 4:3 | 1440×1080 | 胶囊 y66–158 / 标题 y356–593 / 行动条 y568–627 / 小注+品牌 y1010–1046 / 集数 x1099–1380 y40–222 / 人物盘 x816–1336 y178–698 |

**三、自检从 `console.warn` 改成硬失败**

- 叫什么 / 在哪：`cover.html` 内联 JS 的落座校验，结果写在
  `window.__coverLayoutErrors`；门禁在 **`scripts/render_covers.mjs`**（每个比例截图前
  `waitForFunction` 等它落地，非空即计入 `failed`）。
- 失败时行为：逐条打印「贴纸 N「文字」在 <比例> 找不到不压字的落点（锚点 …，盒 …）」
  → 该比例判失败 → **脚本非零退出**（实测 `EXIT CODE = 1`）。
  旧版只 `console.warn`，报了红照样出图 —— 这是评审认定放行的直接原因。

**四、`.pad .ct` 行号列**

`#6E6E6E` / 20px → **`#A8A8A8` / 21px**（在 `#1F1F1F` 上约 **6.9:1**，最坏情况 ≥4.2:1，
远超 hyperframes 的 3:1 门禁）。行号列是把 6 行对应到两次请求的**功能件**，不是装饰。

**五、`captions.html` 时长注入口径**

注入时同时改**两处**：根节点 `data-duration` 与 `var DURATION`，统一到
**最后一条字幕的实际结束时间**（`max(group.end)`；EP.168 = **83.441s**，
旧值 37.728 是脚手架残留）。替换带 `assert`：模板结构变了会**显式报错**。
理由：任何按子文档元数据裁剪/复用的下游会**静默截掉**几十秒字幕。

**六、为什么「DOM 层逐字一致」不足以证明可见性**

`textContent` 逐字一致只说明**文本节点是对的**，它看不见**像素**：贴纸是后画的兄弟节点，
完全可以在视觉上盖住标题，而 DOM 里的文字一个字都没少 —— `render_covers.mjs` 原本那三条
「三比例主标题逐字一致」全是绿的。这次 P0 正是这样漏掉的（而且盖住的是**同色酸柠**强调字，
连对比度差分都看不出来）。可见性只能靠像素证明：隐藏贴纸重渲染做差分，
量标题带的墨迹丢失与酸檬掩膜 IoU。

### 7.4.2 4:3 主版 + 中央 3:4 裁切安全窗（2026-09-11 新增）

**产品口径**：投放位主要按 **4:3** 展示（「因为只能展示这么多」），所以**先按 4:3 构图**；
同一张 4:3 还要能被**中心裁成 3:4**。于是三比例的关系变成：

| 输出 | 尺寸 | 怎么来的 |
|---|---|---|
| **cover-4x3.png** | 1440×1080 | **主版**，母版布局按 `--ms = 1` 渲染 |
| **cover-3x4.png** | 1080×1440 | **主版的中心 810×1080 窗口裁出来，放大 1080/810 = 1.3333×** |
| cover-9x16.png | 1080×1920 | 独立排版（**视频首帧**，首帧契约不变，主标题仍来自 `hero_*`） |

**为什么 3:4 是裁像素而不是按 `--ms = 4/3` 重渲染**：小数倍 CSS 缩放会让浏览器子像素布局
整体漂移，两条路径实测 **MAD 38/255**，根本对不上。改成「裁 + Lanczos 放大」后等价性变成
**构造性成立**（实测 `MAD = 0.0000`，差异>8 的像素 **0.0000%**）。分辨率代价是 810→1080
（1.333×），这是这条口径明示允许的。

**安全窗与母版几何**（`COVER_MASTER`，与 `_COVER_CSS` 的「母版」段同源）：

- 窗口 = **810×1080**，在 1440×1080 母版上居中 → **x315..1125 / y0..1080**；
  `--wx` = 窗口左缘 = `calc(315px * var(--ms))`，**所有内容按窗口左缘定位**。
- 母版是**少元素 + 全居中**（2026-09-11 第三版；第一版左右分栏、第二版四角散布都被否）：
  **元素只有 5 个**，全部以窗中心 x=405（画布 x=720）为轴：

  | # | 元素 | 窗内位置 | 实现 |
  |---|---|---|---|
  | ① | 顶部胶囊 kicker | y72–152，水平居中 | `.kicker{left:50%;transform:translateX(-50%)}` |
  | ② | 主标题 2 行（超粗+描边） | y232–430，居中 | `.hero{left:--wx;width:810px;text-align:center}` |
  | ③ | 人物抠图 | y640–1030，**390×390 = 36.1% 窗高** | `.ava{left:50%;translateX(-50%)}` |
  | ④ | 唯一强调标签 | y≈469–587，居中 | 求解器钉在窗中心（见下） |
  | ⑤ | 底部信息行 | y1024–1052，居中 | `.cap{width:810px;text-align:center}` |

- **集数水印 `.idx`、短横 `.rule`、行动条 `.act`、品牌字 `.brand` 在母版上全部 `display:none`**
  —— 用户口径「乱七八糟」，多一枚元素都是负担。9:16 仍保留它们。
- **贴纸最多 1 枚**：`_cover_stickers()` 的缺省派生改为只取 `act` 的收益前段
  （如「显式缓存命中 10%」），退路是 `kicker` 的第二段；母版求解器
  `_maxn = 1`。**贴纸锚点被钉在窗中心**（`COVER_MASTER_SEAT`），不再走
  box-left→中心 的换算（那条路会因旋转盒宽度差整体偏移）。
- **内容必须在窗内**：胶囊、主标题、标签、人物盘、底注。
- **只有纯氛围层可出窗/出画布**：`.sun`（光芒）、`.glow`（光晕）、`.stripes`（斜纹）、
  `.grid`（点阵）、`.vig`（暗角）。

**三道硬门禁**（写进 `window.__coverLayoutErrors`，`render_covers.mjs` 读到非空即
**非零退出**）：

1. **裁切安全门禁**（`cover.html` 内联 JS 的 `cropSafe()`）：
   - 逐个实测 `.kicker / .ava / .st / .act` 的 `getBoundingClientRect()`，任一越窗
     （容差 **8px**）即报 `裁切不安全：<元素> …`。
     **`.hero / .cap` 是满窗宽居中文本块**（宽度恒等于窗宽），其盒必然顶到窗口两边——
     那是排版方式不是越界，由第 2 条居中校验管；
   - **窗四边各 4px 带内墨迹像素必须为 0**：`cover.html` 是静态文件拿不到位图，所以
     `render_covers.mjs` 用 CDP 抓一张母版原尺寸截图（抓之前把 5 个纯氛围层藏掉），
     通过 `window.__coverRecheck(shot)` 喂回去逐像素扫描并重跑门禁；
   - **主标题必须正好 2 行**。
2. **居中校验**：`.hero / .ava / .st / .cap` 的中心 x 与窗中心偏差 **> 8px 即失败**，
   报 `不居中：<元素> 中心 x = …，窗中心 x = …，偏差 …px`。
3. **贴纸落座门禁**：见 §7.4。母版里求解器的活动范围就是窗口本身。

**复跑命令**

```bash
# ① 出三比例（9:16 首帧 + 4:3 主版 + 4:3 裁切派生的 3:4）——输出到 /tmp，别覆盖仓库产物
node scripts/render_covers.mjs /tmp/<骨架工程> --out /tmp/cover-check
#   退出码 0 = 落座门禁 + 裁切门禁 + 主标题 2 行 全过；非 0 = 有失败项，日志里有逐条原因

# ② 独立的裁切验证（对已出好的图做像素检验）
python3 scripts/chai_cover_crop_check.py /tmp/cover-check --out /tmp/cover-check
#   ① 等价性：4:3 中心裁 810x1080 → 放大 vs 实际 3:4（期望 MAD ≈ 0.0000）
#   ② 标题字形：三种视图各自的白字/酸柠簇数与 x 范围（裁切只是放大，不该丢字/切字）
#   ③ 主体与关键数字：人物盘与 lime 环在窗内的 bbox + 是否贴边（贴边=被切）

# ③ 只出 cover.html（两轮几何量测会跑 headless Chromium，调锚点时用这个更快）
python3 scripts/gen_chai_frames.py --cover-only specs/169.json --out /tmp/169-cover.html
#   加 CHAI_COVER_NO_MEASURE=1 可跳过量测、退回估算（门禁仍会硬校验）
```

**本机实测（2026-09-11，第三版：少元素 + 全居中）**

- **视觉桥（modlens）对 4:3 主版的原话**：*"centered, symmetric composition … The design is
  clean, simple, and uncluttered … There are no obvious design defects such as cut-off
  elements or unbalanced weight; the space is utilized harmoniously."*
  → 上一轮它报的「下方 40% 空白」「元素被切」两条**都没再出现**。
- **视觉桥未能复核裁切件**：对 3:4 连续 3 次撞 `429 quota`，配额耗尽。
  3:4 是 4:3 的**精确中心裁切**（`MAD = 0.0000`，差异>8 像素 `0.0000%`），
  逐像素与主版相同，所以桥对主版的结论可直接沿用；但**没有独立的 3:4 视觉结论**。
- **六个 spec 全绿**：165/166/167/167D/168/169 三比例出图成功，落座 + 裁切 + 居中
  三道门禁 **0 失败**，退出码全 0。
- **居中偏差**（窗中心 x=405）：胶囊 `/` 标题 `0.0px`（Range API 实测两行中心 720/720）
  `|` 标签 `0.0px` `|` 人物 `-0.5px` `|` 底注 `0.0px`。
- **逐 1/10 高度带墨迹占比**（藏氛围层后实测）：

  | spec | 0-1 | 1-2 | 2-3 | 3-4 | 4-5 | 5-6 | 6-7 | 7-8 | 8-9 | 9-10 | 空白带 | 最大相邻差 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | 168 | 9.4 | 11.1 | 19.7 | 30.8 | 14.4 | 9.7 | 34.5 | 38.2 | 34.8 | 16.4 | **0** | 24.8pp |
  | 169 | 10.9 | 13.1 | 25.3 | 27.7 | 13.8 | 8.5 | 34.5 | 38.2 | 34.9 | 19.1 | **0** | 26.0pp |

  （口径要求「无 0 带」已满足；「相邻差 ≤25pp」169 是 26.0pp，略超 1pp —— 已如实记录。）
- **窗四边各 4px 墨迹**：六个 spec 全部 `[0,0,0,0]`，合计 **0**。
- **主标题**：97–115px（168 为 97、169 为 100），**全部 2 行**。
- **人物**：390×390，窗内 bbox `[525,640,915,1030]`，**占窗高 36.1%**（口径 30–45%）。
- **帧零回归**：日更 5 场景的帧**逐字节不变**；只有 `167D/05-config.html` 变 1 处
  （§7.6 的行号列颜色，有意）。

### 7.5 验收清单（本机已跑）

```bash
# ① 三比例出图（别覆盖仓库里的既有封面 → 输出到 /tmp）
node scripts/render_covers.mjs videos/<slug> --out /tmp/cover-check

# ② 五个 spec 兼容（165/166/167/167D/168 全部三比例出图 + 落座校验）
for s in 165 166 167 167D 168; do python3 scripts/gen_chai_frames.py specs/$s.json; done

# ③ 像素级遮挡证明（隐藏贴纸重渲染 → 差分；看标题两行的字形簇与酸柠掩膜 IoU）
node scripts/cover_pixel_proof.mjs <proj> /tmp/proof     # 提示：本文件在 /tmp 的验证脚本里

# ④ 帧零回归：封面改动不许碰帧
#    用备份的改前脚本重跑，frames/*.html 与 captions.html 必须逐字节相同
```

**实测结论（2026-09-11，本机复跑）**

- **五 spec 落座自检全绿**：165/166/167/167D/168 三比例各一条
  「落座校验通过（贴纸不压文案、不出安全区）」，`render_covers.mjs` 退出码 0。
  把**救援搜索关掉**再跑一遍，五个 spec 依然零冲突 ⇒ 锚点是**算对的**，不是靠兜底救回来的。
- **像素级遮挡证明（EP.168）**，方法：隐藏贴纸重渲染做差分。

  | 指标 | 修复前（重建旧锚点+旧容差） | 修复后（出货） |
  |---|---|---|
  | 9:16 标题第二行带内变化 | **7.61%** | **0.00%** |
  | 9:16 酸柠掩膜 IoU | **0.551** | **1.000** |
  | 标题带丢失墨迹（无遮挡真值） | — | **0 / 32494 = 0.00%** |

  （评审在坏版本上量到 9.06% / IoU 0.491，与我重建的 7.61% / 0.551 同量级、同结论。）
  另：贴纸差分区 bbox 在 9:16 是 `y226..922`、3:4 是 `y208..856`，
  标题两行（9:16 y426–796、3:4 y368–728）**完全不含**在差分区内。
- **硬失败真的会失败**：把锚点全压到标题上并关掉救援搜索 →
  `EXIT CODE = 1`，并逐条打印
  「贴纸 0「AI 账单」在 l916 找不到不压字的落点（锚点 300,550,-7,l）」。
- **帧零回归**：165/166/167 的帧**零字节变化**；167D/168 只有 `05-config.html` 变了
  1 处（P1-2 的行号列颜色 `#6E6E6E → #A8A8A8` + 20px→21px），这是**有意**的修复。
- **captions.html**：只变 2 处，都是 P1-3 的时长契约修复（见 §7.6）。
- **无溢出**：三比例 `.hero` 的 `scrollWidth == clientWidth`。
- **4:3 标题不压人物**：标题墨迹最右 ≤ x671，人物盘最左 x816 → 净空 ≥145px。
- **OCR**：见 §7.8 的诚实结论（本机 Vision 对这套风格不可靠）。

### 7.6 顺带修的两个 P1

**P1-2 `05-config` 行号列对比度**（评审：`#6E6E6E` 只有 1.84–2.81:1，低于 3:1 门禁）

`.pad .ct` 由 `#6E6E6E` / 20px 改为 **`#A8A8A8` / 21px**。行号列是把 6 行对应到两次请求的
**功能件**，不是装饰，手机亮度下必须读得出来。新色在 `#1F1F1F` 上约 **6.9:1**；
即使背景按评审实测的更亮取值，最坏情况也 ≥4.2:1，稳过 3:1。

**P1-3 `captions.html` 根节点 `data-duration` 与真实时长不符**

模板里写死的 `data-duration="37.728"` 是脚手架残留，与本期无关。任何按**子文档元数据**
裁剪/复用的下游（Studio 预览、单场景重渲、`hyperframes` 快照）会**静默截掉几十秒字幕**。
现在注入时同时改两处：

- 根节点 `data-duration` 与 `var DURATION` 统一到**最后一条字幕的实际结束时间**
  （EP.168 = 83.441s；旧值 37.728 是错的，旧 `var DURATION` = 83.772 是整片时长）；
- 替换带 `assert`：模板结构改了（`id="captions-root"` 与 `data-duration` 不在同一标签）
  会**显式报错**，不静默漏改。

### 7.7 `render_covers.mjs` 的改动

只加了一件事：**落座校验变成硬门禁**。每个比例截图前读 `window.__coverLayoutErrors`，
非空就打印逐条原因并把该比例计入 `failed`，最后**非零退出**。三比例主标题一致性校验照旧。

### 7.8 ⚠️ 不确定项：本机 Vision OCR 认不准这套风格的强调字

**如实报告**（不接受「我觉得对」）：

- 把唯一一个 lime 强调字「**的**」交给 macOS Vision，**同一种排版，OCR 每次给不同答案**：
  `盲` / `管` / `品` / `实` / `鳃` / `天` / `與`，在 4:3 上偶尔又读对成 `的`。
  放大到 3× 仍然错（读成「與的」）。
- **对照组证明这是 OCR 的问题，不是渲染的问题**：
  1. 用同样的字体/PingFang SC、同样字号把「默认全是关的」画在白底黑字上，
     Vision **一次读对**；
  2. 拿**已知正确的参照图** `content/episode-005/atutun-xhs-cover.png` 去 OCR，
     它的标题 `AI开始进入` 被读成 **`AL开始进入`**（I→L），第二行整行漏掉；
  3. 我这个封面上的 `AI 不再失忆，` 也被读成 `Al 不再失忆，`。
     ⇒ 这类「lime 小字 + 深色描边 + 暗底」的组合，Vision 的 I/l/的 一族都会翻车。
- **渲染本身是对的**，证据是直接把那张 PNG 里的 lime 像素画成 ASCII，
  「关」「的」两个字的结构完整可辨（`的` 的 白 字旁 + 勺 清清楚楚），
  且 `.hero` 的 `textContent` 由 spec 拼接生成、`render_covers.mjs` 的三比例一致性校验通过。

**结论**：**没有**用 OCR 的「通过」来充当验收证据；`的` 这一处**请人工看一眼**
`/tmp/final-167D/cover-9x16.png`。若你要全绿可机检，把强调色从 lime 换回纯白即可
（本文件 §10 待决策第 1 条）。

---

## 8. 写稿阶段：节奏预检（`chai_script_pace.py`）

> 2026-09-11 新增。**写稿阶段就能跑**，不依赖 TTS / 渲染 / spec：只读
> `<content-dir>/audio/NN.txt`（或回退 `SCRIPT.md`）。

### 8.1 为什么加它：总时长合格 ≠ 节奏合格

EP.167D（成片 82.081s、配音 80.136s、7 场景）**总时长门禁是绿的**，但独立评审的核心内容批评是：

> **06-verify 段独占 20.2s（全片 24.6%）却只承载「会话 A 写、新建 B、问它」这种常识化流程**，
> 其中一行说明占屏 4s、信息增量极低 → **最掉人**。

既有门禁里 **没有任何一条能发现"某一段低密度却很长"**：`chai_hook_check.py` 判的是**总时长档位**
＋首帧契约，`chai_pipeline.py verify` 判的是**配音↔脚本一致 / 收尾余量**——一段 20s 的常识段
在两者眼里都是完全合规的。教训因此必须变成机械门禁：

```bash
# 写稿完成、还没配音时就能跑（此时只有估算，没有实测）
python3 scripts/chai_script_pace.py content/episode-190 --min-duration 60 --max-duration 90
# 配音后复跑：自动改用 audio/NN.mp3 实测时长
python3 scripts/chai_script_pace.py content/episode-190 --min-duration 60 --max-duration 90 \
    --json pace-report.json
```

### 8.2 逐段看，不看总数

脚本打印「时长分配表」（段号 / 槽位 / 非空白字符 / 时长 / 占比 / 字符每秒密度 / 时长来源 / 口播开头），
槽位按 §1 场景表推断（5 段 → hook/facts/mechanism/action/verdict；7 段 → 追加 config/verify；
其它段数只按序号打印，不猜）：

```
 段  槽位             字符     时长s      占比     密度 字/s  来源
 1  01-hook        35    7.34    9.2%       4.77  实测
 6  06-verify      92   20.20   25.2%       4.56  实测   ⚠️   ← 评审点名的就是这一行
 7  07-verdict     76   14.33   17.9%       5.30  实测
```

**"字符每秒密度"是这张表的重点**：它把"这 20 秒里到底塞进去多少信息"变成一个可比较的数。
同一期里密度最低的段会被单独点名（上例 `06-verify 4.56 字/s`，是全片最低）。

### 8.3 阈值含义（全部可参数覆盖）

| 规则 | 缺省 | 级别 | 参数 | 为什么是这个数 |
|---|---:|---|---|---|
| 单段过长 | > 18.0s | ⚠️「低信息密度风险：检查是否在讲常识」 | `--seg-warn` | EP.167D 06-verify = 20.196s 被判"最掉人"，取 18s 作预警线 |
| 单段过长 | > 22.0s | ❌ | `--seg-fail` | 明显超出一屏能承载的信息量 |
| 单段过短 | < 5.0s | ⚠️ | `--seg-short` | 4 期实测最短 4.464s（钩子段）；再短要问是不是没讲清 |
| 总时长 | 60–90s 之外 | ❌ | `--min-duration/--max-duration` | 深度版档位 |
| 占比失衡 | > 22% | ⚠️ | `--share-warn` | EP.167D 06-verify 24.6% 被评审点名 |
| 占比失衡 | > 26% | ❌ | `--share-fail` | 单段吃掉 1/4 以上，结构必失衡 |
| 余量不足 | 余量 < 3.0s | ⚠️ | `--headroom` | EP.167D 成片收尾余量只有 1.89s，几乎没得改 |

**退出码**：有 ❌ → `1`；只有 ⚠️ → `0`（打印但不阻断，稿子该不该改由人定）。

### 8.4 日更 5 场景必须显式传档位

缺省档位是**深度版 60/90**（对齐 §4 里 `chai_hook_check.py` 的调用姿势）。跑日更会看到
「总时长 40.46s 低于下限（档位 60–90s）」——**那是对的，不是 bug**：

```bash
python3 scripts/chai_script_pace.py content/episode-NNN --min-duration 25 --max-duration 45
```

同日更档下 `--seg-short` / `--share-warn` 两条偏噪声（25–45s 的片子每段只有 4–11s，
占比天然容易过 22%，钩子段也天然短于 5s）。深度版是目前唯一真要卡这两条的形态；
**日更建议 `--seg-short 3.5 --share-warn 28 --share-fail 33`**（EP.166 的 L4 长段占 30.8%，
按缺省的 26% 会 ❌，但那是已发布的合意稿）。

### 8.5 语速常数 `--sec-per-char`（缺省 0.208）

口径 = `非空白字符数 ÷ NN.mp3 实测时长`。MiniMax `male-qn-qingse` / `speech-2.8-hd` /
speed 1.08 / calm，本工程 4 期 22 段实测（2026-09-11，`--show-calibration` 可复算）：

| 期 | 段数 | 非空白字符 | 实测 | s/字 |
|---|---:|---:|---:|---:|
| EP.165 | 5 | 179 | 35.784s | 0.1999 |
| EP.166 | 5 | 166 | 35.892s | 0.2162 |
| EP.167 | 5 | 187 | 40.464s | 0.2164 |
| EP.167D | 7 | 418 | 80.136s | 0.1917 |

22 段逐段均值 **0.2039**、中位数 **0.207**、σ≈0.019（极差 0.1705–0.2480）。
缺省取 0.208（≈中位数，也与各期 SCRIPT.md 既有的 `418 × 0.208 ≈ 87s` 口径一致）。

- 偏差范围：整期层面 **−4% ~ +8.5%**（EP.167D 估算 86.944s vs 实测 80.136s = **+8.5%**，
  因为它中英混排多、短句多、停顿密）。逐段误差可达 ±20%。
- **有 mp3 就一定用实测**：本脚本对每条都标 `实测` / `估算`，不会把估算伪装成实测。
- 想估算更贴实测：CJK 密集的日更稿 `--sec-per-char 0.216`；深度版这类
  **`--sec-per-char 0.192`**。或先用 `--show-calibration` 看本期实测值再定。

### 8.6 2026-09-11 自证（本机复跑）

```bash
# 三期真实数据（有 mp3 → 全部走实测；槽位/占比/密度逐段可查）
python3 scripts/chai_script_pace.py content/episode-167-deep --min-duration 60 --max-duration 90
# → 80.14s（实测）/ 纯估算 86.94s（+8.50%）· 06-verify 20.20s·25.2%·4.56 字/s → ⚠️×2 → exit 0
python3 scripts/chai_script_pace.py content/episode-167 --min-duration 25 --max-duration 45
python3 scripts/chai_script_pace.py content/episode-166 --min-duration 25 --max-duration 45
# → 5 段正常跑通；166 的 L4（11.05s / 30.8%）会 ❌（缺省占比线对日更偏严，见 §8.4）

# 反例（/tmp 合成，证明门禁真会响）
python3 scripts/chai_script_pace.py /tmp/pace-case1 --min-duration 60 --max-duration 90
# → 第 2 段 23.09s > 22s ❌ [单段超长] → exit 1
python3 scripts/chai_script_pace.py /tmp/pace-case2 --min-duration 60 --max-duration 90
# → 总时长 94.85s > 90s ❌ [总时长档位] → exit 1
```

**EP.167D 的实测结论**：本门禁在**写稿阶段**（只有 `SCRIPT.md`、还没配音时）就能对 06-verify
报出 ⚠️[单段过长] 19.14s，并把它的占比 22.0% 打在表上（正好压在缺省 22% 预警线上，
配音后实测 20.20s / 25.2% 双双越线）——正是评审说"最掉人"的那一段。
**它不改稿，它只保证"这一段跑不掉"。**

---

## 8A. 长视频档（180–300s / 20–30 场景）：规则 6「相邻段字数失衡」

> 2026-09-12 新增。**阈值规则一条没改**（单段 >18s ⚠️ / >22s ❌、占比 >22% ⚠️ / >26% ❌、
> 余量 <3s ⚠️），只做两件事：① 长档位能直接用；② 补一条**长片专用**的检查。

### 8A.1 为什么补「相邻段字数差」

既有五条规则都在看**单段绝对值**与**占比**，没有一条看**相邻关系**。
长视频（20–30 段）里最刺耳的节奏问题恰恰是相邻关系：
**某一段 48 字、紧邻的那段只有 6 字** —— 单段都在 22s 以内、占比都远低于 22%，
五条规则全绿，听感上却是一段赶、一段拖。所以把「相邻段」变成机械门禁：

| 规则 | 缺省 | 级别 | 参数 | 触发条件 |
|---|---:|---|---|---|
| **相邻段字数失衡** | **1.6 倍** | ⚠️ | `--adj-ratio` | 相邻两段「非空白字符数」的比值 > 1.6（无论谁多谁少），且段数 ≥ 12 |

- 为什么是 1.6：本工程 4 期 22 段实测相邻比中位数 1.22、p90 1.55；1.6 落在
  「正常波动」与「明显失衡」之间。
- 为什么段数门槛是 12（`--adj-min-segs`）：短片（5 段）本来就抖，误报多；
  长片 20+ 段时这条才有意义。
- 全绿时会打印一条 `✅ [相邻段字数失衡] N 段相邻字数比全部 ≤ 1.6 倍（长片节奏检查）`，
  这样「这条检查跑过了」是看得见的，不是静默跳过。

### 8A.2 长片的占比阈值要显式传

缺省占比线（22% / 26%）是**按 5/7 段标定**的：段数越多、每段占比天然越小
（**24 段时均值只有 4.2%**），长片上这两条几乎不会响。想让长片也有「某一段特别重」
的检查，就传 `--share-warn / --share-fail`（例如 24 段用 `--share-warn 8 --share-fail 12`）。
长片真正要盯的是**绝对秒数**与**相邻字数差**。

### 8A.3 长片档位速查

```bash
# 只估总时长，判断够不够 3 分钟
python3 scripts/chai_script_pace.py content/episode-900 --min-duration 180 --max-duration 300 \
    --spec specs/900.json
```

24 场景合成用例（4 章 × 6 场，逐段 47–52 字）实测输出：

```
合计 24 段 · 251.47s（估算） · 档位 180–300s · 距上限余量 48.53s
✅ [总时长档位] 总时长 251.47s 落在档位 180–300s
✅ [收尾余量] 距上限余量 48.53s
✅ [相邻段字数失衡] 24 段相邻字数比全部 ≤ 1.6 倍（长片节奏检查）
结论：[PASS] 无告警，节奏与时长都在档。 · 最低密度 01-chapter 4.81 字/s
```

**反例（证明规则 6 真的会响）**：`/tmp/pace-adj`（7 段，第 5 段 6 字、相邻第 4 段 48 字）：

```
⚠️ [相邻段字数失衡] 相邻两段字数差 8.00 倍（5 6 字 ↔ 4 48 字 > 1.6 倍）：
   节奏忽快忽慢，听感上会「一段赶、一段拖」——把长的那段拆开，或给短的那段补一句
```

改前脚本对同一目录**报不出这 4 条**（其余 6 条告警逐字相同）—— 规则 6 是净新增。

### 8A.4 长档在另外三件门禁上的可用性（实测已支持，未改代码）

| 门禁 | 长档调用 | 实测 |
|---|---|---|
| `chai_hook_check.py` | `--min-duration 180 --max-duration 300` | `成片时长 83.66s（档位 180–300s）` ⚠️ 档位不符 —— 参数生效 |
| `chai_check_motion.py` | `--min-duration 180 --max-duration 300` | `FAIL: 时长 83.667s 不在 180.0-300.0s 档` —— 参数生效 |
| `chai_layout_precheck.py` | 无需档位参数 | 新模板预算见 §4.1 |

---

## 9. 长视频 24 场景验证（2026-09-12 本机复跑）

### 9.1 零回归（**这是本次改造的硬约束**）

**方法**：`/tmp/chai24/scripts/gen_chai_frames.baseline.py` 是本仓库
`gen_chai_frames.py` 在改造前的**逐字节副本**（sha256
`15aaedb4242a3e26552e3b1a104344c395e8542e57b63ef34cb9e31cbcefa47b`）。
同一条 spec、两个不同的工程副本、同一个脚本，唯一变量是「改前 / 改后」。
先把改动前的脚本跑一遍冻结基线，再跑改动后的脚本，逐字节对比。

```bash
# 基线（改前脚本）
python3 /tmp/chai24/scripts/gen_chai_frames.baseline.py /tmp/chai24/long/b165/spec.json
python3 /tmp/chai24/scripts/gen_chai_frames.baseline.py /tmp/chai24/long/b168/spec.json
# 改后
python3 scripts/gen_chai_frames.py /tmp/chai24/long/a165/spec.json
python3 scripts/gen_chai_frames.py /tmp/chai24/long/a168/spec.json
# 逐文件 sha256 对拍
diff /tmp/chai24/long/b165.sha256 /tmp/chai24/long/a165.sha256
diff /tmp/chai24/long/b168.sha256 /tmp/chai24/long/a168.sha256
```

**结果**：

| 期 | 帧 HTML | captions.html | cover.html | index.html |
|---|---|---|---|---|
| EP.165（5 场景，扁平 `scenes`） | ✅ 逐字节相同 | ✅ | ✅ | ✅（与仓库产物也逐字节相同） |
| EP.168（7 场景，`01-hook`…`07-verdict`） | ✅ 逐字节相同 | ✅ | ✅ | ✅（与仓库产物也逐字节相同） |
| EP.166 / 167 / 167D / 169（帧+captions+cover） | ✅ 改前改后逐字节相同 | ✅ | ✅ | — |

改前脚本留底在仓库里（`scripts/*.bak-20260912-长视频前`），可随时复跑上方命令。

门禁侧零回归：

| 脚本 | 对拍对象 | 结果 |
|---|---|---|
| `chai_script_pace.py` | episode-165/166/167/167-deep/168 × 对应档位 | 改前改后输出**逐字节相同**（含 exit code） |
| `chai_layout_precheck.py` | specs/165/166/167/167D/168/169 | 原有输出**逐字节相同**，仅在末尾**新增 8 行**「长视频模板启用情况」（见 §9.4 说明） |

> ⚠️ **诚实记录 1**：仓库里 `videos/aliyun-context-cache/`（EP.168）已提交的
> `compositions/captions.html` 与 `frames/05-config.html` 是**更早一版的脚本**产出的
> （captions 的 `data-duration` 还是脚手架残留 `37.728`、05-config 的行号列还是旧色
> `#6E6E6E`/20px、`.idx` 还是 `06`）。用当前脚本重跑会产出**已修复版**，
> 因此「重跑 vs 仓库产物」本来就有差异 —— 那是仓库产物**过期**，不是本次回归。
> 所以 §9.1 的对拍基准取的是**改动前脚本的当场输出**，不是仓库产物。

### 9.2 24 场景合成用例（`/tmp/chai24/deep`，4 章 × 6 场）

| 项 | 结果 |
|---|---|
| 帧数 | **24**（01-chapter … 24-verdict，五种新模板全部出现） |
| 模板分布 | chapter 4 场（01/06/11/16）· quote 4 场 · table 4 场 · flow 5 场 · case 4 场 · config 1 场（21）· verify 1 场（22）· 既有 01–04 与末场 verdict 各 1 |
| index | `24 scenes, total 240.0s, 4 chapters, 3 处章节转场用 1.2s` |
| 转场 | **23 次交接 = 46 条 tween**（40 条 0.5s + 6 条 1.2s，即 3 个章节边界 × 出/入） |
| `hyperframes check --at` | **每场一次、24 个采样点**（5,15.5,26,…,246.5）→ **0 error** |
| 门禁 | `chai_layout_precheck.py` exit 0（无超宽）· `chai_script_pace.py --min-duration 180 --max-duration 300` PASS |
| 生成期自检 | 24 帧全部通过宽度断言（放不下会 SystemExit，实测 5 个反例都正确报错，见 §9.3） |

`check` 的完整结果（0 error）：

```
lint      errors=0  warnings=26   （26 条全是 google_fonts_import：老皮肤特征）
runtime   errors=0  warnings=0
layout    errors=0  warnings=0    （24 个采样点、含 24 帧全部版式）
motion    errors=0  warnings=0
contrast  errors=0  warnings=2    （`.idx` 场号水印 1.84:1，**与 EP.168 完全同因**）
TOTAL errors: 0  warnings: 28  ok: True     ← exit 0
```

> ⚠️ **诚实记录 2**：contrast 那 2 条 warning 来自**共用皮肤** `.idx{color:#4A4A4A}`
> （EP.168 在 5 帧上都报同一条 1.84:1）。它不是新模板引入的，**本次未修**
> （改色会动到老帧的皮肤常量，与「零回归」冲突）。要修的话建议单独开一次改动。

### 9.3 「放不下就报错、不许静默截断」的自证（5 个反例）

```bash
python3 scripts/gen_chai_frames.py /tmp/chai24/deep/bad_quote_too_long.json
```

| 反例 | 报错（exit 1） |
|---|---|
| 引文过长 | `FAIL: 引用页引文在 36px 下仍要 7 行（可用 756px，引文宽 ≈4896px）。` + 3 条改法 |
| 对照表 7 行 | `FAIL: table 的行数必须是 3–6 行（含表头共 4–6 行；当前 7 行）` |
| 因果链 2 段 | `FAIL: case 的 chain 必须正好 3 段（现象 → 机制 → 结果；当前 2 段）` |
| 流程 6 步 | `FAIL: flow 的 steps 必须是 3–5 步（当前 6）` |
| 章节序号 6 位 | `FAIL: 章节页序号「123456」太宽（≈1125px），标题列只剩 -299px < 430px` |

### 9.4 已知的、**有意**的输出变化

| 文件 | 变化 | 为什么 |
|---|---|---|
| `chai_layout_precheck.py` 的输出 | 末尾**新增 8 行**「长视频模板启用情况」 | 本次需求明确要求「打印每种模板的启用情况」（便于确认没漏检）；诊断行与 exit code 一字未变 |
| `chai_script_pace.py` 的输出 | 段数 ≥12 时新增「相邻段字数失衡」1–N 条 | 本次需求明确要求的新检查（规则 6）；5/7 段的老路径输出逐字节不变 |
| `gen_chai_index.py --chapter-progress` | 打开后 index.html 多 **N+9 行**（4 行 CSS + 1 行 DOM + **每场一条 `tl.set`**，N = 场景数；EP.171 起逐场递增，此前是「每章一条」），**删除 0 行** | 本次需求的可选功能；实测 EP.165 的差异是**纯新增**（3 个 diff 块、+10/−0），关掉开关时 index.html 与改造前逐字节相同 |

### 9.5 生成期自检 + 真机 DOM 审计抓到的**真缺陷**（这些都是实测抓到并修掉的）

> 这一节是本次改造最有价值的部分：5 个新模板在**第一版**里各自有真实的版式缺陷，
> 而 `hyperframes check`、预算预检、`_estw` 断言**全都没报**（或报成了 info）。
> 是靠「把帧的 `<template>` 内容取出来、补上父文档的 `*{box-sizing:border-box}`、
> 再用浏览器量真实盒」这条**DOM 审计**路径抓出来的。审计脚本本身也踩过两个坑，
> 一并记下来，免得下次重蹈。

| # | 缺陷 | 表现 | 根因 | 修法 |
|---|---|---|---|---|
| **D1** | flow 的步骤文案被压成**每行 1 个字** | 5 行、末行孤字 | `#fl-axis` 是绝对定位、子元素全绝对定位 → 不给宽就 shrink-to-fit 成 20px（= `.dot` 宽） | 显式 `width:748px` |
| **D2** | flow 的轴点与标签**整体左移 ~140px**，首标签越出 x110 安全线 | `#fl-l1` 盒 `[87,187]` | `#fl-axis` 写成 `position:absolute` → `.dot/.lb` 的 offsetParent 变成 `#fl-card` 而不是轴 | 改 `position:relative`（留在文档流里，同时成为子元素参照） |
| **D3** | flow 标签**伸出卡片 50px** | `text_box_overflow`（**error**） | 卡片声明高度算小（漏了卡头实测 83px 与 flex gap 26）→ flex 把轴从 162px 压到 **51px** | ① 卡片高度按实测重算；② 轴加 `flex:0 0 auto`（宁可靠它顶出去，不许安静被压扁） |
| **D4** | 章节页标题**折成 2 行** | 「代理与缓存踩过的坑」在 60px 下折行 | `_estw` 按 CJK 1.0em 估算，而 Noto Sans SC 900 实测推进 **≈1.13em**（偏低 14%）；且序号列按 268px 算得太宽 | 序号降到 224px、列间距 28→把标题列加宽；「必须一行放下」的标题加 `CJK_ADV_SAFE = 1.15` 安全系数（**不改 `_estw` 本身**，它是共用常量） |
| **D5** | 引用页引号**字形盒撑出元素盒 51px** | `text_box_overflow` | 200px 字形的字形盒高 300px，而元素盒只有 211px | 170px + `line-height:.76` + 上下内边距 40/30 → 字形盒 293 < 元素盒 299 |
| **D6** | 自动折行把**行尾空格**带进视觉 | 行中留出空洞 | `_wrap_est` 在空格处折行时把空格留在上一行行尾 | 折行与显式断行都做 `rstrip/strip` |

**审计脚本自己的两个坑**（会让审计出假结果，务必注意）：

1. **帧文件是 `<template>` 包的**，浏览器不渲染 `<template>` 内容 → 直接 `page.goto(帧文件)`
   量到的 `document.body` 是**空的**，于是「24 帧全部 ✅」是假的（第一版审计就这么被骗了）。
   必须把 `template` 内容取出来注入页面再量。
2. **必须补上父文档的两条全局重置** `*{margin:0;padding:0;box-sizing:border-box}`
   （在 `index.html` 里，帧自己只带 `<style>`）。少了 `box-sizing:border-box`，
   卡片会被量成 `860 + 左右内边距`（实测 `#fl-card` **942px** 而非 860px），
   于是每帧都报「越界」——那是脚手架自己的错。

**最终审计结果**（修正后的脚手架，24 帧）：

```
✅ 24 帧全部通过（无元素越出安全区 x110–970 / y≤1290，无孤行）
真机折行只剩模板契约内的 4 处：quote 引文 3–4 行（允许 2–6 行）、
   章节页标题 1 处折 2 行（44px→36px 档，允许 2 行）
```

### 9.6 渲染时间与体积（实测）

**测法**：`/tmp/chai24/deep/proj` 用 `hyperframes render --quality standard`
（24 场景 / 240s / 1080×1920 / 30fps / 24 段静音 mp3）实测。

**实测结论（2026-09-12，本机 Apple M2 / 8 核 / `--quality standard`）**

| 指标 | 实测值 |
|---|---|
| 成片时长 | **240.000s**（4 分 00 秒；= 24 段 × 10s，与 index 的 total 一致） |
| 分辨率 / 帧率 | 1080×1920 / 30fps / h264 + aac |
| **渲染挂钟时间** | **406s ≈ 6 分 46 秒**（≈ **1.7s 成片 / 秒渲染**，即 **约 50 帧/秒** 出片） |
| 文件体积 | **33,252,776 字节 = 31.71 MB**（平均码率 **1.11 Mbps**） |
| 24 场景渲染 | 7200 帧，≈ **17.7 帧/秒 出片速度**（7200 帧 ÷ 406s） |

**排产换算**（按同一台机器、`standard` 档、1080×1920@30fps）：

| 目标成片 | 场景数 | 预估渲染时间 | 预估体积 |
|---|---|---|---|
| 180s（3 分钟，长档下限） | 20–24 | **≈ 5 分 05 秒** | ≈ 24 MB |
| 240s（4 分钟，本次实测） | 24 | **6 分 46 秒** | 31.7 MB |
| 300s（5 分钟，长档上限） | 30 | **≈ 8 分 28 秒** | ≈ 40 MB |

> 口径提醒：① 本用例每段音频是**静音 mp3**，对渲染速度影响可忽略（画面才是成本）；
> ② 体积对**画面复杂度**敏感（本用例 31.7 MB / 240s ≈ 1.11 Mbps 属"文字+卡片"类画面的典型值，
> 若加实拍素材会明显变大）；③ 首次跑有 Chrome / 字体缓存冷启动成本，第二次起更稳。

**成片验收（`chai_check_motion.py --min-duration 180 --max-duration 300`）**：
规格 1080×1920@30 / 240.000s / 0 长静帧 / 0 黑段 —— **唯一 1 条 FAIL 是「静音 240.0s」**，
来自合成用例的**静音 mp3**（不是配音截断）。也就是说：**除合成音频本身人为静音外零 FAIL**。

```bash
# 复跑（长视频 24 场景渲染 + 验收）
cd /tmp/long-proj && npx --yes hyperframes@0.7.102 render -o /tmp/render24.mp4 --quality standard
python3 scripts/chai_check_motion.py /tmp/render24.mp4 --min-duration 180 --max-duration 300
```

> ⚠️ `hyperframes render` 需要 PATH 上有 `ffmpeg` / `ffprobe`。本仓库把它们放在
> `videos/<slug>/bin/`（Remotion 自带的精简构建包装器）；渲染前记得
> `export PATH="<REPO>/videos/<slug>/bin:$PATH"`，
> 否则会直接报 `FFmpeg not found`（实测：渲染 2.9s 就退出）。

### 9.6.1 EP.170 的槽位路由实录（2026-09-12，24 帧 / 4 章 / 292.248s）

`specs/170.json` 是长片，模板落位**完全由字段决定**（与槽位号解耦）：

| 槽 | 判定 | 槽 | 判定 | 槽 | 判定 | 槽 | 判定 |
|---|---|---|---|---|---|---|---|
| 01 | hook | 07 | chapter | 13 | chapter | 19 | chapter |
| 02 | facts | 08 | **action** | 14 | flow | 20 | verify |
| 03 | **table** | 09 | flow | 15 | table | 21 | table |
| 04 | **flow** | 10 | case | 16 | quote | 22 | verify |
| 05 | **facts** | 11 | quote | 17 | case | 23 | flow |
| 06 | config | 12 | facts | 18 | flow | 24 | verdict |

（**加粗**的是旧代码会崩的位置：03 读 `mm`、04 读 `w1_t`、05 读 `repo_big`、08 读 `w1_t`。）

- `gen_chai_frames.py specs/170.json` → **24 帧全部生成，exit 0**（改前：`KeyError: 'mm'`）；
- `gen_chai_index.py videos/openai-agents-sandbox content/episode-170 "OPENAI AGENTS / 170"
  --scenes=auto --spec specs/170.json --chapter-progress --chapter-trans 1.2`
  → **24 场 / 4 章 / 23 处交接 / 292.248s**，帧名与 index 逐条对齐（无缺失、无多余）；
- `hyperframes check --at`（24 个采样点）→ **0 error**（50 warning 全为既有皮肤特征：
  google_fonts_import / pointer_events_none / clip_media_fit / `.idx` 对比度）；
- 只写 `compositions/frames/*` 与 `cover.html`；`assets/`、`renders/`、`covers/`、
  `caption_groups.json`、`audio_meta.json` **未被触碰**（mtime 不变）；
- 重跑一次产物**逐字节不变**（幂等，25 个工件 sha256 相同）。

### 9.6.2 EP.170 的 3 处「大标题行超宽」判定：**是预算口径问题，不是真溢出**

预检报的 3 处（`⚠️`，缺省不翻退出码）：

| 位置 | 预检（860px 预算，含 1.15 系数） | 实测（浏览器 DOM 逐字 Range） | 像素复核（截图逐列扫描） |
|---|---|---|---|
| `01-hook` 第 1 行「Agent 上云，」 | 900px | **墨迹右缘 x828** | 第一行带内墨迹 ≤ x961 |
| `01-hook` 第 2 行「先管好那把钥匙」 | 950px | **墨迹右缘 x927.8** | 第二行带内墨迹 ≤ x926 |
| `24-verdict` 第 2 行「没省掉的是收尾」 | 885px | **墨迹右缘 x872.3** | — |

**判定：三处都没有越界。** 判据是**画布上的物理边界**而不是那个模型预算：

- 内容安全区右界 = **x970**（`.dash` 虚线实测 `[110,970]`，1080 − 110）；
- 三处墨迹右缘最大 **927.8**，离安全区右界还有 **42px**，离画布边（1080）还有 **152px**；
- 也就是说：**它们比 860px 这个「文字排版预算」宽，但没有任何裁切风险。**

**为什么模型会高估**：`width_px` 对 ASCII 按 **0.66em**、CJK 按 **1.0em** 估宽，而实测是
**CJK ≈1.13em（低估）· 首尾 ASCII/全角标点 ≈0.5em（高估）** —— 模型只对 ASCII 偏高
约 30%。这两行恰好是「短 CJK + 结尾全角标点」，于是被高估。
（`.cover_cover_estw` 的注释里早就把这条标定记下来了：*Calibri 数字/字母实测 0.43–0.47em*。）

**结论与建议**：

1. **不必改稿**，也**不要**因为这条去动 `#f1-hero` / `#f5-hero` 的 CSS —— 那会改动既有模板，
   与「扁平路径逐字节零回归」直接冲突；
2. 这条检查的价值在于「提前知道离预算还有多少」，**缺省只报 ⚠️ 是刻意的**：既有已发货
   spec（如 `specs/168.json` 的「命中缓存省 90%」）也会命中它；
3. 想把它变成硬门禁（例如要求所有大标题行的**实测墨迹** ≤ x970），正确做法是加一条
   以 `x970` 为界的检查，而不是收紧这个 `860px` 的文字排版预算 —— 需要你确认后再做。

---

### 9.7 一处**存量**问题（本次不改，如实记录）

`#f1-hero`（01 首帧，118px）与 `#f5-hero`（末场判词，110px）**没有 `max-width`、也不换行**：
文案比内容区宽就直接向右溢出画布（实测合成用例里 970px 的盒放了 1051px 的一行，
右边缘顶到画面边 x1080）。老路径同理，只是 EP.165 那类的字短、恰好塞得下。

**为什么不在这次顺手修**：给这两个模板加 `max-width`/`white-space:normal` 会**改动老帧的
HTML**，直接破坏本次的硬约束（5/7 场景逐字节零回归）。所以改成**在预检里拦住**：

- `chai_layout_precheck.py` 新增 `hero01_1/hero01_2/hero05_1/hero05_2` 四条「一行必须放下」的预算；
- **缺省只报 ⚠️、不翻退出码**（`--strict` 才升级为 ❌）——因为既有已发货的 spec 会命中它
  （例如 `specs/168.json` 的「命中缓存省 90%」实测一行约 800px，模型算 992px）；
- 想让长视频卡这条就加 `--strict`。

---

## 10. 封面待决策

1. **强调色要不要为「可 OCR」让路？** 现在 `hero_em` 用品牌酸柠绿 `#D1FF00`。
   它对**人眼**对比度很高（在深底上非常跳），但对 macOS Vision 不友好（§7.8）。
   选项：① 保持 lime（推荐，视觉优先，人工看一眼即可）；② 改纯白（机检全绿，但丢了品牌强调色）；
   ③ 加一层 lime 的深色描边/降不透明度做折中。**需要你定。**
2. **贴纸是否上 spec？** 现在 `stickers` 可选，缺省从 `kicker`/`act` 派生。
   若你想每期手工控制贴纸文案与颜色，就在 spec 里写 `stickers`；否则派生已经够用。
3. **人物盘尺寸/位置**（9:16 右下 488px、4:3 右侧 520px）目前是我定的常数，
   在 `gen_chai_frames.py` 的 `_COVER_CSS` 里。要更大/更小改一处即可。
4. **装饰出血**：`.sun`（光芒）与 `.ava`（人物盘）刻意贴边/出血以获取视觉张力。
   若你的平台有硬性「全部内容距边 ≥60px」要求，我可以把所有元素收进安全区
   （会牺牲一点视觉张力）。**需要你定。**

---
