#!/usr/bin/env python3
"""gen_chai_cover_avatar.py — turn the brand avatar (RGB, no alpha) into a clean
transparent bust for the 阿囤囤-style covers.

Why this exists: `videos/*/assets/brand/chai-editor-avatar.png` is RGB with the
character sitting on a navy/cyan backdrop. The cover template needs a cut-out.
The `hyperframes remove-background` CLI is not installed on this machine, so we do
it deterministically in-process:

  1. classify background (blue-dominant, dark) vs subject
  2. keep the largest 4-connected subject component, drop the cyan corner arcs
  3. fill interior holes (eyes / nose / mouth)
  4. **decontaminate the edge**: pixels straddling the boundary carry backdrop
     colour; we replace their RGB with the nearest fully-opaque subject colour so
     the feather can't produce a light halo (a "dirty edge").
  5. feather and tight-crop, write RGBA PNG

Only stdlib + Pillow + numpy. Deterministic: same input -> byte-identical output.

usage:
  python3 scripts/gen_chai_cover_avatar.py <src.png> <dst.png> [--disc 0.98]
"""
from __future__ import annotations

import argparse
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter


def cut(src: str, dst: str, disc: float = 0.98) -> None:
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    H, W, _ = a.shape
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    lum = a.mean(2)
    sat = a.max(2) - a.min(2)

    # --- 1. background = blue-dominant / dark ---------------------------------
    bg_colour = (B > R + 12) & (B > G + 6) & (B > 45) & (lum < 150)
    fg = (~bg_colour) & (lum > 62) & (sat > 18)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rr = np.sqrt((yy - (H - 1) / 2) ** 2 + (xx - (W - 1) / 2) ** 2) / (min(H, W) / 2)
    fg &= rr < disc
    print(f"[1] raw subject {100 * fg.mean():.1f}%")

    # --- 2. largest 4-connected component ------------------------------------
    lab = np.zeros((H, W), np.int32)
    best, best_n, cur = None, 0, 0
    for sy in range(0, H, 3):
        for sx in range(0, W, 3):
            if fg[sy, sx] and lab[sy, sx] == 0:
                cur += 1
                n = 0
                dq = deque([(sy, sx)])
                lab[sy, sx] = cur
                while dq:
                    y, x = dq.popleft()
                    n += 1
                    for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                        if 0 <= ny < H and 0 <= nx < W and fg[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur
                            dq.append((ny, nx))
                if n > best_n:
                    best_n, best = n, cur
    if best is None:
        raise SystemExit("no subject component found")
    mask = lab == best
    print(f"[2] largest component {best_n:,} px ({100 * best_n / (H * W):.1f}%)")

    # --- 3. fill interior holes ----------------------------------------------
    comp = ~mask
    outside = np.zeros((H, W), bool)
    dq = deque()
    for x in range(W):
        for y in (0, H - 1):
            if comp[y, x] and not outside[y, x]:
                outside[y, x] = True
                dq.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if comp[y, x] and not outside[y, x]:
                outside[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < H and 0 <= nx < W and comp[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                dq.append((ny, nx))
    holes = comp & ~outside
    mask = mask | holes
    print(f"[3] filled {int(holes.sum()):,} interior hole px")

    mask_im = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), mode="L")
    mask_im = mask_im.filter(ImageFilter.MedianFilter(5))

    # --- 4. edge decontamination ---------------------------------------------
    # Erode the mask to find "definitely interior"; any pixel that is in the mask
    # but near the boundary gets its colour replaced by the nearest interior
    # colour, so a later feather cannot leak backdrop colour into the edge.
    core = np.asarray(mask_im.filter(ImageFilter.MinFilter(7))).astype(np.float32) > 128
    band = (np.asarray(mask_im).astype(np.float32) > 128) & ~core
    ys, xs = np.where(core)
    by, bx = np.where(band)
    if len(xs) == 0 or len(bx) == 0:
        raise SystemExit("eroded mask or boundary band is empty")
    print(f"[4] decontaminating {len(by):,} boundary px against {len(ys):,} core samples")

    # Grid-accelerated nearest-core colour lookup, in expanding rings of 16 px
    # cells. Fully vectorised: no Python loop over pixels.
    CELL = 16
    GH, GW = (H + CELL - 1) // CELL, (W + CELL - 1) // CELL
    grid = -np.ones((GH, GW), np.int64)
    cell_y, cell_x = ys // CELL, xs // CELL
    flat = cell_y * GW + cell_x
    order = np.argsort(flat, kind="stable")
    flat_s, idx_s = flat[order], order
    uniq, start = np.unique(flat_s, return_index=True)
    counts = np.diff(np.append(start, len(flat_s)))
    print(f"    core cells {len(uniq):,} of {GH * GW:,}")

    rgb = a.copy()
    # per-cell representative core pixel (first sample that landed in the cell)
    cell_rep = np.full(GH * GW, -1, np.int64)
    cell_rep[uniq] = idx_s[start]

    bc_y, bc_x = by // CELL, bx // CELL
    pending = np.ones(len(by), bool)
    for ring in range(1, max(GH, GW) + 1):
        idx = np.where(pending)[0]
        if len(idx) == 0:
            break
        ry, rx = bc_y[idx], bc_x[idx]
        best_d = np.full(len(idx), np.iinfo(np.int64).max)
        best_rep = np.full(len(idx), -1, np.int64)
        for dy in range(-ring, ring + 1):
            for dx in range(-ring, ring + 1):
                if max(abs(dy), abs(dx)) != ring:
                    continue  # only the shell of this ring
                cy_, cx_ = ry + dy, rx + dx
                ok = (cy_ >= 0) & (cy_ < GH) & (cx_ >= 0) & (cx_ < GW)
                if not ok.any():
                    continue
                keys = cy_ * GW + np.where(ok, cx_, 0)
                rep = np.where(ok, cell_rep[np.clip(keys, 0, GH * GW - 1)], -1)
                hit = ok & (rep >= 0)
                if not hit.any():
                    continue
                hidx = idx[hit]
                reps = rep[hit]
                d = (ys[reps] - by[hidx]) ** 2 + (xs[reps] - bx[hidx]) ** 2
                better = d < best_d[hit]
                if better.any():
                    slot = np.where(hit)[0][better]
                    best_d[slot] = d[better]
                    best_rep[slot] = reps[better]
        got = best_rep >= 0
        if got.any():
            sel = idx[got]
            rgb[by[sel], bx[sel]] = a[ys[best_rep[got]], xs[best_rep[got]]]
            pending[sel] = False
    print(f"    decontaminated {int((~pending).sum()):,} / {len(by):,} boundary px")

    # --- 5. feather + tight crop ---------------------------------------------
    alpha = np.asarray(mask_im.filter(ImageFilter.GaussianBlur(0.8)))
    out = Image.fromarray(np.dstack([rgb.astype(np.uint8), alpha]), mode="RGBA")
    bb = out.getchannel("A").point(lambda v: 255 if v > 70 else 0).getbbox()
    if bb:
        pad = 2
        bb = (max(0, bb[0] - pad), max(0, bb[1] - pad),
              min(W, bb[2] + pad), min(H, bb[3] + pad))
        out = out.crop(bb)
    out.save(dst)
    print(f"[5] wrote {dst} {out.size[0]}x{out.size[1]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--disc", type=float, default=0.98)
    ns = ap.parse_args()
    cut(ns.src, ns.dst, ns.disc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
