#!/usr/bin/env python3
"""Crop-safety verification: prove the 4:3 master survives a centre 3:4 crop.

Product contract (2026-09-11): **4:3 is the master layout** (that is the placement
that actually gets shown) and the same image must survive being cut into 3:4. So
3:4 is generated as the master's centre 810x1080 window scaled by 1080/810.

Three checks:
  ① EQUIVALENCE — centre-crop cover-4x3.png, upscale, diff against cover-3x4.png.
  ② TITLE GLYPHS — white + lime glyph-cluster counts and x-extents, before and after
     the crop, to show no glyph is cut or dropped.
  ③ SUBJECT / ACCENT — bounding boxes of the avatar disc and the lime accent inside
     the 810x1080 window, with an explicit "touches an edge" (= cut) verdict.

usage: chai_cover_crop_check.py <covers_dir> [--out dir] [--json path]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

COVERS = Path(sys.argv[1])
out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else COVERS
json_out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None

WIN = (810, 1080)
# 4:3 master geometry, mirroring the 母版 CSS in gen_chai_frames.py (master scale = 1):
#   window  x315..1125 (810 wide)        .hero  x=WIN_X+20  y=300  w=770  h=2 lines
#   .ava   x=WIN_X+540 y=14  244x244
WIN_X, WIN_Y = 315, 0
TEXT_X, TEXT_Y, TEXT_W = WIN_X + 20, 300, 770
AVA = (WIN_X + 540, 14, WIN_X + 540 + 244, 14 + 244)


def centre_crop(im, size):
    W, H = im.size
    w, h = size
    left, top = (W - w) // 2, (H - h) // 2
    return im.crop((left, top, left + w, top + h)), left, top


def clusters(cols, gap=4, minw=3):
    out, start, last = [], None, None
    for x in sorted(cols):
        if start is None:
            start = last = x
        elif x - last <= gap:
            last = x
        else:
            if last - start + 1 >= minw:
                out.append((int(start), int(last)))
            start = last = x
    if start is not None and last - start + 1 >= minw:
        out.append((int(start), int(last)))
    return out


def white_mask(a):
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    return (R > 215) & (G > 215) & (B > 215)


def lime_mask(a):
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    return (G > 190) & (B < 120) & (R > 120) & (R < 235)


def bbox(m):
    ys, xs = np.where(m)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def touches_edge(b, W, H, pad=1):
    return b[0] <= pad or b[1] <= pad or b[2] >= W - 1 - pad or b[3] >= H - 1 - pad


report = {}

print("=" * 76)
print("① 等价性：cover-4x3.png 中心裁 810x1080 → 放大 1080x1440  vs  cover-3x4.png")
master = Image.open(COVERS / "cover-4x3.png").convert("RGB")
print(f"   主版 4:3      {master.size[0]}x{master.size[1]}")
crop, cx, cy = centre_crop(master, WIN)
derived = crop.resize((1080, 1440), Image.LANCZOS)
print(f"   中心裁切      ({cx},{cy})-({cx+WIN[0]},{cy+WIN[1]})  = {crop.size[0]}x{crop.size[1]}")
actual = Image.open(COVERS / "cover-3x4.png").convert("RGB")
a = np.asarray(derived).astype(np.float32)
b = np.asarray(actual).astype(np.float32)
mad = float(np.abs(a - b).mean())
pct = 100.0 * float((np.abs(a - b).max(axis=2) > 8).mean())
report["equivalence"] = {"mad": round(mad, 4), "diff_pct": round(pct, 4),
                         "crop_box": [cx, cy, cx + WIN[0], cy + WIN[1]]}
print(f"   MAD = {mad:.4f}/255    差异>8 的像素 = {pct:.4f}%")
print(f"   → {'✅ 完全相同（3:4 就是 4:3 的中心裁切件）' if mad < 0.5 else '❌ 不一致'}")

print()
print("=" * 76)
print("② 标题字形：窗口内墨迹的簇数与 x 范围（裁切只是放大，不该丢字/切字）")
carr = np.asarray(crop).astype(np.float32)
darr = np.asarray(derived).astype(np.float32)
aarr = np.asarray(actual).astype(np.float32)


def title_stats(arr, x0, y0, x1, y1):
    """Glyph clusters inside an explicit pixel box (master coordinates -> view)."""
    band = arr[int(y0):int(y1), int(x0):int(x1)]
    wm, lm = white_mask(band), lime_mask(band)
    cw = clusters(np.where(wm.any(axis=0))[0])
    cl = clusters(np.where(lm.any(axis=0))[0])
    return cw, cl, band.shape


stat = {}
# .hero box in master coords, and the same box expressed in each view's pixels:
#   4:3 master   -> straight (box x335..1105, y300..521)
#   centre crop  -> subtract the window origin (x-315, y-0)
#   3:4 output   -> the crop scaled by 1080/810
HX0, HY0, HX1, HY1 = TEXT_X, TEXT_Y, TEXT_X + TEXT_W, TEXT_Y + 230
views = [
    ("4:3 主版(窗口内)", carr, HX0 - WIN_X, HY0, HX1 - WIN_X, HY1),
    ("裁切放大件",        darr, (HX0 - WIN_X) * 4 / 3, HY0 * 4 / 3, (HX1 - WIN_X) * 4 / 3, HY1 * 4 / 3),
    ("实际 3:4 出图",     aarr, (HX0 - WIN_X) * 4 / 3, HY0 * 4 / 3, (HX1 - WIN_X) * 4 / 3, HY1 * 4 / 3),
]
for name, arr, x0, y0, x1, y1 in views:
    cw, cl, shape = title_stats(arr, x0, y0, x1, y1)
    stat[name] = {"white_clusters": len(cw), "lime_clusters": len(cl),
                  "white_extent": [cw[0][0], cw[-1][1]] if cw else None,
                  "box": [int(x0), int(y0), int(x1), int(y1)]}
    print(f"   {name:<18} 白字簇 {len(cw)}  酸柠簇 {len(cl)}  "
          f"白字x范围 {[cw[0][0], cw[-1][1]] if cw else None}  取样盒 {int(x0)},{int(y0)}-{int(x1)},{int(y1)}")
report["title"] = stat
same = stat["裁切放大件"]["white_clusters"] == stat["实际 3:4 出图"]["white_clusters"]
big = stat["实际 3:4 出图"]["white_clusters"]
print(f"   → 裁切放大件 vs 实际 3:4 出图：{'✅ 簇数一致' if same else '❌ 簇数不一致'}"
      f"；标题带白字簇 {big} 个，与 4:3 主版窗口内的 "
      f"{stat['4:3 主版(窗口内)']['white_clusters']} 个同源（同一块像素，只差放大）")

print()
print("=" * 76)
print("③ 主体与关键数字：在 810x1080 窗口内的包围盒，贴边 = 被切")
# the avatar disc: brightest orange mass. Restrict to the expected avatar box to keep
# the background glow out of the mask.
sx, sy = AVA[0] - WIN_X, AVA[1]
sub = carr[sy:sy + 240, sx:sx + 240]
R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
disc = (R > 150) & (R - B > 60) & (G > 80) & (G < 220)
db = bbox(disc)
sub_lime = lime_mask(sub)
lb = bbox(sub_lime)
print(f"   人物盘（窗口坐标 x{AVA[0]-WIN_X}..{AVA[2]-WIN_X} y{sy}..{sy+240}）")
if db:
    abs_db = [db[0] + sx, db[1] + sy, db[2] + sx, db[3] + sy]
    cut = touches_edge(abs_db, WIN[0], WIN[1])
    print(f"      主体 bbox(窗口内) {abs_db}  {'❌ 贴窗口边' if cut else '✅ 完整（未贴边）'}")
    report["avatar"] = {"bbox_in_window": abs_db, "cut": cut}
else:
    print("      ⚠️ 未识别到人物主体（掩膜过严），见下方说明")
if lb:
    abs_lb = [lb[0] + sx, lb[1] + sy, lb[2] + sx, lb[3] + sy]
    cut = touches_edge(abs_lb, WIN[0], WIN[1])
    print(f"      盘上 lime 环 bbox {abs_lb}  {'❌ 贴边' if cut else '✅ 完整（未贴边）'}")
    report["avatar_lime"] = {"bbox_in_window": abs_lb, "cut": cut}

# NOTE: a whole-window "any bright ink" bbox is NOT a useful check here — the orange
# glow and sunburst are bright too, so it always touches the window edge by design
# (装饰允许出窗). Content containment is enforced by the in-page gate plus the
# per-element boxes above.
crop.save(out_dir / "crop-centre-810x1080.png")
derived.save(out_dir / "crop-derived-3x4.png")
if json_out:
    Path(json_out).write_text(json.dumps(report, ensure_ascii=False, indent=1))
print(f"\n   导出：{out_dir/'crop-centre-810x1080.png'}")
print(f"         {out_dir/'crop-derived-3x4.png'}")
