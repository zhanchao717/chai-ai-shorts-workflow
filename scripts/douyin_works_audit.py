#!/usr/bin/env python3
"""抖音「作品列表导出.xlsx」审计器 —— 每次用户从后台导出后跑一遍。

输入：`~/Downloads/作品列表导出.xlsx`（列：作品名称/发布时间/体裁/审核状态/播放量/完播率/
5s完播率/封面点击率/2s跳出率/平均播放时长/点赞/分享/评论/收藏/主页访问/粉丝增量）
输出：体裁对比 · 逐周趋势 · 留存相关性 · 重复投稿 · 「自见」白发 · TOP/BOTTOM

用法：
  python3 scripts/douyin_works_audit.py [xlsx路径] [--since 2026-08-01]
"""
from __future__ import annotations
import argparse, collections, datetime as dt, math, re, statistics as st, sys

try:
    import openpyxl
except ImportError:
    print("需要 openpyxl：python3 -m pip install --user openpyxl", file=sys.stderr)
    sys.exit(2)


def num(x):
    if x is None or x in ("-", ""):
        return None
    try:
        return float(x)
    except Exception:
        return None


def load(path, since):
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    out = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[0]:
            continue
        ts = r[1]
        if not isinstance(ts, dt.datetime):
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})", str(ts))
            ts = dt.datetime(*map(int, m.groups())) if m else None
        if ts is None or ts < since:
            continue
        out.append(dict(title=str(r[0]).strip(), ts=ts, genre=str(r[2] or ""), status=str(r[3] or ""),
                        play=num(r[4]) or 0, finish=num(r[5]), f5=num(r[6]), ctr=num(r[7]),
                        j2=num(r[8]), avg=num(r[9]), like=num(r[10]) or 0, share=num(r[11]) or 0,
                        comment=num(r[12]) or 0, fav=num(r[13]) or 0, profile=num(r[14]) or 0,
                        fans=num(r[15]) or 0))
    return out


def pearson(xs, ys):
    n = len(xs)
    if n < 4:
        return float("nan")
    mx, my = st.mean(xs), st.mean(ys)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else float("nan")


