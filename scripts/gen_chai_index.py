#!/usr/bin/env python3
"""柴主编 index.html 生成器（自研，2026-09-04 固化；2026-09-11 支持任意场景数）。

从 publish-timeline/audio_meta.json 读取各段时长，按 Soft Slate 标准结构
生成视频工程的 index.html（场景/音轨/转场/口播窗/嘴型驱动全量写入）。
生成后必须运行 hyperframes check 验证（0 error 才能渲染）。

用法：
  python3 scripts/gen_chai_index.py <video_project> <episode_dir> "<FURNITURE>" \
      [--scenes 01-hook,02-facts,...] [--trans 0.5]
      [--chapter-trans 1.2] [--chapters a|b] [--chapter-progress]
  例（日更 5 场景，行为与 2026-09-11 前完全一致）：
      python3 scripts/gen_chai_index.py videos/doubao-agent-phone \
          content/episode-126 "AI PHONE / 126"
  例（深度版 7 场景，显式给场景表）：
      python3 scripts/gen_chai_index.py /tmp/deep-proj content/episode-190 "DEEP / 190" \
          --scenes=01-hook,02-facts,03-mechanism,04-action,05-config,06-verify,07-verdict

--scenes 缺省 = 01-hook,02-facts,03-mechanism,04-action,05-verdict（日更 5 场景，零变化）；
也可以写成 auto 或省略后由 --spec 自动取 spec 里的场景键（顺序 = 键的两位序号）：
      python3 scripts/gen_chai_index.py /tmp/deep-proj content/episode-190 "DEEP / 190" \
          --scenes=auto --spec specs/190.json
场景数必须与 audio_meta.voices 段数一致，不一致就显式报错（1 段音频 = 1 个场景）。
--trans 是场景交接动画时长（秒），缺省 0.5 = 历史值。

长视频（20–30 场景 + 章节）新增两个开关，**缺省都关闭**，所以既有 5/7 场景行为零变化：
  --chapter-trans <秒>   **章节页之间的转场**时长，缺省 = --trans（即与普通转场一致）。
                         章节切换是长片的呼吸点，比场内转场更长（如 1.2s）观感更清楚；
                         只有同时给 --spec 且 spec 带 chapters 时才知道哪几处是章节边界，
                         否则整片统一用 --trans（老行为）。
  --chapters auto|none   场景 → 章节的映射来源。auto（缺省）= 有 --spec 且 spec 带
                         chapters 时按它切；none = 不区分章节（等价于老行为）。
  --chapter-progress     在画面底部居中加一行「CHAPTER 01/04 · SCENE 05/24」进度指示。
                         **缺省不渲染** —— 不加这个开关，index.html 与改造前逐字节相同。
"""
from __future__ import annotations

import argparse, json, re, shutil, sys
from pathlib import Path

