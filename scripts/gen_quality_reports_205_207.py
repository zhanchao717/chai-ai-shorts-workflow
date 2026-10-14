#!/usr/bin/env python3
"""把本轮（EP.205–207）的独立评审记录落成包内 quality-report.md（release-package.md #13）。

为什么要有这个脚本：EP.177 起 31 期没有把评审报告落包，而 prepublish-checklist 第 26 行一直勾着
「独立评审 P0=0（见 quality-report.md）」——引用了一个不存在的文件（EP.207 首轮评审判为 P0）。
这里把「哪几轮评审、每轮报了什么、怎么处置、最终产物指纹」固化成文件，勾选才有凭据。
"""
import hashlib
import pathlib

SLUG = {205: 'ui-three-helpers', 206: 'ai-output-checkers', 207: 'ai-on-your-devices'}

ROUNDS = {}

ROUNDS[205] = """### 轮次 1（首轮独立评审）· P0=4
1. `sources.md` 缺「选题评分 / 落选候选 / 编辑判断与禁项」三节；且 `lnkiai/m3e-canvas` **EP.178 已上过一次片**（那期 `11-facts` 场景把名字与卖点烧进了画面，只是口播没念）。
2. 发布包只有 12 个文件，规范要求 15。
3. 固定结尾 CTA 缺失（workflow §4）—— 这是 EP.184 以来 20+ 期的**批次性**缺口。
4. `SCRIPT.md` 自报字数 230 ≠ 实测 223（用了含空格的 `len()`）。

**另报 P1**：章节边界把 ThreeUI 的组件清单切进了第 2 章；07 场「十个**已上线**站点」是对 "ten **approved** immersive websites" 的翻译加码；判词卡把自家观点标成「本期观点 · 官方口径」。

### 轮次 2（复评）· P0=2（均为文档层）
1. `package-manifest.md` 里 `publish-copy.md` 的 md5 失效（清单生成之后文案又改过一次）。
2. `quality-report.md` / `visual-review.md` 缺失，而 `prepublish-checklist.md` 已勾「独立评审 P0=0（见 quality-report.md）」——**引用了一个不存在的文件**。

**另报 P1**：`used_repos()` 只补了「反引号」一种写法，粗体名 / npm scope / 正文裸名仍漏（列出 7 个真实历史仓库）；EP.178 重复披露的描述与产物不符（写成"表格数据"，实际名字+卖点上过屏）；`prepublish-checklist.md` 把三项许可写成「MIT / Apache-2.0」（本期三项**全 MIT**）；`performance-record.md` 字段与规范不符。

### 本轮（轮次 3，清零动作）· 已完成
- 清单**最后**重算（在全部文案改动之后）；
- 本报告 + `visual-review.md` 落包，checklist 第 26 行改为引用本报告并写明轮次；
- 205 的 EP.178 披露改成与产物一致的描述（名字与卖点确实上过屏、口播未念）；
- `used_repos()` 扩到「反引号 / 粗体 / npm scope / 正文裸名」四种形态，并加数字单位与本地目录过滤：评审给的 7 个漏检仓库**全部命中**，构造的误报样本全部被挡；
- checklist 许可行与 `performance-record.md` 字段按规范改正；
- 按评审建议改字幕折行：CTA 组由「关注柴主编陪 / 你一起跟上」改为「关注柴主编 / 陪你一起跟上」，并**重渲 + 重跑全部门禁**。"""

ROUNDS[206] = """### 轮次 1（首轮独立评审）· P0=1
**03 场把官方 README 的「四句顺序」说成「三步」并挂在「官方写的顺序」名下**；口播同源漏掉第三句 `Reverify returned work`。
- 证据：README 第 7 行逐字是四句（Write the acceptance ledger first. Execute reviewed checks. Reverify returned work. Report only what the evidence supports.），全文没有 "three steps"；成片 t=13.5s 的大字实测只有两个字（「三步」）。

**另报 P1**：字幕折行切断词（「六万一千／篇」「是给写作去／AI 味」「专拦低证据／代码」）；05 场把 93.2% 与 93.9% 两个**不同口径**的数字并列且缺 95.5% 基线；发布包缺文件；2–3.68s 的第二钩子是首帧同义复述。

### 轮次 2（复评）· P0=0
上一轮唯一的 P0 在**产物层面**确认修实：成片 03 场画面已是「官方四句 / README 原文顺序 / 四句都照做」；成片音轨与重录 `03.mp3` 相关 0.609、逐词 RMS 含「复验」，旧渲染同点位 −0.068；三处折行切词、05 基线、结尾 CTA、声称补的 7 个包文件都已落到产物上。

**另报 P1**：`quality-report.md` / `visual-review.md` 仍缺而 checklist 已勾；`package-manifest.md` 中 `publish-copy.md` 的 md5 失效；`sources.md` 1-2 的旧口播引文仍写「只报证据支持的结论」；新增的 CTA 字幕组折行切了「陪你」。

### 本轮（轮次 3，清零动作）· 已完成
- 本报告 + `visual-review.md` 落包，checklist 第 26 行改为引用本报告；
- 清单**最后**重算；
- `sources.md` 1-2 引文改为四句口径，三平台文案（抖音/小红书/视频号）统一补「复验」；
- CTA 折行改为「关注柴主编 / 陪你一起跟上」，并**重渲 + 重跑全部门禁**。"""

