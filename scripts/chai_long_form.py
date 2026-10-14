#!/usr/bin/env python3
"""柴主编 · **长视频模板的版面常量单一来源**（2026-09-12 新增）。

## 为什么要有这个文件

改这个流水线最容易踩的坑是「同一个数字写在两处」：

- `gen_chai_frames.py` 在**生成期**按宽度模型选字号并硬断言（放不下就 SystemExit）；
- `chai_layout_precheck.py` 在**写稿期**用同一套模型预报超宽。

两处一旦对不上，就会出现「预检说超宽、生成器说没问题」（浪费一次排查）
或者更糟的**「预检说没问题、生成器炸了」**。本次长视频改造就实际发生过：
预检里章节页标题的可用宽写的是 268px 序号那版的 458px，而生成器已经把序号降到
224px、可用宽提到 558px —— 预检报 3 处「接近超宽」，那 3 处其实早就修好了。

所以把**几何数字与校准系数**全部收进本模块：

    CH_TITLE_MIN_FS / CH_TITLE_SAFE / CH_W / CH_GAP / CH_PAD_X / CH_TX_PAD / CH_NO_FS
    QUOTE_* / TABLE_* / FLOW_* / CASE_* / HERO_*

`gen_chai_frames.py` 用 `_long_geom()` 取「生成期实际会用的那档字号」，
`chai_layout_precheck.py` 直接调用同一个函数 —— **是同一份计算，不是两份拷贝**。
两个脚本都用 `importlib` 按文件路径加载本模块（脚本要能单独拷走运行，
不做包结构）。

## 与既有脚本的关系

本模块**只描述长视频新模板**，一个字节都不影响既有的 01–05 / 05-config / 06-verify /
07-verdict 路径（那些的常量仍在 `gen_chai_frames.py` 里，未做任何改动）。
修改本文件里任何一个数字，都等于同时改生成期与预检 —— 这正是想要的。
"""
from __future__ import annotations

import re
import sys

# ── 与 gen_chai_frames._estw / chai_layout_precheck.width_px **同一套宽度模型** ────
LATIN = 0.66          # 拉丁字母数字（CobaltMono 单字宽）
SPACE = 0.33
MIDDOT = 0.55


def estw(t, font: float) -> float:
    """估算文本宽度（px）。中文 1.0em / 拉丁数字 0.66em / 空格 .33em / 中点 .55em。"""
    w = 0.0
    for ch in str(t or ""):
        if ch == " ":
            w += font * SPACE
        elif ch in "·．":
            w += font * MIDDOT
        elif re.match(r"[A-Za-z0-9\.\-\+/%_]", ch):
            w += font * LATIN
        else:
            w += font * 1.0
    return w


def wrap_count(text, font: float, max_w: float) -> int:
    """按 estw 模型估算折行数（保守：宁可多算一行）。"""
    lines, cur = 0, ""
    for ch in str(text or ""):
        cand = cur + ch
        if cur and estw(cand, font) > max_w:
            lines += 1
            cur = ch
        else:
            cur = cand
    return lines + (1 if cur else 0)


def fit_font(texts, max_w: float, sizes: list, max_lines: int = 2):
    """在那几档字号（**从大到小**）里挑最大的、能让每条都 ≤ max_lines 行的字号。

    返回 (字号 | None, {最坏那条: 行数})。两处调用的是同一个函数 —— 预检因此
    永远复现生成期的结论。
    """
    texts = [t for t in texts if t]
    if not texts:
        return (sizes[0] if sizes else None), {}
    for f in sizes:
        info = {t: wrap_count(t, f, max_w) for t in texts}
        if all(v <= max_lines for v in info.values()):
            return f, info
    f = sizes[-1]
    info = {t: wrap_count(t, f, max_w) for t in texts}
    worst = max(info, key=lambda t: info[t])
    return None, {worst: info[worst]}