TPL = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="assets/gsap.min.js"></script>
    <style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@900&display=swap');
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #1A1A1A; }
      #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: linear-gradient(160deg, #1F1F1F 0%, #101010 100%); }
      .scene { position: absolute; inset: 0; width: 100%; height: 100%; }
      .furniture-source { position: absolute; left: 110px; top: 96px; z-index: 30; font: 22px "CobaltMono","PingFang SC",monospace; color: #989188; letter-spacing: .08em; }
      .furniture-brand { position: absolute; right: 110px; top: 100px; z-index: 30; font: 700 23px/1 "Noto Sans SC","PingFang SC",sans-serif; color: #F2EEE8; letter-spacing: .12em; }
      .chai-speaker { border: 2px solid rgba(209,255,0,0.55); 
        position: absolute; top: 1490px; left: 190px; width: 110px; height: 110px; z-index: 40;
        border-radius: 50%; background: linear-gradient(145deg, #242424, #1C1C1C); padding: 7px;
        box-shadow: 0 10px 24px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);
        overflow: visible; will-change: transform;
      }
      .chai-speaker__crop { position: absolute; inset: 7px; overflow: hidden; border-radius: 50%; }
      .chai-speaker__crop img { display: block; width: 100%; height: 100%; object-fit: cover; }
      .chai-speaker__mouth-anchor { position: absolute; left: 50%; top: 66.2%; width: 34px; height: 20px; margin-left: -17px; margin-top: -10px; pointer-events: none; }
      .chai-speaker__mouth {
        position: absolute; inset: 0; border-radius: 48% 48% 54% 54%;
        background: radial-gradient(ellipse at 50% 76%, #d65a68 0 20%, #521e2a 22% 48%, #160b12 52% 100%);
        box-shadow: inset 0 3px 2px rgba(255,255,255,.25), 0 1px 2px rgba(0,0,0,.45);
        opacity: 0; will-change: transform, opacity;
      }
      .chai-speaker__mouth::before { content: ""; position: absolute; top: 1px; left: 5px; width: 24px; height: 5px; border-radius: 0 0 9px 9px; background: #f7eee0; }
      .chai-speaker__name { display: none; }@PROGRESS_CSS@
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0.0" data-duration="@TOTAL@" data-width="1080" data-height="1920">
@SCENES@
      <div class="furniture-source">@FURNITURE@</div>
      <div class="furniture-brand">柴主编｜只讲一件事</div>@PROGRESS_EL@

      <div id="el-captions" class="scene" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0.0" data-duration="@TOTAL@" data-track-index="2"></div>

      <div id="chai-speaker" class="chai-speaker" aria-label="柴主编说话头像">
        <div class="chai-speaker__crop">
          <img src="assets/brand/chai-editor-avatar.png" alt="柴主编">
          <div class="chai-speaker__mouth-anchor">
            <div id="chai-speaker-mouth" class="chai-speaker__mouth"></div>
          </div>
        </div>
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = gsap.timeline({ paused: true });
      (function () { var tl = window.__timelines["main"];
@TRANSITIONS@
        tl.fromTo("#chai-speaker", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.55, ease: "back.out(1.7)" }, 0.18);
        tl.fromTo(".furniture-source", { opacity: 0 }, { opacity: 1, duration: 0.5 }, 0.2);
        tl.fromTo(".furniture-brand", { opacity: 0 }, { opacity: 1, duration: 0.5 }, 0.2);@PROGRESS@
        var speechWindows = @WINDOWS@;
        var mouth = document.getElementById("chai-speaker-mouth");
        var avatar = document.getElementById("chai-speaker");
        var jawDriver = { progress: 0 };
        tl.to(jawDriver, {
          progress: 1, duration: @TOTAL@, ease: "none",
          onUpdate: function () {
            var t = jawDriver.progress * @TOTAL@;
            var active = null;
            for (var i = 0; i < speechWindows.length; i++) {
              if (t >= speechWindows[i][0] && t <= speechWindows[i][1]) { active = speechWindows[i]; break; }
            }
            var openness = 0;
            if (active) {
              var local = t - active[0];
              var attack = Math.min(1, local / 0.07);
              var release = Math.min(1, (active[1] - t) / 0.09);
              var syllable = 0.34 + 0.66 * Math.abs(Math.sin(local * 18.5));
              openness = syllable * Math.max(0, Math.min(attack, release));
            }
            gsap.set(mouth, { scaleX: 0.82 + openness * 0.22, scaleY: 0.12 + openness * 0.94, opacity: openness > 0.04 ? 0.98 : 0 });
            gsap.set(avatar, { y: active ? -2.5 * Math.sin(t * 5.4) : 0, rotation: active ? 0.7 * Math.sin(t * 2.7) : 0 });
          }
        }, 0);
        tl.to({}, { duration: @TOTAL@ }, 0);
      })();
    </script>
  </body>
</html>
"""

IDS = ["01-hook", "02-facts", "03-mechanism", "04-action", "05-verdict"]
# 场景槽位 → 场景 id 归一表（与 gen_chai_frames.py 的 _fid 必须一致）：spec 写纯数字时用它取名
# ⚠️ 已由 scenes_from_spec 内的 _canon() 取代（后者还要处理末场/N>7 的情况）；
#    保留常量只为不破坏任何外部 import。
CANON_ID = {1: "01-hook", 2: "02-facts", 3: "03-mechanism", 4: "04-action"}
# 场景（末场除外）比音频多出的「呼吸量」，与 gen_chai_frames.py 的 durs 口径一致，改一处必须改两处
TAIL_PAD = 0.5
TRANS_DUR = 0.5

def scenes_from_spec(spec_path: str) -> list:
    """从 spec 取场景 id 表（键 = composition id = 帧文件名，按两位序号排序）。

    吃两种 spec 形态，与 gen_chai_frames.py 的 _flat_scenes 完全同源：
      A) 扁平：`"scenes": {"01": …, "02": …}`
      B) 分章：`"chapters": [{"id":1,"title":"…","scenes":{"01-hook": …}}, …]`
         —— 章内的键仍是**全局槽位号**（01…N 连续）。
    纯数字键按槽位归一到角色名（与 gen_chai_frames.py 的 _canon 同表）；
    带角色名的键原样用。序号缺失/重复/不连续会显式报错 —— 宁可停线，
    也不要静默生成指向不存在帧的 index。
    """
    d = json.load(open(spec_path))
    S = d.get("scenes") or {}
    flat = {}
    for c in (d.get("chapters") or []):
        for k, v in (c.get("scenes") or {}).items():
            if k in flat:
                raise SystemExit(f"FAIL: 场景键「{k}」在 chapters 里出现两次（一章一场景）")
            flat[k] = v
    if S:
        missing = [k for k in flat if k not in S]
        if missing:
            raise SystemExit(f"FAIL: spec 同时给了 scenes 与 chapters，但 {missing} 不在 scenes 里")
    else:
        S = flat
    plan = []
    for k in S:
        m = re.match(r"^(\d+)", str(k))
        if not m:
            raise SystemExit(f"FAIL: spec 场景键「{k}」不以数字开头，无法排序（键须形如 05-config）")
        plan.append((int(m.group(1)), str(k)))
    plan.sort()
    nums = [n for n, _ in plan]
    if len(set(nums)) != len(nums):
        raise SystemExit(f"FAIL: spec 场景键序号重复：{plan}")
    for i, n in enumerate(nums, 1):
        if n != i:
            raise SystemExit(f"FAIL: spec 场景键序号必须连续从 01 开始，当前 {nums}")

    _chaptered = bool(d.get("chapters"))

    def _role_of(body: dict) -> str | None:
        """按字段判角色 —— 与 gen_chai_frames.py 的 _classify_role 同一张表、同一个顺序。

        两处必须一致，否则帧文件名与 index 的场景表会对不上（本文件下方有断言）。
        """
        if not isinstance(body, dict):
            return None
        for role, keys in (("chapter", ("no",)), ("table", ("table",)), ("case", ("chain",)),
                           ("quote", ("quote",)), ("flow", ("steps",)), ("config", ("lines",)),
                           ("verify", ("checks",)), ("action", ("w1_t", "w2_t")),
                           ("mechanism", ("n1_t", "n2_t", "n3_t")), ("facts", ("repo_big",)),
                           ("hook", ("warn_a", "warn_b", "card_big")),
                           ("verdict", ("hero_l1", "note"))):
            if all(k in body for k in keys):
                return role
        return None

    def _canon(i: int, total: int, body: dict) -> str:
        # 扁平路径：与改造前的 CANON_ID/_canon 表逐字一致
        if not _chaptered:
            if i == 1:
                return "01-hook"
            if i == 2:
                return "02-facts"
            if i == 3:
                return "03-mechanism"
            if i == 4:
                return "04-action"
            if i == total:
                return f"{i:02d}-verdict"
            if i == 5:
                return "05-verdict"
            if i == 6:
                return "06-verify"
            return f"{i:02d}-scene"
        # 长片路径：纯数字键时按**实际角色**起名（与 gen_chai_frames 的 _canon_sub 同表）
        return f"{i:02d}-{_role_of(body) or 'scene'}"

    out = []
    for i, (_, k) in enumerate(plan, 1):
        out.append(_canon(i, len(plan), S[k]) if re.fullmatch(r"\d+", k) else k)
    return out


def chapters_from_spec(spec_path: str, ids: list) -> list:
    """返回场景下标（0 起）→ 章节号（1 起）的映射；spec 没有 chapters 时返回 []。

    章节号按 spec 的 chapters 数组顺序算。spec 里的场景键是**全局槽位号**，
    所以这里按键的前两位数字对齐到 index 的 ids 顺序，而不是按 chapters 内部顺序硬排
    —— ids 的顺序已经由 --scenes=auto 校验过（必须 01..N 连续），两者不会错位。
    """
    if not spec_path:
        return []
    d = json.load(open(spec_path))
    chs = d.get("chapters") or []
    if not chs:
        return []
    slot2ch = {}
    for i, c in enumerate(chs, 1):
        for k in (c.get("scenes") or {}):
            m = re.match(r"^(\d+)", str(k))
            if not m:
                raise SystemExit(f"FAIL: chapters[{i}] 里的场景键「{k}」不以数字序号开头")
            slot2ch[int(m.group(1))] = i
    out = []
    for i, sid in enumerate(ids, 1):
        if i not in slot2ch:
            raise SystemExit(
                f"FAIL: 场景 {sid}（第 {i} 槽）不在 spec 的 chapters 里——"
                f"chapters 覆盖了 {sorted(slot2ch)} 槽，--scenes 有 {len(ids)} 个。\n"
                f"  改法：① 把该场景补进某一章；② 传 --chapters none 关掉章节映射。")
        out.append(slot2ch[i])
    return out


# 章节进度指示的两段注入（CSS / DOM）。**只在 --chapter-progress 时注入**，所以
# 不加这个开关时 index.html 与改造前逐字节相同（零回归的硬约束）。
POS = ["""
      /* 章节进度指示（--chapter-progress 专用；不加开关时这两段根本不存在） */
      .chapter-progress { position: absolute; left: 110px; bottom: 96px; z-index: 30;
        font: 22px "CobaltMono","PingFang SC",monospace; color: #989188; letter-spacing: .14em; }
      .chapter-progress .now { color: #D1FF00; }"""]


def build(proj, episode_dir, furniture, scenes=None, trans_dur=TRANS_DUR,
          chapter_trans=None, chapter_of=None, progress=False, prog_el=""):
    vendor_gsap = Path(__file__).resolve().parents[1] / "_vendor" / "gsap.min.js"
    if vendor_gsap.is_file():
        Path(f"{proj}/assets").mkdir(parents=True, exist_ok=True)
        shutil.copy(vendor_gsap, f"{proj}/assets/gsap.min.js")
    m = json.load(open(f"{episode_dir}/publish-timeline/audio_meta.json"))
    durs = [round(v["duration_s"], 3) for v in m["voices"]]
    total = round(sum(durs), 3)
    ids = list(scenes) if scenes else list(IDS)
    if len(ids) != len(durs):
        raise SystemExit(
            f"FAIL: --scenes 给了 {len(ids)} 个场景（{','.join(ids)}），"
            f"但 audio_meta.voices 有 {len(durs)} 段——1 段音频 = 1 个场景，数量必须相等。")
    starts = [0.0]
    for d in durs[:-1]:
        starts.append(round(starts[-1] + d, 3))
    lines = []
    for i, sid in enumerate(ids):
        dur = round(durs[i] + (TAIL_PAD if i < len(ids) - 1 else 0.0), 3)
        lines.append(f'      <div id="el-{sid}" class="scene" data-composition-id="{sid}" data-composition-src="compositions/frames/{sid}.html" data-start="{starts[i]}" data-duration="{dur}" data-track-index="{i % 2}"></div>')
    for i, sid in enumerate(ids):
        lines.append(f'      <audio id="el-{sid}-voice" src="assets/voice/{i+1:02d}.mp3" data-start="{starts[i]}" data-duration="{durs[i]}" data-track-index="{10+i}" data-volume="1"></audio>')
    scenes_html = "\n".join(lines)
    # 章节页之间的转场可以更长（--chapter-trans）。chapter_of 为空 = 不区分章节，
    # 此时每一处都用 trans_dur → 与改造前逐字节相同。
    #
    # 2026-09-12（EP.171）：**章节边界只把「上一场的退场」拉长，新场的入场仍用 trans_dur**。
    # 起因（实测，非推断）：原来两处都用 ctrans=1.2s，于是新场元素要 1.2s 才到 opacity 1；
    # 而新场背景是不透明的，`+0.5s` 采样时它的整体不透明度只有 power2.inOut(0.5/1.2)=0.36，
    # 内容区白字像素（R,G,B>195）实测 **0**——三个章节页（07/13/19）全都落在「上一场已淡、
    # 这一场还没亮」的窗口里，正是 EP.170 §13.6(a) 那条「边界无字」的残留。
    # 修法：入场固定用 `trans_dur`（0.5s，与场内交接一致）→ 新场在 +0.5s 已完全不透明；
    # 退场仍用 ctrans（章节感保留在上一场的退场节奏上）。
    # 零回归：`chapter_trans is None` 时 ctrans == trans_dur，两处时长本来就相同 →
    # index.html 与改造前**逐字节相同**；不带 chapters 的扁平路径更不受影响。
    ctrans = trans_dur if chapter_trans is None else chapter_trans
    n_long = 0
    trans = []
    for i in range(len(ids) - 1):
        d = trans_dur
        if chapter_of and chapter_of[i] != chapter_of[i + 1]:
            d = ctrans
            n_long += 1
        trans.append(f'        tl.to("#el-{ids[i]}", {{ opacity: 0, y: -14, scale: 0.985, duration: {d}, ease: "power2.inOut" }}, {starts[i+1]});')
        trans.append(f'        tl.fromTo("#el-{ids[i+1]}", {{ opacity: 0, y: 24, scale: 0.99 }}, {{ opacity: 1, y: 0, scale: 1, duration: {trans_dur}, ease: "power2.inOut" }}, {starts[i+1]});')
    # 章节进度指示：**缺省关闭**（不加 --chapter-progress 时这一行不渲染，模板里
    # 的 @PROGRESS@ 占位符是空串 —— 与改造前逐字节相同）。
    # 2026-09-12（EP.171）：原实现在 `chapter_of` 存在时**只在章节边界打点**，同一章内的
    # 5 场都停留在章首编号（EP.170 实测 12 场显示 `SCENE 07/24`）——SCENE 计数等于没工作。
    # 现改为**逐场递增**：每一场都写一次 `CHAPTER NN/04 · SCENE MM/24`。
    # 零回归：本分支只在 `--chapter-progress` 且 spec 带 chapters 时进入；
    # 不加开关时 prog_html 仍是空串，index.html 与改造前逐字节相同。
    prog_html = ""
    if progress:
        if chapter_of:
            nch = max(chapter_of)
            for i, c in enumerate(chapter_of):
                prog_html += (f'\n        tl.set("#el-chapter-progress .now", '
                              f'{{ textContent: "CHAPTER {c:02d}/{nch:02d} · SCENE {i+1:02d}/{len(ids):02d}" }}, {starts[i]});')
        else:
            for i in range(len(ids)):
                prog_html += (f'\n        tl.set("#el-chapter-progress .now", '
                              f'{{ textContent: "SCENE {i+1:02d}/{len(ids):02d}" }}, {starts[i]});')
    windows = [[round(s + 0.04, 3), round(s + d - 0.04, 3)] for s, d in zip(starts, durs)]
    prog_css = "" if not prog_el else POS[0]
    html = (TPL.replace("@PROGRESS_CSS@", prog_css)
               .replace("@PROGRESS_EL@", prog_el)
               .replace("@SCENES@", scenes_html)
               .replace("@PROGRESS@", prog_html)
               .replace("@TRANSITIONS@", "\n".join(trans))
               .replace("@WINDOWS@", json.dumps(windows))
               .replace("@FURNITURE@", furniture)
               .replace("@TOTAL@", str(total)))
    open(f"{proj}/index.html", "w").write(html)
    extra = ""
    if chapter_of:
        nch = max(chapter_of)
        extra = f", {nch} chapters, {n_long} 处章节转场用 {ctrans}s"
    if progress:
        extra += ", 章节进度指示 ON"
    print(f"{proj.split('/')[-1]}: index rebuilt, {len(ids)} scenes, total {total}s{extra}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project", help="视频工程目录 videos/<slug>")
    ap.add_argument("episode_dir", help="content/episode-NNN")
    ap.add_argument("furniture", help='顶部来源行，如 "AI PHONE / 126"')
    ap.add_argument("--scenes", default="", metavar="IDS",
                    help="逗号分隔的场景 id（默认 5 场景：01-hook,02-facts,03-mechanism,04-action,05-verdict）；"
                         "逗号分隔值请写成 --scenes=a,b 形式；传 auto 时由 --spec 的场景键推导")
    ap.add_argument("--spec", default="", help="specs/NNN.json（--scenes=auto 时必填）")
    ap.add_argument("--trans", type=float, default=TRANS_DUR,
                    help=f"场景交接动画时长（秒，默认 {TRANS_DUR}）")
    ap.add_argument("--chapter-trans", type=float, default=None, metavar="SEC",
                    help="章节页之间的转场时长（秒）；默认 = --trans（即与普通转场一致，老行为不变）")
    ap.add_argument("--chapters", choices=["auto", "none"], default="auto",
                    help="场景→章节映射：auto（默认，有 --spec 且 spec 带 chapters 时按它切）/ none")
    ap.add_argument("--chapter-progress", action="store_true",
                    help="在画面底部加一行章节进度指示（缺省关闭；开启会改动 index.html）")
    a = ap.parse_args()
    if a.scenes.strip() == "auto":
        if not a.spec:
            raise SystemExit("FAIL: --scenes=auto 需要同时给 --spec specs/NNN.json")
        ids = scenes_from_spec(a.spec)
    else:
        ids = [s.strip() for s in a.scenes.split(",") if s.strip()] or None
    chapter_of = []
    if a.chapters == "auto" and a.spec:
        ids_for_map = ids if ids else list(IDS)
        chapter_of = chapters_from_spec(a.spec, ids_for_map)
    if a.chapter_trans is not None and a.chapter_trans < a.trans:
        raise SystemExit(f"FAIL: --chapter-trans {a.chapter_trans:g} 比 --trans {a.trans:g} 还短"
                         "——章节转场就是要比场内转场更长，短了等于没设。")
    # 章节进度指示：缺省不渲染 → @PROGRESS_EL@ 是空串（占位符单独占一行，替换掉后
    # 不留空行），index.html 与改造前逐字节相同。
    prog_el = ('\n      <div id="el-chapter-progress" class="chapter-progress">'
               '<span class="now"></span></div>')
    build(a.project, a.episode_dir, a.furniture, ids, a.trans,
          a.chapter_trans, chapter_of or None, a.chapter_progress,
          prog_el if a.chapter_progress else "")
