#!/usr/bin/env python3
"""Derive cover-3x4.png from cover-4x3.png as a centre crop.

The product decision (2026-09-11) is: **4:3 is the master layout**, because that is
the placement that actually gets shown; the same image must also survive being cut
into 3:4. So 3:4 is not a second layout — it is the master's centre 810x1080 window
scaled by 1080/810 up to 1080x1440.

Doing this by cropping pixels (rather than re-rendering the master at a fractional
CSS scale) makes the equivalence exact: at --ms = 4/3 the browser's sub-pixel layout
drifts and the two renders diverge globally (measured MAD 38/255). Crop + Lanczos
upscale is deterministic and provably the same composition.

usage: derive_cover_3x4.py <cover-4x3.png> <cover-3x4.png> [win_w win_h]
"""
import sys
from pathlib import Path

from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
win = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (810, 1080)

im = Image.open(src).convert("RGB")
W, H = im.size
w, h = win
if w > W or h > H:
    raise SystemExit(f"FAIL: 裁切窗口 {w}x{h} 比主版 {W}x{H} 还大")
left, top = (W - w) // 2, (H - h) // 2
crop = im.crop((left, top, left + w, top + h))
out = crop.resize((1080, 1440), Image.LANCZOS)
out.save(dst, optimize=True)
print(f"{dst}  1080x1440  <- {Path(src).name} 中心裁 ({left},{top})-({left+w},{top+h}) 放大 {1080/w:.4f}x")
