#!/usr/bin/env python3
"""柴主编 · 版面宽度前置检查（渲染前跑，拦住"文案超宽折行"这一类返工）

为什么需要：EP.160/162/164 都因文案超宽返工过（封面主标题折 3 行带孤字、字幕孤字折行、
节点卡 "Qwen3-VL-4B" 断词、仓库名被 flex 压成两行）。这些**在 spec 阶段就能算出来**，
不用等渲染后靠 OCR 发现。

用法：
  python3 scripts/chai_layout_precheck.py specs/165.json [--strict]
退出码：0 = 无风险；1 = 有超宽风险（渲染前应改文案或折行）。
只用标准库。宽度常量取自 design-system 与生成器实测值，若模板改了请同步本表。
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

# ── 版面预算（单位 px；来源：gen_chai_frames.py 的 CSS + 评审实测）────────────────
# 中文按 1.0em、拉丁/数字按 0.65em 估宽
# ⚠️ 2026-09-11 校准：原用 0.58em，被 EP.166 独立评审像素实测证伪——`HTTPS_PROXY`
#    (26px) 实测墨迹 183px，旧系数只算 165.9px，**偏低 10–14%**，导致"绿灯"其实只剩
#    4px 内边距仍放行。现改用 0.63em（对评审像素实测值 183/168/138px 拟合，误差 ±2%），并新增 NEAR 阈值：占用 > 90% 预算即
#    报 ⚠️「接近超宽」，别等真溢出才发现。
LATIN = 0.66
NEAR_RATIO = 0.90
BUDGETS = {
    # key          可用宽  字号   说明
    "fnode_t":   (191, 26, "场景 03 节点卡主文案（.fnode .t，flow3 内被 flex 压到 ~191px；已 nowrap 无回退）"),
    "fnode_s":   (191, 19, "场景 03 节点卡副文案（.fnode .s）"),
    "repo_big":  (9999, 46, "场景 02 仓库名（#f2-repo .big，已 flex:0 0 auto 不收缩）"),
    "lb_s":      (496, 22, "场景 02 右栏副文案（.lb .s，860-108-216-40）"),
    "lb_t":      (528, 32, "场景 02 右栏主文案（.lb .t，32px；EP.167 评审指出旧表未建模）"),
    "card_s":    (760, 20, "卡片底部小字（.card_s / note 类，20px）"),
    "card_t":    (601, 36, "场景 01 卡片主文案（.card_t 实为 36px；旧表误用 card_s 的 20px 预算，EP.167 评审指出）"),
    "cover_916": (720, 74, "封面 9:16 主标题行（卡内可用 720px，font 由 spec 决定）"),
    # ── 深度版 06/07（2026-09-11 新增）────────────────────────────────────────
    "cfg_hero":  (860, 30, "场景 06 顶部小标题（#f6-hero，860px 整行，30px）"),
    "cfg_row":   (744, 22, "场景 06 单行上界（.pad .mono：860 内容宽 − 34×2 内边距 − 计数器列 38 − 间距 18×2；"
                           "字号由生成器在 22→19px 间自适，这里按最大 22px 判超宽）"),
    "vfy_head":  (772, 38, "场景 07 卡头标题（#f7-card .hd .h，860 − 44×2 内边距；38px）"),
    "vfy_sub":   (772, 23, "场景 07 卡头副标题（#f7-card .hd .sub，等宽 23px）"),
    "vfy_t":     (686, 38, "场景 07 步骤主文案（#f7-card .ck .tx .t：860 − 44×2 − 90 导轨缩进；38px）"),
    "vfy_s":     (686, 22, "场景 07 步骤说明（#f7-card .ck .tx .s，22px，可折行，只提醒）"),
}
CAPTION = (542, 56, "字幕带单行（约 10 个中文字；≥11 字须在 line_breaks 里折行）")

# ── 既有大标题行（01 首帧 / 末场判词）：**不是新模板，但长视频里最容易翻车** ─────────
# `#f1-hero`（118px）/ `#f5-hero`（110px）都**没有 max-width、也不换行**：文本比内容区宽
# 就直接溢出画布（实测 2026-09-12：合成用例的首帧 970px 盒里放了 1051px 的一行，
# 右边缘到 x1080 = 贴到画布边）。老路径同理，只是 EP.165 那类的字短、恰好塞得下。
# 这里给出「一行必须放下」的预算（与既有口径一致：标题一行），超了就报 ❌。
# 注意：**模板本身一个字没改**（改 CSS 会破坏老路径的逐字节零回归），
# 超长文案请写短，或按模板既有的两行结构自己断行。
_LC2 = {
    "hero01_1": (860, 118, "场景 01 首帧第 1 行（#f1-hero .line，118px，不换行 → 必须一行放下）"),
    "hero01_2": (860, 118, "场景 01 首帧第 2 行（#f1-hero .line.em，118px，不换行）"),
    "hero05_1": (860, 110, "末场判词第 1 行（#f5-hero .line，110px，不换行）"),
    "hero05_2": (860, 110, "末场判词第 2 行（hero_l2_pre + hero_l2_em + hero_l2_tail，110px）"),
}

# ── 长视频 5 个新模板的预算（2026-09-12；与 gen_chai_frames.py 的 _build_* 同源）────────
# 单位 px，内容宽 860（1080 − 110×2）。所有新模板**都不用 white-space:nowrap**，
# 所以这里的口径是「允许折几行、单行放不下就报」而不是「一行必须放下」。
LONG_W = 860

# ── 长视频模板的几何：**直接调用共享模块** scripts/chai_long_form.py ────────────
# 生成期（gen_chai_frames.py）用的是同一批函数，所以预检的结论必然是生成期的结论
# （此前的坑：预检把章节页标题可用宽写成 268px 序号那版的 458px，而生成器已经用 224px
#  序号 → 可用 563px，于是预检报了 3 处早就修好的「接近超宽」）。
def _load_long_form():
    import importlib.util as _ilu
    _p = pathlib.Path(__file__).with_name("chai_long_form.py")
    _spec = _ilu.spec_from_file_location("chai_long_form", str(_p))
    _m = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    return _m


LF = _load_long_form()
_LC = {
    "ch_title": (LONG_W * 0.30, 60, "长视频·章节页标题（#ch-title .tx）：章节序号占左列，"
                                    "剩余宽度按 60px 起逐档降到 40px；允许折 2 行"),
    "ch_step":  (LONG_W - 52 - 46 - 20, 30, "长视频·章节页预览行（#ch-steps .stp .tx）："
                                            "860 − 内边距 26×2 − 序号列 46 − 间距 20；30px，只允许 1 行"),
    "quote_q":  (LONG_W - 52 * 2, 68, "长视频·引用页引文（#qt-card .q）：860 − 内边距 52×2；"
                                      "68px 起逐档降到 36px，允许折 2–6 行"),
    "quote_src": (LONG_W - 52 * 2 - 40, 22, "长视频·引用页来源角标（#qt-tail .src）：等宽 22px"),
    "tbl_k":    (LONG_W * 0.18 - 44 - 3, 26, "长视频·对照表行名列（.tb-c.k）：内容宽 18% − 内边距；"
                                              "26px 起降到 20px，允许折 2 行"),
    "tbl_v":    (LONG_W * 0.82 - 44 - 3, 28, "长视频·对照表数值列（.tb-c.v）：内容宽 82% − 内边距；"
                                              "28px 起降到 20px，允许折 2 行"),
    "flow_t":   (172, 24, "长视频·流程步骤标题（#fl-axis .lb .t）：每步列宽 860/5 = 172px；"
                          "24px 起降到 18px，允许折 2 行"),
    "flow_s":   (172, 17, "长视频·流程步骤说明（#fl-axis .lb .s）：172px；17px 起降到 15px，允许折 2 行"),
    "case_t":   (LONG_W - 96 - 72, 32, "长视频·案例段正文（#cs-chain .nd .tx）：860 − 竖轨缩进 96 − "
                                       "内边距 36×2；32px 起降到 24px，允许折 2 行"),
    "case_hd":  (LONG_W - 96 - 72, 25, "长视频·案例段标签（#cs-chain .nd .hd）：同正文列宽；25px，1 行"),
}
LONG_BUDGETS = {k: (round(v[0]), v[1], v[2]) for k, v in _LC.items()}


def wrap_count(text: str, font: int, max_w: float) -> int:
    """按 width_px 模型估算**折行数**（与 gen_chai_frames._wrap_est 同一口径）。

    这是保守估算：宁可多算一行，也不要把「其实放不下」判成放得下。
    """
    lines, cur = 0, ""
    for ch in str(text):
        cand = cur + ch
        if cur and width_px(cand, font) > max_w:
            lines += 1
            cur = ch
        else:
            cur = cand
    return lines + (1 if cur else 0)


def width_px(text: str, font: int) -> float:
    """按字符类估宽（em）。**这是渲染前哨，不是像素级还原**：与 EP.166/167 独立评审的
    墨迹实测相比误差约 ±10%（等宽字体 + 中英混排 + letter-spacing 使精确建模不划算）。
    因此：❌ 红色请对照渲染帧复核，⚠️ 黄色（>90% 预算）请人工确认。"""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += font * 0.33          # 空格
        elif ch in "·．":
            w += font * 0.55          # 中点等窄标点
        elif re.match(r"[A-Za-z0-9\.\-\+/%_]", ch):
            w += font * LATIN         # 等宽字母数字（CobaltMono 单字宽）
        else:
            w += font * 1.0           # 中日韩全角
    return w


def check(text: str, key: str, label: str, out: list, near: list | None = None) -> None:
    if not text:
        return
    avail, font, _ = BUDGETS[key]
    w = width_px(text, font)
    if w > avail:
        out.append((key, label, text, round(w), avail, font))
    elif near is not None and w > avail * NEAR_RATIO:
        near.append((key, label, text, round(w), avail, font))


def gen_budgets(sc06: dict | None = None, sc07: dict | None = None) -> dict:
    """按 06/07 场景里实际出现的字符，算出与 gen_chai_frames.py 一致的行内预算。

    为什么必须动态算：`.pad .row` 是 flex 行，计数器列/注释列宽度取决于 spec 内容，
    固定常量会给出错误的绿灯。锚点：生成器用 chai_layout_precheck.width_px 同一模型
    选字号，这里再用同一模型反算可用宽 ⇒ 预检结论与生成期断言一致。
    """
    B = {}
    if sc06:
        lines = sc06.get("lines") or []
        if lines:
            ind_max = max(int(l.get("i", 0) or 0) for l in lines)
            numbers = [f"{k + 1:02d}" for k in range(max(len(lines), 6))]
            ct_w = max(width_px(n, 20) for n in numbers)
            tg_w = max((width_px(str(l.get("c", "")), 20) for l in lines if l.get("c")), default=0.0)
            base = 860 - 68 - 38 - 36
            B["cfg_row"] = (round(base - ct_w - tg_w), 22,
                            f"场景 06 单行（.pad .mono：860 − 34×2 内边距 − 计数器列 {ct_w:.0f}px − 间距 36 − "
                            f"注释列 {tg_w:.0f}px；缩进 {ind_max} 级另算；字号由生成器自适 22→19px）")
    if sc07:
        cks = sc07.get("checks") or []
        if cks:
            chips = [width_px(str(c.get("tag", "")), 19) for c in cks if c.get("tag")]
            body = 860 - 88 - 90 - 40 - (28 + 16 if chips else 0)
            if chips:
                body = min(body, 860 - 88 - 90 - 40 - max(chips) - 28 - 16)
            B["vfy_t"] = (round(body), 38, f"场景 07 步骤主文案（.ck .tx .t：860 − 44×2 内边距 − 90 导轨缩进"
                                           f"{' − 小标签列 %.0fpx' % max(chips) if chips else ''}；38px，可折行）")
            B["vfy_s"] = (round(body), 22, "场景 07 步骤说明（.ck .tx .s，22px，正常折行，只作提醒）")
    return B


def build_pad_column_plan(sc06: dict | None) -> list:
    """复刻 gen_chai_frames._config_geom 的列预算，逐行给出「实际占用 / 可用宽」。"""
    out = []
    if not sc06:
        return out
    lines = sc06.get("lines") or []
    if not lines:
        return out
    ind_max = max(int(l.get("i", 0) or 0) for l in lines)
    cs = max((width_px(str(l.get("c", "")), 20) for l in lines), default=0.0)
    col_c = round(cs) + 12 if cs else 0
    base = 860 - 68 - 38 - 36 - col_c
    fsz = None
    for f in (22, 21, 20, 19):
        if all(width_px(str(l.get("t", "")), f) <= base - 11.5 * ind_max for l in lines):
            fsz = f
            break
    fsz = fsz or 19
    for k, l in enumerate(lines, 1):
        ind = 11.5 * int(l.get("i", 0) or 0)
        cw = width_px(str(l.get("c", "")), 20)
        out.append((k, str(l.get("t", "")), ind, _w(str(l.get("t", "")), fsz), cw,
                    bool(l.get("hl")), fsz))
    return out


def _w(t: str, f: int) -> float:
    return width_px(t, f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--strict", action="store_true",
                    help="把「既有大标题行（01 首帧 / 末场判词）」的一行预算也算作 ❌。"
                         "缺省只报 ⚠️ 不翻退出码 —— 这条检查是长视频新增的，"
                         "而**既有已发货 spec 会命中它**（例如 specs/168.json 的"
                         "「命中缓存省 90%」实测一行 992px > 860px 内容宽，但它实际只是"
                         "贴到画布右边而不是溢出，属于存量现象）。要卡这条就显式加 --strict。")
    a = ap.parse_args()
    p = pathlib.Path(a.spec)
    if not p.exists():
        print(f"❌ 找不到 {p}"); return 2
    d = json.loads(p.read_text())

    problems: list = []
    near: list = []
    role_problems: list = []      # 「槽位/模板不匹配」类（不是宽度问题，单独打印）
    # 既有大标题行的超宽：缺省记进 near（⚠️，不翻退出码），--strict 时才升级为 ❌
    hero_problems: list = []
    wraps: list = []
    cover = d.get("cover", {})
    font = int(cover.get("font", 78))
    # 封面：hero_l1 与 hero_pre+hero_em+hero_tail 两行
    l1 = str(cover.get("hero_l1", ""))
    l2 = "".join(str(cover.get(k, "")) for k in ("hero_pre", "hero_em", "hero_tail"))
    for label, t in (("封面 9:16 第 1 行", l1), ("封面 9:16 第 2 行", l2)):
        if not t:
            continue
        w = width_px(t, font)
        avail = BUDGETS["cover_916"][0]
        if w > avail:
            problems.append(("cover_916", label, t, round(w), avail, font))
        elif w > avail * NEAR_RATIO:
            near.append(("cover_916", label, t, round(w), avail, font))

    # ── 守卫：模板用 {em} 占位符注入强调段；宿主字段漏写 {em} → 强调段被静默丢弃 ──
    EM_HOST = {"mm_em": "mm", "strip_em": "strip", "card_tt_em": "card_tt",
               "card_t_em": "card_t", "repo_t_em": "repo_t"}
    for sid, sc in (d.get("scenes") or {}).items():
        if not isinstance(sc, dict):
            continue
        for ek, host in EM_HOST.items():
            ev, hv = str(sc.get(ek, "")), str(sc.get(host, ""))
            if ev and "{em}" not in hv:
                near.append(("em_placeholder", f"场景{sid} {host}",
                             f"{ek}=「{ev}」但 {host} 里没有 {{em}} 占位符——强调段会被丢弃",
                             0, 0, 0))
    for k in ("hero_l2_em",):
        if str(cover.get(k, "")) and "{em}" not in str(cover.get("hero_pre", "")) + str(cover.get("hero_l2_pre", "")):
            pass  # 封面走 hero_pre+hero_em 拼接，不走占位符，无需守卫

    lb = d.get("line_breaks", {})
    for sid, sc in (d.get("scenes") or {}).items():
        for k in ("n1_t", "n2_t", "n3_t"):
            check(str(sc.get(k, "")), "fnode_t", f"场景{sid} {k}", problems, near)
        for k in ("n1_s", "n2_s", "n3_s"):
            check(str(sc.get(k, "")), "fnode_s", f"场景{sid} {k}", problems, near)
        check(str(sc.get("repo_big", "")), "repo_big", f"场景{sid} repo_big", problems, near)
        check(str(sc.get("repo_t", "")), "lb_t", f"场景{sid} repo_t", problems, near)
        check(str(sc.get("repo_s", "")), "lb_s", f"场景{sid} repo_s", problems, near)
        check(str(sc.get("card_t", "")), "card_t", f"场景{sid} card_t", problems, near)
        for k in ("card_s", "card_tt", "note"):
            check(str(sc.get(k, "")), "card_s", f"场景{sid} {k}", problems, near)

    # ── 深度版「配置逐行 / 三步验证」（2026-09-11）：01–05 的检查逻辑与结论完全不变 ──
    # ⚠️ F-3 修复（2026-09-11）：原先只认 `scenes["06"]`/`scenes["07"]` 两个**写死的槽位号**，
    #    而深度版 spec 的键是 `05-config` / `06-verify`（或 `05`/`06`）→ **两个新模板的逐行/步骤
    #    预算被静默跳过**（EP.167D/168/169 都中招，预检只报封面）。改为**按键名/字段识别**，
    #    与槽位号解耦：带 `lines`（或键含 config）的即配置屏，带 `checks`（或含 verify）的即验证屏。
    # ⚠️ 长视频 spec 用 "chapters" 承载场景（章内的键仍是全局槽位号），所以先摊平：
    #    扁平 scenes 优先（老路径一字不变），没有就摊 chapters；两者都给时以 scenes 为准。
    _all = d.get("scenes") or {}
    if not _all:
        for _c in (d.get("chapters") or []):
            _all.update(_c.get("scenes") or {})
    def _find_scene(pred):
        for _k, _v in _all.items():
            if isinstance(_v, dict) and pred(str(_k), _v):
                return _v
        return None
    sc06 = _find_scene(lambda k, v: "config" in k or v.get("lines"))
    sc07 = _find_scene(lambda k, v: ("verify" in k or k.endswith("07") or "verdict" in k) and v.get("checks")) \
        or _find_scene(lambda k, v: v.get("checks"))
    extra = gen_budgets(sc06, sc07)
    old = {k: BUDGETS[k] for k in extra}
    BUDGETS.update(extra)                       # 临时并入，供 check() 取用
    pad_plan = []
    if sc06:
        check(str(sc06.get("hero_l1", "")).replace("{em}", str(sc06.get("hero_em", ""))),
              "cfg_hero", "配置屏 hero_l1（含 {em}）", problems, near)
        pad_plan = build_pad_column_plan(sc06)
        for k, t, ind, w, cw, hl, fsz in pad_plan:
            if w + ind > BUDGETS["cfg_row"][0]:
                problems.append(("cfg_row", f"配置屏 第{k}行（{fsz}px，缩进 {ind:.0f}px）", t,
                                 round(w + ind), BUDGETS["cfg_row"][0], fsz))
            elif w + ind > BUDGETS["cfg_row"][0] * NEAR_RATIO:
                near.append(("cfg_row", f"配置屏 第{k}行（{fsz}px）", t, round(w + ind),
                             BUDGETS["cfg_row"][0], fsz))
    if sc07:
        check(str(sc07.get("title", "")).replace("{em}", str(sc07.get("hero_em", ""))),
              "vfy_head", "验证屏 title", problems, near)
        check(str(sc07.get("sub", "")), "vfy_sub", "验证屏 sub", problems, near)
        for ci, c in enumerate(sc07.get("checks") or [], 1):
            check(str(c.get("t", "")), "vfy_t", f"验证屏 步骤{ci} 主文案", problems, near)
            # ⚠️ 步骤说明（.s）在模板契约里**允许正常折行**（README-deep §2.2：38px 标题不折、
            #    22px 说明可折）→ 超预算只记信息项，**不报 ❌**，否则会把合规排版当成超宽。
            _sv, _sb = str(c.get("s", "")), BUDGETS["vfy_s"][0]
            if _sv and width_px(_sv, BUDGETS["vfy_s"][1]) > _sb:
                wraps.append(f"验证屏 步骤{ci} 说明（{round(width_px(_sv, BUDGETS['vfy_s'][1]))}px / {_sb}px，"
                             f"按模板折 2 行）")
    BUDGETS.update(old)

    # ── 长视频 5 个新模板（2026-09-12）：chapter / quote / table / flow / case ──────────
    # 与生成期同一套宽度模型；生成期会在同一处硬断言（放不下就 SystemExit），
    # 这里提前到 spec 阶段报，省一次渲染。
    # 打印每种模板的**启用情况**（便于确认没有漏检：哪些模板被用了、各几场）。
    # ⚠️ 这里的分类**必须与 gen_chai_frames.py 的 _classify_role 同一张表、同一个顺序** ——
    # 否则预检与生成期会对同一份 spec 给出不同结论（本次 EP.170 的教训：预检按字段扫、
    # 生成期按槽位写死，于是预检报 ✅ 而生成期直接 KeyError: 'mm'）。
    ROLE_KEYS = (("chapter", ("no",)), ("table", ("table",)), ("case", ("chain",)),
                 ("quote", ("quote",)), ("flow", ("steps",)), ("config", ("lines",)),
                 ("verify", ("checks",)), ("action", ("w1_t", "w2_t")),
                 ("mechanism", ("n1_t", "n2_t", "n3_t")), ("facts", ("repo_big",)),
                 ("hook", ("warn_a", "warn_b", "card_big")), ("verdict", ("hero_l1", "note")))
    NEW_ROLES = ("chapter", "quote", "table", "flow", "case")

    def _role_of(body):
        for role, keys in ROLE_KEYS:
            if isinstance(body, dict) and all(k in body for k in keys):
                return role
        return None

    _ordered = sorted((_all or {}), key=lambda k: int(re.match(r"^(\d+)", str(k)).group(1) or 0))
    _roles = {}
    _used: dict = {k: [] for k in ("chapter", "quote", "table", "flow", "case")}
    for _sid in _ordered:
        _sc = _all[_sid]
        _role = _role_of(_sc)
        _roles[_sid] = _role
        if _role in _used:
            _used[_role].append(_sid)
        elif _role is None:
            role_problems.append(f"场景 {_sid}：字段对不上任何模板"
                                 f"（生成期会直接报错中止；契约见 README-deep §2A / §2B）")
    if not _roles:
        pass
    # 长片（spec 带 chapters）：01 槽必须是 hook、末槽必须是判词卡 —— 与生成期的硬校验一致。
    # 这两条正是首帧契约门禁能生效、以及收尾卡有内容的前提。
    if d.get("chapters") and _ordered:
        if _roles.get(_ordered[0]) != "hook":
            role_problems.append(
                f"首槽 {_ordered[0]}：判定为「{_roles.get(_ordered[0]) or '无匹配'}」，不是首帧钩子（hook）"
                f" —— 首帧契约门禁比的是 01 槽文字与封面文字，01 槽必须是 hook")
        if _roles.get(_ordered[-1]) != "verdict":
            role_problems.append(
                f"末槽 {_ordered[-1]}：判定为「{_roles.get(_ordered[-1]) or '无匹配'}」，不是收尾判词（verdict）"
                f" —— 末槽固定是收尾卡")

    def _lchk(text, key, label):
        if not text:
            return
        avail, font, _ = BUDGETS[key]
        w = width_px(text, font)
        if w > avail:
            problems.append((key, label, text, round(w), avail, font))
        elif w > avail * NEAR_RATIO:
            near.append((key, label, text, round(w), avail, font))

    BUDGETS.update(LONG_BUDGETS)          # 临时并入，供 check()/报错打印取用
    BUDGETS.update(_LC2)

    # 既有大标题行的一行预算（01 首帧 + 末场判词）：长视频里这两处最容易溢出。
    # ⚠️ 这里用 1.15 的实测校准系数（CJK 实测推进 ≈1.13em，而 width_px 按 1.0em 算，
    #    偏低约 13%）：只有这两条**硬性要求一行放下**的预算才加系数，
    #    其余「允许折行」的预算保持原口径 —— 与 gen_chai_frames.py 的 _build_chapter 同一决策。
    _slots_sorted = sorted((_all or {}).keys(), key=lambda k: int(re.match(r"^(\d+)", str(k)).group(1)) or 0) \
        if _all else []
    if _slots_sorted:
        _s01 = _all[_slots_sorted[0]]
        _s_last = _all[_slots_sorted[-1]]
        for _k, _v, _bg in (("hero01_1", str(_s01.get("hero_l1", "")), "hero01_1"),
                            ("hero01_2", str(_s01.get("hero_l2", "")), "hero01_2")):
            if _v:
                _av, _fs, _d = BUDGETS[_bg]
                # 2026-09-12（EP.171）：首帧大字支持可选字段 `hero_fs`（生成器按它改 #f1-hero 字号）。
                # 没写这个字段时口径与改造前逐字相同（保持 118px 预算）。
                _fs = int(_s01.get("hero_fs") or _fs)
                _w = width_px(_v, _fs) * 1.15
                if _w > _av:
                    (problems if a.strict else hero_problems).append(
                        (_bg, f"场景 {_slots_sorted[0]} {_k}", _v, round(_w), _av, _fs))
                elif _w > _av * NEAR_RATIO:
                    near.append((_bg, f"场景 {_slots_sorted[0]} {_k}", _v, round(_w), _av, _fs))
        _l2 = "".join(str(_s_last.get(_kk, "")) for _kk in
                      ("hero_l2_pre", "hero_l2_em", "hero_l2_tail")) or str(_s_last.get("hero_l2", ""))
        for _k, _v, _bg in (("hero05_1", str(_s_last.get("hero_l1", "")), "hero05_1"),
                            ("hero05_2", _l2, "hero05_2")):
            if _v:
                _av, _fs, _d = BUDGETS[_bg]
                _fs = int(_s_last.get("hero_fs") or _fs)
                _w = width_px(_v, _fs) * 1.15
                if _w > _av:
                    (problems if a.strict else hero_problems).append(
                        (_bg, f"末场 {_slots_sorted[-1]} {_k}", _v, round(_w), _av, _fs))
                elif _w > _av * NEAR_RATIO:
                    near.append((_bg, f"末场 {_slots_sorted[-1]} {_k}", _v, round(_w), _av, _fs))
    for _sid in sorted(_used["chapter"]):
        _sc = _all[_sid]
        # 章节页几何（序号列宽 / 标题可用宽 / 字号）**直接来自共享模块**
        _steps = [str(_t) for _t in (_sc.get("steps") or [])]
        _g = LF.chapter_geom(_sc.get("no"), str(_sc.get("title", "")), _steps)
        for _kind, _msg in _g["errors"]:
            problems.append(("ch_title" if _kind != "steps" else "ch_step",
                             f"章节页 {_sid}", _msg, 0, 0, 0))
        # 生成器实际会用的那档字号（共享模块算出来的），照它报「占用 / 可用」
        # 「接近超宽」只在**生成器被迫降档**时才报：字号已经是共享模块算出来的那一档，
        # 所以「该档放不下」= 下一档会更小 = 再长 1 个字就掉档。老口径（拿预算的 90%
        # 去比模型估算宽度）会在中文上大面积误报 —— 模型对 CJK 偏低 13%，90% 阈值
        # 实际上约等于「已经用掉 100%」，所以长标题必报，报出来也没用。
        _tt = str(_sc.get("title", ""))
        _av = _g["title_avail"]
        if _g["title_fs"] and _tt and width_px(_tt, _g["title_fs"]) * LF.CJK_ADV_SAFE > _av:
            near.append(("ch_title", f"章节页 {_sid} 标题（生成器降到 {_g['title_fs']}px 才放下）",
                         _tt, round(width_px(_tt, _g["title_fs"]) * LF.CJK_ADV_SAFE), round(_av),
                         _g["title_fs"]))
        for _i, _t in enumerate(_steps, 1):
            if _g["step_fs"] and width_px(_t, _g["step_fs"]) * LF.CJK_ADV_SAFE > LF.CH_STEP_AVAIL:
                near.append(("ch_step", f"章节页 {_sid} 预览行{_i}（生成器降到 {_g['step_fs']}px）",
                             _t, round(width_px(_t, _g["step_fs"]) * LF.CJK_ADV_SAFE), LF.CH_STEP_AVAIL,
                             _g["step_fs"]))
    for _sid in sorted(_used["quote"]):
        _sc = _all[_sid]
        _q = str(_sc.get("quote", ""))
        _qg = LF.quote_geom(_q, str(_sc.get("head", "") or ""))
        for _kind, _msg in _qg["errors"]:
            problems.append(("quote_q", f"引用页 {_sid}", _msg, 0, 0, _qg["fs"] or LF.QT_MIN_FS))
        # 引文是「允许折 2–6 行」的，折行本身不是问题 —— 只有**折到 5 行以上**才算接近上限
        if not _qg["errors"] and _qg["lines"] >= 5:
            near.append(("quote_q", f"引用页 {_sid} 引文已折 {_qg['lines']} 行（上限 {LF.QT_MAX_LINES} 行），"
                                    f"再长就要换更小档",
                         _q[:40], round(width_px(_q[:40], _qg["fs"])), LF.QT_INNER, _qg["fs"]))
        _lchk(str(_sc.get("source", "")), "quote_src", f"引用页 {_sid} 来源角标")
    for _sid in sorted(_used["table"]):
        _sc = _all[_sid]
        _tb = _sc["table"]
        _hd = (_tb.get("head") if isinstance(_tb, dict) else None)
        _rows = (_tb.get("rows") if isinstance(_tb, dict) else _tb) or []
        for _i, _r in enumerate(_rows, 1):
            _k = str(_r[0]) if isinstance(_r, (list, tuple)) else str(_r.get("k", ""))
            _v = str(_r[1]) if isinstance(_r, (list, tuple)) else str(_r.get("v", ""))
            _tg = LF.table_geom([[_k, _v]])
            for _key, _msg in _tg["errors"]:
                problems.append(("tbl_k", f"对照表 {_sid} 第{_i}行", _msg, 0, 0, LF.TB_MIN_FS))
            if not _tg["errors"]:
                # 单元格**允许折 2 行**，所以「宽度 > 列宽」是正常现象，不是接近超宽；
                # 只有「生成器已经降到更小档」才提示（即该档下要折 > 2 行）。
                for _txt, _key, _fs, _fmax, _lab in ((_k, "tbl_k", _tg["k_fs"], 26, "行名"),
                                                     (_v, "tbl_v", _tg["v_fs"], 28, "数值")):
                    _av = _tg["k_avail"] if _key == "tbl_k" else _tg["v_avail"]
                    if _txt and _fs < _fmax and wrap_count(_txt, _fmax, _av) > 2:
                        near.append((_key, f"对照表 {_sid} 第{_i}行 {_lab}（生成器降到 {_fs}px）",
                                     _txt, round(width_px(_txt, _fs)), round(_av), _fs))
        if not (3 <= len(_rows) <= 6):
            problems.append(("tbl_v", f"对照表 {_sid}", f"{len(_rows)} 行（须 3–6 行）", 0, 0, 0))
        if _hd and len(_hd) != 2:
            problems.append(("tbl_v", f"对照表 {_sid} 表头", f"{len(_hd)} 列（须正好 2 列）", 0, 0, 0))
    for _sid in sorted(_used["flow"]):
        _sc = _all[_sid]
        _steps = [({"t": str(x), "s": ""} if isinstance(x, str) else
                   {"t": str(x.get("t", "")), "s": str(x.get("s", "") or "")})
                  for x in (_sc.get("steps") or [])]
        _fg = LF.flow_geom(_steps)
        for _kind, _msg in _fg["errors"]:
            problems.append(("flow_t", f"流程 {_sid}", _msg, 0, 0,
                             _fg["t_fs"] or LF.FLOW_T_SIZES[-1]))
        if not _fg["errors"]:
            for _i, _st in enumerate(_steps, 1):
                for _txt, _key, _fs in ((_st["t"], "flow_t", _fg["t_fs"]),
                                        (_st["s"], "flow_s", _fg["s_fs"])):
                    # 每步列宽只有 172px，两步标题本来就常折 2 行 —— 只在**掉到更小档**时提示
                    _fmax = LF.FLOW_T_SIZES[0] if _key == "flow_t" else LF.FLOW_S_SIZES[0]
                    if _txt and _fs and _fs < _fmax and wrap_count(_txt, _fmax, LF.FLOW_LB_W) > 2:
                        near.append((_key, f"流程 {_sid} 第{_i}步（生成器降到 {_fs}px）",
                                     _txt, round(width_px(_txt, _fs)), LF.FLOW_LB_W, _fs))
    for _sid in sorted(_used["case"]):
        _sc = _all[_sid]
        _ch = [c for c in (_sc.get("chain") or []) if isinstance(c, dict)]
        _cg = LF.case_geom([{"t": str(c.get("t", ""))} for c in _ch]) if len(_ch) == 3 else None
        if _cg is None:
            problems.append(("case_t", f"案例 {_sid}",
                             f"{len(_ch)} 段（须正好 3 段：现象/机制/结果）", 0, 0, 0))
        else:
            for _kind, _msg in _cg["errors"]:
                problems.append(("case_t", f"案例 {_sid}", _msg, 0, 0, _cg["t_fs"]))
            for _i, _nd in enumerate(_ch, 1):
                _ct, _av = str(_nd.get("t", "")), _cg["avail"]
                if _ct and _cg["t_fs"] < LF.CS_T_SIZES[0] and wrap_count(_ct, LF.CS_T_SIZES[0], _av) > 2:
                    near.append(("case_t", f"案例 {_sid} 第{_i}段 正文（生成器降到 {_cg['t_fs']}px）",
                                 _ct, round(width_px(_ct, _cg["t_fs"])), _av, _cg["t_fs"]))
                _lchk(str(_nd.get("hd", "")), "case_hd", f"案例 {_sid} 第{_i}段 标签")

    # 字幕：本脚本读不到时间轴（渲染前可能还没生成），只能提示 spec 里已配多少折行
    print(f"版面预检 · {p.name}")
    if role_problems:
        print(f"\n❌ 槽位 / 模板不匹配 {len(role_problems)} 处"
              f"（**写稿阶段就能拦下**，不用等生成期崩；契约见 README-deep §2A/§2B）：")
        for _m in role_problems:
            print(f"  ❌ {_m}")
    if hero_problems:
        print(f"\n  ⚠️ 既有大标题行超宽 {len(hero_problems)} 处"
              f"（01 首帧 / 末场判词的 #f1-hero·#f5-hero **不换行也无 max-width**，"
              f"文案过长会向右溢出；缺省只报 ⚠️ 不翻退出码，要卡请加 --strict）：")
        for key, label, text, w, avail, f in hero_problems:
            print(f"  ⚠️ {label}：{w}px > {avail}px（{f}px 字号）「{text}」")
            print(f"      → {BUDGETS.get(key, (0, 0, ''))[2]}")

    if problems:
        print(f"\n⚠️ 可能超宽 {len(problems)} 处（渲染后会折行/断词，建议先改文案或加 line_breaks）：")
        for key, label, text, w, avail, f in problems:
            print(f"  ❌ {label}：{w}px > {avail}px（{f}px 字号）「{text}」")
            print(f"      → {BUDGETS.get(key, (0, 0, LONG_BUDGETS.get(key, (0, 0, '（长视频模板预算）'))[2]))[2]}")
    else:
        print("  ✅ 未发现超宽风险")

    if wraps:
        print(f"\n  ℹ️ 允许折行 {len(wraps)} 处（模板契约内，不判超宽）：")
        for _w in wraps:
            print(f"  ℹ️ {_w}")

    if near:
        print(f"\n  ⚠️ 接近超宽 {len(near)} 处（占用 > {int(NEAR_RATIO*100)}% 预算，再长 1 个字就可能溢出）：")
        for key, label, text, w, avail, f in near:
            if key == "em_placeholder":
                print(f"  ⚠️ {label}：{text}")
            else:
                print(f"  ⚠️ {label}：{w}px / {avail}px（{f}px 字号）「{text}」")

    if pad_plan:
        fsz = pad_plan[0][6]
        print(f"\n  ℹ️ 场景06 配置逐行：{len(pad_plan)} 行，生成器将用 {fsz}px 等宽字号，"
              f"单行可用宽 {BUDGETS['cfg_row'][0]}px（+缩进）")
        for k, t, ind, w, cw, hl, _f in pad_plan:
            flag = "HL " if hl else "   "
            print(f"     {flag}{k:02d} 占 {w + ind:6.1f}px / {BUDGETS['cfg_row'][0]}px"
                  f"（缩进 {ind:.0f}）「{t[:46]}」")

    # 长视频模板启用情况（**每种都打印**，便于确认没有漏检）
    _tb_files = sorted({k for k, v in _used.items() if v})
    print(f"\n  ℹ️ 模板启用情况（**按字段扫描全部 {len(_ordered)} 个槽位**，与生成期同一套分类）：")
    for _k in ("chapter", "quote", "table", "flow", "case"):
        _v = _used[_k]
        print(f"     {'✅' if _v else '－'} {_k:<8} {len(_v)} 场"
              + (f"：{'、'.join(_v)}" if _v else "（未启用）"))
    _legacy = {r: [k for k in _ordered if _roles.get(k) == r]
               for r in ("hook", "facts", "mechanism", "action", "config", "verify", "verdict")}
    print("     （既有角色按字段命中："
          + " · ".join(f"{r} {len(v)} 场" for r, v in _legacy.items() if v)
          + "）")
    _none = [k for k in _ordered if _roles.get(k) is None]
    if _none:
        print(f"     ❌ 对不上任何模板的槽位：{'、'.join(_none)}")
    if not _tb_files:
        print("     （没有长视频模板字段 —— 走既有 5/7 场景模板或既有角色），本节其余检查跳过")

    print(f"\n  ℹ️ 已配 line_breaks：{len(lb)} 条 —— 字幕组 ≥11 字必须折行（字幕带可用宽 {CAPTION[0]}px ≈ 10 个中文字；跑 `build_chai_timeline.py` 后可用")
    print("     `python3 - <<'PY'` 自查：统计 caption_groups 里 ≥11 字的组是否都在 line_breaks 中。")
    # ── 字幕折行行数 vs 字幕带高度（2026-09-17 加，EP.187–189 复评 P1-1）──────────────
    # 模板的 `--cap-band-height` 是 114px，实测**2 行 = 98px 正好在带内**，3 行 = 150px
    # 会上下各多出约 17px（离场景注脚最近只剩 15px）。`mk_line_breaks.py` 已改成「能 2 行就
    # 不折 3 行」，但**分词边界上两行确实放不下**的长句仍会折到 3 行 —— 这里把它显式报出来，
    # 别让它静默存在。
    deep = {k: v for k, v in lb.items() if isinstance(v, list) and len(v) >= 3}
    if deep:
        print(f"\n  ⚠️ 折到 3 行及以上的字幕组 {len(deep)} 个（字幕带 114px 只容 2 行 ≈ 98px，3 行 ≈ 150px）：")
        for k, v in list(deep.items())[:6]:
            print(f"     {k}: {v}")
        print("     → 想彻底消掉就把这些句子的主句写短一点（或拆成两条字幕）；不阻断渲染。")
    else:
        print("\n  ✅ 字幕折行全部 ≤2 行（落在 114px 字幕带内）")
    return 1 if (problems or role_problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())
