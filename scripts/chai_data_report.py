#!/usr/bin/env python3
"""抖音后台导出表 → 本频道的「期 ↔ 数据」对照报告 + 体裁/时长/钩子视角复盘。

为什么是脚本（而不是每次让我现算）：
  · 抖音后台的权威数据只有两条来源 —— ① 创作者中心「导出数据」（作品列表 / 短视频全量指标），
    ② 发布时那个开着的浏览器窗口（MultiPost 只在发布期间开窗口，平时 `execute_script` 报 View not found；
    我们的 ego 浏览器又没有抖音登录态）。→ 日常走 ① 这条路最稳。
  · 表是**给人看的中文列名**，而且不同批次列有增减（`封面点击率` 有时是 `-`）→ 每次手工对列必错。

它做三件事：
  ① 把导出的每一行与**我们的期号**对上（用各期 `publish-copy.md` 的抖音标题做匹配），
     这样能直接看「哪一期跑出来了」，也能回填各期 `publish-record.md` / `performance-record.md`；
  ② 按**体裁/时长档**分组给中位数（播放、5s 完播、2s 跳出、平均播放时长）——
     2026-09-13 的归因是本频道改档位的依据，这张表是它的续期；
  ③ 列出 5s 完播最高/最低各若干条（含未对上期号的历史存量），供选题复盘。

用法：
  python3 scripts/chai_data_report.py                       # 自动取 ~/Downloads 里最新的一份
  python3 scripts/chai_data_report.py --works <作品列表.xlsx> [--metrics <全量指标.xlsx>]
  python3 scripts/chai_data_report.py --json /tmp/douyin-data.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DL = pathlib.Path.home() / 'Downloads'
COLS = ['作品名称', '发布时间', '体裁', '审核状态', '播放量', '完播率', '5s完播率', '封面点击率',
        '2s跳出率', '平均播放时长', '点赞量', '分享量', '评论量', '收藏量', '主页访问量', '粉丝增量']


def newest(pattern: str) -> pathlib.Path | None:
    hits = [pathlib.Path(p) for p in glob.glob(str(DL / pattern))]
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def load_rows(path: pathlib.Path) -> tuple[list[str], list[dict]]:
    import warnings
    warnings.filterwarnings('ignore')
    import openpyxl
    ws = openpyxl.load_workbook(str(path), read_only=True).active
    it = ws.iter_rows(values_only=True)
    head = [str(c).strip() if c is not None else '' for c in next(it)]
    rows = []
    for r in it:
        d = {h: r[i] if i < len(r) else None for i, h in enumerate(head)}
        if any(v not in (None, '') for v in d.values()):
            rows.append(d)
    return head, rows


def num(v) -> float | None:
    if v in (None, '', '-'):
        return None
    try:
        return float(str(v).replace('%', '').replace(',', ''))
    except Exception:
        return None


def rate(v) -> float | None:
    """导出的比率列可能是 0.348 也可能是 34.8%；统一成百分数。"""
    x = num(v)
    if x is None:
        return None
    return x * 100 if x <= 1.5 else x


def pct(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def episode_titles() -> dict[int, str]:
    """各期抖音标题（publish-copy.md 里「## 抖音」节的第 1 条标题）。"""
    out = {}
    for p in sorted(ROOT.glob('content/episode-*/publish-package-*/publish-copy.md')):
        m = re.fullmatch(r'episode-(\d+)', p.parent.parent.name)
        if not m:
            continue
        ep = int(m.group(1))
        txt = p.read_text(encoding='utf-8')
        sec = txt.split('## 抖音', 1)
        if len(sec) < 2:
            continue
        body = sec[1].split('## 小红书', 1)[0]
        t = re.search(r'^\s*1\.\s*(.+?)\s*$', body, re.M)
        if t:
            out[ep] = t.group(1).strip().replace('**', '')
    return out


