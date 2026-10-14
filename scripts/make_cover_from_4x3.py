#!/usr/bin/env python3
"""柴主编 · 由 4:3 主版封面派生出 3:4 与 9:16（完整 4:3 居中嵌板，不裁任何内容）

用户要求（2026-09-12）：
  「第一版 4:3 居中放在 3:4 的中间，这样抖音就可以自动选择到横版的封面」
  → 4:3 是**主版**；3:4 与 9:16 把**整张 4:3 原样居中**放进去，多余上下空间由
    **图像自身的外延**填充。
  → 平台按任意比例展示都不丢内容；平台从竖版中间裁 4:3 时拿到的正是原图。

⚠️ 2026-09-12 第二版（用户反馈「3x4 看起来很突兀」）：
  旧实现的外延来自"整张图缩放到覆盖后再裁"的**另一块区域**（再模糊压暗），
  它与内容带**边缘的亮度根本不是一家**，于是在接缝处留下**硬台阶**——
  实测 EP.171 的 cover-3x4 上接缝 **Δ=65.1**（外延 78 vs 内容带顶 13），
  肉眼看就是一条断裂的边。
  新实现改成 **「取内容带自己的边缘行 → 垂直镜像 → 纵向铺满 → 强模糊 → 亮度坡」**：
  - **镜像**保证紧贴接缝的那一行**恰好等于内容带的边缘行** → 接缝**亮度连续**；
  - 模糊在**镜像后的图**上做，对称延拓不破坏连续性；
  - 亮度坡在**接缝处为 1.0**、向远端降到 `--falloff` → 只"往外淡"，**不在接缝处制造台阶**。
  保留 `--legacy-bg` 可回到旧行为（对比用）。

实现用 **PIL**（本工程的精简 ffmpeg 不含 gblur/eq，滤镜路线不可用）。

用法：
  python3 scripts/make_cover_from_4x3.py <source-4x3.png> --out <dir> [--proj <工程目录>]
      [--blur 36] [--falloff 0.58] [--slice 200] [--legacy-bg]
产出：
  cover-4x3.png 1440×1080（主版，等比归一）
  cover-3x4.png 1080×1440（4:3 内容 1080×810 居中，上下各 315px 外延）
  cover-9x16.png 1080×1920（4:3 内容居中，上下各 555px 外延；用于视频首帧）
"""
from __future__ import annotations
import argparse, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RATIOS = {
    "cover-4x3.png": (1440, 1080),
    "cover-3x4.png": (1080, 1440),
    "cover-9x16.png": (1080, 1920),
}



# ── 竖版外延区的"内容带"（2026-09-12 用户反馈「3x4 上下还是有点空，加点内容看起来协调」）──────
# 设计：**四不像不碰主版**（主版逐像素不变 → 平台中央裁 4:3 拿到的还是原图），只在**外延区**加：
#   上带＝来源 kicker（等宽小字，灰）+ 酸柠色短横线
#   下带＝酸柠色短横线 + 账号署名（粗体白）+ 核验说明（等宽小字，灰）
# 两条横线像"画框上下缘"，把中间的 4:3 主版括起来 → 竖版读起来是一张**海报**而不是"中间一块图 + 上下雾"。
CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]
MONO_FONT_CANDIDATES = ["assets/fonts/CobaltMono.ttf", "videos/openai-deprecation-timeline/assets/fonts/CobaltMono.ttf"]
ACCENT = (209, 255, 0)
GRAY = (152, 145, 136)
WHITE = (242, 238, 232)


