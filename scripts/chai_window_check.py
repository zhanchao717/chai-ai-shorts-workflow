#!/usr/bin/env python3
"""空窗自证（chai_window_check）：每场开窗瞬间是否真的有「内容」。

用法：
    python3 scripts/chai_window_check.py <成片.mp4> <audio_meta.json> [--out window-check.json]
        [--offset-hit 0.8] [--settle 3.0] [--min-rel 0.30] [--lo 0.0] [--hi 1.6] [--step 0.2]

口径（与 finalize_episode 一致）：
    场起点 = **0.4s 封面头 + Σ voices[].duration_s**（渲染件把槽位收缩到媒体长度，
    所以成片时间轴 = Σ配音）。

⚠️ 判据为什么不能是「最大亮度 > 60」（2026-09-12 EP.176 评审 P2 的教训）：
    永久装饰件（四角准星）自身亮度就有 **62–65**，酸柠装饰条到 **118–122** →
    固定亮度阈值**恒真**，内容卡全空也会报"有内容"，等于没查。
⚠️ 也不能用「绝对高亮像素占比」（如 L≥160）：**酸柠绿 #D1FF00 的亮度约 227**，
    装饰件本身就够亮 → 同样会把装饰当内容。

**本脚本的判据（相对自身稳定态）**：
    以**文字/卡片密度**为内容信号 —— 内容区（y210–1440）的**边缘像素占比** `edge_ratio`
    （相邻像素亮度差 > 阈值）。装饰件是**模糊光斑 / 细直线**，边缘稀疏；文字与卡片边缘密集。
    逐场比较：`edge_ratio(+offset_hit)` 对比 `edge_ratio(settle)`（同场稳定态，默认 +3.0s）。
    硬判据：**22 场全部 ≥ --min-rel（默认 30%）** —— 若某场开窗是空的，该比值会接近 0。

退出码：0 = 通过；1 = 有场次开窗内容不足；2 = 输入缺失。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
FFMPEG = ROOT / "scripts" / "hyperframes_ffmpeg_wrapper.sh"
COVER_HOLD = 0.4
CONTENT_BOX = (0, 210, 1080, 1440)   # 内容区（不含字幕带 y1488+）
EDGE_THR = 40                        # 相邻像素亮度差阈值


def scene_starts(meta_path: pathlib.Path):
    # 2026-09-14（EP.181 独立评审 P1-1）：封面头**以包内 finalize-meta.json 为准**（旧包回退 0.4s）。
    # 封面已不进成片（cover_hold=0.0），硬编码 0.4 会让场起点整体偏 0.36s →
    # "每场开窗瞬间是否真有内容"这条检查**从未采样到真正的开窗**。
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    starts, t = [], COVER_HOLD
    durs = []
    for v in meta["voices"]:
        starts.append(t)
        d = float(v["duration_s"])
        durs.append(d)
        t += d
    return starts, durs, t


def grab(video: pathlib.Path, t: float, out: pathlib.Path) -> np.ndarray:
    subprocess.run([str(FFMPEG), "-y", "-v", "error", "-ss", f"{max(t, 0.0):.3f}", "-i", str(video),
                    "-frames:v", "1", str(out)], check=True)
    im = Image.open(out).convert("L").crop(CONTENT_BOX)
    return np.asarray(im, dtype=np.float32)


def edge_ratio(y: np.ndarray) -> float:
    gx = np.abs(np.diff(y, axis=1))[:-1, :]      # (H-1, W-1)
    gy = np.abs(np.diff(y, axis=0))[:, :-1]      # (H-1, W-1)
    g = gx + gy
    return float((g > EDGE_THR).mean())


def cover_hold_of(audio_meta_path: str) -> float:
    """成片里**实际**的封面头时长：优先读同包内的 `finalize-meta.json`，没有则回退历史默认 0.4s。

    为什么（2026-09-14，EP.181 独立评审 P1-1 抓到）：封面已改成"不进成片"
    （`finalize_episode.py --no-cover`，包内 `finalize-meta.json` 写 `cover_hold: 0.0`），
    而本脚本仍硬编码 0.4s → 场起点整体偏 +0.36s，**从未采样到每场真正的 0–0.4s 开窗**，
    与它自称"每场开窗瞬间是否真有内容"不符。`chai_pipeline.py` 早有 `cover_hold_of()`，这里补齐。
    """
    import json as _json
    import os as _os
    pkg = _os.path.dirname(_os.path.abspath(audio_meta_path))
    for cand in (pkg, _os.path.dirname(pkg)):
        f = _os.path.join(cand, "finalize-meta.json")
        try:
            with open(f, encoding="utf-8") as fh:
                return float(_json.load(fh).get("cover_hold", 0.4))
        except Exception:
            continue
    # ⚠️ 静默回退是 2026-09-17 独立评审的 P1：拿**渲染件**跑（videos/<slug>/renders/x.mp4）时
    #    这里找不到 finalize-meta.json，会悄悄按 0.4s 算场起点，写进包里的 window-check.json
    #    就带着一个**错的前提**（成片其实 cover_hold=0.0）。现在改成**大声说出来**。
    print(f"⚠️ 在 {pkg} 与上一级都没找到 finalize-meta.json → 封面头回退按 0.4s 计算；"
          "要拿到正确口径，请对**发布包里的成片**跑本脚本（包里才有 finalize-meta.json）。")
    return 0.4

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("audio_meta")
    ap.add_argument("--out", default=None,
                    help="明细 JSON 落盘路径；缺省写到**成片所在目录**（不是 CWD）——"
                         "EP.182 评审 P2-5：默认写 CWD，评审者一重跑就覆盖仓库根的同名文件")
    ap.add_argument("--lo", type=float, default=0.0)
    ap.add_argument("--hi", type=float, default=1.6)
    ap.add_argument("--step", type=float, default=0.2)
    ap.add_argument("--offset-hit", type=float, default=0.8)
    ap.add_argument("--settle", type=float, default=3.0)
    ap.add_argument("--min-rel", type=float, default=0.30)
    ap.add_argument("--min-abs", type=float, default=0.006,
                    help="绝对下限：内容区边缘占比必须 ≥ 此值（防「整场都空但相对自身仍是 100%」）")
    a = ap.parse_args()
    if not a.out:
        a.out = str(pathlib.Path(a.video).resolve().parent / "window-check.json")
    # 封面头以**成片所在发布包**的 finalize-meta.json 为准（旧包回退 0.4s）。
    # ⚠️ 2026-09-14（EP.181 评审 P1-1）：不能用 audio_meta 的目录去找 —— 它在工程目录下，
    #    包里才有 finalize-meta.json；用错路径会静默回退成 0.4，检查口径就又错了。
    global COVER_HOLD
    COVER_HOLD = cover_hold_of(str(a.video))

    video, meta = pathlib.Path(a.video), pathlib.Path(a.audio_meta)
    if not video.is_file() or not meta.is_file():
        print(f"缺少输入：{video} / {meta}")
        return 2

    starts, durs, total = scene_starts(meta)
    tmp = pathlib.Path("/tmp/chai-window-frames")
    tmp.mkdir(parents=True, exist_ok=True)
    steps = [round(a.lo + i * a.step, 2)
             for i in range(int(round((a.hi - a.lo) / a.step)) + 1)]

    rows, ok = [], 0
    for i, (s, d) in enumerate(zip(starts, durs), 1):
        settle_off = min(a.settle, max(0.6, d - 0.2))
        settled = edge_ratio(grab(video, s + settle_off, tmp / f"s{i:02d}_settle.png"))
        rec = {"scene": i, "t0": round(s, 3), "settle_offset": round(settle_off, 2),
               "settled_edge_ratio": round(settled, 5), "steps": {}}
        for st in steps:
            er = edge_ratio(grab(video, s + st, tmp / f"s{i:02d}_{st:.1f}.png"))
            rec["steps"][f"{st:.1f}"] = {"edge_ratio": round(er, 5),
                                         "rel": round(er / settled, 3) if settled > 0 else None}
        hit = rec["steps"][f"{a.offset_hit:.1f}"]
        # 2026-09-12（复核轮次 2 的反例）：只看"相对自身稳定态"会漏掉「**整场为空**」——
        #   评审用真实帧合成 30s 测试片：内容列全空 0.0017 / 空卡 0.0033 / 纯色块 0.0022
        #   的 rel 全是 1.00 → 会 PASS。故**再加一道绝对下限**：
        #   有效判据 = (rel ≥ --min-rel) AND (edge_ratio ≥ --min-abs)。
        rec["hit"] = {"offset": a.offset_hit, "edge_ratio": hit["edge_ratio"], "rel": hit["rel"],
                      "min_abs": a.min_abs,
                      "ok": ((hit["rel"] or 0) >= a.min_rel) and (hit["edge_ratio"] >= a.min_abs)}
        ok += 1 if rec["hit"]["ok"] else 0
        rows.append(rec)

    worst = min((r["hit"]["rel"] or 0) for r in rows)
    min_edge = min(r["hit"]["edge_ratio"] for r in rows)
    summary = {
        "video": str(video), "cover_hold": COVER_HOLD, "voice_total": round(total - COVER_HOLD, 3),
        "scenes": len(rows), "steps": steps, "content_box": CONTENT_BOX, "edge_threshold": EDGE_THR,
        "criterion": (f"edge_ratio(+{a.offset_hit}s) ≥ {a.min_rel:.0%} × edge_ratio(+settle) "
                      f"AND edge_ratio(+{a.offset_hit}s) ≥ {a.min_abs}"),
        "min_abs_required": a.min_abs, "global_min_edge_ratio": round(min_edge, 5),
        "hit_offset": a.offset_hit, "min_rel_required": a.min_rel,
        "hit_scenes_ok": ok, "hit_ratio": round(ok / len(rows), 4), "worst_rel": round(worst, 3),
        "verdict": "PASS" if ok == len(rows) else "FAIL", "scenes_detail": rows,
    }
    pathlib.Path(a.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"成片 {video.name}")
    print(f"口径：场起点 = {COVER_HOLD}s 封面头 + Σ配音；Σ配音 = {total - COVER_HOLD:.3f}s（下表 total 含封面头 {COVER_HOLD}s）；{len(rows)} 场 × {len(steps)} 档"
          f"（{a.lo}–{a.hi}s，步长 {a.step}）")
    print(f"内容信号 = 内容区（y210–1440）边缘像素占比")
    print(f"判据：+{a.offset_hit}s 的值 ≥ {a.min_rel:.0%} × 同场 +settle 稳定态的值，"
          f"**且 ≥ 绝对下限 {a.min_abs}**（下限用于挡「整场都空、相对自身仍 100%」）")
    for r in rows:
        h = r["hit"]
        print(f"  {r['scene']:2d}  t0={r['t0']:8.3f}s  +{a.offset_hit}s 边缘占比={h['edge_ratio']:.4f}"
              f"（下限 {a.min_abs}）  相对稳定态={h['rel']:.2f}  {'✅' if h['ok'] else '❌'}")
    print(f"\n+{a.offset_hit}s 达标场次：{ok}/{len(rows)} = {ok/len(rows)*100:.1f}% · 最差比值 {worst:.2f}"
          f" · 最小绝对边缘占比 {min_edge:.4f}（下限 {a.min_abs}）")
    print(f"结论：[{summary['verdict']}] · 明细写入 {a.out}")
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