ROUNDS[207] = """### 轮次 1（首轮独立评审）· P0=2（均为文档层）
1. `prepublish-checklist.md` 勾了「独立评审 P0=0（见 quality-report.md）」，而**该文件不在包里**（与 EP.177 起 31 期没有报告落包是同一笔账）。
2. `sources.md` 把 **ARTEMIS 仓库 description 字段**的文字标成「README 逐字」，`publish-copy.md` 的口径行连带声明「全部来自 README / LICENSE」；同表另两处引用也非逐字（`IDE Diagnostics` 少了 "Model Context Protocol"；`It is a Chrome MV3 unpacked extension.` README 里没有句首 "It"）。

**另报 P1**：缺 `quality-report.md` / `visual-review.md`；小红书与视频号节缺「`chrome://` 这类受限页面用不了」这条风险前提（只有抖音正文写全）；`caption-group-13` 把产品名 `Chat On Steroids` 折行切开（实测合并宽 ≈526px < 可用 ≈610px，本可不折）。

**评审同时确认（留档）**：成片规格/密度/运动/窗口/字幕带/封面边距与出处/尾部 CTA/合规红线全部 PASS；**未误用 AndroidWorld 99%**；爪爪与 Chat On Steroids 的引文逐字命中，且口播照实点了「不打算绕过用量限制、额度还是共享的」。

### 本轮（轮次 2，清零动作）· 已完成
- 本报告 + `visual-review.md` 落包，checklist 第 26 行改为引用本报告；
- `sources.md` 1-2 定性改为「**官方仓库 description 字段逐字**」并注明来源字段，另两处引文按 README 原文回改；`publish-copy.md` 口径行同步；
- 三平台文案补「不在应用商店 / 要开发者模式加载 / Chrome 135+ / `chrome://` 与应用商店这类受限页面用不了」；
- `caption-group-13` 折行改为「第三个 / Chat On Steroids」，并**重渲 + 重跑全部门禁**。"""

for ep, slug in SLUG.items():
    pkg = pathlib.Path(f'content/episode-{ep}/publish-package-2026-09-22')
    video = pkg / f'czbvideo-{ep}-{slug}-bgm.mp4'
    md5 = hashlib.md5(video.read_bytes()).hexdigest()
    gate = [l.strip() for l in (pkg / 'gate-report.txt').read_text(encoding='utf-8').splitlines()
            if '门禁' in l and ('✓' in l or '★' in l)]
    body = f"""# quality-report — EP.{ep} 独立评审记录

> 评审由**未参与制作**的独立 subagent 完成（workflow §7 / `release-package.md` #13）。
> 本批成片在评审之后又因「字幕折行」修过一次并**重渲**，因此下方给出**评审后最终产物**的指纹。

## 产物指纹（最终）
- 成片 `czbvideo-{ep}-{slug}-bgm.mp4` · md5 `{md5}` · {video.stat().st_size:,} B
- 封面 `cover-3x4.png` / `cover-4x3.png`（出处与后处理见 `cover-meta.json`；`verify_cover_postprocess.py` 可逐像素复算）
- 门禁明细：`gate-report.txt`

## 评审轮次与处置

{ROUNDS[ep]}

## 最终门禁状态
```
{chr(10).join(gate)}
```
- 门禁H（成片字幕带墨迹/孤行）：≤2 行 · 最大墨迹 ≤98px（上限 120px）· 无 <70px 孤行
- `chai_check_motion.py` PASS（黑段 0 · 静音 0）· `chai_window_check.py` PASS 8/8
- 首帧 `chai_hook_check.py` ❌=0（唯一 ⚠️ 是「前 2 秒画面黑名单」人工确认项，评审已逐帧像素确认：四角准星自 t=0 恒定、无柔光渐显、首帧大字带数字）
- 封面：门禁E 逐字命中 · 主标题四边 ≥8% · 门禁F PASS（`generator=gpt-atutun`、跨期结构一致）

## 残留（如实记，不阻断发布）
1. 字幕折行修好后**重渲**，评审的 md5 边界随之失效；改动仅限一个字幕组的折行，已由制作方窄口径复核（门禁H + 抽帧），未再跑整轮评审。
2. 视频号**正文**含连字符（`scroll-craft` / `anti-slop` / `unlazy`）：三条标题干净，正文平台是否受限尚无定论。
3. `chai_cover_check.py` 临时文件按 basename 命名 → **并发跑多期会串图**（历史残留，未修）。
4. 门禁F 打印的参考值「同套 GPT 版 ≈0.54」与本机复算不符（阈值 0.10、余量充足，判定不受影响），属文案陈旧。
5. 形态档位：本批是「≤60s 清单型 + 2 章 8 场」，skill 形态表只列了 5 / 7 / 20–30 场；`chai_script_pace.py` 会自报「段数 8 不在槽位表内」。
"""
    pkg.joinpath('quality-report.md').write_text(body, encoding='utf-8')
    print(f'EP.{ep} quality-report.md ✓ 成片 md5 {md5[:12]}…')