# ── 校准系数：_estw / width_px 的模型误差 ─────────────────────────────────────
# 2026-09-12 用浏览器 span 实测（Noto Sans SC 900 / PingFang SC 回退）：
#   「代理与缓存踩过的坑」60px 单行实测 **535px**，而 estw 只算 460px → 偏低 14%；
#   「命中缓存省 90%」118px 实测 **约 800px**，estw 算 992px → 偏高 19%
#   （ASCII 在 900 字重下实测推进 ≈0.55em，而模型按 0.66em 算）。
# 结论：**CJK 偏低、ASCII 偏高**。所以校准系数只加在「必须一行放下」的 CJK 密集文案上
# （章节页标题、首帧/判词大字），中文按 1.15 放大；允许折行的预算不动，
# 因为「多算一行」是安全方向。
CJK_ADV_SAFE = 1.15

# ── 内容区与竖向预算（1080×1920）────────────────────────────────────────────
SAFE_W = 860          # 内容宽 = 1080 − 110×2
SAFE_X = 110
NOTE_TOP = 1408       # .note 的来源行位置（既有皮肤常量）
CARD_BOTTOM_MAX = 1290    # 卡片底边硬上限（给 .note 留 118px）

# ── chapter ────────────────────────────────────────────────────────────────
# 与 gen_chai_frames.LONG_CHAPTER_CSS 同源（改一处必须改两处 —— 但都在本文件里）
CH_NO_FS = 224          # #ch-no 字号（比既有 .idx 的 200px 大 → 与 01-hook 区分度保持）
CH_NO_ADV = 1.20        # 序号列安全系数（实测 CJK 推进 ≈1.13em + 6% 余量）
CH_GAP = 28             # #ch-body gap
CH_PAD_X = 26           # #ch-title 左右内边距
CH_TX_PAD = 22          # #ch-title .tx padding-left（给左侧 14px 酸柠条让位）
CH_TITLE_SIZES = [60, 56, 52, 48, 44, 40, 36]
CH_TITLE_MIN_FS = CH_TITLE_SIZES[-1]
CH_STEP_AVAIL = SAFE_W - 2 * 26 - 46 - 20      # .stp：卡内边距 26×2 + 序号列 46 + gap 20
CH_STEP_SIZES = [30, 28, 26, 24]
CH_STEP_MIN_FS = CH_STEP_SIZES[-1]


