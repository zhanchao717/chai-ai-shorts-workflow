#!/usr/bin/env python3
"""封面逐字校验门禁（2026-09-14 起，封面改由 GPT 出图后的**必需门**）。

**为什么必须有它**：封面从"我们模板渲染"改成"GPT 出图"之后，中文与数字的正确性不再由代码保证。
实测踩到两类事故：
  ① **数字看错/写错**：`1.6万星` 在原生分辨率下会被 OCR 读成 `16万`（10 倍差别）；
  ② **编造数据**：模型自己加过 8 个我们没给过的星数（`Awesome 12.4k`、`DevTools 8.7k` …）——数据纪律红线。

**做法（关键设计都是踩坑换来的）**：
  · 同一张图在 **1× / 2× / 4× 三个倍率各识别一次，把结果拼成一段文本再比对** ——
    单倍率会漏：原生分辨率丢小数点，4× 有时又把小数点跟字粘在一起；
  · `--must` 是**硬门**：拼出来的文本里必须逐字出现（例：`--must 1.6万`）；
  · 未在 `--allow-num` 里的数字 = **WARN 列出待人工定谳**（不硬判：OCR 会把 `1.6` 读成 `0716`，
    硬判必然假报）；要严格可加 `--strict-numbers`；
  · 全程打印每个倍率的原始读数，便于人工核。

用法：
  python3 scripts/chai_cover_check.py <cover.png> [<cover2.png> …] \
      --must "1.6万" --must "GitHub 本周涨星榜" --allow-num 1.6 --allow-num 01
退出码：0 = PASS；1 = FAIL（有 must 未命中）
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWIFT = os.path.join(ROOT, "scripts", "vision_ocr.swift")
BIN = os.path.join(ROOT, "scripts", "bin", "vision_ocr")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*\s*(?:[kKmM万千米]|%|个|条|张|步)?")
SCALES = (1.0, 2.0, 4.0)


def ensure_binary() -> str:
    if os.path.isfile(BIN) and os.access(BIN, os.X_OK):
        return BIN
    os.makedirs(os.path.dirname(BIN), exist_ok=True)
    r = subprocess.run(["swiftc", "-O", SWIFT, "-o", BIN], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"❌ 编译 vision_ocr 失败：{r.stderr[:400]}")
    return BIN


def _tmp_key(path: str) -> str:
    """临时文件名用的**唯一键**。

    ⚠️ 2026-09-26 事故（EP.215 门禁E）：原来临时文件名只按 `os.path.basename(path)` 拼
    （`_cc_4.0_cover-4x3.png`），而**每一期的发布包里都有同名封面** —— 于是跑 EP.215 时，
    4× 档读到的是上一次 EP.214 跑剩下的缓存图，门禁E 的 OCR 文本里混进了
    「三天三家，／价格砍半／本周AI•EP 214」。那次恰好 ❌=0 没被翻成 PASS，但这是**假阴性**：
    真出错的那张封面可以永远读到别人的缓存。
    → 键改成「绝对路径 + 大小 + mtime」的短哈希：换目录、换内容都必然换缓存名。
    """
    try:
        st = os.stat(path)
        sig = f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}"
    except OSError:
        sig = os.path.abspath(path)
    return hashlib.sha1(sig.encode("utf-8")).hexdigest()[:12]


def ocr_one(path: str, scale: float) -> list[str]:
    """在指定倍率下识别单张图；放大用 PIL（缺失时退化用原图）。"""
    src = path
    if scale != 1.0:
        try:
            from PIL import Image
            im = Image.open(path)
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
            src = os.path.join(tempfile.gettempdir(), f"_cc_{scale}_{_tmp_key(path)}.png")
            im.save(src)
        except Exception:
            src = path
    r = subprocess.run([ensure_binary(), src], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    try:
        return [l["t"] for item in json.loads(r.stdout) for l in item["lines"]]
    except Exception:
        return []



def region_zoom_text(path: str) -> str:
    """**局部放大兜底**：整图 OCR 读不出时，把"含数字那一行"裁出来放大到高 ≥480px 再识别。

    为什么需要（2026-09-14 实测）：3:4 封面的大数字在整图 1×/2×/4× 都被读成 `16万`
    （小数点丢失），但把该行裁出来放大后能正确读出 `1.6万` —— 局部放大对"小字号小数点"有效。
    """
    try:
        from PIL import Image
    except Exception:
        return ""
    r = subprocess.run([ensure_binary(), path], capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    try:
        items = json.loads(r.stdout)
    except Exception:
        return ""
    if not items:
        return ""
    im = Image.open(path)
    W, H = im.size
    cands = [l for l in items[0]["lines"] if re.search(r"\d", l["t"])]
    cands.sort(key=lambda l: -l.get("h", 0))
    out = []
    for l in cands[:4]:
        x0 = int(max(0.0, l["x"] - 0.03) * W)
        x1 = int(min(1.0, l["x"] + 0.70) * W)
        y0 = int(max(0.0, l["y"] - 0.02) * H)
        y1 = int(min(1.0, l["y"] + l.get("h", 0.1) + 0.02) * H)
        if x1 <= x0 or y1 <= y0:
            continue
        crop = im.crop((x0, y0, x1, y1))
        k = max(1.0, 480.0 / max(1, crop.height))
        crop = crop.resize((int(crop.width * k), int(crop.height * k)), Image.LANCZOS)
        q = os.path.join(tempfile.gettempdir(), f"_ccz_{_tmp_key(path)}_{len(out)}.png")
        crop.save(q)
        rr = subprocess.run([ensure_binary(), q], capture_output=True, text=True)
        if rr.returncode == 0:
            try:
                out += [x["t"] for it in json.loads(rr.stdout) for x in it["lines"]]
            except Exception:
                pass
    return norm("".join(out))


def norm(s: str) -> str:
    return re.sub(r"\s", "", s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("covers", nargs="+")
    ap.add_argument("--must", action="append", default=[], help="拼合文本里必须逐字出现的串（可多次）")
    ap.add_argument("--allow-num", action="append", default=[], help="允许出现的数字 token（可多次）")
    ap.add_argument("--strict-numbers", action="store_true", help="未知数字也算 FAIL（默认只 WARN）")
    a = ap.parse_args()

    # 2026-09-17 复评 P2-9：单独跑本脚本（不经 chai_pipeline.py）时，--must 里的「EP 190」这种期号
    # 会被当成「未在允许清单里的数字」报 ⚠️，复核者容易误判成「封面编造数字」。
    # 既然是我们自己要求它必须逐字出现的串，里面的数字当然是我们给的。
    for _s in list(a.must or []):
        for _n in NUM_RE.findall(_s):
            _n = _n.strip()
            if _n and _n not in a.allow_num:
                a.allow_num.append(_n)

    allow = [norm(x) for x in a.allow_num]
    fails, warns = [], []
    for path in a.covers:
        print(f"── {os.path.basename(path)}")
        parts = []
        for sc in SCALES:
            lines = ocr_one(path, sc)
            if lines:
                print(f"   [{sc:g}×] " + " ｜ ".join(lines))
                parts.append("".join(lines))
        blob = norm("".join(parts))

        zoom_blob = None
        for must in a.must:
            m = norm(must)
            if m and m in blob:
                print(f"   ✅ 命中「{must}」")
                continue
            if zoom_blob is None:
                zoom_blob = region_zoom_text(path)
                print(f"   （整图读不到，改用局部放大兜底：{'读到 ' + zoom_blob[:60] if zoom_blob else '无结果'}）")
                blob += zoom_blob
            if zoom_blob and m in zoom_blob:
                print(f"   ✅ 命中「{must}」（局部放大）")
            else:
                print(f"   ❌ 找不到「{must}」")
                fails.append(f"{os.path.basename(path)}：找不到「{must}」")

        unknown = []
        for tok in NUM_RE.findall(blob):
            tok = norm(tok)
            if not tok:
                continue
            if any(tok.startswith(al) or al in tok for al in allow):
                continue
            unknown.append(tok)
        unknown = sorted(set(unknown))
        if unknown:
            msg = (f"{os.path.basename(path)}：未在允许清单里的数字 {unknown}"
                   f"（模型可能编造；也可能是 OCR 噪声，如 1.6 被读成 0716 —— 定谳后确属我们要的就加进 --allow-num）")
            print(f"   ⚠️  {msg}")
            (fails if a.strict_numbers else warns).append(msg)
        else:
            print(f"   ✅ 数字都在允许清单内（{allow}）")
        print()

    print(f"结论：{'PASS' if not fails else 'FAIL'}（❌ {len(fails)} · ⚠️ {len(warns)}）")
    for s in fails:
        print(f"  ❌ {s}")
    for s in warns:
        print(f"  ⚠️  {s}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
