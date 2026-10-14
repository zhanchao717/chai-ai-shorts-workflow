#!/usr/bin/env python3
"""柴主编 · 达标连击判定器（抖音「优化开头」目标专用）

背景：官方门槛 =「**近 4 个视频的 2s 跳出率连续 ≤30%**」，且**只算新发布的视频**。
后台只给区间（如 37%–57%）、按天导出又无法归因到单条 → 拿到**单条**数字后用它判定。

用法：
  python3 scripts/chai_streak_check.py 160=28.9 161=31.2 162=26.4 163=29.1
  python3 scripts/chai_streak_check.py 160=28.9 161=26.4 --write     # 回填 performance-record

参数：`<期号>=<单条 2s 跳出率>`，可给多个；顺序按**发布时间从早到晚**。
`--target`（默认 30）为门槛百分数；`--write` 把数值写入各期发布包的 performance-record.md。
退出码：0 = 已凑满连续 4 条达标；1 = 未达标。只用标准库。
"""
from __future__ import annotations
import argparse, glob, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def parse_pairs(items: list[str]) -> list[tuple[str, float]]:
    out = []
    for it in items:
        m = re.fullmatch(r"(\d{3})\s*=\s*([0-9]+(?:\.[0-9]+)?)", it.strip())
        if not m:
            raise SystemExit(f"参数格式应为 <期号>=<数值>，收到：{it}")
        out.append((m.group(1), float(m.group(2))))
    return out


def record_path(ep: str) -> pathlib.Path | None:
    hits = sorted(glob.glob(str(ROOT / f"content/episode-{ep}" / "publish-package-*" / "performance-record.md")))
    return pathlib.Path(hits[-1]) if hits else None


def write_back(ep: str, value: float) -> str:
    p = record_path(ep)
    if not p:
        return f"EP.{ep} 未找到 performance-record.md，跳过回填"
    s = p.read_text(encoding="utf-8")
    # ① 若已有「单条 2 秒跳出率（回填）行」→ 覆盖；② 否则在 24 小时数据段下插入一行；③ 都没有 → 文件末尾追加
    line = f"**单条 2 秒跳出率（回填）：{value}%**（发布后回填，门槛 ≤30%）"
    before = s
    if re.search(r"\*\*单条 2 秒跳出率（回填）：[\d.]+%\*\*", s):
        s = re.sub(r"\*\*单条 2 秒跳出率（回填）：[\d.]+%\*\*[^\n]*", line, s, count=1)
    elif "## 24 小时数据" in s:
        s = s.replace("## 24 小时数据", "## 24 小时数据", 1)  # anchor
        idx = s.find("## 24 小时数据")
        eol = s.find("\n", idx)
        s = s[:eol + 1] + line + "\n" + s[eol + 1:]
    else:
        s = s.rstrip("\n") + "\n" + line + "\n"
    if s == before:
        return f"EP.{ep} 回填失败（未匹配到写入位置）"
    p.write_text(s, encoding="utf-8")
    return f"EP.{ep} 已回填 {value}% → {p.relative_to(ROOT)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="+", help="形如 160=28.9（期号=单条 2s 跳出率）")
    ap.add_argument("--target", type=float, default=30.0, help="门槛百分数（默认 30）")
    ap.add_argument("--need", type=int, default=4, help="需要连续达标的条数（默认 4）")
    ap.add_argument("--write", action="store_true", help="把数值回填进各期 performance-record.md")
    a = ap.parse_args()

    rows = parse_pairs(a.pairs)
    print(f"达标判定 · 门槛 2s 跳出率 ≤ {a.target:g}% · 需连续 {a.need} 条\n")
    print(f"{'期号':>5} {'单条 2s 跳出':>12} {'判定':>6}")
    for ep, v in rows:
        print(f"{ep:>5} {v:>11.1f}% {'✅' if v <= a.target else '❌':>6}")

    streak = 0
    for _, v in reversed(rows):          # 从最新一条往回数
        if v <= a.target:
            streak += 1
        else:
            break
    tail = "".join("✅" if v <= a.target else "❌" for _, v in rows)
    print(f"\n逐条（早→晚）：{tail}")
    print(f"当前连击：**{streak}/{a.need}**" + ("　→ 已达标，等后台进度更新" if streak >= a.need else ""))

    if streak < a.need:
        bad = [f"{ep}({v:g}%)" for ep, v in rows if v > a.target]
        print(f"未达标原因：{'、'.join(bad) if bad else '样本不足 ' + str(len(rows)) + ' 条'}")

    if a.write:
        print()
        for ep, v in rows:
            print("  " + write_back(ep, v))

    return 0 if streak >= a.need else 1


if __name__ == "__main__":
    raise SystemExit(main())
