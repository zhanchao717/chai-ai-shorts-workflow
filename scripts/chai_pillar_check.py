#!/usr/bin/env python3
"""柴主编 · 内容配比核算器（workflow §1：60% 免费/省钱/避坑 + 30% DSH/Agent 教程 + 10% 重大热点）

为什么需要它：配比是滚动 14 期的目标，靠记忆一定会跑偏（2026-09-11 实测：教程档连续 5 期缺失）。
读每期 `sources.md` 里的「选题支柱：」一行归类，输出近 N 期的配比与缺口。

用法：
  python3 scripts/chai_pillar_check.py            # 默认最近 14 期
  python3 scripts/chai_pillar_check.py --last 20
退出码：0 = 配比在容差内；1 = 有档位缺口（只提示，不阻塞生产）。
只用标准库。
"""
from __future__ import annotations
import argparse, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

# 归类关键词 → 档位
RULES = [
    ("教程", ("教程", "实操", "步骤", "怎么用", "上手")),
    ("热点", ("热点", "重大热点")),
    ("省钱", ("省钱", "成本", "免费", "避坑", "账单", "价格")),
]
TARGET = {"省钱": 0.60, "教程": 0.30, "热点": 0.10}


def classify(text: str) -> str:
    for name, keys in RULES:
        if any(k in text for k in keys):
            return name
    return "未标注"


# EP.151–159 的 sources.md 早于「选题支柱」标记约定，按当时选题人工归类（**推断**，非源文件自述）
LEGACY = {
    "151": "省钱",  # DeepSeek 回答慢、烧 token
    "152": "省钱",  # Kimi Code 省钱功能转正
    "153": "省钱",  # 端侧小模型省钱账
    "154": "热点",  # 蚂蚁开源多模态（模型发布）
    "155": "热点",  # NeoHorse-1 发布
    "156": "教程",  # DSH 子代理并行
    "157": "热点",  # 星火 X2.5 发布
    "158": "省钱",  # MiniMax H3 本地部署避坑
    "159": "教程",  # DSH 多代理编排
}


def pillar_of(ep_dir: pathlib.Path) -> tuple[str, bool] | None:
    """返回 (档位, 是否来自源文件自述)。源文件无标记时回落到 LEGACY 推断表。"""
    ep = ep_dir.name.replace("episode-", "")
    src = ep_dir / "sources.md"
    if src.exists():
        for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
            if "选题支柱" in line:
                return classify(line), True
    return (LEGACY[ep], False) if ep in LEGACY else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=14)
    a = ap.parse_args()

    eps = sorted([d for d in CONTENT.glob("episode-*") if d.is_dir()],
                 key=lambda d: int(re.sub(r"\D", "", d.name) or 0))
    eps = eps[-a.last:]
    rows = []
    for d in eps:
        r = pillar_of(d)
        if r:
            rows.append((d.name.replace("episode-", ""), r[0], r[1]))

    counts = {k: 0 for k in TARGET}
    for _, p, _src in rows:
        if p in counts:
            counts[p] += 1
    n = len(rows)
    if not n:
        print("未找到任何带「选题支柱」标记的 sources.md"); return 1

    print(f"内容配比（最近 {n} 期，目标 60/30/10）\n")
    print(f"{'档位':<6}{'期数':>4}{'实际':>8}{'目标':>8}{'偏差':>8}")
    gaps = []
    for k, want in TARGET.items():
        got = counts[k] / n
        dev = got - want
        mark = "" if abs(dev) <= 0.15 else ("  ← 偏少" if dev < 0 else "  ← 偏多")
        if dev < -0.15:
            gaps.append(k)
        print(f"{k:<6}{counts[k]:>4}{got:>8.0%}{want:>8.0%}{dev:>+8.0%}{mark}")
    inferred = [e for e, _, src in rows if not src]
    if inferred:
        print(f"\n其中 {len(inferred)} 期无源文件标记、按选题推断：{'、'.join(inferred)}")

    print("\n逐期（早→晚）：" + " ".join(f"{e}:{p}{'' if src else '*'}" for e, p, src in rows)
          + "   （\* = 推断）")
    if gaps:
        print(f"\n缺口：{'、'.join(gaps)} —— 下一期优先补 **{'/'.join(gaps)}** 档")
    else:
        print("\n配比在 ±15% 容差内。")
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