def _font(kind: str, size: int):
    cands = CJK_FONT_CANDIDATES if kind == "cjk" else MONO_FONT_CANDIDATES
    for c in cands:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _has_cjk(t: str) -> bool:
    return any("\u2e80" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" for ch in (t or ""))


def _font_for(text: str, size: int, prefer: str = "mono"):
    """⚠️ 2026-09-12 修：**CobaltMono 没有中文字形** —— 拿它去画「官方文档」「核验」会渲染成豆腐块
    （实测 OCR 读成 `000d` / `0I`，等于上屏乱码）。所以**按字符串内容选字体**：
    只要含 CJK 就走 CJK 字体，纯 ASCII 才用等宽。"""
    if _has_cjk(text):
        return _font("cjk", size)
    return _font(prefer, size)


def draw_bands(out: Image.Image, top: int, fg_h: int, kicker: str, cap: str, brand: str,
               margin_x: int = 70, gutter: int = 78) -> None:
    """在竖版外延区画上/下内容带（**不触碰主版区域**）。"""
    if not (kicker or cap or brand):
        return
    d = ImageDraw.Draw(out)
    W, H = out.size
    band_top, band_bot = top, top + fg_h
    rule_w, rule_h = 110, 6

    # ── 上带：kicker + 横线（紧贴主版上沿 gutter 像素之上）
    if band_top > gutter + 60:
        f = _font_for(kicker, 26)
        y_line = band_top - gutter + 22
        if kicker:
            d.text((margin_x, band_top - gutter - 8), kicker, font=f, fill=GRAY)
        d.rectangle([margin_x, y_line, margin_x + rule_w, y_line + rule_h], fill=ACCENT)

    # ── 下带：横线 + 署名 + 核验说明
    if H - band_bot > gutter + 60:
        y_rule = band_bot + gutter - 24
        d.rectangle([margin_x, y_rule, margin_x + rule_w, y_rule + rule_h], fill=ACCENT)
        if brand:
            fb = _font("cjk", 34)
            d.text((margin_x, y_rule + 34), brand, font=fb, fill=WHITE)
        if cap:
            fm = _font_for(cap, 24)
            d.text((margin_x, y_rule + 92), cap, font=fm, fill=GRAY)


def cover_resize(im: Image.Image, w: int, h: int) -> Image.Image:
    """等比缩放到完全覆盖 w×h 后居中裁切（背景层用）。"""
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    nw, nh = round(sw * scale), round(sh * scale)
    r = im.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return r.crop((left, top, left + w, top + h))


def contain_resize(im: Image.Image, w: int) -> Image.Image:
    """等比缩放到宽 = w（前景 4:3 内容用）。"""
    sw, sh = im.size
    return im.resize((w, round(sh * w / sw)), Image.LANCZOS)


def mirror_extension(fg: Image.Image, height: int, at_top: bool,
                     blur: float, falloff: float, slice_h: int) -> Image.Image:
    """从内容带边缘行做**镜像延拓**，得到与内容带接缝亮度连续的外延块。

    at_top=True  → 外延块贴接缝的**底边**等于 `fg` 第 0 行；
    at_top=False → 外延块贴接缝的**顶边**等于 `fg` 最后一行。
    """
    W = fg.width
    slice_h = max(24, min(slice_h, fg.height // 2))
    if at_top:
        part = fg.crop((0, 0, W, slice_h)).transpose(Image.FLIP_TOP_BOTTOM)
    else:
        part = fg.crop((0, fg.height - slice_h, W, fg.height)).transpose(Image.FLIP_TOP_BOTTOM)
    band = part.resize((W, height), Image.LANCZOS)
    if blur > 0:
        band = band.filter(ImageFilter.GaussianBlur(radius=blur))
    a = np.asarray(band).astype(np.float32)
    # 亮度坡：**接缝处 = 1.0**（不产生台阶），远端降到 falloff
    ramp = (np.linspace(falloff, 1.0, height) if at_top else np.linspace(1.0, falloff, height))
    a *= ramp[:, None, None]
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


def build(src: Image.Image, W: int, H: int, *, legacy: bool = False,
          blur: float = 36.0, falloff: float = 0.58, slice_h: int = 200,
          kicker: str = "", cap: str = "", brand: str = "", bands: bool = True) -> Image.Image:
    if (W, H) == (1440, 1080):                      # 主版：等比覆盖 + 居中裁
        return cover_resize(src.convert("RGB"), W, H)
    fg = contain_resize(src.convert("RGB"), W)      # 完整 4:3 内容
    if fg.height > H:
        return cover_resize(src.convert("RGB"), W, H)
    top = (H - fg.height) // 2
    bot = H - fg.height - top
    if legacy:
        bg = cover_resize(src.convert("RGB"), W, H)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=48))
        bg = ImageEnhance.Brightness(bg).enhance(0.62)
        bg = ImageEnhance.Color(bg).enhance(0.85)
        bg.paste(fg, (0, top))
        return bg
    out = Image.new("RGB", (W, H))
    if top > 0:
        out.paste(mirror_extension(fg, top, True, blur, falloff, slice_h), (0, 0))
    if bot > 0:
        out.paste(mirror_extension(fg, bot, False, blur, falloff, slice_h), (0, top + fg.height))
    out.paste(fg, (0, top))
    if bands:
        draw_bands(out, top, fg.height, kicker, cap, brand)
    return out


def seam_report(img: Image.Image, top: int, fg_h: int) -> str:
    """量接缝台阶：接缝上下各 20px 的平均亮度差。"""
    a = np.asarray(img.convert("RGB")).astype(np.float32).mean(axis=2)
    rows = []
    for y, label in ((top, "上接缝"), (top + fg_h, "下接缝")):
        if 20 <= y <= a.shape[0] - 20:
            d = abs(float(a[y - 20:y].mean()) - float(a[y:y + 20].mean()))
            rows.append(f"{label} Δ={d:.1f}")
    return " · ".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="AI 生成的 4:3 原图（尺寸接近 4:3 即可）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--proj", default=None, help="可选：同时写入 <proj>/covers/")
    ap.add_argument("--blur", type=float, default=36.0, help="外延块的模糊半径（缺省 36）")
    ap.add_argument("--falloff", type=float, default=0.58, help="远端亮度系数（接缝处固定 1.0）")
    ap.add_argument("--slice", type=int, default=200, dest="slice_h", help="取内容带边缘多少行做镜像")
    ap.add_argument("--legacy-bg", action="store_true", help="回到旧的'覆盖裁切+模糊'外延（仅对比用）")
    ap.add_argument("--kicker", default="", help="竖版**上方**的来源/系列小字（如「Google · Gemini 官方文档」）")
    ap.add_argument("--cap", default="", help="竖版**下方**的核验说明小字（如「Gemini Agentic Video · 2026-09-12 核验」）")
    ap.add_argument("--brand", default="柴主编｜只讲一件事", help="竖版**下方**的账号署名")
    ap.add_argument("--no-bands", action="store_true", help="竖版外延区不加内容带（只有模糊延展）")
    a = ap.parse_args()
    p = pathlib.Path(a.src).expanduser().resolve()
    if not p.is_file():
        sys.exit(f"❌ 找不到 {p}")
    out = pathlib.Path(a.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    src = Image.open(p)
    for name, (W, H) in RATIOS.items():
        img = build(src, W, H, legacy=a.legacy_bg, blur=a.blur,
                    falloff=a.falloff, slice_h=a.slice_h,
                    kicker=a.kicker, cap=a.cap, brand=a.brand, bands=not a.no_bands)
        img.save(out / name)
        extra = ""
        if (W, H) != (1440, 1080):
            fg_h = round(src.size[1] * W / src.size[0])
            extra = "  →  " + seam_report(img, (H - fg_h) // 2, fg_h)
        print(f"✅ {name}  {W}×{H}{extra}")
    if a.proj:
        pcov = pathlib.Path(a.proj).expanduser().resolve() / "covers"
        pcov.mkdir(parents=True, exist_ok=True)
        for name in RATIOS:
            (pcov / name).write_bytes((out / name).read_bytes())
        print(f"✅ 已同步到 {pcov}")
    print("ℹ️ 三比例 = 完整 4:3 居中 + **接缝亮度连续**的镜像外延")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
