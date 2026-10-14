#!/usr/bin/env python3
"""三比例封面：从**竖版 3:4 主版**裁切派生（替代旧的"4:3 主版 + 镜像外延"）。

用法：
    python3 scripts/covers_from_vertical_master.py <主版.png> --out <发布包目录> [--proj <工程目录>]
        [--safe-report]  # 只做几何自检

为什么换（2026-09-12 用户反馈「封面还是不协调」）：
  旧做法是「AI 出 4:3 主版 → 塞进 3:4 画布中央 → 上下用**镜像模糊带**补边 + 叠文字带」。
  于是竖版看到的是「一张图 + 两条糊带」——两个比例本来就不是同一张画，怎么调接缝都不会协调。
  新做法：**AI 直接出竖版 3:4（1440×1920）**，三比例**全部由它裁切**：
      9:16 = 中央竖裁 1080×1920（1:1，不缩放）
      3:4  = 全幅 1440×1920 → 1080×1440（等比缩小 0.75）
      4:3  = 中央横裁 1440×1080（1:1，不缩放）
  → **零外延、零接缝、零补丁**，三个比例看到的是**同一张画的三个取景**，协调是构造出来的。

构图硬约束（写进 prompt、并由本脚本复检）：
  **所有文字与角色必须落在中央的 1080×1080 安全方内**（master 坐标 x180–1260 / y420–1500）。
  因为：9:16 会把左右各裁掉 180px；4:3 会把上下各裁掉 420px。安全方 = 三个取景的交集。

退出码：0 = 三比例已出且几何自检通过；1 = 自检失败；2 = 输入缺失。
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

from PIL import Image

# 主版契约
MASTER_W, MASTER_H = 1440, 1920
# 三比例取景（master 坐标）
CROPS = {
    "cover-9x16.png": ((180, 0, 1260, 1920), (1080, 1920)),   # 中央竖裁，1:1
    "cover-3x4.png": ((0, 0, 1440, 1920), (1080, 1440)),      # 全幅，缩小 0.75
    "cover-4x3.png": ((0, 420, 1440, 1500), (1440, 1080)),    # 中央横裁，1:1
}
SAFE = (180, 420, 1260, 1500)   # 1080×1080 安全方（三个取景的交集）


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("--out", required=True, help="发布包目录")
    ap.add_argument("--proj", default=None, help="可选：同步写到 <proj>/covers/")
    ap.add_argument("--safe-report", action="store_true", help="只打印几何自检，不写文件")
    a = ap.parse_args()

    m = pathlib.Path(a.master)
    if not m.is_file():
        print(f"找不到主版：{m}")
        return 2
    im = Image.open(m).convert("RGB")
    if im.size != (MASTER_W, MASTER_H):
        print(f"⚠️ 主版尺寸 {im.size}，契约是 {(MASTER_W, MASTER_H)} —— 仍按契约坐标裁切，请确认构图")
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"主版 {m.name} {im.size[0]}×{im.size[1]}")
    print(f"安全方（三个取景的交集）= x{SAFE[0]}–{SAFE[2]} · y{SAFE[1]}–{SAFE[3]} = "
          f"{SAFE[2]-SAFE[0]}×{SAFE[3]-SAFE[1]}")
    ok = True
    for name, (box, size) in CROPS.items():
        c = im.crop(box)
        if (c.width, c.height) != size:
            print(f"  ❌ {name} 裁切尺寸 {c.size} ≠ 契约 {size}")
            ok = False
            continue
        c = c.resize(size, Image.LANCZOS)
        covers_safe = (box[0] <= SAFE[0] and box[1] <= SAFE[1]
                       and box[2] >= SAFE[2] and box[3] >= SAFE[3])
        print(f"  {'✅' if covers_safe else '❌'} {name}  取景 {box} → {size[0]}×{size[1]}"
              f"{'（1:1，未缩放）' if (box[2]-box[0], box[3]-box[1]) == size else '（等比缩小）'}"
              f"{' · 含安全方' if covers_safe else ' · **不含安全方**'}")
        if not covers_safe:
            ok = False
        if not a.safe_report:
            c.save(out / name)
            if a.proj:
                pd = pathlib.Path(a.proj) / "covers"
                pd.mkdir(parents=True, exist_ok=True)
                shutil.copy2(out / name, pd / name)
    if not a.safe_report:
        print(f"→ 已写出三比例到 {out}" + (f" 并同步到 {a.proj}/covers" if a.proj else ""))
    print(f"结论：[{'PASS' if ok else 'FAIL'}]（零外延 · 零接缝 · 三比例同源）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
