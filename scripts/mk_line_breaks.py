#!/usr/bin/env python3
"""把 spec 的 line_breaks 按「分词 + DP 装箱」自动生成，并保证**逐字拼回原文**。

用法：
    python3 scripts/mk_line_breaks.py specs/176.json content/episode-176/publish-timeline/caption_groups.json

为什么这么写（2026-09-12 EP.176 两次踩坑）：
  ① `gen_chai_frames.py` 有硬断言 `"".join(lines) == text` → 折行**不能吃掉空格**
     （拉丁词前后的空格会被 jieba 分词丢掉）。本脚本按**原文切片**重建每一行。
  ② 按字数对半切会把「一批」「声音」这种词切开 → 用 jieba 分词后 DP 装箱，行内是整词。
  ③ 单行宽度上限按「汉字 1.0 / ASCII 0.6」折算，默认 10（字幕带 542px ≈ 10 个汉字）。
可选：脚本里 OVERRIDES 按**原文**给人工指定折行（语义更顺），键是去空格后的原文。

⚠️ jieba 只用于**写稿期**生成 spec；管线脚本（gate/render）仍零第三方依赖。
"""
from __future__ import annotations
import json, math, re, sys, unicodedata
from pathlib import Path

import jieba
jieba.setLogLevel(60)

# 与 `chai_layout_precheck.py` 同一套宽度模型（字幕带预算 = 542px @ 字号 56）
CAPTION_FONT = 56
CAPTION_MAXW = 542.0
LATIN = 0.66
MAXW = CAPTION_MAXW     # 单行预算（px）         # 与 chai_layout_precheck.LATIN 一致（该文件第 22 行）
OVERRIDES: dict[str, list[str]] = {
    "苹果九月九号给新手表加了一批和声音有关的功能": ["苹果九月九号", "给新手表加了一批", "和声音有关的功能"],
    "一条补你刚没听清的那句": ["一条补你", "刚没听清的那句"],
    "但官方自己写了一条边界": ["但官方自己", "写了一条边界"],
    "官方写激活时会出手表提示音": ["官方写激活时", "会出手表提示音"],
    "这是为了让周围的人知道": ["这是为了", "让周围的人知道"],
    "官方专门给它做了提示音和动画": ["官方专门给它", "做了提示音和动画"],
    "第二章看官方自己写下的边界": ["第二章", "看官方自己写下的边界"],
    "还有一天结束后的对话摘要": ["还有一天结束后", "的对话摘要"],
    "但不会标出是哪个人说的": ["但不会标出", "是哪个人说的"],
    "回看要在手机的 Watch 应用里点 Siri": ["回看要在手机的", "Watch 应用里点 Siri"],
}


def units(t: str) -> float:
    """返回该行的**像素宽度**（口径同 `chai_layout_precheck.width_px`，font=56）。
    空格 0.33em · 拉丁/数字/半角符号 0.6em · 中日韩全角 1.0em。"""
    w = 0.0
    for ch in t:
        if ch == " ":
            w += CAPTION_FONT * 0.33
        elif ch in "·．":
            w += CAPTION_FONT * 0.55
        elif re.match(r"[A-Za-z0-9\.\-\+/%_]", ch):
            w += CAPTION_FONT * LATIN
        else:
            w += CAPTION_FONT * 1.0
    return w


MEASURE = set("号年月日点分秒万亿个条次种家版本张只块元度千米岁人位名层份篇章节款台件颗枚遍趟回番遭圈%倍")


def _tokens(text: str) -> list[tuple[str, int]]:
    """分词 → 单元列表 [(单元文本, 结束偏移)]，并做**三类合并**（2026-09-12 EP.177 实测）：

    ① 空白并入前一个单元（空格真实占宽 0.33em，漏算会假通过）；
    ② 数字/拉丁 单元与**紧邻的量词**合并（防「10 号」→「10 / 号」、「17 年」→「17 / 年」）；
    ③ 相邻的数字/拉丁 单元合并（防模型名被拆：`V4.1-Flash`、`GPT-Live-1`、`LingBot-World 2.0`、`K2.8 Preview`），
       合并上限 = 单行预算的 80%，超长的名字仍允许被切开。
    """
    raw: list[tuple[str, int]] = []
    pos = 0
    for t in jieba.lcut(text):
        if not t:
            continue
        if not t.strip():
            if raw:
                w, e = raw[-1]
                raw[-1] = (w + t, e)
            pos += len(t)
            continue
        i = text.find(t, pos)
        if i < 0:
            i = pos
        pos = i + len(t)
        raw.append((t, pos))

    def is_num(w: str) -> bool:
        c = w.strip()
        return bool(c) and bool(re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.\-+/_]*", c))

    # ② + ③：合并
    merged: list[tuple[str, int]] = []
    for w, e in raw:
        if merged:
            pw, pe = merged[-1]
            start_ch = w.lstrip()[:1]
            if is_num(pw) and start_ch and start_ch in MEASURE:
                merged[-1] = (pw + w, e)
                continue
            if is_num(pw) and is_num(w) and units(pw + w) <= MAXW * 0.8:
                merged[-1] = (pw + w, e)
                continue
            # ③b：把「拉丁连写段」尽量并成一个单元（连字符/点/空格也并入），
            #     上限 1.15×预算 —— 让 `LingBot-World 2.0` 这类名字整体不被打断，
            #     万不得已时也只允许在连字符处切（见 pack 里的"非自然切点"惩罚）。
            if is_num(pw) and (is_num(w) or w.strip()[:1] in "-.[]"):
                if units(pw + w) <= MAXW * 1.15:
                    merged[-1] = (pw + w, e)
                    continue
        merged.append((w, e))
    return merged


