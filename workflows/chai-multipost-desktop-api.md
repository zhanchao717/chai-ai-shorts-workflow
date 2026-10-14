# MultiPost 桌面版发布手册（2026-10-11 实测沉淀）

来源：EP240 实际发布（抖音 ✅ / 小红书 ✅ / 视频号 ❌ 网络）。所有结论都是实跑验证过的，不是推测。

---

## 一、通道选择

| 通道 | 状态 |
|---|---|
| 浏览器扩展（云端 `api.multipost.app`） | ❌ `GET /extension/clients` 始终返回空，无已链接客户端 |
| **桌面版本地 API** | ✅ 可用，**首选** |

### 本地 API

- 地址：`http://127.0.0.1:19528`
- Token：`~/Library/Application Support/multipost-desktop/app-settings.json` → `externalApi.token`（字段 `externalApi.enabled` 需为 true）
- 路由（从 `app.asar` 提取，实测有效）：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/v1/accounts` | 三平台账号与 accountId |
| GET | `/v1/platforms` | 平台定义与支持的 contentTypes |
| POST | `/v1/publish` | 创建任务（返回 202 + groupId） |
| GET | `/v1/publish/:id` | 任务与各目标状态 |
| POST | `/v1/publish/:id/submit` | 整任务提交 |
| POST | `/v1/publish/:id/targets/:tid/submit` | **逐平台提交**（推荐） |
| POST | `/v1/publish/:id/targets/:tid/retry` | 逐平台重试 |
| DELETE | `/v1/publish/:id` | 关闭任务 |
| GET | `/v1/history` | 发布历史（含 success/failed） |
| GET | `/v1/debug/views` | 视图、分组与各目标 URL |
| POST | `/v1/debug/exec` | `{viewId, script}` 在账号视图执行 JS |
| POST | `/v1/debug/exec-group` | `{groupId, accountId, script}` 在任务视图执行 JS |
| GET | `/v1/debug/logs` | 应用日志（排障关键） |

### 请求体（zod schema 提取）

```json
{
  "contentType": "VIDEO",
  "accountIds": ["<accountId>"],
  "autoSubmit": false,
  "data": {
    "title": "必填",
    "content": "正文（可选）",
    "video": { "path": "/绝对路径.mp4" },
    "cover": { "path": "/绝对路径.png" },
    "tags": ["标签1", "标签2"]
  }
}
```

`video` / `cover` 可以是路径字符串，或 `{path|url, name}`。

---

## 二、发布流程（已验证）

1. `GET /v1/accounts` 取 accountId。
2. **一个平台一个任务**。API 的 `title`/`content` 是全平台共用一份，做多平台会丢掉各平台专属文案；逐平台建任务就没这个问题。
3. `POST /v1/publish`，`autoSubmit: false`。
4. 轮询 `GET /v1/publish/:id` 直到目标状态为 `ready` / `failed`。
5. **手动补 AI 声明**（见第三节）。
6. `POST /v1/publish/:id/targets/:tid/submit`。
7. 到平台内容管理页核实（见第五节）。

---

## 三、⚠️ 最大的坑：MultiPost 不会设 AI 声明

在 `app.asar` 中检索：

| 关键词 | 命中数 |
|---|---|
| `声明原创` | **1**（有实现，点 `textContent === '声明原创'`） |
| `AI生成` / `AI 生成` | **0** |
| `作品声明` / `内容声明` | **0** |

**结论：MultiPost 能勾"声明原创"，但完全没有 AI 生成声明能力。**
含 AI 生成内容的作品必须标注（中央网信办规范短视频内容标注 / 小红书 AI 治理规则 / 微信主动声明要求），**所以自动发布前必须手动补声明，否则不合规。**

### 各平台的声明项（实测）

| 平台 | 控件 | 要选的值 |
|---|---|---|
| 抖音 | `自主声明`（自定义下拉，`.selectBox-buZRzi`） | **内容由AI生成** |
| 小红书 | `添加内容类型声明` | **笔记含AI合成内容** |
| 视频号 | 需在发布页手动确认 | 微信要求主动声明 |

**做法**：用 `exec-group` 执行 JS 点击控件（真实 `.click()` 会触发 React 状态），再读回控件文本确认：

```js
// 打开抖音下拉
document.querySelector('.selectBox-buZRzi').click();
// 选 AI 声明
document.querySelectorAll('.semi-radio-addon').forEach(function(el){
  if((el.textContent||'').trim()==='内容由AI生成') el.click();
});
// 复核
document.querySelector('.selectText-XSrMFZ').textContent.trim();  // → "内容由AI生成"
```

---

## 四、另一个坑：正文里不要再写标签

**踩过的错**：把标签同时写进了 `content` 正文和 `tags` 数组，结果平台把标签追加了一次 →
描述里出现「#AI漫剧 #ai短剧 … #AI漫剧 #ai短剧 …」**重复两遍**。

**规则：`content` 只放正文，标签只放 `tags`。**

**事后改不了**：用 `document.execCommand('insertText')` 改页面上的富文本编辑器，**React 状态不会同步**，提交时用的仍是原值。要改必须走真实按键（全选后重新输入），而且抖音发布后标签已生效，改不回来。

---

## 五、各平台自动化现状（实测）

| 平台 | 自动化 | 失败点 | 绕过办法 |
|---|---|---|---|
| 抖音 | 可用（**前提是登录态有效**） | 登录失效时报 `input[type=file] not found within 10000ms` | 重新登录后重建任务；`retry` 也可 |
| 小红书 | **部分可用**：视频、标题、正文都能填 | 卡在封面：`未找到封面上传触发器: div.noCover.uploadCover`（带/不带封面都失败），因此不走到提交 | 填充完成后**手动发布**（见下） |
| 视频号 | 填充可用 | **上传端点连接超时**：`finderassistanced.video.qq.com`（`connect timeout`）；页面报「网络出错，请重新上传。」 | 需网络能通到 `*.video.qq.com` |
| 视频号登录 | 易失效 | 视图停在 `channels.weixin.qq.com/login.html` | 需手机微信**扫码**，无法代为完成 |

### 小红书的正确发布手法

**不要**用 JS 找 text 为「发布笔记」的元素去点——那是**侧边栏菜单项**（点了 URL 会变成 `?from=menu&target=video`，看起来像跳转成功，其实什么都没发）。

**要**用 computer use 看画面，点页面底部那个**红色「发布」按钮**（预览坐标约窗口 1568×1146 下的 (835, 1112)）。成功标志：URL 变为 `publish/publish?source=&published=true`。

---

## 六、⚠️ 会话不可靠：每次动手前先确认登录态

实测中三个平台的登录态都会在几小时内失效，而且**账号列表仍显示「已登录 / active」——那是缓存值，不能信**。必须以视图里的实际页面为准：

| 平台 | 失效表现 | 恢复方式 |
|---|---|---|
| 抖音 | 视图变成 `creator.douyin.com` 的扫码登录页 | 扫码 |
| 小红书 | 视图被公开笔记页替换（页签名变成笔记标题），`/v1/debug/exec` 随之整体 500 | 重新打开创作者平台页 |
| 视频号 | 视图停在 `channels.weixin.qq.com/login.html` | 扫码 |

**动手前的检查清单（30 秒）**

1. `GET /v1/debug/views` 看各视图 URL 是否还是后台页
2. 用 `POST /v1/debug/exec` 跑一句 `location.href` 确认接口可用（500 = 该视图已不可控）
3. 再决定要不要建任务

**教训**：抖音的发布自动化在登录失效时报的是 `input[type=file] not found within 10000ms`，看起来像选择器问题，**其实是登录页**。先排除登录态，再去怀疑选择器。

---

## 七、验证（不能只信任务状态）

1. `GET /v1/history` → 该平台应为 `success`
2. **平台内容管理页**：抖音 `content/manage`（看是否出现新作品与「已发布」）；小红书 `new/note-manager`（看总数是否 +1、状态「审核中/已发布」）
3. 账号数据：`POST /v1/accounts/:id/refresh` 后看 `stats.works`
4. 抖音的 AI 声明可打开作品编辑页读取：`content/post/video?mid=<id>&enter_from=edit_item` → 读「自主声明」的值

---

## 八、发布前合规清单

- [ ] 三平台正文都写了 AI 生成声明句（例：「画面里的动画片段由 AI 生成，出自自有项目，用于演示，不是真实拍摄。」）
- [ ] 平台侧声明项已勾选并**读回确认**
- [ ] 正文无 URL、无二维码、无联系方式
- [ ] 无绝对化用语（最/第一/顶级）
- [ ] 标题长度：抖音 ≤30、小红书 ≤20、视频号禁用标点
- [ ] 正文里没有重复写标签
- [ ] 无收益/效果承诺
- [ ] 经验判断类断言在画面已标注

---

## 九、2026-10-12 补充：EP241 实际发布

**结果：视频号 ✅（1/3）** —— 恰好是 EP240 因网络失败的那个平台。

- **逐平台独立任务**是正确做法：每个平台一份专属文案，避免"三平台共用一份标题正文"。
- **标签只放 `tags` 字段**，正文不重复写 —— 规避了 EP240 抖音那条「标签重复两遍」。
- **视频号的网络问题会自行恢复**：EP240 时报 `finderassistanced.video.qq.com` 连接超时，EP241 同流程一次填充成功。**不要把它当成永久故障。**

### 新踩到的两个坑

1. **小红书提交阶段还有第二道坎**：除了填充期的 `div.noCover.uploadCover`，提交时还会报 `Publish button not found`。
   **应用自己的小红书发布按钮选择器也是过时的**——EP240 能发出去，靠的是用 computer use 手动点页面底部的红色「发布」。
2. **驱动会拒绝对 MultiPost 主窗口投递后台输入**：报
   `off_space_or_ax_unresolved: window 560 is not among the process's current AXWindows`。
   截图可用、输入不可用。本次该进程遗留了 **3 个陈旧的文件选择器窗口**（`打开`），
   疑似导致 AX 窗口判定歧义。**重启 MultiPost 可同时清掉残留窗口并刷新登录态。**

