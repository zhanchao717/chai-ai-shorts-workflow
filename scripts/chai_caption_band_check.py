#!/usr/bin/env python3
"""门禁H：**在成片上量字幕实际占了几行**（2026-09-21 事故后新增）。

**为什么必须有它**（当天真实事故）：EP.203/EP.204 的 `specs/*.json` 里 `line_breaks` 写的是 2 行，
`chai_layout_precheck.py` 也打印「✅ 字幕折行全部 ≤2 行」，但**成片里那 4 组字幕实际是 3 行**
（墨迹高 148–149px，而字幕带只容 114px ≈ 2 行，上下各溢出约 17px）。
根因：precheck **只读 spec、不读产物**，而那次改完 spec **没有重渲**（`compositions/captions.html`
里烘焙的还是旧的 3 行折法）。一句话：**门禁审的是"我以为要渲的东西"，不是"真的渲出来的东西"。**

做法（不依赖 OCR，纯像素）：对每一组字幕，取它的时间中点抽帧，在字幕带 x∈[320,984] 内做**行投影**——
按灰度 >200 的像素计数找出行区间，合并间距 <20px 的行，量出**墨迹总高度**：

  · `h ≤ --max-ink`（默认 120px）→ 2 行以内 ✅
  · 否则 → 该组超过 2 行 ❌（失败）

用法：
  python3 scripts/chai_caption_band_check.py <成片.mp4> [--groups <caption_groups.json>] [--max-ink 120]
退出码：0 = 全部 ≤2 行；1 = 有 3 行及以上的组。
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
FF = ROOT / 'node_modules' / '@remotion' / 'compositor-darwin-arm64'


def grab(video: str, t: float, out: str) -> np.ndarray:
    # ⚠️ 包装器 `videos/*/bin/ffmpeg`（= 本目录里的 ./ffmpeg）会先 cd 进 compositor 目录，
    #    所以**输入/输出都必须是绝对路径**，否则一律 "No such file or directory"。
    video = os.path.abspath(str(video))
    out = os.path.abspath(str(out))
    subprocess.run(['./ffmpeg', '-v', 'error', '-ss', str(t), '-i', video,
                    '-frames:v', '1', '-y', out], cwd=str(FF), check=False)
    if not os.path.exists(out):
        raise SystemExit(f'❌ 抽帧失败：{video} @ {t}s（检查 ffmpeg 与路径）')
    return np.asarray(Image.open(out).convert('L')).astype('int16')


def ink_height(gray: np.ndarray, x0: int = 320, x1: int = 984, thr: int = 200,
               merge_gap: int = 20, band_top: int = 1420, band_bottom: int = 1680,
               min_line_px: int = 70
               ) -> tuple[int, list[tuple[int, int]], list[int]]:
    """返回（墨迹总高度, 行区间列表）。

    只在**字幕带**里量：模板把字幕放在 `--cap-band-top: 1488px` / `--cap-band-height: 114px`
    （`videos/*/compositions/captions.html`），所以这里取 y∈[1420, 1680] 作为带内窗口，
    再把 x∈[320,984] 的亮像素按行投影 —— 不这样框住的话，画面里的卡片/大数字会被一起量进去
    （第一版就是这么误报的：整帧投影量出 200–350px 的"墨迹"）。
    """
    band = gray[band_top:band_bottom, x0:x1]
    rows = (band > thr).sum(axis=1)
    idx = np.where(rows > 3)[0]
    if len(idx) == 0:
        return 0, [], []
    spans, start, prev = [], int(idx[0]), int(idx[0])
    for y in idx[1:]:
        if y - prev > merge_gap:
            spans.append((start, prev)); start = int(y)
        prev = int(y)
    spans.append((start, prev))
    # 每一行的**墨迹宽度**（用于抓「2 行但某行只剩一个字」的孤行 —— 上一轮独立评审指出的盲区：
    # 门禁H 原来只量高度，97px 明明 2 行就判 ✅，可第 2 行宽只有 42px、只有一个「的」字）
    widths = []
    for (y0, y1) in spans:
        cols = (band[y0:y1 + 1] > thr).sum(axis=0)
        nz = np.where(cols > 0)[0]
        widths.append(int(nz[-1] - nz[0] + 1) if len(nz) else 0)
    spans = [(a + band_top, b + band_top) for a, b in spans]
    return int(sum(b - a + 1 for a, b in spans)), spans, widths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--groups', default=None, help='caption_groups.json（缺省取成片同目录的）')
    ap.add_argument('--max-ink', type=int, default=120, help='墨迹高度上限，默认 120px（2 行≈98px，3 行≈148px）')
    ap.add_argument('--min-line-px', type=int, default=70, help='单行墨迹宽度下限，默认 70px（抓「某行只剩一个字」的孤行）')
    ap.add_argument('--frame-margin', type=float, default=0.35,
                    help='取时间中点前后这个比例处再抽一帧（避开转场），默认 0.35')
    a = ap.parse_args()

    video = pathlib.Path(os.path.abspath(a.video))
    gp = pathlib.Path(a.groups) if a.groups else video.parent / 'caption_groups.json'
    if not gp.is_file():
        print(f'❌ 找不到 caption_groups.json：{gp}')
        return 1
    data = json.load(open(gp, encoding='utf-8'))
    groups = data['groups'] if isinstance(data, dict) and 'groups' in data else data

    tmp = pathlib.Path('/tmp/chai-cap-band'); tmp.mkdir(parents=True, exist_ok=True)
    bad, rows, orphans = [], [], []
    for i, g in enumerate(groups):
        start, end = float(g['start']), float(g['end'])
        span = max(0.05, end - start)
        for frac in (0.5, 0.5 - a.frame_margin, 0.5 + a.frame_margin):
            t = start + span * frac
            png = tmp / f'g{i:02d}_{frac:.2f}.png'
            h, spans, widths = ink_height(grab(video, t, str(png)))
            rows.append((g.get('id') or f'#{i}', round(t, 2), h, len(spans)))
            orphan = [w for w in widths if 0 < w < a.min_line_px]
            if h > a.max_ink:
                bad.append((g.get('id') or f'#{i}', round(t, 2), h, len(spans), (g.get('text') or '')[:24]))
                break
            if orphan:
                orphans.append((g.get('id') or f'#{i}', round(t, 2), orphan, (g.get('text') or '')[:24]))
                break

    worst = max((r[2] for r in rows), default=0)
    print(f'── {video.name} · {len(groups)} 组字幕 · 抽样 {len(rows)} 帧')
    print(f'   墨迹高度上限 {a.max_ink}px · 实测最大 {worst}px')
    if bad:
        print(f'   ❌ 有 {len(bad)} 组超过 2 行（成片里真的是 3 行及以上）：')
        for gid, t, h, lines, text in bad:
            print(f'      {gid} t={t}s 墨迹 {h}px / {lines} 行 —「{text}…」')
        print('   → 修法：把该句口播真正缩短（或按**逐字**拆分写进 spec 的 line_breaks）后**重渲**；'
              'spec 改了不重渲，成片不会变。')
    if orphans:
        print(f'   ❌ 有 {len(orphans)} 组出现**孤行**（某一行墨迹窄于 {a.min_line_px}px，通常只剩一个字）：')
        for gid, t2, ws, text in orphans:
            print(f'      {gid} t={t2}s 行宽 {ws} —「{text}…」')
        print('   → 修法：给该组写**逐字**的 2 行 line_breaks（别让渲染器自然绕行），然后重渲。')
    print('\n结论：' + ('✅ 成片字幕全部 ≤2 行且无孤行' if not bad and not orphans
                        else '❌ 有字幕超过 2 行或有孤行，禁止发布'))
    return 0 if (not bad and not orphans) else 1


if __name__ == '__main__':
    sys.exit(main())
