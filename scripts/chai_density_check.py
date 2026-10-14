#!/usr/bin/env python3
"""信息密度门禁（屏上字/秒）—— 2026-09-13 从流量归因里长出来的门禁。

**为什么有它**：把最近 7 天后台数据与我们自己的成片放在一起看，发现
「口播语速全程没变（4.3–5.1 字/秒），但**屏上字/秒从 8.9 涨到 15.1（+67%）**」——
观众没听快，是**画面里塞的字变多了**（口径声明、核验行、双数字块、附注、章节页）。
用户的原话是「内容变乱了」，这就是它的量化定义。

口径：**屏上字 = spec 里所有会被烧上屏的字符串字段**（模板按字段渲染，凡字符串都会上屏）；
**屏上字/秒 = 屏上字 ÷ 成片时长**。时长优先用成片的**实测**值（--duration），
其次用 `audio_meta.json` 的 Σ配音，最后按口播字数估算。

阈值（按历史实测定标）：
  EP.150–159 ≈ 7.4–11.9（短视频期）· EP.160–167 ≈ 11.6–13.1 · EP.177–179 = 14.1–15.1（偏乱）
  → **> 13.0 FAIL**（已进入"乱"的区间）· **> 11.5 WARN**（超出目标带宽）

用法：
  python3 scripts/chai_density_check.py --spec specs/179.json [--duration 115.24] [--script content/episode-179/SCRIPT.md]
退出码：0 = PASS/WARN；1 = FAIL
"""
from __future__ import annotations
import argparse, json, os, re, sys

FAIL_OVER = 13.0
WARN_OVER = 11.5

# 这些字段是**元数据**，模板不渲染，不计入屏上字
META_KEYS = {"id", "template", "kind", "type", "slug", "scene", "chapter"}


def collect(node, out, key=None):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in META_KEYS:
                continue
            collect(v, out, k)
    elif isinstance(node, list):
        for v in node:
            collect(v, out, key)
    elif isinstance(node, str):
        if len(node) < 300:          # 超长文本不是屏上文案（是说明），但仍计入并单列
            out.append(node)
        else:
            out.append(node)


def scenes_of(spec):
    if spec.get("chapters"):
        out = []
        for c in spec["chapters"]:
            out += list((c.get("scenes") or {}).items())
        return out
    return list((spec.get("scenes") or {}).items())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--duration", type=float, default=0.0, help="成片实测时长（秒）")
    ap.add_argument("--audio-meta", default="", help="audio_meta.json（备用时长来源）")
    ap.add_argument("--script", default="", help="SCRIPT.md（最后兜底：按口播字数估时）")
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding="utf-8"))
    scenes = scenes_of(spec)

    per_scene, total = [], 0
    for sid, body in scenes:
        strs = []
        collect(body, strs)
        n = len(re.sub(r"\s", "", "".join(strs)))
        per_scene.append((sid, n))
        total += n

    dur = a.duration
    src = "成片实测"
    if not dur and a.audio_meta and os.path.exists(a.audio_meta):
        am = json.load(open(a.audio_meta, encoding="utf-8"))
        dur = sum(v.get("duration_s", 0) for v in am.get("voices", [])) + 1.9   # +封面头/尾帧
        src = "audio_meta Σ配音 + 1.9s"
    if not dur and a.script and os.path.exists(a.script):
        spoken = "".join(re.findall(r"^\s*\d{1,2}\.txt\s*[：:]\s*(.+)$",
                                    open(a.script, encoding="utf-8").read(), re.M))
        n_spoken = len(re.sub(r"\s", "", spoken))     # 不放进 f-string：避免反斜杠
        dur = n_spoken / 4.8
        src = "按口播估算（%d 字 ÷ 4.8）" % n_spoken
    if not dur:
        print("❌ 拿不到时长：给 --duration / --audio-meta / --script 之一", file=sys.stderr)
        return 2

    d = total / dur
    verdict = "FAIL" if d > FAIL_OVER else ("WARN" if d > WARN_OVER else "PASS")
    mark = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[verdict]

    print("信息密度门禁 · 屏上字/秒")
    print(f"  屏上字 **{total}** ÷ 时长 **{dur:.2f}s**（{src}）= **{d:.2f} 字/秒**")
    print(f"  阈值：> {WARN_OVER} 警告 · > {FAIL_OVER} 失败（EP.150–159 ≈ 7.4–11.9 为健康区）")
    print(f"\n  最密的 5 场：")
    for sid, n in sorted(per_scene, key=lambda x: -x[1])[:5]:
        print(f"    {sid:12} {n:5} 字  {n / dur:5.2f} 字/秒")
    print(f"\n结论：{mark} {verdict}（屏上 {d:.2f} 字/秒）")
    if verdict != "PASS":
        print("→ 修法：把**口径/核验/附注**类文字移到置顶评论与文案；每条只留**一个主角数字**；")
        print("  删掉与口播重复的屏上文字（口播已经说了的不必再写一遍）。")
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