### 登录态复检（再次验证第六节的判断）

抖音本次失败报的是 `input[type=file] not found`，实际是**视图停在扫码登录页**。
**结论不变：先查登录态，再怀疑选择器。**

---

## 十、2026-10-12 收尾：三平台 3/3 的完整解法

**EP241 最终三平台全部发布成功。** 三条经验固化如下：

| 平台 | 正确做法 |
|---|---|
| **抖音** | 登录态有效时，填充与提交**一次通过**。失败时报 `input[type=file] not found` 或 `[sliderView reInit]` 一律先查登录态 |
| **小红书** | **不带封面**建任务（带封面会崩在 `div.noCover.uploadCover` 或 `span[class="title"]`）→ 填充成功 → **手动点页面底部红色「发布」** |
| **视频号** | 正常走 API 提交即可；上传端点偶发超时属暂时故障，重试或稍后再试 |

**发布后核实用平台侧数字**，不看任务状态：
- 抖音：`POST /v1/accounts/{id}/refresh` → `stats.works` +1
- 小红书：笔记管理页「全部 N」+1
- 视频号：视频管理页首条 + `stats.works` +1

**规避标签重复**：`content` 只放正文，标签只放 `tags` 数组。本期抖音实测 `#` 计数 = 5（EP240 时因两处都写导致 10）。