def _cut_penalty(text: str, c: int) -> float:
    """切点 c 的"不自然"惩罚：**拉丁词内部**（两侧都是字母/数字/点）切开要付代价，
    迫使 DP 优先在连字符、空格或中文边界处断开（2026-09-12 EP.177：`模型 LingBot | -World 2.0`）。"""
    if c <= 0 or c >= len(text):
        return 0.0
    a, b = text[c - 1], text[c]
    lat = lambda ch: bool(re.match(r"[0-9A-Za-z.]", ch))
    if lat(a) and lat(b):
        return 5000.0
    return 0.0


def pack(text: str) -> list[str]:
    """把一行字幕折成若干行：**切点只能落在（合并后的）单元边界上**，且每行 ≤ 预算。

    实现 = 在单元边界上做 DP，代价 = Σ(行宽 − 目标行宽)²（目标 = 总宽 / 行数），
    行数取 `ceil(总宽 / 预算)` 与 `+1` 里可行的更优者。DP 只在**边界**上枚举 → 不会把词/数字拆开。
    """
    toks = _tokens(text)
    if len(toks) <= 1 or units(text) <= MAXW:
        return [text]
    n = len(toks)
    ends = [0] + [e for _, e in toks]
    W = [units(text[ends[i]:ends[i + 1]]) for i in range(n)]
    total = sum(W)
    best: tuple[float, list[str]] | None = None
    INF = float("inf")
    for K in range(max(2, math.ceil(total / MAXW)), max(2, math.ceil(total / MAXW)) + 2):
        if K > n:
            break
        target = total / K
        dp = [[INF] * (K + 1) for _ in range(n + 1)]
        par = [[-1] * (K + 1) for _ in range(n + 1)]
        dp[0][0] = 0.0
        for i in range(1, n + 1):
            for l in range(1, K + 1):
                acc = 0.0
                for j in range(i - 1, -1, -1):
                    acc += W[j]
                    if acc > MAXW:
                        break
                    if dp[j][l - 1] < INF:
                        c = dp[j][l - 1] + (acc - target) ** 2 + _cut_penalty(text, ends[j])
                        if c < dp[i][l]:
                            dp[i][l] = c
                            par[i][l] = j
        if dp[n][K] >= INF:
            continue
        cuts, i, l = [], n, K
        while l > 0 and i > 0:
            cuts.append(ends[i])
            i = par[i][l]
            l -= 1
        cuts.reverse()
        lines, prev = [], 0
        for c in cuts:
            lines.append(text[prev:c])
            prev = c
        if dp[n][K] < (best[0] if best else INF):
            best = (dp[n][K], [x for x in lines if x])
        # ⚠️ 2026-09-17 修（EP.187/188/189 复评 P1-1）：**只要 K 行可行就用 K 行，不再试 K+1**。
        #    旧写法会在 K 与 K+1 里挑「行宽更均衡」的那个，于是 20 来字的字幕经常被折成 **3 行**——
        #    实测字幕盒 150px，而模板的 `--cap-band-height` 只有 **114px**（2 行 = 98px 正好在带内），
        #    3 行会向上多出 17px、向下多出 18px，离场景注脚最近只剩 15px（模板契约被破）。
        #    少折一行既不改变语义，也不越过单行预算（DP 里 `acc > MAXW` 仍然硬拦）。
        break
    return best[1] if best else [text]


def main() -> int:
    spec_p, groups_p = Path(sys.argv[1]), Path(sys.argv[2])
    spec = json.loads(spec_p.read_text(encoding="utf-8"))
    cg = json.loads(groups_p.read_text(encoding="utf-8"))
    groups = cg if isinstance(cg, list) else cg.get("groups", cg)
    lb, bad = {}, []
    for g in groups:
        t = g.get("text", "").strip()
        key = g.get("id") or g.get("key")
        if len(re.sub(r"\s", "", t)) < 11:
            continue
        # 键与原文都做空格归一化后再比（否则带空格的键永远匹配不上）
        _norm = t.replace(" ", "")
        ov = next((v for k, v in OVERRIDES.items() if k.replace(" ", "") == _norm), None)
        parts = pack(t)
        if ov:
            # 人工折行也要把空格按原文补齐
            fixed, pos = [], 0
            for k, seg in enumerate(ov):
                core = seg.strip()
                if k == len(ov) - 1:
                    fixed.append(t[pos:]); break
                j = t.find(core, pos)
                end = j + len(core)
                while end < len(t) and t[end] == " ":
                    end += 1
                fixed.append(t[pos:end]); pos = end
            parts = fixed
        if len(parts) > 1:
            lb[key] = parts
        if "".join(parts) != t:
            bad.append((key, parts, t))
    spec["line_breaks"] = lb
    spec_p.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    over = [(k, [x for x in v if units(x) > MAXW + 1]) for k, v in lb.items() if any(units(x) > MAXW + 1 for x in v)]
    print(f"✅ 写入 line_breaks {len(lb)} 条 · 逐字拼回不一致 {len(bad)} 条 · 单行超预算({CAPTION_MAXW:.0f}px) 的 {len(over)} 条")
    for k, p, t in bad:
        print("   ❌", k, p, "原:", t)
    for k, v in over:
        print("   ⚠️", k, v)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