def match_episode(title: str, titles: dict[int, str]) -> int | None:
    """导出的作品名 == 我们发的标题（去掉空格后做包含匹配）。"""
    t = re.sub(r'\s+', '', str(title or ''))
    for ep, want in titles.items():
        w = re.sub(r'\s+', '', want)
        if w and (w == t or w in t or t.startswith(w)):
            return ep
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--works', default=None, help='作品列表导出 xlsx；缺省取 ~/Downloads 里最新一份')
    ap.add_argument('--metrics', default=None, help='短视频全量指标 xlsx（逐日汇总）')
    ap.add_argument('--json', default=None)
    ap.add_argument('--top', type=int, default=8)
    a = ap.parse_args()

    wp = pathlib.Path(a.works) if a.works else (newest('作品列表*.xlsx') or newest('*作品列表*.xlsx'))
    if not wp or not wp.exists():
        print('❌ 没找到作品列表导出（~/Downloads/作品列表导出.xlsx）。'
              '导出路径：creator.douyin.com → 数据中心 → 内容数据 → 导出')
        return 2
    head, rows = load_rows(wp)
    missing = [c for c in ('播放量', '5s完播率', '发布时间') if c not in head]
    if missing:
        print(f'⚠️ 这份表里缺列 {missing}（实际列：{head[:12]}…）')
    titles = episode_titles()
    for r in rows:
        r['_ep'] = match_episode(r.get('作品名称'), titles)

    print(f'── 数据源：{wp.name}（{wp.stat().st_size / 1024:.0f}KB · '
          f'改于 {__import__("datetime").datetime.fromtimestamp(wp.stat().st_mtime):%Y-%m-%d %H:%M}）· {len(rows)} 行')
    ts = [str(r.get('发布时间') or '') for r in rows if r.get('发布时间')]
    if ts:
        print(f'   覆盖时间：{min(ts)[:16]} → {max(ts)[:16]}')

    # ① 与期号对上
    eps = sorted((r for r in rows if r['_ep']), key=lambda r: r['_ep'])
    print(f'\n── 能对上期号的 {len(eps)} 条（其余 {len(rows) - len(eps)} 条是更早的存量/未纳管内容）')
    if eps:
        print(f"{'期':>5} {'发布':<16} {'播放':>8} {'5s完播':>7} {'2s跳出':>7} {'均播':>7} {'粉丝+':>6}  作品名")
        for r in eps[-15:]:
            print(f"{r['_ep']:>5} {str(r.get('发布时间'))[:16]:<16} "
                  f"{(num(r.get('播放量')) or 0):>8.0f} "
                  f"{(rate(r.get('5s完播率')) or 0):>6.1f}% "
                  f"{(rate(r.get('2s跳出率')) or 0):>6.1f}% "
                  f"{(num(r.get('平均播放时长')) or 0):>6.1f}s "
                  f"{(num(r.get('粉丝增量')) or 0):>6.0f}  {str(r.get('作品名称'))[:24]}")

    # ② 体裁/时长档
    by = {}
    for r in rows:
        by.setdefault(str(r.get('体裁') or '未知'), []).append(r)
    print('\n── 按体裁/时长档（播放量列 > 0 的记录才计入中位数）')
    for k, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        plays = [num(r.get('播放量')) for r in rs if (num(r.get('播放量')) or 0) > 0]
        s5 = [rate(r.get('5s完播率')) for r in rs]
        jump = [rate(r.get('2s跳出率')) for r in rs]
        avg = [num(r.get('平均播放时长')) for r in rs]
        print(f'   {k:<12} n={len(rs):<4} 播放中位 {pct(plays) or 0:>8.0f} · '
              f'5s完播中位 {pct(s5) or 0:>5.1f}% · 2s跳出中位 {pct(jump) or 0:>5.1f}% · 均播中位 {pct(avg) or 0:>5.1f}s')

    # ③ 5s 完播两端
    withp = [r for r in rows if num(r.get('播放量')) and (num(r.get('播放量')) or 0) >= 100]
    srt = sorted(withp, key=lambda r: -(rate(r.get('5s完播率')) or 0))
    print(f'\n── 5s 完播最高 {a.top} 条（播放 ≥100 的 {len(withp)} 条里）')
    for r in srt[:a.top]:
        print(f"   {(rate(r.get('5s完播率')) or 0):>5.1f}%  播放 {(num(r.get('播放量')) or 0):>7.0f}  "
              f"{str(r.get('发布时间'))[:10]}  {str(r.get('作品名称'))[:30]}")
    print(f'\n── 5s 完播最低 {a.top} 条')
    for r in srt[-a.top:]:
        print(f"   {(rate(r.get('5s完播率')) or 0):>5.1f}%  播放 {(num(r.get('播放量')) or 0):>7.0f}  "
              f"{str(r.get('发布时间'))[:10]}  {str(r.get('作品名称'))[:30]}")

    # ④ 逐日汇总（可选）
    mp = pathlib.Path(a.metrics) if a.metrics else newest('数据表现_短视频全量指标*.xlsx')
    if mp and mp.exists():
        mh, mr = load_rows(mp)
        print(f'\n── 逐日汇总：{mp.name}（{len(mr)} 天）')
        cols = [c for c in ('日期', '投稿量', '总播放量', '5秒完播率', '2秒跳出率', '封面点击率', '平均播放时长') if c in mh]
        print('   ' + ' | '.join(cols))
        for r in mr[-10:]:
            print('   ' + ' | '.join(str(r.get(c))[:12] for c in cols))

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            [dict(ep=r['_ep'], title=r.get('作品名称'), published=str(r.get('发布时间')),
                  plays=num(r.get('播放量')), s5=rate(r.get('5s完播率')), jump2=rate(r.get('2s跳出率')),
                  avg=num(r.get('平均播放时长')), likes=num(r.get('点赞量')), fans=num(r.get('粉丝增量')),
                  genre=r.get('体裁'), review=r.get('审核状态')) for r in rows],
            ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'\n📝 明细写入 {a.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