---

## 十一、2026-10-12 标签调研：别再写「死标签」

**在抖音创作中心首页就能读到平台为你的赛道推荐的热门话题**（`group` 视图的 `/v1/debug/exec-group` 可读）：

| 平台推荐话题（AI 赛道） | 热度 |
|---|---|
| 人工智能ai软件 | 224.6 万 |
| AI的发展有多快 | 204 万 |
| AI智能软件推荐 | 272 万 |
| 未来十年AI能干什么 | 192.5 万 |

### 结论

本账号历史标签全是**产品/型号专名**（`#DeepSeekHarness`、`#KimiCode`、`#WeatherNext`、`#4Director`、`#ComfyUI`、`#可灵`），
**搜索量接近零**——只有已经在用该工具的人才会搜，带不来新观众。而平台推荐的大盘话题一个都没用。

**定标签的新规则**：`1 个专名` + `2–3 个平台推荐话题` + `1 个品牌（#柴主编）`。

### 复读方法

```bash
# 列出该账号的 group id
curl -s -H "Authorization: Bearer $T" http://127.0.0.1:19528/v1/debug/views
# 读创作中心首页的热门话题区块（父容器 innerText 才含内容，标题节点本身是空的）
POST /v1/debug/exec-group  {groupId, accountId, script: 取含"热门话题"节点的父容器 innerText}
```

