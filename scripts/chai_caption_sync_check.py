#!/usr/bin/env python3
"""门禁I · 字幕「烘焙件 ↔ 发布件」一致性检查（2026-09-23 新增，EP.209 事故后固化）。

## 为什么要这道门
EP.209 我重录了 `audio/02.mp3`、重建了 `publish-timeline/caption_groups.json`，**但忘了重跑
`gen_chai_frames.py`** → 工程里 `compositions/captions.html` 的 `var GROUPS` 还是旧的一组
（15 组），成片里于是出现：
  · 口播里没有的「4B」孤行（墨迹 60px < 70px 下限）；
  · 从第 6.37 秒起**全片字幕比声音慢 0.43 秒**。
而 `chai_caption_band_check.py` 报了 PASS —— 因为它按**发布件**的组区间抽帧，
恰好绕过了成片里那段旧字幕的窗口。也就是说：**门禁审的是"我以为要渲的东西"，不是"真渲出来的东西"**。

同一类事故本批之前已经发生过一次（EP.207：改了 spec 的折行没重跑 frames，成片里仍是旧折行）。
→ 这道门就是那个缺口的补丁：**把工程里真正被渲染的字幕（烘焙件）与将要交付的字幕（发布件）逐组对齐**。

## 判据
① 组数必须相同；② 每组文本逐字相同；③ 每组 start/end 与发布件的差 ≤ `--tol`（默认 0.05s）。
任一条不满足即 FAIL（退出码 1）。

用法：
  python3 scripts/chai_caption_sync_check.py videos/<slug> content/episode-NNN
  python3 scripts/chai_caption_sync_check.py videos/<slug> content/episode-NNN --tol 0.1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


def baked_groups(html: str) -> list[dict] | None:
    """从 captions.html 里读 `var GROUPS = [...]`（gen_chai_frames.py 注入的那一份）。"""
    m = re.search(r'var\s+GROUPS\s*=\s*(\[.*?\])\s*;', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('project', help='视频工程 videos/<slug>')
    ap.add_argument('episode_dir', help='content/episode-NNN')
    ap.add_argument('--tol', type=float, default=0.05, help='时间容差（秒），默认 0.05')
    a = ap.parse_args()

    cap = pathlib.Path(a.project) / 'compositions' / 'captions.html'
    pub = pathlib.Path(a.episode_dir) / 'publish-timeline' / 'caption_groups.json'
    if not cap.exists():
        print(f'❌ 找不到 {cap}（工程没生成或路径不对）')
        return 2
    if not pub.exists():
        print(f'❌ 找不到 {pub}')
        return 2

    baked = baked_groups(cap.read_text(encoding='utf-8'))
    if baked is None:
        print(f'❌ {cap} 里读不到 `var GROUPS = [...]`（模板被改过？）')
        return 2
    published = json.loads(pub.read_text(encoding='utf-8'))
    if isinstance(published, dict):
        published = published.get('groups') or published.get('caption_groups') or []

    print(f'── 门禁I 字幕烘焙件 ↔ 发布件')
    print(f'   烘焙：{cap}（mtime {__import__("datetime").datetime.fromtimestamp(cap.stat().st_mtime):%m-%d %H:%M:%S}）· {len(baked)} 组')
    print(f'   发布：{pub}（mtime {__import__("datetime").datetime.fromtimestamp(pub.stat().st_mtime):%m-%d %H:%M:%S}）· {len(published)} 组')

    fails: list[str] = []
    if len(baked) != len(published):
        fails.append(f'组数不一致：烘焙 {len(baked)} vs 发布 {len(published)}')
    warn: list[str] = []
    for i in range(min(len(baked), len(published))):
        b, p = baked[i], published[i]
        bt, pt = str(b.get('text', '')).strip(), str(p.get('text', '')).strip()
        if bt != pt:
            fails.append(f'组{i} 文本不一致：烘焙「{bt}」 vs 发布「{pt}」')
            continue
        for k in ('start', 'end'):
            if k in b and k in p:
                d = abs(float(b[k]) - float(p[k]))
                if d > a.tol:
                    fails.append(f'组{i} {k} 偏差 {d:.3f}s > {a.tol}s（烘焙 {b[k]} vs 发布 {p[k]}）')
                elif d > a.tol / 2:
                    warn.append(f'组{i} {k} 偏差 {d:.3f}s（接近容差）')

    for w in warn[:5]:
        print(f'   ⚠️ {w}')
    if fails:
        print(f'\n❌ 有 {len(fails)} 处不一致（前 6 条）：')
        for f in fails[:6]:
            print(f'   · {f}')
        print('\n→ 修法：`python3 scripts/gen_chai_frames.py specs/<NNN>.json`（重注入字幕）→ 重渲 → 重跑门禁。')
        print('   注意：只跑 `gen_chai_index.py` **不会**更新 captions.html。')
        return 1
    print('\n✅ 烘焙件与发布件逐组一致（文本 + 时间轴）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
