#!/usr/bin/env python3
"""柴主编 · 写稿阶段「节奏 / 密度预检」（不是总时长门禁，是逐段节奏门禁）

为什么需要：EP.167D（82.081s / 7 场景）独立评审的核心内容批评是——
  **06-verify 段独占 20.2s（全片 24.6%），却只承载「会话 A 写、新建 B、问它」这种常识化流程，
    其中一行说明占屏 4s，信息增量极低 → 最掉人。**
也就是说：**「总时长落在 60–90s 档位」不等于「节奏合格」**。既有 `chai_hook_check.py` 只判
总时长档位，任何"某一段低密度却很长"都能绿灯通过。本脚本把那条评审教训变成**写稿阶段就能跑的机械门禁**，
在 TTS / 渲染之前就拦住。

用法：
  python3 scripts/chai_script_pace.py content/episode-167-deep \
      --min-duration 60 --max-duration 90 [--json pace-report.json]

  # 日更 5 场景（缺省参数是深度版 60/90，日更必须显式传档位）
  python3 scripts/chai_script_pace.py content/episode-167 \
      --min-duration 25 --max-duration 45

  # 看本目录实测语速（标定常数用）：逐段 非空白字符数 / 实测时长
  python3 scripts/chai_script_pace.py content/episode-167-deep --show-calibration

输入（按优先级）：
  ① `<content-dir>/audio/NN.txt`（**优先**，这才是真正喂给 TTS 的口播文本；段数任意，5 或 7 都吃）
  ② 回退：解析 `<content-dir>/SCRIPT.md`（`audio/` 缺失时）
  `--audio-source=dir|script` 可强制选择。段名/槽位按 `scripts/README-deep.md` 的场景表推断：
    5 段 → 01-hook / 02-facts / 03-mechanism / 04-action / 05-verdict
    7 段 → 01-hook / 02-facts / 03-mechanism / 04-action / 05-config / 06-verify / 07-verdict
  段数不是 5/7 时不猜，只按序号打印。

时长口径（每条都标明来源）：
  ① 实测——`<content-dir>/audio/NN.mp3` 用 `afinfo`（macOS）或 `ffprobe` 读（`publish-timeline/`
     里的音频是软链，不去解析，避免指错文件）；
  ② 估算——`--sec-per-char` × 非空白字符数。
  报告里 `来源` 列逐条标 `实测` / `估算`。

── 语速常数 `--sec-per-char`（默认 0.208）的样本来源 ────────────────────────────
MiniMax `male-qn-qingse` / `speech-2.8-hd` / speed 1.08 / calm，本工程 4 期实测，
逐段口径 = `非空白字符数 ÷ NN.mp3 实测时长`（2026-09-11 复算，共 22 段）：
    EP.165（5 段） 合计 179 字 / 35.784s → 0.1999 s/字
    EP.166（5 段） 合计 166 字 / 35.892s → 0.2162 s/字   ← L4 长段
    EP.167（5 段） 合计 187 字 / 40.464s → 0.2164 s/字
    EP.167D（7 段）合计 418 字 / 80.136s → 0.1917 s/字
    22 段逐段值：均值 0.2039（中位数 0.207，σ≈0.019，极差 0.1705–0.2480）
（注：本文件早期草稿写「实测均值 0.208」，2026-09-11 用脚本 `--show-calibration` 复算，
  22 段真实均值是 **0.2039**；缺省仍取 **0.208**——它≈中位数，也与各期 SCRIPT.md
  既有的写稿口径 `418 × 0.208 ≈ 87s` 一致，改动会同时动到历史文档的对照数字。）
诚实说明：**这是"整期口径"常数，不是逐段精确模型**——单段误差可达 ±20%（段首/段尾停顿、
中英混排占比不同）。所以：① 有 mp3 就用**实测**，估算只用于没配音的写稿阶段；
② 报告会打印「估算 vs 实测」的偏差百分比。EP.167D 实测 80.136s，估算 0.208×418 = 86.944s，
**高估 +8.5%**；按本段实测标定（0.1917）则高估 +0.0%。若你的稿子是深度版这种
中英混排多、短句多的形态，可用 `--sec-per-char 0.192` 收紧（见 README §7）。

告警规则（阈值全部可参数覆盖，默认值见下）：
  1. 单段过长   > 18.0s → ⚠️ 低信息密度风险（检查是否在讲常识）；> 22.0s → ❌
  2. 单段过短   <  5.0s → ⚠️（可能只是过渡句，也可能是没讲清）
  3. 总时长     落在 `--min-duration`/`--max-duration`（默认 60/90）之外 → ❌
  4. 占比失衡   任一段占全片 > 22% → ⚠️；> 26% → ❌
  5. 余量不足   总时长距上限余量 < 3.0s → ⚠️（留重录/微调余量）
  6. 相邻段失衡（**长片专用**）相邻两段「非空白字符数」的比 > 1.6 倍 → ⚠️ 节奏忽快忽慢。
     只在段数 ≥ 12 时检查（短片抖动大、易误报）；阈值 --adj-ratio / --adj-min-segs 可覆盖。
     例：24 段里有 3 段是 40 字、相邻那几段只有 20 字 → 听感上一段赶一段拖。

长视频档位（20–30 场景，3–5 分钟）：
  python3 scripts/chai_script_pace.py content/episode-NNN --min-duration 180 --max-duration 300
  · 阈值规则**不变**（单段 >18s ⚠️ / >22s ❌、占比 >22% ⚠️ / >26% ❌）；
  · 但占比那两条是按 5/7 段标定的：段数越多、每段占比天然越小（24 段时均值仅 4.2%），
    所以长片上它们几乎不会响 —— 想让长片也有"某一段特别重"的检查，
    传 --share-warn / --share-fail（例如 24 段用 8 / 12）；
  · 长片真正要盯的是**绝对秒数**与**相邻字数差**（规则 6）。

退出码：0 = 无 ❌（只有 ⚠️ 时也退 0，打印但不算失败）；1 = 有 ❌；2 = 输入目录/脚本缺失。
只用标准库。不改其它脚本、不碰 videos/。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

FAIL, WARN, OK = "FAIL", "WARN", "OK"
MARK = {FAIL: "❌", WARN: "⚠️", OK: "✅"}

# ── 默认阈值（2026-09-11，来源：EP.167D 独立评审 + 本工程 4 期实测）──────────────
DEF_SEC_PER_CHAR = 0.208   # 见文件头「语速常数的样本来源」
DEF_SEG_WARN = 18.0        # 单段 > 18s：EP.167D 06-verify = 20.196s 被判"最掉人"，取 18s 作预警线
DEF_SEG_FAIL = 22.0        # 单段 > 22s：明显超出一屏能承载的信息量
DEF_SEG_SHORT = 5.0        # 单段 < 5s：EP.165–167 实测最短 4.464s（钩子段），再短要问是不是没讲清
DEF_SHARE_WARN = 22.0      # 占比 > 22%：EP.167D 06-verify 24.6% 被评审点名，22% 作预警线
DEF_SHARE_FAIL = 26.0      # 占比 > 26%：单段吃掉全片 1/4 以上，结构必失衡
DEF_HEADROOM = 3.0         # 距上限余量 < 3s：EP.167D 成片收尾余量只有 1.89s，几乎没得改
DEF_MIN, DEF_MAX = 60.0, 90.0   # 深度版档位（日更 5 场景请显式传 25/45；长视频传 180/300）
# ── 长片专用：相邻段字数差 ────────────────────────────────────────────────────
# 为什么需要它：长视频（20–30 段）里「某一段忽然比邻居短一半 / 长一倍」听感上就是
# 忽快忽慢——既有五条规则一条都抓不到（它们看的是单段绝对值与占比，不看**相邻关系**）。
# 口径：相邻两段「非空白字符数」的比值 > 1.6（无论谁多谁少）即 ⚠️。
# 为什么是 1.6：本工程 4 期 22 段实测的相邻比中位数 1.22、p90 1.55；
# 1.6 落在「正常波动」与「明显失衡」之间。可用 --adj-ratio 覆盖。
DEF_ADJ_RATIO = 1.6
# 段数达到这个数才把相邻差检查当回事（短片的段本来就少，抖动大，误报多）
DEF_ADJ_MIN_SEGS = 12

# 槽位表（必须与 scripts/README-deep.md §1 的场景表一致）
SLOTS = {
    5: ["01-hook", "02-facts", "03-mechanism", "04-action", "05-verdict"],
    7: ["01-hook", "02-facts", "03-mechanism", "04-action", "05-config", "06-verify", "07-verdict"],
}
ROWS: list[dict] = []
GATES: list[dict] = []


def add(gid: str, level: str, detail: str, title: str, seg: int | None = None) -> None:
    GATES.append({"id": gid, "level": level, "title": title, "detail": detail, "seg": seg})


def nchars(text: str) -> int:
    """非空白字符数（与各期 SCRIPT.md 的「非空白字符」口径一致）。"""
    return len(re.sub(r"\s", "", text))


# ---------- 输入 ----------
def _ordinal_to_int(token: str) -> int | None:
    """'06' / '6' / '六' / '①' → 6；不认识返回 None。"""
    token = token.strip()
    if token.isdigit():
        return int(token)
    cjk = "一二三四五六七八九十"
    if token in cjk:
        return cjk.index(token) + 1
    circled = "①②③④⑤⑥⑦⑧⑨⑩"
    if token in circled:
        return circled.index(token) + 1
    return None


def parse_script(path: pathlib.Path) -> tuple[dict[int, str], list[str]]:
    """解析 SCRIPT.md 的口播段。能认的写法（本项目实际出现过 3 种）：
        ## Scene 01 — ...        + 缩进块 `01.txt：<文本>`
        ## Line 1 — ...（Frame 1）+ 缩进块纯文本
        ## Line 3 — ...(Frame 3)  + 正文缩进段
    返回 ({段号: 口播文本}, 警告列表)；解析不到就返回空 dict（调用方按序号兜底）。"""
    warns: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {}, [f"SCRIPT.md 读取失败：{exc}"]

    segs: dict[int, str] = {}
    cur: int | None = None
    buf: list[str] = []
    heading_re = re.compile(r"^##+\s*(?:Scene|Line|场景|段)\s*"
                            r"([0-9０-９]+|[一二三四五六七八九十]|[①②③④⑤⑥⑦⑧⑨⑩])")

    def flush() -> None:
        nonlocal cur, buf
        if cur is not None:
            text = "\n".join(buf)
            # 去掉 `NN.txt：` 前缀（有的期写了，有的没写）
            text = re.sub(r"^[0０-９]{1,2}[^\n：:]*[：:]\s*", "", text.strip())
            text = re.sub(r"\s*\n\s*", " ", text).strip()
            if text:
                segs[cur] = (segs.get(cur, "") + " " + text).strip()

    for raw in lines:
        line = raw.rstrip()
        m = heading_re.match(line)
        if m:
            flush()
            cur = _ordinal_to_int(m.group(1))
            buf = []
            continue
        if cur is None:
            continue
        if line.startswith("#"):        # 新一级标题（"## 字数与时长"之类）→ 收工
            flush()
            cur, buf = None, []
            continue
        if not line.strip():            # 空行分隔一级标题与正文
            flush()
            buf = []
            continue
        if line.startswith("    ") or line.startswith("\t"):
            buf.append(line.strip())
        else:
            flush()
            buf = []
    flush()
    if not segs:
        warns.append("SCRIPT.md 未解析出任何口播段（不认识它的标题格式）")
    return segs, warns


def read_segments(content: pathlib.Path, source: str) -> tuple[dict[int, str], list[str]]:
    """优先 audio/NN.txt（真正喂 TTS 的），缺失才回退 SCRIPT.md。"""
    audio_dir = content / "audio"
    from_dir: dict[int, str] = {}
    if audio_dir.is_dir():
        for p in sorted(audio_dir.glob("*.txt")):
            if p.stem.isdigit():
                try:
                    from_dir[int(p.stem)] = p.read_text(encoding="utf-8")
                except OSError as exc:
                    return {}, [f"audio/{p.name} 读取失败：{exc}"]
    if source == "script" or (source == "auto" and not from_dir):
        segs, warns = parse_script(content / "SCRIPT.md")
        if segs:
            return segs, warns
        return from_dir, warns + ["已回退 SCRIPT.md 但解析失败"]
    return from_dir, []


# ---------- 时长：实测优先 ----------
def mp3_seconds(path: pathlib.Path, tool: str = "auto") -> float | None:
    """实测单条音频时长。macOS 用 afinfo，其次 ffprobe（含本工程的 wrapper）。失败返回 None。"""
    def _run(cmd: list[str]) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return ""
        return r.stdout if r.returncode == 0 else ""

    if tool in ("auto", "afinfo") and shutil.which("afinfo"):
        out = _run(["afinfo", str(path)])
        m = re.search(r"estimated duration:\s*([0-9.]+)", out)
        if m:
            return float(m.group(1))
        if tool == "afinfo":
            return None
    if tool in ("auto", "ffprobe"):
        exe = shutil.which("ffprobe")
        if not exe:
            wrapper = pathlib.Path(__file__).with_name("hyperframes_ffprobe_wrapper.sh")
            exe = str(wrapper) if wrapper.exists() else None
        if exe:
            out = _run([exe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)])
            m = re.search(r"([0-9]+\.?[0-9]*)", out)
            if m:
                return float(m.group(1))
    return None


def measure_all(content: pathlib.Path, n_segs: int, tool: str) -> dict[int, float]:
    """逐段实测：audio/NN.mp3。有的期只留了部分 wav/mp3，测不到就留给估算。"""
    audio_dir = content / "audio"
    measured: dict[int, float] = {}
    for n in range(1, n_segs + 1):
        for cand in (audio_dir / f"{n:02d}.mp3", audio_dir / f"{n:02d}.wav", audio_dir / f"{n:02d}.m4a"):
            if cand.is_file():
                sec = mp3_seconds(cand, tool)
                if sec and sec > 0:
                    measured[n] = sec
                break
    return measured


# ---------- 报告 ----------
def build_report(segs: dict[int, str], measured: dict[int, float], script_warns: list[str],
                 source: str, a) -> dict:
    order = sorted(segs)
    if not order:
        raise SystemExit("❌ 没有任何口播段：<content-dir>/audio/NN.txt 与 SCRIPT.md 都取不到内容")

    slots = SLOTS.get(len(order))
    slot_guess = slots is not None
    if not slot_guess and getattr(a, "spec", ""):
        # 长视频：段数不在 5/7 表里时，用 spec 的场景键当槽位名（键 = 帧名 = 槽位角色）
        try:
            _d = json.load(open(a.spec))
            _names = []
            for _k in sorted(_d.get("scenes") or {}, key=lambda k: int(re.match(r"^(\d+)", str(k)).group(1))):
                _names.append(str(_k))
            if not _names:
                for _c in (_d.get("chapters") or []):
                    for _k in sorted(_c.get("scenes") or {},
                                     key=lambda k: int(re.match(r"^(\d+)", str(k)).group(1))):
                        _names.append(str(_k))
            if len(_names) == len(order):
                slots = _names
                slot_guess = True
        except (OSError, ValueError, AttributeError, json.JSONDecodeError):
            pass
    rows: list[dict] = []
    for i, n in enumerate(order, start=1):
        text = segs[n]
        chars = nchars(text)
        est = round(chars * a.sec_per_char, 3)
        if n in measured:
            sec, src = measured[n], "实测"
        else:
            sec, src = est, "估算"
        rows.append({"seg": n, "idx": i, "slot": (slots[i - 1] if slots else f"{i:02d}"),
                     "slot_inferred": slot_guess, "chars": chars, "sec": sec, "sec_source": src,
                     "sec_est": est, "preview": re.sub(r"\s+", " ", text).strip()[:24]})

    total = sum(r["sec"] for r in rows)
    est_total = round(sum(r["sec_est"] for r in rows), 3)
    n_measured = sum(1 for r in rows if r["sec_source"] == "实测")
    for r in rows:
        r["share"] = round(100.0 * r["sec"] / total, 2) if total else 0.0
        r["cps"] = round(r["chars"] / r["sec"], 2) if r["sec"] else 0.0

    # ── 规则 1/2/4：逐段 ────────────────────────────────────────────────────
    for r in rows:
        tag = f"{r['slot']}（第 {r['idx']} 段 / {r['chars']} 字 / {r['sec']:.2f}s）"
        if r["sec"] > a.seg_fail:
            add(f"gate.seg_long.{r['seg']}", FAIL,
                f"{tag} 单段 {r['sec']:.2f}s > {a.seg_fail:g}s 硬线：一段吃这么多秒，几乎必然在讲常识或复述画面",
                "单段超长", r["seg"])
        elif r["sec"] > a.seg_warn:
            add(f"gate.seg_long.{r['seg']}", WARN,
                f"{tag} 单段 {r['sec']:.2f}s > {a.seg_warn:g}s：低信息密度风险，检查是否在讲常识",
                "单段过长", r["seg"])
        if r["sec"] < a.seg_short:
            add(f"gate.seg_short.{r['seg']}", WARN,
                f"{tag} 单段 {r['sec']:.2f}s < {a.seg_short:g}s：可能只是过渡句，也可能是没讲清",
                "单段过短", r["seg"])
        if r["share"] > a.share_fail:
            add(f"gate.share.{r['seg']}", FAIL,
                f"{tag} 占全片 {r['share']:.1f}% > {a.share_fail:g}%：单段吃掉四分之一以上，结构失衡",
                "占比失衡", r["seg"])
        elif r["share"] > a.share_warn:
            add(f"gate.share.{r['seg']}", WARN,
                f"{tag} 占全片 {r['share']:.1f}% > {a.share_warn:g}%：与其它段比明显偏重",
                "占比偏重", r["seg"])

    # ── 规则 3：总时长（估算 vs 实测一并给）────────────────────────────────
    if a.min_duration <= total <= a.max_duration:
        add("gate.duration", OK,
            f"总时长 {total:.2f}s 落在档位 {a.min_duration:g}–{a.max_duration:g}s", "总时长档位")
    else:
        side = "超出上限" if total > a.max_duration else "低于下限"
        add("gate.duration", FAIL,
            f"总时长 {total:.2f}s {side}（档位 {a.min_duration:g}–{a.max_duration:g}s）", "总时长档位")

    # ── 规则 5：余量 ──────────────────────────────────────────────────────
    headroom = a.max_duration - total
    if headroom < a.headroom:
        add("gate.headroom", WARN,
            f"距上限只剩 {headroom:.2f}s（< {a.headroom:g}s）：没有重录/微调余量，改一句就可能爆档",
            "收尾余量")
    else:
        add("gate.headroom", OK, f"距上限余量 {headroom:.2f}s", "收尾余量")

    # ── 规则 6（长片专用）：相邻两段的字数差 > --adj-ratio 倍 → ⚠️ 节奏忽快忽慢 ──
    adj_checked = len(rows) >= a.adj_min_segs
    if adj_checked:
        for i in range(len(rows) - 1):
            a1, b1 = rows[i], rows[i + 1]
            if not a1["chars"] or not b1["chars"]:
                continue
            hi, lo = (a1, b1) if a1["chars"] >= b1["chars"] else (b1, a1)
            ratio = hi["chars"] / lo["chars"]
            if ratio > a.adj_ratio:
                add(f"gate.adj_len.{lo['seg']}_{hi['seg']}", WARN,
                    f"相邻两段字数差 {ratio:.2f} 倍（{lo['seg']} {lo['chars']} 字 ↔ "
                    f"{hi['seg']} {hi['chars']} 字 > {a.adj_ratio:g} 倍）：节奏忽快忽慢，"
                    f"听感上会「一段赶、一段拖」——把长的那段拆开，或给短的那段补一句",
                    "相邻段字数失衡", lo["seg"])
        if not any(g["id"].startswith("gate.adj_len") for g in GATES):
            add("gate.adj_len", OK,
                f"{len(rows)} 段相邻字数比全部 ≤ {a.adj_ratio:g} 倍（长片节奏检查）",
                "相邻段字数失衡")

    if n_measured not in (0, len(rows)):
        add("gate.mixed_measure", OK,
            f"{n_measured}/{len(rows)} 段为实测，其余为估算——混用口径，看占比时注意",
            "口径混用")

    fails = [g for g in GATES if g["level"] == FAIL]
    warns = [g for g in GATES if g["level"] == WARN]
    verdict = "FAIL" if fails else "PASS"
    densities = sorted(rows, key=lambda r: r["cps"])
    return {
        "content_dir": str(a.content_dir), "source": source,
        "n_segments": len(rows), "slot_inferred": slot_guess,
        "sec_per_char": a.sec_per_char,
        "duration_s": round(total, 3), "duration_est_s": est_total,
        "n_measured": n_measured,
        "est_error_pct": (round(100.0 * (est_total - total) / total, 2) if n_measured == len(rows) else None),
        "bounds": [a.min_duration, a.max_duration], "headroom_s": round(headroom, 3),
        "segments": rows, "gates": GATES, "verdict": verdict,
        "n_fail": len(fails), "n_warn": len(warns),
        "lower_density_seg": densities[0]["slot"] if rows else None,
        "adj_ratio_limit": a.adj_ratio, "adj_checked": adj_checked,
        "script_warnings": script_warns,
    }


def print_table(rep: dict) -> None:
    print("── 时长分配表 ————————————————————————————————————————————————")
    print(f"{'段':>2}  {'槽位':<12}{'字符':>5} {'时长s':>7} {'占比':>7} {'密度 字/s':>10}  {'来源':<5} 口播开头")
    for r in sorted(rep["segments"], key=lambda x: x["idx"]):
        mark = ""
        for g in rep["gates"]:
            if g.get("seg") == r["seg"] and g["level"] != OK:
                mark = MARK[g["level"]]
                break
        slot = r["slot"] if rep["slot_inferred"] else f"{r['slot']}?"
        print(f"{r['seg']:>2}  {slot:<12}{r['chars']:>5} {r['sec']:>7.2f} {r['share']:>6.1f}% "
              f"{r['cps']:>10.2f}  {r['sec_source']:<5} {r['preview']} {mark}".rstrip())
    print("─" * 78)
    src = {r["sec_source"] for r in rep["segments"]}
    src_txt = "+".join(sorted(src)) if len(src) > 1 else src.pop()
    line = (f"合计 {rep['n_segments']} 段 · {rep['duration_s']:.2f}s（{src_txt}）"
            f" · 档位 {rep['bounds'][0]:g}–{rep['bounds'][1]:g}s · 距上限余量 {rep['headroom_s']:.2f}s")
    print(line)
    if rep["est_error_pct"] is not None:
        print(f"口径对照：全部实测 = {rep['duration_s']:.2f}s；纯估算（{rep['sec_per_char']:g} s/字）= "
              f"{rep['duration_est_s']:.2f}s（估算偏差 {rep['est_error_pct']:+.2f}%）")
    elif rep["n_measured"]:
        print(f"口径对照：纯估算（{rep['sec_per_char']:g} s/字）= {rep['duration_est_s']:.2f}s"
              f"（{rep['n_measured']}/{rep['n_segments']} 段有实测，不与实测混算偏差）")


def print_gates(rep: dict) -> None:
    print("\n── 节奏门禁 ——————————————————————————————————————————————————")
    for g in rep["gates"]:
        print(f"{MARK[g['level']]} [{g['title']}] {g['detail']}")
    lowest = next((r for r in sorted(rep["segments"], key=lambda x: x["cps"])), None)
    print("\n" + "=" * 78)
    verdict = f"[{rep['verdict']}]"
    tail = (f"共 {rep['n_segments']} 段 · 总时长 {rep['duration_s']:.2f}s · "
            f"档位 {rep['bounds'][0]:g}–{rep['bounds'][1]:g}s · 距上限余量 {rep['headroom_s']:.2f}s · "
            f"最低密度 {lowest['slot']} {lowest['cps']:.2f} 字/s")
    if rep["n_fail"]:
        bad = "、".join(g["title"] for g in rep["gates"] if g["level"] == FAIL)
        print(f"结论：{verdict} ❌ {rep['n_fail']} 项 · ⚠️ {rep['n_warn']} 项（{bad}）——先改稿再配音。{tail}")
    elif rep["n_warn"]:
        print(f"结论：{verdict} ⚠️ {rep['n_warn']} 项待看（不阻断，但请人工确认「低信息密度风险」那几条）。{tail}")
    else:
        print(f"结论：{verdict} 无告警，节奏与时长都在档。{tail}")


def print_calibration(content: pathlib.Path, segs: dict[int, str], measured: dict[int, float],
                      sec_per_char: float, tool: str) -> None:
    print(f"── 语速标定 · {content} ————————————————————————————————")
    print(f"缺省常数 --sec-per-char = {sec_per_char:g}（口径：非空白字符数 ÷ NN.mp3 实测时长）")
    if not measured:
        print("本目录没有可实测的 audio/NN.mp3（或 afinfo/ffprobe 都不可用），无法标定。")
        return
    print(f"{'段':>2} {'字符':>5} {'实测s':>8} {'s/字':>8} {'字/s':>8}")
    tot_c = tot_s = 0.0
    for n in sorted(segs):
        if n not in measured:
            continue
        c, s = nchars(segs[n]), measured[n]
        tot_c += c
        tot_s += s
        print(f"{n:>2} {c:>5} {s:>8.3f} {s / c:>8.4f} {c / s:>8.4f}")
    print("─" * 40)
    print(f"合计 {tot_c:.0f} 字 / {tot_s:.3f}s → 本期实测 {tot_s / tot_c:.4f} s/字"
          f"（缺省 {sec_per_char:g}，偏差 {100 * (sec_per_char / (tot_s / tot_c) - 1):+.1f}%）")
    print(f"若本目录估算要贴实测，可加 --sec-per-char {round(tot_s / tot_c, 4)}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="柴主编 · 写稿阶段节奏/密度预检（逐段时长、占比、字符密度）",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("content_dir", help="内容目录，如 content/episode-167-deep")
    ap.add_argument("--sec-per-char", type=float, default=DEF_SEC_PER_CHAR,
                    help=f"每非空白字符秒数（缺省 {DEF_SEC_PER_CHAR}，样本来源见文件头注释/README §7）")
    ap.add_argument("--min-duration", type=float, default=DEF_MIN,
                    help=f"总时长下限秒（缺省 {DEF_MIN:g} = 深度版；日更 5 场景传 25）")
    ap.add_argument("--max-duration", type=float, default=DEF_MAX,
                    help=f"总时长上限秒（缺省 {DEF_MAX:g} = 深度版；日更 5 场景传 45）")
    ap.add_argument("--seg-warn", type=float, default=DEF_SEG_WARN, help=f"单段过长 ⚠️（缺省 {DEF_SEG_WARN:g}s）")
    ap.add_argument("--seg-fail", type=float, default=DEF_SEG_FAIL, help=f"单段过长 ❌（缺省 {DEF_SEG_FAIL:g}s）")
    ap.add_argument("--seg-short", type=float, default=DEF_SEG_SHORT, help=f"单段过短 ⚠️（缺省 {DEF_SEG_SHORT:g}s）")
    ap.add_argument("--share-warn", type=float, default=DEF_SHARE_WARN, help=f"占比失衡 ⚠️（缺省 {DEF_SHARE_WARN:g}%%）")
    ap.add_argument("--share-fail", type=float, default=DEF_SHARE_FAIL, help=f"占比失衡 ❌（缺省 {DEF_SHARE_FAIL:g}%%）")
    ap.add_argument("--headroom", type=float, default=DEF_HEADROOM, help=f"余量不足 ⚠️（缺省 {DEF_HEADROOM:g}s）")
    ap.add_argument("--adj-ratio", type=float, default=DEF_ADJ_RATIO,
                    help=f"相邻两段字数比 > 该值 → ⚠️ 节奏忽快忽慢（缺省 {DEF_ADJ_RATIO:g}）")
    ap.add_argument("--adj-min-segs", type=int, default=DEF_ADJ_MIN_SEGS,
                    help=f"段数 ≥ 该值才做相邻字数检查（缺省 {DEF_ADJ_MIN_SEGS}；短片抖动大易误报）")
    ap.add_argument("--spec", default="", metavar="SPEC.json",
                    help="可选：specs/NNN.json。给了就用它的场景键当槽位名（长视频 20–30 段时"
                         "槽位列会显示 05-case / 06-chapter 这类真名，而不是 01?…24?）")
    ap.add_argument("--audio-source", choices=["auto", "dir", "script"], default="auto",
                    help="口播文本来源：auto（audio/NN.txt 优先，缺则 SCRIPT.md）/ dir / script")
    ap.add_argument("--duration-tool", choices=["auto", "afinfo", "ffprobe"], default="auto",
                    help="实测工具（缺省 auto：afinfo 优先，失败回退 ffprobe）")
    ap.add_argument("--json", dest="json_out", metavar="PATH", help="把完整报告写成 JSON")
    ap.add_argument("--show-calibration", action="store_true", help="打印本目录逐段实测语速标定")
    a = ap.parse_args()

    if a.min_duration > a.max_duration:
        raise SystemExit(f"❌ --min-duration {a.min_duration:g} 大于 --max-duration {a.max_duration:g}")
    if a.seg_warn > a.seg_fail:
        raise SystemExit(f"❌ --seg-warn {a.seg_warn:g} 大于 --seg-fail {a.seg_fail:g}")
    if a.share_warn > a.share_fail:
        raise SystemExit(f"❌ --share-warn {a.share_warn:g} 大于 --share-fail {a.share_fail:g}")
    if a.sec_per_char <= 0:
        raise SystemExit("❌ --sec-per-char 必须为正数")

    content = pathlib.Path(a.content_dir).expanduser()
    a.content_dir = content
    if not content.is_dir():
        raise SystemExit(f"❌ 内容目录不存在：{content}")

    segs, warns = read_segments(content, a.audio_source)
    if not segs:
        for w in warns:
            print(f"❌ {w}")
        print(f"❌ 取不到口播段：{content}/audio/NN.txt 与 {content}/SCRIPT.md 都没有可用内容")
        return 2
    source = a.audio_source if a.audio_source != "auto" else ("audio/NN.txt" if (content / "audio").is_dir() else "SCRIPT.md")
    measured = measure_all(content, max(segs), a.duration_tool)

    if a.show_calibration:
        print_calibration(content, segs, measured, a.sec_per_char, a.duration_tool)
        print()

    header = (f"节奏预检 · {content}" + (f"（{source}）" if source else "")
              + f" · {len(segs)} 段"
              + ("" if (len(segs) in SLOTS or (a.spec and len(segs) >= 8))
                 else "（非 5/7 段：槽位只按序号打印，可加 --spec 显示真名）"))
    print(header)
    print(f"阈值：单段 >{a.seg_warn:g}s ⚠️ / >{a.seg_fail:g}s ❌ · <{a.seg_short:g}s ⚠️ · "
          f"占比 >{a.share_warn:g}% ⚠️ / >{a.share_fail:g}% ❌ · 余量 <{a.headroom:g}s ⚠️ · "
          f"档位 {a.min_duration:g}–{a.max_duration:g}s"
          + (f" · 相邻段字数差 >{a.adj_ratio:g} 倍 ⚠️（≥{a.adj_min_segs} 段才查）\n" if len(segs) >= a.adj_min_segs else "\n"))

    rep = build_report(segs, measured, warns, source, a)
    print_table(rep)
    print_gates(rep)
    for w in warns:
        print(f"⚠️ {w}")
    if not rep["slot_inferred"]:
        print(f"ℹ️ 段数 {rep['n_segments']} 不在槽位表内（5/7），本报告只按序号 01…{rep['n_segments']:02d} 输出"
              f"（长视频可加 --spec specs/NNN.json 显示 05-case 这类真名）")

    if a.json_out:
        out = pathlib.Path(a.json_out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(f"📄 JSON 报告已写出：{out}")

    return 1 if rep["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