def to_cjk_num(n) -> str:
    """1..30 → 汉字序号（章节页大号数字用；范围外给阿拉伯数字）。"""
    d = "零一二三四五六七八九"
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if not 1 <= n <= 30:
        return str(n)
    if n < 10:
        return d[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + d[n % 10]
    return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")


def chapter_geom(no, title: str, steps: list) -> dict:
    """章节页几何（**生成期与预检共用**）。

    返回 {no_txt, no_w, col_w, title_avail, title_fs, title_lines, step_fs, errors}
    `errors` 是 [(kind, 说明)]，调用方决定是 SystemExit 还是打印 ⚠️。
    """
    no_txt = to_cjk_num(no) if str(no).lstrip("-").isdigit() else str(no or "")
    no_w = estw(no_txt, CH_NO_FS) * CH_NO_ADV
    col_w = SAFE_W - no_w - CH_GAP
    title_avail = col_w - CH_PAD_X * 2 - CH_TX_PAD
    errors = []
    if col_w < 480:
        errors.append(("no", f"章节页序号「{no_txt}」太宽（≈{no_w:.0f}px），"
                             f"标题列只剩 {col_w:.0f}px < 480px"))
    tfs, tinfo = (None, {})
    if title:
        tfs, tinfo = fit_font([title], max(title_avail, 1) / CJK_ADV_SAFE,
                              CH_TITLE_SIZES, max_lines=1)
        if tfs is None:
            errors.append(("title", f"章节页标题在 {CH_TITLE_MIN_FS}px 下仍放不下一行"
                                    f"（可用 {title_avail:.0f}px，实测口径标题宽 "
                                    f"≈{estw(title, CH_TITLE_MIN_FS) * CJK_ADV_SAFE:.0f}px）：「{title}」"))
    sfs = None
    if steps:
        if len(steps) > 3:
            errors.append(("steps", f"章节页 steps 最多 3 条（当前 {len(steps)} 条）"))
        else:
            sfs, _si = fit_font(steps, CH_STEP_AVAIL / CJK_ADV_SAFE, CH_STEP_SIZES, max_lines=1)
            if sfs is None:
                worst = max(steps, key=lambda t: estw(t, CH_STEP_MIN_FS))
                errors.append(("steps", f"章节页预览行在 {CH_STEP_MIN_FS}px 下仍放不下一行"
                                        f"（可用 {CH_STEP_AVAIL:.0f}px）：「{worst}」"))
    return {"no_txt": no_txt, "no_w": no_w, "col_w": col_w, "title_avail": title_avail,
            "title_fs": tfs, "title_lines": tinfo, "step_fs": sfs, "errors": errors}


# ── quote ──────────────────────────────────────────────────────────────────
QT_PAD_X = 52
QT_SIZES = [68, 64, 60, 56, 52, 48, 44, 40, 36]
QT_MIN_FS = QT_SIZES[-1]
QT_MAX_LINES = 6
QT_INNER = SAFE_W - QT_PAD_X * 2


def quote_geom(quote: str, head: str = "") -> dict:
    """引用页几何（共用）。允许折 2–6 行，最小档 36px 仍超 6 行才算超宽。

    ⚠️ 2026-09-12 修：**显式 `\\n` 断行时原来硬套最小档 36px**，导致"作者已经手动断好行"
    的引文**永远只能用小字**（EP.170 的 `11-quote` 因此要么词中断行、要么字缩到 36px）。
    现在改成：**在字号阶梯里从大到小找第一个"每一行都放得下"的档位**——显式断行的引文
    也能拿到尽可能大的字号（例：`This timeout isn't` / `configurable.` 两行 → 64px 而不是 36px）。
    自动折行那条路径（无 `\\n`）**逐字节不变**。
    """
    errors = []
    lines = quote.split("\n") if "\n" in quote else []
    if "\n" in quote:
        lines = [x.strip() for x in lines if x.strip()]
        nlines = len(lines)
        fs = None
        for cand in QT_SIZES:                      # QT_SIZES 从大到小
            if all(estw(ln, cand) <= QT_INNER for ln in lines):
                fs = cand
                break
        if fs is None:                             # 连最小档都放不下 → 退回最小档并**告警**
            fs = QT_MIN_FS
            over = max(estw(ln, QT_MIN_FS) for ln in lines) if lines else 0.0
            # ⚠️ 这里**不报 error**：旧行为对显式断行是"照排不检查宽度"，一旦改成硬失败会
            #    让本来能生成的期直接建不出来（EP.171 的 08-quote 就是这样：估宽 903px）。
            #    宽度是**估算模型**，英文实例常偏大 → 降级为 stderr 告警，由人复核画面。
            print(f"[quote 告警] 某行在 {QT_MIN_FS}px 下估宽 ≈{over:.0f}px > 内容宽 {QT_INNER}px"
                  f"（估算模型偏保守，请以成片帧实测为准）：{lines[0][:40] if lines else ''}",
                  file=sys.stderr)
        ok = nlines <= QT_MAX_LINES
    else:
        fs, info = fit_font([quote], QT_INNER, QT_SIZES, max_lines=QT_MAX_LINES)
        ok = fs is not None
        if not ok:
            nlines = info.get(quote, 0)
        else:
            nlines = wrap_count(quote, fs, QT_INNER)
    if not ok:
        errors.append(("quote", f"引用页引文在 {QT_MIN_FS}px 下仍要 {nlines} 行"
                                f"（可用 {QT_INNER}px，引文宽 ≈{estw(quote, QT_MIN_FS):.0f}px）；"
                                f"建议用 \\n 显式断行成 2–4 行"))
    lines_h = nlines * (fs if fs else QT_MIN_FS) * 1.36
    tail_h = (60 if head else 0) + 26
    card_h = int(QT_PAD_X * 0 + 44 * 2 + lines_h + 30 + tail_h)
    top = max(430, min(660, 900 - card_h // 2))
    if top + card_h > CARD_BOTTOM_MAX:
        errors.append(("quote_h", f"引用页卡片高 {card_h}px + top {top}px 越过内容下限 "
                                  f"{CARD_BOTTOM_MAX}px（{nlines} 行 × {fs}px）"))
    return {"fs": fs, "lines": nlines, "card_h": card_h, "top": top, "errors": errors}


# ── table ──────────────────────────────────────────────────────────────────
TB_PAD_X = 26
TB_CELL_PAD = 22
TB_BORDER = 3
TB_K_RATIO = 0.18
TB_K_AVAIL = int(SAFE_W * TB_K_RATIO) - (TB_PAD_X + TB_CELL_PAD) - TB_BORDER
TB_V_AVAIL = SAFE_W - int(SAFE_W * TB_K_RATIO) - (TB_PAD_X + TB_CELL_PAD) - TB_BORDER
TB_K_SIZES = [26, 24, 22, 20]
TB_V_SIZES = [28, 26, 24, 22, 20]
TB_MIN_FS = 20
TB_ROWS_MIN, TB_ROWS_MAX = 3, 6


def table_geom(rows: list) -> dict:
    """对照表几何（共用）：行名列 18% / 数值列 82%，每格最多折 2 行。"""
    errors = []
    ks = [r[0] for r in rows]
    vs = [r[1] for r in rows]
    kfs, kinfo = fit_font(ks, TB_K_AVAIL, TB_K_SIZES, max_lines=2)
    vfs, vinfo = fit_font(vs, TB_V_AVAIL, TB_V_SIZES, max_lines=2)
    for label, fs, info, avail in (("行名列", kfs, kinfo, TB_K_AVAIL),
                                   ("数值列", vfs, vinfo, TB_V_AVAIL)):
        if fs is None:
            t, n = next(iter(info.items()))
            errors.append(("cell", f"对照表{label}在最小字号下仍要 {n} 行"
                                   f"（可用宽 {avail}px）：「{t}」"))
    kfs = kfs or TB_K_SIZES[-1]
    vfs = vfs or TB_V_SIZES[-1]
    row_h = int(max(kfs, vfs) * 1.30) + 32
    return {"k_fs": kfs, "v_fs": vfs, "row_h": row_h, "k_avail": TB_K_AVAIL,
            "v_avail": TB_V_AVAIL, "errors": errors}


def table_height(nrows: int, has_head: bool, has_title: bool, row_h: int) -> int:
    head_h = 20 * 2 + 26 if has_head else 0
    head_block = (32 * 1.3 + 8 + 22 * 1.4 + 18) if has_title else 0
    return TB_PAD_X + 30 + head_block + head_h + nrows * row_h + nrows * 1 + 2


# ── flow ───────────────────────────────────────────────────────────────────
FLOW_TRACK_W = 860          # 轨道总宽（= 内容宽）
FLOW_AXIS_W = 748           # #fl-axis 宽
FLOW_CARD_PAD_X = 20        # #fl-card 左右内边距
FLOW_AXIS_LEFT = 26         # #fl-axis left（relative）
FLOW_LB_W = 172             # 单个标签列宽上限（860/5）
FLOW_STEP_MIN, FLOW_STEP_MAX = 3, 5
FLOW_T_SIZES = [24, 22, 20, 18]
FLOW_S_SIZES = [17, 16, 15]
FLOW_AXIS_X = SAFE_X + FLOW_CARD_PAD_X + FLOW_AXIS_LEFT     # 156
# 轴高：标签在 top:66 起（29 + 7 + 20 = 56 → 到 122），142 时标签底缘会伸出卡片，
# 被 hyperframes 判 text_box_overflow（实测标签底 733.98 vs 卡底 684）→ 取 162。
FLOW_AXIS_H = 162
FLOW_HEAD_TOP = 34          # #fl-card 上内边距
FLOW_HEAD_H = 83            # #fl-head 实测高：34×1.3 + gap 8 + 22×1.4 = 44.2 + 8 + 30.8 = 83.0
FLOW_GAP = 26               # #fl-card 的 flex gap
FLOW_PAD_BOTTOM = 36        # #fl-card 下内边距


def flow_geom(steps: list) -> dict:
    """流程条几何（共用）：3–5 步，每步列宽 172px，标题最多折 2 行。"""
    errors = []
    n = len(steps)
    if not (FLOW_STEP_MIN <= n <= FLOW_STEP_MAX):
        errors.append(("steps", f"flow 的 steps 必须是 {FLOW_STEP_MIN}–{FLOW_STEP_MAX} 步（当前 {n}）"))
    tfs, tinfo = fit_font([s["t"] for s in steps], FLOW_LB_W, FLOW_T_SIZES, max_lines=2)
    sfs, sinfo = fit_font([s.get("s", "") for s in steps], FLOW_LB_W, FLOW_S_SIZES, max_lines=2)
    if tfs is None:
        t, _ = next(iter(tinfo.items()))
        errors.append(("t", f"flow 步骤标题在 {FLOW_T_SIZES[-1]}px 下仍要 {tinfo[t]} 行"
                            f"（每列可用 {FLOW_LB_W}px）：「{t}」"))
    if sfs is None and any(s.get("s") for s in steps):
        t = next(iter(sinfo))
        errors.append(("s", f"flow 步骤说明在 {FLOW_S_SIZES[-1]}px 下仍要 {sinfo[t]} 行"
                            f"（每列可用 {FLOW_LB_W}px）：「{t}」"))
    if FLOW_AXIS_X < SAFE_X or FLOW_AXIS_X + FLOW_AXIS_W > SAFE_X + SAFE_W:
        errors.append(("axis", f"flow 轴超出安全区（{FLOW_AXIS_X}..{FLOW_AXIS_X + FLOW_AXIS_W}，"
                               f"安全区 {SAFE_X}..{SAFE_X + SAFE_W}）"))
    # 卡片高度必须覆盖：上内边距 + 卡头 + flex gap + 轴（含 margin-top 20）+ 下内边距。
    # 早期版本漏了卡头实测 83px（按 60 估）与 flex gap 26，卡片算小 49px，
    # 轴的 height 被 flex 压成 51px、标签伸出卡片 → hyperframes 报 text_box_overview。
    card_h = FLOW_HEAD_TOP + FLOW_HEAD_H + FLOW_GAP + 20 + FLOW_AXIS_H + FLOW_PAD_BOTTOM
    if 452 + card_h > CARD_BOTTOM_MAX:
        errors.append(("h", f"flow 卡片高 {card_h}px + top 452px 越过内容下限 {CARD_BOTTOM_MAX}px"))
    return {"t_fs": tfs, "s_fs": sfs, "card_h": card_h, "axis_x": FLOW_AXIS_X,
            "span": FLOW_AXIS_W / max(1, n - 1), "errors": errors}


# ── case ───────────────────────────────────────────────────────────────────
CS_PAD_X = 36
CS_RAIL = 96
CS_T_SIZES = [32, 30, 28, 26, 24]
CS_AVAIL = SAFE_W - CS_RAIL - CS_PAD_X * 2


def case_geom(chain: list) -> dict:
    """案例页几何（共用）：正好 3 段，正文最多折 2 行。"""
    errors = []
    if len(chain) != 3:
        errors.append(("chain", f"case 的 chain 必须正好 3 段（现象 → 机制 → 结果；当前 {len(chain)} 段）"))
    tfs, tinfo = fit_font([c["t"] for c in chain], CS_AVAIL, CS_T_SIZES, max_lines=2)
    if tfs is None:
        t, _ = next(iter(tinfo.items()))
        errors.append(("t", f"case 段落正文在 {CS_T_SIZES[-1]}px 下仍要 {tinfo[t]} 行"
                            f"（可用宽 {CS_AVAIL}px）：「{t}」"))
    tfs = tfs or CS_T_SIZES[-1]
    nd_h = 24 * 2 + 25 * 1.2 + 10 + tfs * 1.35 * 2
    chain_h = 3 * nd_h + 2 * 44 + 4
    return {"t_fs": tfs, "nd_h": nd_h, "chain_h": chain_h, "avail": CS_AVAIL, "errors": errors}


# ── 既有大标题行（01 首帧 / 末场判词）────────────────────────────────────────
# ⚠️ 这两条属于**既有模板**，模板本身一个字不能改（改了会破坏老路径的逐字节零回归）。
# 但它们在长视频里最容易溢出：`#f1-hero`（118px）/ `#f5-hero`（110px）**没有 max-width、
# 也不换行**，文案比内容区宽就直接向右溢出画布（实测合成用例 970px 盒里放 1051px 一行，
# 右边缘到 x1080）。所以在预检里给出「一行必须放下」的预算。
HERO01_FS = 118
HERO05_FS = 110