def corr(sub, kx, ky, label, log=False):
    pairs = [(r[kx], r[ky]) for r in sub if r[kx] is not None and r[ky] is not None]
    if len(pairs) < 5:
        print(f"  {label:32} 样本不足（n={len(pairs)}）")
        return
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    if log:
        xs = [math.log1p(max(v, 0)) for v in xs]
        ys = [math.log1p(max(v, 0)) for v in ys]
    print(f"  {label:32} r = {pearson(xs, ys):+.3f}   (n={len(pairs)})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", nargs="?", default="/Users/chao/Downloads/作品列表导出.xlsx")
    ap.add_argument("--since", default="2026-08-01")
    a = ap.parse_args()
    since = dt.datetime.strptime(a.since, "%Y-%m-%d")
    recs = load(a.xlsx, since)
    if not recs:
        print("没有符合条件的数据", file=sys.stderr)
        return 1

    print(f"作品列表审计 · {a.since} 起 · 共 {len(recs)} 条\n")

    # ── 1. 体裁对比 ──────────────────────────────────────────────
    print("=== ① 体裁对比（这就是「变长」的代价）===")
    by = collections.defaultdict(list)
    for r in recs:
        by[r["genre"]].append(r)
    print(f"  {'体裁':12} {'n':>4} {'播放中位':>8} {'播放均值':>9} {'均播中位':>8} "
          f"{'2s跳出':>7} {'5s完播':>7} {'完播率中位':>9}")
    for g, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        pl = [x["play"] for x in v]
        av = [x["avg"] for x in v if x["avg"] is not None]
        j2 = [x["j2"] for x in v if x["j2"] is not None]
        f5 = [x["f5"] for x in v if x["f5"] is not None]
        fi = [x["finish"] for x in v if x["finish"] is not None]
        print(f"  {g:12} {len(v):>4} {st.median(pl):>8.0f} {st.mean(pl):>9.0f} "
              f"{st.median(av) if av else 0:>8.2f} {st.median(j2) if j2 else 0:>7.3f} "
              f"{st.median(f5) if f5 else 0:>7.3f} {st.median(fi) if fi else 0:>9.4f}")

    # ── 2. 逐周趋势 ──────────────────────────────────────────────
    print("\n=== ② 逐周趋势 ===")
    byw = collections.defaultdict(list)
    for r in recs:
        byw[r["ts"].date() - dt.timedelta(days=r["ts"].weekday())].append(r)
    for wk in sorted(byw):
        v = byw[wk]
        pl = [x["play"] for x in v]
        av = [x["avg"] for x in v if x["avg"] is not None]
        j2 = [x["j2"] for x in v if x["j2"] is not None]
        print(f"  {wk} 起  n={len(v):3}  播放中位 {st.median(pl):7.0f}  合计 {sum(pl):8.0f}  "
              f"均播中位 {st.median(av) if av else 0:5.2f}s  2s跳出 {st.median(j2) if j2 else 0:.3f}")

    # ── 3. 相关性（用样本量最大的体裁组）─────────────────────────
    big = max(by.items(), key=lambda kv: len(kv[1]))
    print(f"\n=== ③ 什么和播放量相关？（用样本最大的组：{big[0]}，n={len(big[1])}）===")
    sub = big[1]
    for k, lab in (("f5", "播放 ↔ 5s完播率"), ("avg", "播放 ↔ 平均播放时长"),
                   ("finish", "播放 ↔ 完播率"), ("j2", "播放 ↔ 2s跳出率")):
        corr(sub, k, "play", lab, log=True)
    corr(sub, "f5", "j2", "2s跳出 ↔ 5s完播率")

    # ── 4. 白发与重复（两个发布事故）─────────────────────────────
    print("\n=== ④ 发布事故：白发 / 重复 ===")
    zi = [r for r in recs if r["status"] != "公开"]
    print(f"  审核状态非「公开」= {len(zi)} 条（占 {len(zi)/len(recs)*100:.0f}%），播放合计 "
          f"{sum(r['play'] for r in zi):.0f}  —— **发了等于没发**")
    for r in zi[:8]:
        print(f"     {r['ts'].strftime('%m-%d %H:%M')} [{r['status']}] {r['title'][:34]}")
    seen = collections.defaultdict(list)
    for r in recs:
        key = (r["ts"].date(), re.sub(r"\s+", "", r["title"])[:26])
        seen[key].append(r)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    print(f"\n  同一天同标题重复投稿 = {len(dups)} 组，共 {sum(len(v) for v in dups.values())} 条")
    for k, v in list(dups.items())[:6]:
        print(f"     {k[0]} ×{len(v)} 条 · 播放 {[int(x['play']) for x in v]} · {k[1][:26]}")

    # ── 5. TOP / BOTTOM ─────────────────────────────────────────
    print("\n=== ⑤ TOP 10 播放（学它）===")
    for r in sorted(recs, key=lambda r: -r["play"])[:10]:
        print(f"  {r['ts'].strftime('%m-%d %H:%M')} {r['play']:>7.0f} 均播{(r['avg'] or 0):>5.2f}s "
              f"5s{(r['f5'] or 0):.3f} 完播{(r['finish'] or 0):.4f} {r['genre'][:9]:10} {r['title'][:30]}")
    print("\n=== ⑥ BOTTOM 10 播放（播放>0，学反面）===")
    nz = [r for r in recs if r["play"] > 0]
    for r in sorted(nz, key=lambda r: r["play"])[:10]:
        print(f"  {r['ts'].strftime('%m-%d %H:%M')} {r['play']:>7.0f} 均播{(r['avg'] or 0):>5.2f}s "
              f"2s跳出{(r['j2'] or 0):.3f} {r['genre'][:9]:10} {r['title'][:30]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
