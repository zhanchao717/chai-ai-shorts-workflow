#!/usr/bin/env python3
"""重算发布包的 package-manifest.md（文件清单 + 逐文件 md5）。

必须**在包内所有文件都定稿之后**跑 —— 否则清单里的 md5 会失效，而「清单对不上产物」
在独立评审里会被判 P0（EP.205/206 各撞过一次：清单生成后 `publish-copy.md` 又被改过）。

用法：
  python3 scripts/gen_package_manifest.py content/episode-205/publish-package-2026-09-22 [...]
"""
from __future__ import annotations

import datetime
import hashlib
import pathlib
import sys


def build(pkg: pathlib.Path) -> int:
    files = sorted(p for p in pkg.rglob('*') if p.is_file() and p.name != 'package-manifest.md')
    lines = [f'# 发布包清单 — {pkg.name}（重算于 {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")} CST）', '',
             f'共 {len(files)} 个文件（含 `qa-frames/`）。`package-manifest.md` 自身不计。', '',
             '| 文件 | 字节 | md5 |', '|---|---:|---|']
    for f in files:
        b = f.read_bytes()
        lines.append(f'| `{f.relative_to(pkg)}` | {len(b):,} | {hashlib.md5(b).hexdigest()} |')
    lines += ['', '**豁免**：`cover-9x16.png` —— 2026-09-14 起封面不进成片（`finalize-meta.json` 记 `cover_hold=0`），'
                  '抖音用 3:4 + 4:3 两张，9:16 已废（skill §9 / 发布映射 douyin→4:3 · xhs·视频号→3:4）。',
              '**发布后补**：`publish-record.md`（发布记录）在发布动作完成后写入；本清单需在它入包后重算一次。']
    (pkg / 'package-manifest.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{pkg}: 清单重算 {len(files)} 个文件')
    return len(files)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for a in sys.argv[1:]:
        build(pathlib.Path(a))
