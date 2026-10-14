#!/usr/bin/env python3
"""封面后处理「凭证核验 / 回填」：证明包里的封面确实是从 `_prepad/` 里那张原图、按记录参数算出来的。

**为什么有它（2026-09-17 第二轮独立复评 P1-4）**：`cover-meta.json` 的 `safe_margin_postprocess`
第一版记的是 `cover-X.raw.png` 的 md5 —— 而当时脚本「文件已存在就不覆盖」，
于是**加垫两次时留下的 raw 是上一次的**，记的 md5 指向一张和成品毫无关系的图（评审实测：复算 maxdiff 255）。
凭证一旦不可复算，它就不是凭证。

做法：对每个 `cover-*.png`：
  · 若同目录 `_prepad/<同名>` 存在 → 用它当输入，按 meta 里记的参数（或自动搜索）重跑加垫，
    与成品逐像素比较，报 `maxdiff`；
  · `maxdiff == 0` → ✅ 可复算（凭证成立）；否则 ❌ 并给出反推出来的最优参数，提示记账要改。

用法：
  python3 scripts/verify_cover_postprocess.py content/episode-194/exp-gpt
  python3 scripts/verify_cover_postprocess.py <dir> --write-meta     # 把核验通过/反推的参数回填进 cover-meta.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FIT = os.path.join(HERE, "fit_cover_safe_margins.py")


def md5(p: str) -> str:
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def replay(src: str, scale: float, darken: float, feather: float, blur: float, mode: str) -> np.ndarray:
    tmpd = tempfile.mkdtemp(prefix="ccpp-")
    dst = os.path.join(tmpd, os.path.basename(src))
    shutil.copy2(src, dst)
    subprocess.run([sys.executable, FIT, dst, "--scale", str(scale), "--darken", str(darken),
                    "--feather", str(feather), "--blur", str(blur), "--mode", mode],
                   capture_output=True)
    return np.asarray(Image.open(dst).convert("RGB")).astype("int16")


def diff(a: np.ndarray, b: np.ndarray) -> tuple[int, float]:
    d = np.abs(a - b)
    return int(d.max()), round(float(d.mean()), 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--write-meta", action="store_true", help="把核验结果/反推参数回填 cover-meta.json")
    a = ap.parse_args()

    d = a.dir
    meta_p = os.path.join(d, "cover-meta.json")
    meta = json.load(open(meta_p, encoding="utf-8")) if os.path.exists(meta_p) else {}
    recorded = {e["file"]: e for e in (meta.get("safe_margin_postprocess") or {}).get("files", [])}
    prepad_dir = os.path.join(d, "_prepad")

    ok_all = True
    filled = []
    for f in sorted(os.listdir(d)):
        if not (f.startswith("cover-") and f.endswith(".png")):
            continue
        cur = os.path.join(d, f)
        pre = os.path.join(prepad_dir, f)
        print(f"── {f}")
        if not os.path.exists(pre):
            print("   ℹ 没有 _prepad 输入件 → 视为「未做后处理」。包内件应与出图件一致（可查 md5 与 OCR）。")
            continue
        rec = recorded.get(f) or {}
        best, params = None, None

        def try_cands(cands, target, pre):
            nonlocal best, params
            for (s, dk, ft, bl, md) in cands:
                got = replay(pre, s, dk, ft, bl, md)
                mx, mean = diff(got, target)
                if best is None or mx < best[0]:
                    best, params = (mx, mean), (s, dk, ft, bl, md)
                if mx == 0:
                    return True
            return False

        def scored(cands, target, pre):
            """跑一批候选，返回 [(maxdiff, 参数)]（用于挑出多个"最像"的再细搜）。"""
            out = []
            for cand in cands:
                got = replay(pre, cand[0], cand[1], cand[2], cand[3], cand[4])
                d = np.abs(got - target)
                # ⚠️ 只按 maxdiff 排序没用：参数不对时几乎全是 255（并列一大片），
                #    排序结果等于随便挑 → 细搜会围绕"错得很离谱"的种子展开，整个错过真值。
                #    必须用 (maxdiff, mean) 才有区分度。
                out.append((int(d.max()), float(d.mean()), cand))
            return sorted(out, key=lambda x: (x[0], x[1]))

        target = np.asarray(Image.open(cur).convert("RGB")).astype("int16")

        # ① 先按账本记的参数复算（记账已补全 darken/blur 的快路径）
        if rec.get("scale"):
            hit = try_cands([(rec["scale"], rec.get("darken", 0.80), rec.get("feather", 0.035),
                              rec.get("blur_frac", 0.06), rec.get("mode", "blur"))], target, pre)
        else:
            hit = False

        # ② 没记全参数（早期记账）→ 粗网格（scale 0.02 步长 × darken 0.05 步长）
        if not hit:
            coarse = [(round(0.86 + 0.02 * i, 2), round(0.68 + 0.02 * j, 2), 0.035, 0.06, "blur")
                      for i in range(8) for j in range(15)]
            coarse_scored = scored(coarse, target, pre)
            if coarse_scored:
                mx, mn, cand = coarse_scored[0]
                best, params = (mx, mn), cand
                if mx == 0:
                    hit = True

        # ③ 还不行 → 围绕**最像的三个**候选做细搜（只围绕一个会因为粗网格偏一格而整个错过）
        if not hit:
            seeds = [c for _, _, c in coarse_scored[:3]] if coarse_scored else ([params] if params else [])
            fine = []
            for seed in seeds:
                s0, dk0 = seed[0], seed[1]
                for i in range(-5, 6):
                    for j in range(-3, 4):
                        fine.append((round(s0 + 0.005 * i, 3), round(dk0 + 0.01 * j, 3), 0.035, 0.06, "blur"))
            hit = try_cands(fine, target, pre)

        mx, mean = best
        if mx == 0:
            print(f"   ✅ 可复算：用 _prepad/{f} + 参数 scale={params[0]} darken={params[1]} "
                  f"feather={params[2]} blur={params[3]} mode={params[4]} → 逐像素一致")
        else:
            ok_all = False
            print(f"   ❌ 不可复算：最优也只有 maxdiff={mx}（mean {mean}），参数 scale={params[0]} "
                  f"darken={params[1]} feather={params[2]} —— 记账与文件对不上，必须改记账")
        filled.append({
            "file": f, "size": list(Image.open(cur).size), "scale": params[0], "mode": params[4],
            "feather": params[2], "blur_frac": params[3], "darken": params[1],
            "indir": "_prepad/" + f, "in_md5": md5(pre), "out_md5": md5(cur),
            "replay_maxdiff": mx,
        })
    if a.write_meta and filled:
        # ⚠️ 2026-09-20 复评 P0 的成因：这里原来**无条件**把 filled 全写回，还给每条盖
        #    「逐像素复算」章 —— 于是「复算失败（maxdiff≠0）」的参数也被当成有效凭证写进包，
        #    评审一比对就发现「记账说 maxdiff 255、旁边却写着逐像素复算」。
        #    规矩：只有 maxdiff == 0 的条目才回填；失败的一条都不写，并且**不盖**章。
        good = [e for e in filled if e.get("replay_maxdiff") == 0]
        bad = [e for e in filled if e.get("replay_maxdiff") != 0]
        if good:
            sp = meta.get("safe_margin_postprocess") or {}
            by = {e["file"]: e for e in sp.get("files", [])}
            for e in good:
                by[e["file"]] = e
            sp["files"] = sorted(by.values(), key=lambda x: x.get("file", ""))
            sp.setdefault("script", "scripts/fit_cover_safe_margins.py")
            meta["safe_margin_postprocess"] = sp
        meta.pop("verified_by", None)
        if good and not bad:
            meta["verified_by"] = "scripts/verify_cover_postprocess.py（逐像素复算，全部命中）"
        json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"📝 已回填 {meta_p}（有效 {len(good)} 条"
              + (f"，**失败 {len(bad)} 条未写回**：{[e['file'] for e in bad]}" if bad else "") + "）")
    print("\n结论：" + ("✅ 所有后处理都可复算" if ok_all else "❌ 有不可复算的后处理记录"))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
