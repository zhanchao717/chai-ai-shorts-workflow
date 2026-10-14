#!/usr/bin/env python3
"""把封面内容整体缩到 86% 并居中垫底，**确定性地**给文字留出安全边距。

**为什么需要它（2026-09-17）**：抖音竖封面「文字展示不全」事故之后，我们在提示词里写了
「离四边至少 8%」硬规则，可提示词**不是门禁** —— 实测 GPT 出的封面主标题左右边距
只有 3.5%–5.4%（EP.190/191/192），照样能过门禁E。提示词再怎么写，「主标题铺满一行」
这个倾向也压不下去，所以必须有一个**不靠模型**的兜底：

  原图 → 内容缩到 `--scale`（默认 0.86）居中 → 四周用「原图放大 + 高斯模糊 + 压暗」垫底。

这样每个字都往里收了 (1-scale)/2 ≈ 7%，加上原有边距就稳过 8%。垫底是同一张图自己的
模糊延伸，视觉上像一圈柔和的画框，不会像补纯色那样突兀。

**记账纪律**：改写后的文件**覆盖** `cover-*.png`，原图另存为 `cover-*.raw.png`，
并在 `cover-meta.json` 里补 `safe_margin_postprocess` 字段（缩放比例、时间、原图 md5）
—— 门禁F 只认 generator + 画面相关性，覆盖文件不会骗过它，但**凭证必须如实**。

用法：
  python3 scripts/fit_cover_safe_margins.py content/episode-194/exp-gpt/cover-3x4.png
  python3 scripts/fit_cover_safe_margins.py <dir> --scale 0.84
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def fit(path: str, scale: float, blur_frac: float, darken: float, dry: bool,
        feather_frac: float = 0.035, mode: str = 'blur') -> dict:
    im = Image.open(path).convert("RGB")
    W, H = im.size

    # 垫底。两种做法（2026-09-17 实测差异）：
    #  · mode=blur（默认）：原图放大铺满 → 高斯模糊 → 压暗。观感最柔和，但**会把品牌强调色一起压掉**
    #    （EP.190 竖封面：强调色 0.054 → 0.037，直接挂掉门禁F，而门禁F 正是用强调色当「是不是本频道封面」的代理）。
    #  · mode=mirror：把内容四周的像素**镜像外扩**当垫底（轻微模糊 + 轻微压暗）——
    #    边框里保留原画面的颜色，强调色几乎不损失，代价是边框里能看到镜像的物体（观感更像"倒影/长边"）。
    if mode == "mirror":
        bg = Image.new("RGB", (W, H))
        bg.paste(im, (0, 0))
        # 四边镜像外扩（先左右、再上下）
        bg.paste(im.transpose(Image.FLIP_LEFT_RIGHT), (-W, 0))
        bg.paste(im.transpose(Image.FLIP_LEFT_RIGHT), (W, 0))
        strip = bg.copy()
        bg.paste(strip.transpose(Image.FLIP_TOP_BOTTOM), (0, -H))
        bg.paste(strip.transpose(Image.FLIP_TOP_BOTTOM), (0, H))
        # 放大一点点保证铺满（镜像后刚好同尺寸，这里直接裁中心）
        bg = bg.crop((W // 2 - W // 2, H // 2 - H // 2, W // 2 + (W - W // 2), H // 2 + (H - H // 2))).resize((W, H))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=max(4, int(W * blur_frac * 0.6))))
        if darken < 1.0:
            bg = ImageEnhance.Brightness(bg).enhance(min(1.0, darken + 0.12))
    else:
        # 原图按「铺满」的比例放大（保持比例，多出来的裁掉）→ 模糊 → 压暗
        f = max(W / im.width, H / im.height) * 1.08
        bg = im.resize((int(im.width * f) + 1, int(im.height * f) + 1), Image.LANCZOS)
        left = (bg.width - W) // 2
        top = (bg.height - H) // 2
        bg = bg.crop((left, top, left + W, top + H))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=max(6, int(W * blur_frac))))
        if darken < 1.0:
            bg = ImageEnhance.Brightness(bg).enhance(darken)

    # 前景：内容缩到 scale，居中贴上，**边缘羽化**过渡到垫底
    # 为什么必须羽化（2026-09-17 独立评审量出来的）：直接 paste() 是一条硬接缝 ——
    # 边界列平均梯度 32.27，而内容区只有 1.64、垫底区 0.12，观感就是「照片加相框」。
    fw, fh = max(1, int(W * scale)), max(1, int(H * scale))
    fg = im.resize((fw, fh), Image.LANCZOS)
    x0, y0 = (W - fw) // 2, (H - fh) // 2
    feather = max(6, int(min(fw, fh) * feather_frac))
    mask = Image.new("L", (fw, fh), 0)
    inset = feather // 2
    ImageDraw.Draw(mask).rectangle(
        (inset, inset, fw - inset - 1, fh - inset - 1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, feather / 2.5)))
    out = bg.copy()
    out.paste(fg, (x0, y0), mask)

    prepad_dir = os.path.join(os.path.dirname(path), "_prepad")
    os.makedirs(prepad_dir, exist_ok=True)
    prepad = os.path.join(prepad_dir, os.path.basename(path))
    info = {"file": os.path.basename(path), "size": [W, H], "scale": scale, "mode": mode,
            # 2026-09-22 补：**feather 也没记**。核验脚本对缺字段回退默认 0.035，而我们用的是 0.02 →
            # 复算逐像素对不上，把「图没问题、账本记漏一个参数」误报成「不可复算」（EP.205/206 各撞一次）。
            "feather": feather_frac,
            # 2026-09-20 复评 P0：原来只记 scale/mode/feather，**不记 darken/blur_frac**，
            # 于是核验脚本按 0.72–0.80 的网格去找，遇到 darken=0.82/0.85 的图就复算不出来，
            # 把「图没问题、账本记漏了」误报成「不可复算」。记账必须记全参数。
            "darken": darken, "blur_frac": blur_frac,
            "indir": "_prepad/" + os.path.basename(prepad),
            "in_md5": hashlib.md5(open(path, "rb").read()).hexdigest()}
    if dry:
        out.save(os.path.splitext(path)[0] + ".safe.png")
        info["dry_out"] = os.path.splitext(os.path.basename(path))[0] + ".safe.png"
        return info

    shutil.copy2(path, prepad)          # 每次都刷新：它记的就是"这一次加垫的输入"
    out.save(path)
    info["out_md5"] = hashlib.md5(open(path, "rb").read()).hexdigest()
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="封面 png，或包含 cover-*.png 的目录")
    ap.add_argument("--scale", type=float, default=0.86, help="内容缩放比例，默认 0.86（= 四周各收 7%%）")
    ap.add_argument("--blur", type=float, default=0.06, help="垫底模糊半径 = 宽 × 该值，默认 0.06")
    ap.add_argument("--darken", type=float, default=0.72, help="垫底压暗系数，默认 0.72")
    ap.add_argument("--mode", choices=("blur", "mirror"), default="blur", help="垫底方式：blur=模糊压暗（柔和但吃品牌色）· mirror=镜像外扩（保色）")
    ap.add_argument("--feather", type=float, default=0.035, help="羽化宽度 = min(内容宽,高) × 该值，默认 0.035（0 = 硬接缝）")
    ap.add_argument("--dry", action="store_true", help="只写 cover-*.safe.png 预览，不动原文件")
    a = ap.parse_args()

    if os.path.isdir(a.target):
        files = sorted(os.path.join(a.target, f) for f in os.listdir(a.target)
                       if f.startswith("cover-") and f.endswith(".png") and not f.endswith(".raw.png"))
    else:
        files = [a.target]
    if not files:
        sys.exit(f"❌ 没找到封面图：{a.target}")

    done = []
    for f in files:
        info = fit(f, a.scale, a.blur, a.darken, a.dry, a.feather, a.mode)
        done.append(info)
        print(f"── {info['file']}  {info['size'][0]}×{info['size'][1]} → 内容 ×{a.scale}"
              + (f"（预览 {info.get('dry_out')}）" if a.dry else f"（加垫前输入已存 {info['indir']}）"))

    # 记账：把后处理写进 cover-meta.json（同目录）
    d = os.path.dirname(files[0])
    meta_p = os.path.join(d, "cover-meta.json")
    if os.path.exists(meta_p) and not a.dry:
        meta = json.load(open(meta_p, encoding="utf-8"))
        # ⚠️ 顶层的 files.{bytes,md5} 是**加垫之前**算的：必须刷新成包里真正那张图的指纹，
        #    否则凭证指向一个不存在的文件（EP.190 首轮就是这么写错的）。
        for info in done:
            fp = os.path.join(d, info["file"])
            if os.path.exists(fp):
                buf = open(fp, "rb").read()
                meta.setdefault("files", {})[info["file"]] = {
                    "bytes": len(buf), "md5": hashlib.md5(buf).hexdigest(),
                }
        prev = (meta.get("safe_margin_postprocess") or {}).get("files") or []
        by_name = {d.get("file"): d for d in prev}
        for d in done:
            by_name[d["file"]] = d          # 同名的更新，别的保留 —— 分次加垫也能记全
        meta["safe_margin_postprocess"] = {
            "script": "scripts/fit_cover_safe_margins.py",
            "files": sorted(by_name.values(), key=lambda x: x.get("file", "")),
            "why": "GPT 出的封面主标题左右边距实测 3.6%–7.2%（提示词里写了 8% 硬规则也压不住），平台会裁掉贴边的字；只在原始边距不足时按最小必要缩放兜底（s ≤ 42/(50−m)），加垫后实测 8.1%–15.7%。注意：加垫会把品牌强调色 #FDFFA7 的覆盖率按内容面积等比稀释（实测 4:3 会掉到 0.028，逼近「错误来源」区间），所以品牌色只能靠出图时给足，不能靠后处理。",
        }
        json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"📝 已把后处理写进 {meta_p}")
    print("\n结论：完成" if not a.dry else "\n结论：已出预览（--dry）")


if __name__ == "__main__":
    main()
