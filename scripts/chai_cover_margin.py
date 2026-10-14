#!/usr/bin/env python3
"""封面安全边距门禁（2026-09-17 起）。

**为什么有它**：2026-09-16 抖音竖封面「文字展示不全」事故之后，我们在封面提示词里写了
「离四边至少留 8%」这条硬规则 —— 但**提示词不是门禁**：模型照样产出过主标题右边距
只有 1.16% 的封面（EP.190 3:4，实测），包照样能过门禁E，照样发得出去。

做法：用 macOS Vision 逐字 OCR（scripts/bin/vision_ocr，必须带 `w` 字段）拿到每行文字的
归一化包围盒，算出「左边距 / 右边距 / 上边距 / 下边距」，硬判：

  · **主标题行**（字号最大的那一行）四边边距必须 ≥ `--hero-min`（默认 8%），
    左右边距必须 ≥ `--hero-min-x`（默认 8%；12% 是更稳的目标，竖封面两侧都可能被裁）。
  · **其余任何文字**四边边距必须 ≥ `--text-min`（默认 3%，装饰性背景字可以更贴边一些，
    但仍不许被裁），越界只报 ⚠️ 不硬判。

⚠️ 已知局限（踩过的坑，别当 bug）：
  · Vision 的包围盒**不含描边/阴影**，所以「量出来 8%」实际视觉上可能更贴边 ——
    阈值故意留了余量；反过来，带描边的艺术字可能被量成「贴边」，属误报，人工看一眼。
  · OCR 认不出的行（字太小、太艺术）不会参与判定 —— 所以**它不能替代人眼**，
    只是把「明显贴边」这类事故变成一条可复现的数字。

用法：
  python3 scripts/chai_cover_margin.py content/episode-194/exp-gpt/cover-3x4.png
  python3 scripts/chai_cover_margin.py <covers_dir>            # 目录下所有 cover-*.png
退出码：0 = PASS；1 = FAIL（有硬判项越界）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "scripts", "bin", "vision_ocr")


def ocr(path: str) -> list[dict]:
    out = subprocess.run([BIN, path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"❌ vision_ocr 失败：{out.stderr[:300]}（先跑 swiftc -O scripts/vision_ocr.swift -o scripts/bin/vision_ocr）")
    data = json.loads(out.stdout)
    if not data:
        return []
    lines = data[0].get("lines", [])
    if lines and "w" not in lines[0]:
        sys.exit("❌ vision_ocr 输出没有 w 字段：请重新编译（swiftc -O scripts/vision_ocr.swift -o scripts/bin/vision_ocr）")
    return lines


def margins(l: dict) -> tuple[float, float, float, float]:
    """返回 (左, 右, 上, 下) 边距，百分比。"""
    return (l["x"] * 100, (1 - l["x"] - l["w"]) * 100, l["y"] * 100, (1 - l["y"] - l["h"]) * 100)


def check(path: str, hero_min: float, hero_min_x: float, text_min: float) -> bool:
    lines = ocr(path)
    name = os.path.basename(os.path.dirname(path)) + "/" + os.path.basename(path)
    print(f"── {name}")
    if not lines:
        print("   ⚠️ 一个字都没识别出来，跳过（人工看一眼这张图）")
        return True
    hero = max(lines, key=lambda l: l["h"])
    ok = True
    for l in lines:
        lm, rm, tm, bm = margins(l)
        is_hero = l is hero
        need = hero_min if is_hero else text_min
        need_x = hero_min_x if is_hero else text_min
        bad = (lm < need_x) or (rm < need_x) or (tm < need) or (bm < need)
        tag = "主标题" if is_hero else "文字  "
        mark = "❌" if (bad and is_hero) else ("⚠️" if bad else "✅")
        if bad and is_hero:
            ok = False
        print(f"   {mark} {tag}「{l['t'][:22]}」 左 {lm:5.2f}% 右 {rm:5.2f}% 上 {tm:5.2f}% 下 {bm:5.2f}%"
              f"（要求 ≥ {need_x:g}% 左右 / ≥ {need:g}% 上下）")
    print(f"   → {'✅ 安全边距通过' if ok else '❌ 主标题贴边，必须重出封面（平台会裁掉贴边的字）'}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="封面 png，或包含 cover-*.png 的目录")
    ap.add_argument("--hero-min", type=float, default=8.0, help="主标题上下边距下限（%%），默认 8")
    ap.add_argument("--hero-min-x", type=float, default=8.0, help="主标题左右边距下限（%%），默认 8（= 提示词里写死的硬规则；12 是更稳的目标）")
    ap.add_argument("--text-min", type=float, default=3.0, help="其余文字边距下限（%%），默认 3")
    a = ap.parse_args()

    if os.path.isdir(a.target):
        files = sorted(
            os.path.join(a.target, f) for f in os.listdir(a.target)
            if f.startswith("cover-") and f.endswith(".png") and not f.endswith(".raw.png")
        )
    else:
        files = [a.target]
    if not files:
        sys.exit(f"❌ 没找到封面图：{a.target}")

    allok = all(check(f, a.hero_min, a.hero_min_x, a.text_min) for f in files)
    print("\n结论：" + ("[PASS] 封面文字都在安全区内" if allok else "[FAIL] 有封面主标题贴边，禁止发布"))
    sys.exit(0 if allok else 1)