注意：小红书「笔记灵感」页面的 exec 会返回 HTTP 500（两个视图都如此），**未能读取**，目前只能按同一原则推断。

## 十二、2026-10-12 补充：视频号静默卡死的处置

EP242 第一次视频号任务 `filling` 持续 5 分钟以上，**页面始终空白、日志无报错**（与 EP240 的显式超时不同）。

**删除任务重建后 30 秒即 `ready`，提交成功。**

**规则**：视频号卡在 `filling` 超过 2 分钟且 `exec-group` 读到的页面仍无视频文件时，**直接删除重建**，不要继续等待。

---

## 十三、2026-10-12 B-roll 管线（可复用）

**背景**：单场景 80 秒的片子平均 13 秒才换一次画面，观众容易走开。B-roll 把「新画面间隔」压到 5–7 秒。

**实现位置**：`videos/dialogue-242/broll_242.py`
- 每项 B-roll = `html` + `js(t0)` 生成器 + **字幕锚点**（用台词定位，不写死秒数）+ 停留时长
- 由 `build_242.py` 按场次注入；`cap_time(子串)` 把台词映射到绝对秒
- **锚点要用句首匹配**：`cap_time('官方说的')` 会命中提问句「这是官方说的还是你试的」，须用 `cap_time_head()`

**硬规则（踩过的坑）**
1. **只能动 transform**：`left`/`width` 会被 lint 拦下（`gsap_non_transform_motion`），改用 `x` / `scaleX`
2. **`visibility:hidden` 的元素必须显式 `tl.set(...,{visibility:'visible'})`**——只 tween `opacity` 不会让它出现（这个坑犯了两次）
3. **每个 B-roll 必须在窗口结束时 `tl.set(...,{visibility:'hidden'})`**，否则会一路留到后面的场次并和内容重叠
4. **静态内容要给 B-roll 让位**：用 `tl.to('#卡片',{opacity:0})` 淡出、结束后淡回
5. 示意图形右下角标「示意 · 非实际界面」，颜色不低于 `#9aa3ab`（对比度 4.5:1）

---

## 十四、2026-10-13 双人配音管线的两个真 bug（EP243 修掉）

### 1. 缓存失效 bug（会让成片用旧音频）

`generate_dialogue_*.py` 的缓存逻辑里：

```python
if not cached:
    raw.with_suffix('.txt').write_text(turn['text'])          # 写了新文本
    if not (raw.mp3.exists() and raw.json.exists()):          # ← 但 raw 还在，于是跳过 TTS
        ... 调 TTS ...
    settings.write_text(signature)                            # 却写入了新签名
```

**后果**：文本改了、音频没重生成，而签名被更新成新的 → **之后每次都被判定为"已缓存"**，旧音频永远留在成片里。
EP243 的 `what-01`/`what-02` 就是这样变成了旧文本。

**修法**：检测到 signature 不匹配时，**先删掉 `raw/*.mp3` 与 `raw/*.json`**，再请求 TTS。

### 2. 数字与拉丁缩写的分词会连续重复

同一串数字/缩写，MiniMax 的**字幕分词**会输出多次：

| 文本 | 音频时长 | 分词结果 |
|---|---|---|
| `552B` | 正常 | `552B552B552B552B552B552B` |
| `429` | 正常 | `429429429` |
| `V4.1` | 正常 | `V4.1V4.1V4.1V4.1` |

