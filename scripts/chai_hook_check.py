#!/usr/bin/env python3
"""柴主编 · 首帧契约门禁（每期必过，常驻标准）

用途：把「前 2 秒达标 + 精选四维」从文档变成可执行门禁。在 TTS/时间轴之后、
渲染之前跑；有 ❌ 就别往下渲。

用法：
  python3 scripts/chai_hook_check.py --project videos/<slug> [--script content/episode-NNN/SCRIPT.md]
                                     [--spec specs/NNN.json] [--json out.json]
                                     [--min-duration 25] [--max-duration 45]

时长档位（2026-09-11 起可配置；缺省仍是日更 5 场景的 25–45s，行为不变）：
  日更 5 场景：默认即可
  深度版 7 场景（60–90s）：--min-duration 60 --max-duration 90

退出码：0 = 无 ❌；1 = 有 ❌（可作为流水线门禁）；2 = 输入缺失
只用标准库。
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

FAIL, WARN, OK = "FAIL", "WARN", "OK"
CHECKS: list[dict] = []


def add(cid: str, level: str, detail: str, title: str) -> None:
    CHECKS.append({"id": cid, "level": level, "title": title, "detail": detail})


# ---------- 规则表 ----------
BANNED_OPENERS = ["大家好", "各位好", "今天", "最近", "我是柴主编", "我是", "很多人在问",
                  "你还在", "相信很多人", "很多人不知道", "hello", "哈喽"]
BANNED_VISUAL = ["logo 入场", "四角准星入场", "中心柔光渐显", "皮肤转场（人工确认）",
                 "BGM 前奏只出音乐（人工确认）"]
NUM_RE = re.compile(r"[0-9０-９]|[一二三四五六七八九十百千万亿两]")
# 封面=首帧的关键词口径（2026-09-11 增补）：NUM_RE 认不出不带数词前缀的分数/份额词
# （EP.160「省一半」的「半」、「四分之一」），这类词同样是"数字型承诺"，应计入共同关键词。
KEYWORD_RE = re.compile(r"一半|四分之一|八分之一|腰斩|翻倍|减半|免费|省|降|涨|跌破")
# 严格数字信号：数字，或「数词+量词」，或万/千/百/亿 —— 避免"一起""一下"这类假阳性
# 严格数字信号：阿拉伯数字；或「数词+量词」（量词表已扩到种/道/类/项/套/组/批/轮/步/处…）；
# 或「数词+十百千万亿」与「十百千万亿+数词」构成的多位数（六十、两千五百、十六），避免"一起/一下"这类假阳性。
# 2026-09-11 补量词「遍/趟/回/番/遭/圈」：EP.165「口头交代十遍」的「十遍」原被漏判为无数字信号。
NUMERIC_RE = re.compile(
    r"[0-9０-９]"
    r"|[一二三四五六七八九十两](?=[个倍元块张%％天日年月小时分钟秒万人条次种道类项套组批轮步处位名层份篇章节款台件颗枚遍趟回番遭圈])"
    r"|[一二三四五六七八九][十百千万亿]"
    r"|[十百千万亿][一二三四五六七八九]"
    r"|[万千百亿]")
HOOK_RE = re.compile(r"比|省|免费|快|倍|%|％|块|元|小时|分钟|天|工资|成本|坑|错|别|第二|还有|反而|其实|却|但")
TURN_RE = re.compile(r"但|却|其实|反而|然而|不过|第二|第三|还有|三处|真相|坑|注意|别买|别急|并不是|不是")

BENEFIT_RE = re.compile(r"[0-9０-９]+\s*(?:%|％|倍|折|元|块|万|亿|GB|MB|TB|G|M|token|tokens|秒|分钟|小时|天|卡|张|条|次|个)"
                        r"|免费|白嫖|白领|省下|省了|便宜|只要|不到|低于|高于|起步价", re.I)
VERSION_RE = re.compile(r"\d+\.\d+|\b\d+\s*[BbKkMmGgTt]\b")


def strength(text: str) -> tuple[str, str]:
    """判断一句钩子文字的"信息强度"：strong=带利益数字/利益词；weak=只有型号/版本号；none=都没有。"""
    if BENEFIT_RE.search(text):
        return "strong", "利益数字/利益词"
    if VERSION_RE.search(text) and NUMERIC_RE.search(text):
        return "weak", "只有型号/版本号（如 3.0 / 4B），不是利益数字"
    if NUMERIC_RE.search(text):
        return "strong", "数字"
    if HOOK_RE.search(text):
        return "strong", "利益/对比词"
    return "none", "没有数字也没有利益词"

VERSION_TOKEN = re.compile(r"[A-Za-z0-9]+(?:\.[0-9A-Za-z]+)+")  # Ling-3.0 / 3.5 / v2.1 —— 小数点不是标点问题
PUNCT_RE = re.compile(r"[，。！？；：、,\.!\?;:]")


def punct_offenders(text: str) -> bool:
    """字幕标点检查：型号/版本号里的小数点不算标点（EP.154「Ling-3.0-flash-VL」曾误判）。"""
    return bool(PUNCT_RE.search(VERSION_TOKEN.sub(lambda m: m.group(0).replace(".", ""), text)))


def read_text(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def script_line1(script: str) -> str:
    """第一句口播。三种写法都认（顺序敏感，先判旧的以保零回归）：
       ① `## Line 1 …` + 缩进口播（日更 165–167）
       ② `## Scene 01 …` + 缩进口播（深度版 / 长片 167D–169）
       ③ **长片按章写稿**（EP.170 起）：`## 第一章｜…（001–006）` + 块内每场一行 `01.txt：…`
          —— 此时「第一句」是块内**第一个 `NN.txt：` 行**，且要剥掉 `NN.txt：` 前缀
          （原实现的两条规则在 ③ 上会落到「正文里的第一个缩进行」，
           返回 `01.txt：官方文档…` 这种带前缀的串，把「前 12 字是铺垫」判歪）。
    """
    m = re.search(r"##\s*Line\s*1[^\n]*\n+(?:\s{2,}|\t)(.+)", script)
    if m:
        return m.group(1).strip()
    # ③ 只在**没有**「## Line N」/「## Scene NN」标题时才用 —— 167D/168/169 也有
    #    `01.txt：` 行，但它们走 ①②，必须在那边逐字保持（否则 167D 的
    #    「第一句（数字）」会退化成「没有数字也没有利益词」）。
    if not re.search(r"##\s*(?:Line|Scene|段)", script):
        m = re.search(r"^[ \t]*(\d{1,2}\.txt\s*[：:].*)$", script, re.M)
        if m:
            return re.sub(r"^\d{1,2}(?:\.txt)?\s*[：:]\s*", "", m.group(1).strip())
    # 退化：取第一个缩进段
    m = re.search(r"^\s{2,}(\S.+)$", script, re.M)
    return m.group(1).strip() if m else ""


def load_spec(spec_path: pathlib.Path | None, proj: pathlib.Path, eps: str | None,
              root: pathlib.Path) -> tuple[dict | None, str]:
    """按 ①显式路径 ②spec.proj 与工程路径匹配 ③期号 依次查找 spec。"""
    if spec_path:
        return (json.loads(read_text(spec_path)), str(spec_path)) if spec_path.exists() else (None, str(spec_path))
    try:
        want = str(proj.relative_to(root))
    except ValueError:
        want = proj.name
    cands = []
    for f in sorted((root / "specs").glob("*.json")):
        try:
            d = json.loads(read_text(f))
        except Exception:
            continue
        cands.append((f, d))
    for f, d in cands:                                   # ② 按 proj 字段
        if str(d.get("proj", "")).rstrip("/") == want.rstrip("/"):
            return d, str(f)
    for f, d in cands:                                   # ③ 按期号
        if eps and str(d.get("ep")) == str(eps):
            return d, str(f)
    return None, "（未找到，可用 --spec 指定）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="videos/<slug> 工程目录")
    ap.add_argument("--script", help="content/episode-NNN/SCRIPT.md")
    ap.add_argument("--spec", help="specs/NNN.json（省略则按 ep 自动匹配）")
    ap.add_argument("--json", help="把报告写到这个路径")
    ap.add_argument("--target-fade", type=float, default=0.30,
                    help="首屏文字出现时间上限（秒，默认 0.30）")
    ap.add_argument("--min-duration", type=float, default=25.0,
                    help="成片时长档位下限（秒，默认 25 = 日更 5 场景；深度版可传 60）")
    ap.add_argument("--max-duration", type=float, default=45.0,
                    help="成片时长档位上限（秒，默认 45 = 日更 5 场景；深度版可传 90）")
    a = ap.parse_args()
    if a.min_duration > a.max_duration:
        raise SystemExit(f"--min-duration {a.min_duration} 大于 --max-duration {a.max_duration}")

    proj = pathlib.Path(a.project).resolve()
    root = proj.parent.parent if proj.parent.name == "videos" else proj.parent
    miss = []
    caps_p = proj / "caption_groups.json"
    if not caps_p.exists():
        miss.append(str(caps_p))
    caps = json.loads(read_text(caps_p)) if caps_p.exists() else {}
    groups = caps.get("groups", [])
    dur = caps.get("total_duration_s") or (groups[-1]["end"] if groups else 0)

    # 先定 spec（按 proj 字段反查，不依赖期号），再据此定期号与 SCRIPT.md
    spec, spec_p = load_spec(pathlib.Path(a.spec) if a.spec else None, proj, None, root)
    eps = str(spec.get("ep")) if spec and spec.get("ep") else None

    script_p = pathlib.Path(a.script).resolve() if a.script else None
    if script_p is None and eps:
        # 期号目录名不一定等于 spec 的 ep 字段（EP.167D 的 ep="167D"，目录却是
        # `episode-167-deep`）——所以按 `episode-{eps}` → `episode-{eps}-*` 依次找。
        # ⚠️ 2026-09-12 修：原实现只找 `episode-{eps}`，找不到就**静默**退到「最大期号目录」，
        #    于是 EP.167D 一直在读 **EP.170 的 SCRIPT.md** 做「第一句」判定（误导性结果）。
        #    注意 `episode-{eps}-*` 必须带连字符，避免 ep="167" 命中 `episode-167D`。
        content_dir = root / "content"
        exact = content_dir / f"episode-{eps}" / "SCRIPT.md"
        if exact.exists():
            script_p = exact
        else:
            # 第三种写法：ep 带字母后缀（"167D"）而目录用中文语义名（`episode-167-deep`）。
            # 先用 episode-{eps}-*（严格带连字符），再用「数字前缀 + 更长名字」，
            # 最后才回退到纯数字目录名本身。
            near = sorted(d for d in content_dir.glob(f"episode-{eps}-*")
                          if (d / "SCRIPT.md").exists())
            base = (re.match(r"^(\d+)", str(eps)) or [None, None])[1] if eps else None
            if not near and base:
                near = sorted(
                    (d for d in content_dir.glob(f"episode-{base}*")
                     if (d / "SCRIPT.md").exists() and d.name != f"episode-{base}"),
                    key=lambda d: len(d.name))
            if not near and base:
                plain = content_dir / f"episode-{base}" / "SCRIPT.md"
                if plain.exists():
                    near = [plain.parent]
            if near:
                script_p = near[0] / "SCRIPT.md"
    if script_p is None:                      # 兜底：只在 episode-<数字> 目录里挑最大期号，
        cands = [(int(m.group(1)), d) for d in (root / "content").glob("episode-*")
                 if (m := re.fullmatch(r"episode-(\d{1,3})", d.name)) and (d / "SCRIPT.md").exists()]
        if cands:
            script_p = max(cands)[1] / "SCRIPT.md"
            # 兜底必须**说出来**：否则「读错期的脚本」会静默变成一次错误的 PASS。
            print(f"  ⚠️  没找到本期 SCRIPT.md（试过 episode-{eps} / episode-{eps}-*），"
                  f"已退回 {script_p.parent.name}——请用 --script 指定本期脚本，"
                  f"否则「第一句」判定的是别人的稿子。")
    if not script_p or not script_p.exists():
        miss.append("SCRIPT.md（用 --script 指定）")
    script = read_text(script_p) if script_p and script_p.exists() else ""
    if spec is None:
        miss.append("specs/NNN.json（用 --spec 指定）")

    # ---- 1. 首帧契约：结论字存在 ----
    # 场景键兼容两种写法：既有各期写 "01"，深度版写 "01-hook"（槽位序号在前），都取 01 槽。
    # ⚠️ 2026-09-12 修：长片 spec 顶层**没有 scenes、只有 chapters**（章内的键仍是全局槽位号），
    #    原实现只读 scenes → 拿到空字典 → 把「01 槽没有 hero* 大字」误报成 ❌。
    #    EP.170 实测：`specs/170.json` 顶层键 = [ep, proj, line_breaks, chapter_progress,
    #    cover, chapters]，本门禁对同一份 spec 报 FAIL，而生成器/预检/节奏脚本都能读。
    #    口径与 gen_chai_frames._flat_scenes / gen_chai_index.scenes_from_spec /
    #    chai_layout_precheck 的摊平**逐字一致**：无 scenes 时按章顺序展平 chapters；
    #    两者都给时以 scenes 为准（不覆盖、不合并，避免静默改口径）。
    _scenes = (spec or {}).get("scenes", {}) or {}
    if not _scenes:
        _ch = (spec or {}).get("chapters") or []
        for _c in _ch:
            if not isinstance(_c, dict):
                add("hook.spec_shape", FAIL,
                    f"spec 的 chapters 里有非对象项（{type(_c).__name__}）→ 读不到场景", "spec 形态")
                continue
            _scenes.update(_c.get("scenes") or {})
        if _ch:
            add("hook.spec_shape", OK,
                f"长片章节形态：{len(_ch)} 章 / 展平后 {len(_scenes)} 场"
                f"（顶层无 scenes，按章顺序取 chapters[].scenes）", "spec 形态")
    _k01 = next((k for k in _scenes
                 if str(k) == "01" or re.match(r"^01\D", str(k))), "01")
    scene01 = _scenes.get(_k01, {})
    # 2026-09-12（EP.171）：只把**字符串**的 hero* 字段当「大字」。`hero_fs`（可选字号覆盖，
    # 见 gen_chai_frames.py `_emit_hook`）是数字，旧写法 `str(v)` 会把它当文字拼进去
    # （实测拼出「官方让你迁到的东西，自己也在关停名单上84」，还因此误判成「有数字」）。
    # 既有各期 spec 的 hero* 全是字符串 → 本改动对它们逐字无影响。
    hero = {k: v for k, v in scene01.items()
            if k.startswith("hero") and isinstance(v, str) and v.strip()}
    hero_txt = "".join(hero.values())
    if not hero:
        add("hook.first_frame_text", FAIL, "spec 场景 01 没有任何 hero* 大字 → 首帧没有结论字", "首帧结论字")
    else:
        st, why = strength(hero_txt)
        if st == "strong":
            add("hook.first_frame_text", OK, f"首帧大字「{hero_txt}」（{why}）", "首帧结论字")
        else:
            add("hook.first_frame_text", WARN, f"首帧大字「{hero_txt}」{why}", "首帧结论字")

    # ---- 2. 首屏 0.3s 内出字 ----
    if groups:
        t0 = groups[0]["start"]
        lvl = OK if t0 <= a.target_fade else WARN
        add("hook.first_cue", lvl, f"首条字幕 {t0:.2f}s 出现（上限 {a.target_fade}s）", "首屏 0.3s 出字")
    else:
        add("hook.first_cue", FAIL, "caption_groups.json 没有 groups", "首屏 0.3s 出字")

    # ---- 3. 口播第一句：黑名单 + 信息量 ----
    line1 = script_line1(script)
    if not line1:
        add("hook.line1_text", FAIL, f"没能从 {script_p} 解析出 Line 1（格式需为「## Line 1 …」+ 缩进口播）", "第一句无铺垫")
    else:
        head = line1[:6]
        hit = [b for b in BANNED_OPENERS if head.startswith(b)]
        if hit:
            add("hook.line1_text", FAIL, f"第一句以「{hit[0]}」开头：{line1[:24]}…", "第一句无铺垫")
        else:
            st, why = strength(line1)
            if st == "strong":
                add("hook.line1_text", OK, f"第一句（{why}）：{line1[:32]}", "第一句无铺垫")
            elif st == "none":
                add("hook.line1_text", WARN, f"第一句{why}：{line1[:28]}…", "第一句无铺垫")
            else:
                add("hook.line1_text", WARN, f"第一句{why}：{line1[:28]}…", "第一句无铺垫")
        # 利益点位置：前 12 字内必须已出现数字/利益/对比信号（"第一个词就要有信息量"）
        if line1 and not hit:
            head12 = line1[:12]
            if not (BENEFIT_RE.search(head12) or NUMERIC_RE.search(head12) or HOOK_RE.search(head12)):
                add("hook.line1_lead", WARN,
                    f"前 12 字是铺垫（「{head12}」），利益点太靠后", "第一句前置利益点")

    # ---- 4. 2–5s 第二钩子 ----
    win = [g for g in groups if g["end"] > 2.0 and g["start"] < 5.0]
    win_txt = "".join(g.get("text", "") for g in win)
    if not win:
        add("hook.second_hook", WARN, "2–5s 窗口内没有字幕", "2–5s 第二钩子")
    elif NUMERIC_RE.search(win_txt) or TURN_RE.search(win_txt):
        add("hook.second_hook", OK, f"2–5s 内容：「{win_txt}」", "2–5s 第二钩子")
    else:
        add("hook.second_hook", WARN, f"2–5s 没有数字/反转/清单信号：「{win_txt}」", "2–5s 第二钩子")

    # ---- 5. 封面 = 首帧（关键词重合，软检查）----
    cover = (spec or {}).get("cover", {})
    cover_txt = "".join(str(cover.get(k, "")) for k in ("hero_l1", "hero_pre", "hero_em", "hero_tail"))
    if cover_txt and hero_txt:
        cv = set(NUM_RE.findall(cover_txt)) | set(KEYWORD_RE.findall(cover_txt))
        hv = set(NUM_RE.findall(hero_txt)) | set(KEYWORD_RE.findall(hero_txt))
        shared = cv & hv
        digits = shared & set(NUM_RE.findall(cover_txt))
        if digits:
            add("hook.cover_match", OK, f"封面与首帧共有数字：{''.join(sorted(digits))}", "封面=首帧")
        elif shared:
            add("hook.cover_match", OK, f"封面与首帧共有关键词：{'、'.join(sorted(shared))}", "封面=首帧")
        else:
            add("hook.cover_match", WARN,
                f"封面「{cover_txt}」与首帧「{hero_txt}」没有共同数字/关键词", "封面=首帧")
    else:
        add("hook.cover_match", WARN, "封面或首帧文字缺失，无法比对", "封面=首帧")

    # ---- 6. 字幕去标点（skill 硬规则）----
    bad = [g["text"] for g in groups if punct_offenders(g.get("text", ""))]
    if bad:
        add("gate.caption_punct", FAIL, f"{len(bad)} 组字幕含标点，例如「{bad[0]}」", "字幕去标点")
    else:
        add("gate.caption_punct", OK, f"{len(groups)} 组字幕均无标点", "字幕去标点")

    # ---- 7. 时长档位（默认 25–45s = 日更 5 场景；深度版用 --min-duration/--max-duration）----
    lvl = OK if a.min_duration <= dur <= a.max_duration else WARN
    add("gate.duration", lvl,
        f"成片时长 {dur:.2f}s（档位 {a.min_duration:g}–{a.max_duration:g}s）", "时长档位")

    # ---- 8. 人工确认项（无法静态检查）----
    add("manual.visual_blacklist", WARN,
        "人工确认前 2 秒无：" + "、".join(BANNED_VISUAL), "前 2 秒画面黑名单")

    fails = [c for c in CHECKS if c["level"] == FAIL]
    warns = [c for c in CHECKS if c["level"] == WARN]
    icon = {OK: "✅", WARN: "⚠️ ", FAIL: "❌"}
    print(f"首帧契约门禁 · {proj.name}")
    print(f"  字幕 {len(groups)} 组 / 时长 {dur:.2f}s / spec {spec_p}")
    for c in CHECKS:
        print(f"  {icon[c['level']]} [{c['title']}] {c['detail']}")
    verdict = "PASS" if not fails else "FAIL"
    print(f"\n结论：{verdict}（❌ {len(fails)} · ⚠️ {len(warns)}）")
    if miss:
        print("缺输入：" + "；".join(miss))
    report = {"project": str(proj), "duration_s": dur, "verdict": verdict,
              "fails": len(fails), "warns": len(warns), "checks": CHECKS, "missing": miss}
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"[written] {a.json}")
    if miss and not groups:
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