**音频本身是好的**（时长与正常语速一致），**只有字幕分词重复**。

**修法（两层）**
1. **时间轴层折叠**：连续相同的分词合并为一个（保留首起点、末终点）。
2. **发音字典**（`--pronunciation`，可重复传）：`V4.1/V四点一`、`552B/五百五十二B`、`429/四二九`、`403/四零三`、`2.8万亿/两万八千亿`、`100万/一百万`。
   文档明确：**只影响读音，不影响字幕文本**。

### 3. 保护词要覆盖「去空格」的写法

分词去重后 `DeepSeek V4.1 Flash` 会变成 `DeepSeek V4.1Flash`（空格消失），
旧的保护词带空格就匹配不上，字幕会断成 `DeepSeek V4.1F` + `lash`。**保护词要同时覆盖有空格和无空格两种写法。**

---

## 十五、2026-10-14 锁屏会让 GUI 自动化全线失效

EP243 发布时用户已出门（屏幕锁定）。观察到的完整现象链：

| 现象 | 含义 |
|---|---|
| `get_window_state` 返回 0 元素、无截图 | 窗口 AX 面不可用 |
| `bring_to_front` 报未验证为前台 | 无法激活窗口 |
| **`get_desktop_state` 返回纯黑图** | **屏幕锁定/睡眠（决定性证据）** |
| `open`/`open -n`/驱动 `launch_app` 启动 MultiPost 后**立即正常退出**（日志 `Entering/Exiting exit handler`） | 锁屏会话里 Electron 无法创建窗口 |

**结论与规则**

1. **发布前先判定会话是否可用**：`get_desktop_state` 若为纯黑，说明锁屏 → **不要尝试任何 GUI 操作**，直接走 API 能做的部分。
2. **纯 API 路径（抖音、视频号提交）不受锁屏影响**；**需要点页面的平台（小红书）在锁屏下必然失败**。
3. **不要在锁屏状态下重启应用**：本期我为修 AX 面重启了 MultiPost，结果它在锁屏下起不来，把用户的应用留在了关闭状态。**这是一次失误，不应重复。**

---

## 十六、2026-10-14 MultiPost 0.5.2：更新方式与一个新的应用缺陷

### 更新装不上时，先看 ShipIt 日志

```
~/Library/Caches/com.multipost.desktop.ShipIt/ShipIt_stderr.log
~/Library/Caches/multipost-desktop-updater/pending/   ← 已下载的更新包与 sha512
```

EP243 时更新连续两次失败，日志给出确切原因：

```
SQRLInstallerErrorDomain Code=-9 "App Still Running Error"
All instances of the target application should be quit during the update process
```

**规则：应用内置更新即使在后台下载完成，也必须先完全退出应用才会落地。**
退出后**几秒内**即完成（0.4.4 → 0.5.2）。

### 0.5.2 修好的

- ✅ **视频号上传卡死**（0.4.4 连续卡 `filling`；0.5.2 一次到 `ready`）

### 0.5.2 的新缺陷：小红书正文被写入两遍

应用会把同一段正文写入编辑器**两次**，并把换行放大（实测 19 行 → 169 行），
然后自己的校验报 `正文未能完整保留文字与换行，请核对编辑器`，任务标记 `failed`。

**单段（0 换行）也无法绕过**——重复写入是应用行为。

**可靠流程**

1. 正常建任务，让应用填视频/标题/封面（这部分是对的）
2. 任务报 `failed` 后**不要重建**，直接处理当前页面
3. computer use：点进正文 → `Cmd+A` 全选 → **像素点击 + 逐字输入**替换为正确正文
   （**后台模式的 `Cmd+V` 送不到该编辑器**；`type_text` 传 x,y 的像素形式可行）
4. 确认字数（编辑器右下角显示 `n/1000`）
5. 手动点页面底部红色「发布」→ 核对 URL 变为 `published=true`

### `unconfirmed` 不是失败

视频号提交返回 `unconfirmed`（「到平台页核对结果，确认前不要重复发布」）。
**必须去平台页核对**：EP243 核对到首条即本期。**核对到就不要重发。**
