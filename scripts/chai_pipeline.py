#!/usr/bin/env python3
"""柴主编单集发布流水线（2026-09-07 固化）——把 克隆适配→渲染→QA→发布包 串成一键，门禁内建。

背景：EP.139-142 曾发生「克隆工程音频残留」事故（工程内 mp3 是别的集的），且 wrapper ffmpeg
有多个坑。本脚本把当日全部教训固化为可执行门禁，任何一步 FAIL 即停线。

用法：
  全流程（同步→校验→渲染→QA→打包）:
    python3 scripts/chai_pipeline.py all --episode 142 --project huashu-mac-use
  断点续跑（从某阶段开始）:
    python3 scripts/chai_pipeline.py all --episode 142 --project huashu-mac-use --from render
  只跑门禁体检（不渲染，秒级）:
    python3 scripts/chai_pipeline.py verify --episode 142 --project huashu-mac-use

阶段:
  sync     publish-timeline 音频/JSON → 工程内；帧时长以 index.html 为权威源同步
  gates    门禁A: audio_meta 逐句词 vs SCRIPT.md（相似度≥0.85）
  check    hyperframes check（chrome 抖动自动重试 3 次）
  render   hyperframes render
  motion   chai_check_motion PASS 门禁
  qaframes chai_qa_frames 锚点帧提取（供 judge 验收）
  package  正片无封面头 → 门禁B 音视频等长；BGM 按内容决定，默认不加

已固化教训（勿删）:
  - wrapper ffmpeg 无 zoompan/afade，filtergraph 解析残缺（fps=30,setsar=1 都报错）
  - concat -c copy 的 AAC 时间戳伪影会把音频轨拉长数秒 → 必须 -t 裁齐
  - wrapper ffmpeg 解码 afconvert AAC 时长会错读（134217s）→ 门禁C 必须用 afconvert 解码
  - 场景交接 0.5s 双场景同位 note 是设计行为 → 帧内 note 标 data-layout-allow-overlap
"""
import argparse, json, os, re, shutil, subprocess, sys, wave, io
import difflib
import pathlib
import textwrap

ROOT = "/Users/chao/Documents/dailyvideos"
NPX = ["npx", "--yes", "hyperframes@0.7.102"]
FF = f"{ROOT}/videos/qwen38-max-explained/bin/ffmpeg"
FP = f"{ROOT}/videos/llada-image-turbo/bin/ffprobe"
AFCONVERT = "/usr/bin/afconvert"
# 日更 5 场景的缺省场景表（深度版 7 场景由 index.html 实际内容驱动，见 index_scenes()）
SCENES = ["01-hook", "02-facts", "03-mechanism", "04-action", "05-verdict"]
SCENE_RE = re.compile(r'data-composition-id="(\d\d-[\w-]+)" data-composition-src="compositions/frames/')
BED_GAIN = 0.07
BGM_MP3 = f"{ROOT}/assets/bgm/paperman-the-king.mp3"

class Gate(Exception):
    pass

def sh(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd[:6]), "..." if len(cmd) > 6 else "")
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise Gate(f"命令失败 {' '.join(str(c) for c in cmd[:3])}: {r.stderr[-400:]}")
    return r.stdout

def index_scenes(proj: str) -> list:
    """从工程 index.html 读出实际场景表（长度 = 实际段数，5 场景日更与 7 场景深度版都吃）。
    取不到就退回缺省 5 场景表，保证既有路径行为不变。"""
    try:
        found = SCENE_RE.findall(open(f"{proj}/index.html").read())
    except OSError:
        found = []
    return found or list(SCENES)

def _pkg_dir(ep: str) -> str:
    """解析该期的发布包目录：已存在则取最新（按目录名日期排序），否则用 PKG_DATE 或今天。
    2026-09-11 修：原实现把日期硬编码成 publish-package-2026-09-08，导致 verify 静默跳过成品检查。"""
    import glob as _glob, datetime as _dt, os as _os
    base = f"{ROOT}/content/episode-{ep}"
    found = sorted(_glob.glob(f"{base}/publish-package-*"))
    if found:
        return found[-1]
    return f"{base}/publish-package-{_os.environ.get('PKG_DATE') or _dt.date.today().isoformat()}"

def paths(ep, proj):
    return {
        "proj": f"{ROOT}/videos/{proj}",
        "ep": f"{ROOT}/content/episode-{ep}",
        # 包目录：优先取该期已存在的 publish-package-*（取最新的），否则用 PKG_DATE/今天
        "pkg": _pkg_dir(ep),
    }

# ---------- 门禁工具 ----------
def audio_dur_via_afconvert(path):
    """afconvert 权威解码 → wav → 时长。wrapper ffmpeg 解不了 afconvert AAC（时长错读）。"""
    out = "/tmp/_pipe_afc.wav"
    sh([AFCONVERT, "-f", "WAVE", "-d", "LEI16@44100", "-c", "2", path, out])
    w = wave.open(out)
    return w.getnframes() / w.getframerate()

def decode_env(path, win=0.05, sr=16000):
    """包络序列。一律 afconvert 解码——wrapper ffmpeg 解不了 concat 拷贝/afconvert 产的
    AAC（时长会错读成 134217s），不能用作测量。"""
    tmp = "/tmp/_pipe_dec.wav"
    sh([AFCONVERT, "-f", "WAVE", "-d", f"LEI16@{sr}", "-c", "1", os.path.abspath(path), tmp])
    w = wave.open(tmp)
    x = np_from_wav(w)
    wlen = int(win * sr)
    return [x[i:i + wlen].std() for i in range(0, len(x) - wlen, wlen)]

def np_from_wav(w):
    import numpy as np
    n = w.getnframes()
    return np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0

def afc_decode_path(path, sr=16000):
    """afconvert 解码 → 一维 PCM（测量专用，wrapper 解码不可信）。"""
    tmp = "/tmp/_pipe_verify.wav"
    sh([AFCONVERT, "-f", "WAVE", "-d", f"LEI16@{sr}", "-c", "1", os.path.abspath(path), tmp])
    return np_from_wav(wave.open(tmp))

def env_align_score(e_a, e_b, expect_win, max_shift=1.5):
    """在 expect_win(秒)±max_shift 内找包络最佳对齐，返回 (offset, score)。"""
    import numpy as np
    tn_a = np.array(e_a); tn_a = (tn_a - tn_a.mean()) / (tn_a.std() + 1e-9)
    c0 = int(expect_win / 0.05)
    lo = max(0, c0 - int(max_shift / 0.05))
    hi = min(len(e_b) - len(e_a) + 1, c0 + int(max_shift / 0.05))
    best = (-2.0, c0)
    for off in range(lo, max(lo + 1, hi)):
        seg = np.array(e_b[off:off + len(e_a)])
        if len(seg) < len(e_a):
            break
        s = (seg - seg.mean()) / (seg.std() + 1e-9)
        sc = float((s * tn_a).mean())
        if sc > best[0]:
            best = (sc, off)
    return best[1] * 0.05, best[0]

def norm_text(s):
    s = re.sub(r"\s+", "", s)
    return re.sub(r"[，。；：、！？「」（）/.·—-]", "", s)

# ---------- 阶段 ----------
def stage_sync(ep, proj, P):
    print("▶ sync: publish-timeline → 工程")
    tl = f"{P['ep']}/publish-timeline"
    for f in ("audio_meta.json", "caption_groups.json"):
        shutil.copy2(f"{tl}/{f}", f"{P['proj']}/{f}")
    # 音频段数按实际段数同步（5 场景日更仍是 1..5；深度版 7 场景不再被截断）
    scenes = index_scenes(P["proj"])
    src = sorted(f for f in os.listdir(f"{P['ep']}/audio") if re.fullmatch(r"\d\d\.mp3", f))
    if len(src) != len(scenes):
        raise Gate(f"音频段数 {len(src)}（{src[:3]}…）与 index 场景数 {len(scenes)}（{scenes}）不一致——"
                   f"1 段音频 = 1 个场景，先重跑 gen_chai_index.py")
    for f in src:
        shutil.copy2(f"{P['ep']}/audio/{f}", f"{P['proj']}/assets/voice/{f}")
    # 帧时长以 index.html 为权威源
    index = open(f"{P['proj']}/index.html").read()
    for sid in scenes:
        m = re.search(r'data-composition-id="%s" data-composition-src="[^"]*" '
                      r'data-start="[\d.]+" data-duration="([\d.]+)"' % sid, index)
        assert m, f"index 缺场景 {sid}"
        newd = m.group(1)
        fp_ = f"{P['proj']}/compositions/frames/{sid}.html"
        html = open(fp_).read()
        m2 = re.search(r'data-composition-id="%s" data-width="1080" data-height="1920" '
                       r'data-start="[\d.]+" data-duration="([\d.]+)"' % sid, html)
        if m2 and m2.group(1) != newd:
            html = html.replace(m2.group(1), newd)
            open(fp_, "w").write(html)
            print(f"  {sid}: 时长 {m2.group(1)}→{newd}")
    print(f"  ✓ 音频+JSON+帧时长已同步（{len(scenes)} 场景）")

def cover_hold_of(pkg: str) -> float:
    """成片里**实际**的封面头时长：读包内 `finalize-meta.json`（finalize_episode.py 装配时写的），
    没有该文件（2026-09-14 之前的旧包）则回退历史默认 0.4s —— 保证既有各期仍可复现。

    背景（2026-09-14 用户指令）：**封面不再拼进成片**，改为发布时单独上传封面图。
    于是下游工具的 0.4s 偏移假设必须跟着变，否则「真实尾部留白」等公式会整体差 0.4s。
    """
    try:
        import json as _json
        m = _json.load(open(os.path.join(pkg, "finalize-meta.json"), encoding="utf-8"))
        return float(m.get("cover_hold", 0.4))
    except Exception:
        return 0.4


def stage_gates(ep, proj, P):
    print("▶ 门禁A: 配音 ↔ 脚本逐句比对")
    am = json.load(open(f"{P['proj']}/audio_meta.json"))
    script = open(f"{P['ep']}/SCRIPT.md").read()
    lines = []
    # 段落标记：日更用「## Line N」，深度版（7 场景）用「## Scene NN」——两种都要认。
    # ⚠️ 2026-09-11：此前只认 `## Line \d+`，深度版解析出 **0 句** → 逐句比对**整个被跳过**，
    #    却仍打印「✓ 门禁A PASS」。**空转报 PASS 比报 FAIL 更危险**，故同时加下面的硬守卫。
    # ⚠️ 2026-09-12 补第三种写法：**长片按章写稿**（EP.170 起）。
    #    EP.170 的 SCRIPT.md 是 `## 第一章｜它是什么：会话、环境、事件（001–006）`
    #    + 一章一段的缩进块，块内每场一行（`01.txt：…` / `02.txt：…`）——
    #    上面那条「一个标题 = 一句口播」的规则在这里只能匹配到每章的**第一行**，
    #    于是一章只出 1 句、24 场只出 4 句，逐句比对的名次全错位（还会掩盖真正的不符）。
    #    所以：先按**「NN.txt：」行**解析；解析不到才回退到「标题 + 首行」的老规则
    #    （老规则必须逐字保留 —— 165–169 六期的输出要字节不变）。
    txt_lines = [norm_text(
        re.sub(r"^\d{1,2}(?:\.txt)?\s*[：:]\s*", "", m.group(1).strip()))
        for m in re.finditer(r"^[ \t]*(\d{1,2}\.txt\s*[：:].*)$", script, re.M)
        if not m.group(1).strip().startswith(("|", ">", "#", "-", "*", "```"))]
    if txt_lines:
        lines = txt_lines
    else:
        for m in re.finditer(r"##\s*(?:Line|Scene|段)\s*[0-9A-Za-z\u4e00-\u9fa5]*[^\n]*\n\s+(.+)", script):
            cand = m.group(1).strip()
            # 跳过非口播行（表格 / 引用 / 列表 / 说明性冒号句）
            if cand.startswith(("|", ">", "#", "-", "*", "```")):
                continue
            # 剥掉口播行前缀「NN.txt：」/「03.txt:」——它不属于口播内容，
            # 留着会把相似度压到 0.93 左右，掩盖真正的不符
            cand = re.sub(r"^\d{1,2}(?:\.txt)?\s*[：:]\s*", "", cand)
            lines.append(norm_text(cand))
    if not lines:
        raise Gate("门禁A FAIL: 从 SCRIPT.md 解析出 0 句口播——"
                   "段落标记需为「## Line N」或「## Scene NN」（口播为缩进行）、"
                   "或长片的「NN.txt：」（一章一段、块内每场一行）；空转不得报 PASS")
    voices = am["voices"]
    scenes = index_scenes(P["proj"])
    # 段数按实际段数校验（日更 5 场景仍是 5；深度版 7 场景按 7 报错）
    assert len(voices) == len(scenes), \
        f"voices 段数 {len(voices)} ≠ index 场景数 {len(scenes)}（{scenes}）"
    # 段 ↔ 脚本句数不一致时只告警：把语音克隆残留（内容不符）交给下面的相似度硬门禁抓，
    # 否则深度版 7 场景 / 剧本分段与配音段不等长的既有各期会被误杀。
    if len(voices) != len(lines):
        print(f"  ⚠ SCRIPT.md 解析出 {len(lines)} 句，配音 {len(voices)} 段——按段序逐一比对到较短的一侧")
    for i, v in enumerate(voices):
        said = norm_text("".join(w["text"] for w in v["words"]))
        if i < len(lines):
            ratio = difflib.SequenceMatcher(None, said, lines[i]).ratio()
            flag = "✓" if ratio >= 0.85 else "✗"
            print(f"  L{i+1} 相似度 {ratio:.2f} {flag} | 配音: {said[:24]}…")
            if ratio < 0.85:
                raise Gate(f"门禁A FAIL: L{i+1} 配音与脚本不符（{ratio:.2f}）——疑似克隆残留音频")
    # 时长一致性：audio_meta 时长 vs 实际 mp3
    for i, v in enumerate(voices):
        r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of",
                            "csv=p=0", f"{P['proj']}/assets/voice/{i+1:02d}.mp3"],
                           capture_output=True, text=True)
        d = float(r.stdout.strip())
        if abs(d - v["duration_s"]) > 0.05:
            raise Gate(f"门禁A FAIL: voice{i+1:02d}.mp3 实际 {d:.3f}s ≠ audio_meta {v['duration_s']}s")
    print("  ✓ 门禁A PASS（配音即本集脚本，时长一致）")

    # ── 门禁C：③ 档「GitHub 涨星榜」A 方案格式（2026-09-13 起）──────────────
    # 为什么要有它：对标「开源情报局 GitHub 周榜」后用户裁决 A 方案（口播改成
    # 「第 N 名 + 你能拿它干什么」+ 口语化数字 + 系列集数 `EP n`）。规范不进流水线
    # 就只是一纸空文 —— 这里把它变成硬门，且**只在本期确实是榜单形态时启用**
    # （SCRIPT.md 里出现「涨星榜 / 涨星最快」），避免误杀 ① 档新闻片。
    if ("涨星榜" in script) or ("涨星最快" in script):
        # 已发布的期属于**冻结历史**：A 方案 2026-09-13 才生效，不能回头把 EP.178 判死，
        # 否则「EP.178 verify ★PASS」这条可复现记录会被新规推翻。包内有 publish-record.md
        # 即视为已发布 → 跳过（并且**明说跳过**，不静默跳过 —— 静默跳过是这个仓库踩过的坑）。
        if os.path.exists(f"{P['pkg']}/publish-record.md"):
            print("▶ 门禁C: 涨星榜 A 方案格式 —— 跳过（该包已有 publish-record.md，属已发布冻结历史）")
        else:
            print("▶ 门禁C: 涨星榜 A 方案格式（句式 / 集数 / 口语化数字）")
            rc = subprocess.run(["python3", f"{ROOT}/scripts/chai_rank_series_check.py",
                                 "--script", f"{P['ep']}/SCRIPT.md",
                                 "--spec", f"{ROOT}/specs/{ep}.json", "--ep", str(ep)],
                                capture_output=True, text=True)
            print(textwrap.indent((rc.stdout + rc.stderr).strip(), "  "))
            if rc.returncode != 0:
                raise Gate("门禁C FAIL: 涨星榜 A 方案格式未达标（见上：句式 / 集数 / 口语化数字）")
            print("  ✓ 门禁C PASS")

    # ── 门禁D：信息密度（屏上字/秒）—— 2026-09-13 从流量归因里长出来 ──────────
    # 依据（见 daily-workbench/流量归因-2026-09-13.md）：口播语速全程没变（4.3–5.1 字/秒），
    # 但屏上字/秒从 8.9 涨到 15.1。用户说「内容变乱了」，这就是量化定义。
    # 同样对**已发布**的包豁免（历史不可回改，且不能推翻既有 verify 记录）。
    if os.path.exists(f"{P['pkg']}/publish-record.md"):
        print("▶ 门禁D: 信息密度（屏上字/秒）—— 跳过（已有 publish-record.md，属已发布冻结历史）")
    else:
        print("▶ 门禁D: 信息密度（屏上字/秒）")
        rc = subprocess.run(["python3", f"{ROOT}/scripts/chai_density_check.py",
                             "--spec", f"{ROOT}/specs/{ep}.json",
                             "--duration", "0"], capture_output=True, text=True)
        # 拿不到成片时长时用 audio_meta 兜底
        if rc.returncode == 2:
            rc = subprocess.run(["python3", f"{ROOT}/scripts/chai_density_check.py",
                                 "--spec", f"{ROOT}/specs/{ep}.json",
                                 "--audio-meta", f"{P['proj']}/audio_meta.json",
                                 "--script", f"{P['ep']}/SCRIPT.md"],
                                capture_output=True, text=True)
        print(textwrap.indent((rc.stdout + rc.stderr).strip(), "  "))
        if rc.returncode == 1:
            raise Gate("门禁D FAIL: 屏上信息密度超上限（>13 字/秒）——把口径/核验/附注移到置顶评论与文案，每条只留一个主角数字")
        if rc.returncode == 0:
            print("  ✓ 门禁D 通过")
    stage_cover_check(ep, proj, P)
    stage_cover_provenance(ep, proj, P)


def stage_cover_provenance(ep, proj, P):
    """门禁F：封面文件、制作出处和平台比例；视觉质量交给当期编辑评审。

    不以相邻期封面的颜色/结构相似度阻断。固定构图会让封面趋同，
    也不能证明本期承诺在缩略图中清楚。
    """
    pkg = pathlib.Path(P["pkg"])
    names = ("cover-3x4.png", "cover-4x3.png")
    present = {name: pkg / name for name in names if (pkg / name).is_file()}
    if not present:
        print("▶ 门禁F: 包内无封面；制作阶段跳过")
        return
    missing = [name for name in names if name not in present]
    if missing:
        raise Gate(f"门禁F FAIL: 缺少平台封面 {', '.join(missing)}")
    meta_path = pkg / "cover-meta.json"
    if not meta_path.is_file():
        raise Gate("门禁F FAIL: 缺少 cover-meta.json，无法追溯封面制作来源")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise Gate(f"门禁F FAIL: cover-meta.json 无法读取：{exc}") from exc
    method = str(meta.get("generator") or meta.get("method") or "").strip()
    if not method:
        raise Gate("门禁F FAIL: cover-meta.json 缺少 generator/method")
    origin = (meta.get("source_assets") or meta.get("source") or meta.get("reference")
              or meta.get("prompt_file") or meta.get("generator_script"))
    if not origin:
        raise Gate("门禁F FAIL: cover-meta.json 缺少素材或提示词来源")
    try:
        from PIL import Image
        for name, path in present.items():
            with Image.open(path) as image:
                width, height = image.size
                image.verify()
            expected = 3 / 4 if name == "cover-3x4.png" else 4 / 3
            if min(width, height) < 1000 or abs(width / height - expected) > 0.002:
                raise Gate(
                    f"门禁F FAIL: {name} 尺寸 {width}×{height} 不符合平台比例或清晰度"
                )
            print(f"  {name}: {width}×{height}")
    except Gate:
        raise
    except Exception as exc:
        raise Gate(f"门禁F FAIL: 封面图无法解码：{exc}") from exc
    print(f"  ✓ 门禁F PASS（制作方式 {method}；尺寸与来源已记录）")
    print("  当期缩略图可读性和标题承诺仍须人工编辑评审")



def _cover_key_numbers(spec_path: str) -> list:
    """只核对封面文案自己承诺的数字，不把首帧数字强塞上封面。"""
    import re as _re
    try:
        d = json.load(open(spec_path, encoding="utf-8"))
    except Exception:
        return []
    texts = []
    cov = d.get("cover") or {}
    texts += [str(cov.get(k, "")) for k in ("hero_l1", "hero_em", "act")]
    out, seen = [], set()
    for s in texts:
        for m in _re.finditer(r"\d+(?:[.,]\d+)*\s*[万千米kK%]?", s):
            tok = _re.sub(r"\s", "", m.group(0))
            if not any(ch.isdigit() for ch in tok):
                continue
            # 只保留**利益数字**：带单位（万/千/%）或有小数、或多位数字。
            # ⚠️ 单个计数位（如「8 条」）不取：封面上通常写作中文「八个」，逼它出现数字形式是过严，
            #    实测会把正确封面判 FAIL（EP.180：封面写「八个狠货」，OCR 当然找不到 "8"）。
            has_unit = bool(_re.search(r"[万千米kK%]", tok))
            has_dot = ("." in tok) or ("," in tok)
            digits = _re.sub(r"\D", "", tok)
            if not (has_unit or has_dot or len(digits) >= 3):
                continue
            if tok not in seen:
                seen.add(tok)
                out.append(tok)
    return out


def stage_cover_check(ep, proj, P):
    """门禁E：封面逐字校验（核对封面自己的主句与数字，拦编造数字）。

    已发布的包跳过（历史不可回改）—— 与门禁C/D 同一套豁免规则。
    """
    pkg = P["pkg"]
    covers = [os.path.join(pkg, f) for f in ("cover-3x4.png", "cover-4x3.png")
              if os.path.isfile(os.path.join(pkg, f))]
    if not covers:
        print("▶ 门禁E: 封面逐字校验 —— 包里没有封面图，跳过")
        return
    if os.path.exists(os.path.join(pkg, "publish-record.md")):
        print("▶ 门禁E: 封面逐字校验 —— 跳过（已有 publish-record.md，属已发布冻结历史）")
        return
    nums = _cover_key_numbers(f"{ROOT}/specs/{ep}.json")
    # 没有数字时以主标题为 OCR 锚点；期号只列入允许数字，不强制出现。
    ep_label = None
    try:
        _d = json.load(open(f"{ROOT}/specs/{ep}.json", encoding="utf-8"))
        _k = str((_d.get("cover") or {}).get("kicker", ""))
        _m = re.search(r"EP\s*0*(\d+)", _k)
        if _m:
            ep_label = f"EP {int(_m.group(1))}"
    except Exception:
        ep_label = None
    musts = list(nums)
    allow = list(nums)
    # 无多位利益数字的任务型封面，用主标题做 OCR 锚点；避免为过门禁把期号塞回封面。
    if not musts:
        try:
            _title_anchor = str((_d.get("cover") or {}).get("hero_l1", "")).strip()
            if _title_anchor:
                musts.append(_title_anchor)
        except Exception:
            pass
    if not musts:
        try:
            _cover_meta = json.load(open(os.path.join(pkg, "cover-meta.json"), encoding="utf-8"))
            _title_anchor = str(_cover_meta.get("cover_title", "")).strip()
            if _title_anchor:
                musts.append(_title_anchor)
        except (OSError, ValueError):
            pass
    if ep_label:
        allow.append(str(int(re.search(r"\d+", ep_label).group(0))))
    # ⚠️ 2026-09-14（EP.182/183 复评 P2-6）：封面右下角的抓取日期注脚（如「09-14」）会被 OCR
    #    拆成 '09'/'14' 报「未在允许清单里的数字」，每期必挂 2 条 ⚠️。把**包名里的日期**数字
    #    （月、日、完整 YYYYMMDD）与期号一起加进允许清单，消掉这种必然噪声。
    for _tok in re.findall(r"\d+", os.path.basename(pkg.rstrip("/"))):
        if len(_tok) >= 2:
            allow.append(_tok)
            allow.append(str(int(_tok)))
    # ⚠️ 2026-09-14：`cover-prompt.json` 里**明确交给模型**的那些数字（三条清单/主副标题/横幅里的
    #    2000、20GB 等）属于"授权数字"，不该再报「模型可能编造」。从该文件里把数字全部加进白名单。
    _cp = os.path.join(ROOT, "content", f"episode-{ep}", "cover-prompt.json")
    if os.path.isfile(_cp):
        try:
            _c = json.load(open(_cp, encoding="utf-8"))
            _blob = " ".join([str(_c.get(k, "")) for k in ("kicker", "hero", "sub", "banner", "ep_label")]
                             + [str(x) for x in (_c.get("items") or [])])
            for _tok in re.findall(r"\d+", _blob):
                # ⚠️ 2026-09-17（EP.189 复评 P1-C）：原来 `len(_tok) >= 2` 会把**单个数字**丢掉，
                #    于是 VoxCPM2 / YuE2 里的 `2` 永远进不了允许清单，EP.189 每轮必报
                #    「未在允许清单里的数字 ['2']」——长期会把 ⚠️ 磨钝。授权来源里的单数字也一并放行。
                allow.append(_tok)
                allow.append(str(int(_tok)))
                allow.append(f"{int(_tok):,}")       # 2,000 这种带千分位的写法
        except Exception:
            pass
    if not musts:
        print("▶ 门禁E: spec 里无封面文案锚点，交编辑人工确认")
        return
    print(f"▶ 门禁E: 封面逐字校验（必须命中：{musts}）")
    cmd = ["python3", f"{ROOT}/scripts/chai_cover_check.py", *covers]
    for n in musts:
        cmd += ["--must", n]
    for n in allow:
        cmd += ["--allow-num", n]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(textwrap.indent((r.stdout + r.stderr).strip()[-3000:], "  "))
    if r.returncode != 0:
        raise Gate("门禁E FAIL: 封面逐字校验未过（承诺文字缺失或出现编造数字）")
    print("  ✓ 门禁E PASS")


def stage_check(ep, proj, P):
    print("▶ hyperframes check")
    for attempt in range(1, 4):
        r = subprocess.run(NPX + ["check"], cwd=P["proj"], capture_output=True, text=True)
        out = r.stdout + r.stderr
        if "Check passed" in out:
            print("  ✓ Check passed")
            return
        if "Navigation timeout" in out:
            print(f"  chrome 抖动，重试 {attempt}/3")
            subprocess.run(["pkill", "-9", "-f", "chrome-headless-shell"], capture_output=True)
            import time; time.sleep(3)
            continue
        errs = [l for l in out.splitlines() if "✗" in l][:6]
        raise Gate("check FAIL:\n" + "\n".join(errs))
    raise Gate("check FAIL: 连续 3 次 Navigation timeout")

def stage_render(ep, proj, P):
    print("▶ hyperframes render")
    subprocess.run(["pkill", "-9", "-f", "chrome-headless-shell"], capture_output=True)
    import time; time.sleep(2)
    out = sh(NPX + ["render"], cwd=P["proj"], env={**os.environ, "PATH": f"{P['proj']}/bin:{os.environ['PATH']}"})
    m = re.search(r"(renders/\S+\.mp4)", out)
    render = f"{P['proj']}/{m.group(1)}" if m else None
    if not render or not os.path.exists(render):
        raise Gate("render FAIL: 未找到渲染产物")
    print(f"  ✓ {os.path.basename(render)}")
    return render

def stage_motion(ep, proj, P, render):
    print("▶ motion QA")
    out = sh(["python3", f"{ROOT}/scripts/chai_check_motion.py", render])
    print("  " + out.strip().splitlines()[-1])
    if "PASS" not in out and "长静帧" in out:
        # GSAP CDN 偶发加载失败会导致整片冻结——重渲一次再验
        print("  ⚠ 检测到整片冻结（CDN 偶发），自动重渲一次…")
        subprocess.run(["pkill", "-9", "-f", "chrome-headless-shell"], capture_output=True)
        import time; time.sleep(3)
        render = stage_render(ep, proj, P)
        out = sh(["python3", f"{ROOT}/scripts/chai_check_motion.py", render])
        print("  " + out.strip().splitlines()[-1])
    if "PASS" not in out:
        raise Gate("motion FAIL")
    return render

def stage_qaframes(ep, proj, P, render, final=None):
    print("▶ QA 锚点帧提取（从成品抽，检查首帧与关键画面）")
    qa = f"{P['pkg']}/qa-frames"
    shutil.rmtree(qa, ignore_errors=True)
    os.makedirs(qa, exist_ok=True)
    src = final or render
    suffix = "bgm"
    cand = f"{P['pkg']}/czbvideo-{ep}-{proj}-{suffix}.mp4"
    if os.path.exists(cand):
        src = cand
    sh(["python3", f"{ROOT}/scripts/chai_qa_frames.py", src,
        f"{P['proj']}/caption_groups.json", "--out", qa])
    n = len([f for f in os.listdir(qa) if f.endswith(".jpg")])
    print(f"  ✓ {n} 帧 ← {os.path.basename(src)}")

def stage_package(ep, proj, P, render, bgm=False):
    print("▶ package: finalize_episode（正片无封面头+尾帧留白，numpy音频零拉伸）")
    os.makedirs(P["pkg"], exist_ok=True)
    suffix = "bgm" if bgm else "nobgm"
    out = f"{P['pkg']}/czbvideo-{ep}-{proj}-{suffix}.mp4"
    cmd = ["python3", f"{ROOT}/scripts/finalize_episode.py", render,
           f"{P['proj']}/covers/cover-9x16.png", out, "--no-cover"]
    if bgm:
        cmd.append("--bgm")
    out_text = sh(cmd)
    print("  " + out_text.strip().splitlines()[-1])
    # 门禁B: finalize 内已验音视频等长与收尾余量，这里复读成品
    def stream_dur(f, sel):
        r = subprocess.run([FP, "-v", "error", "-select_streams", sel, "-show_entries",
                            "stream=duration", "-of", "csv=p=0", os.path.abspath(f)],
                           capture_output=True, text=True)
        return float(r.stdout.strip())
    vd, ad = stream_dur(out, "v"), stream_dur(out, "a")
    if abs(vd - ad) > 0.1:
        raise Gate(f"门禁B FAIL: 音视频差 {abs(vd-ad):.3f}s")
    print(f"  ✓ 门禁B PASS（v={vd:.2f} a={ad:.2f}）")
    # 刷新 motion-report
    json.dump({"file": render, "fails": [], "warns": [],
               "specs": {"width": 1080, "height": 1920, "fps": 30.0,
                         "duration_s": vd, "audio_duration_s": ad},
               "motion_check": "PASS", "pipeline": "chai_pipeline 2026-09-07"},
              open(f"{P['pkg']}/motion-report.json", "w"), ensure_ascii=False, indent=2)
    # 包完整性：平台封面由当期封面流程写入，不能从旧工程模板覆盖。
    import shutil as _sh, glob as _glob
    for f in ("sources.md", "SCRIPT.md"):
        src = f"{P['ep']}/{f}"
        if os.path.exists(src):
            _sh.copy2(src, f"{P['pkg']}/{f}")
    for f in ("audio_meta.json", "caption_groups.json"):
        src = f"{P['ep']}/publish-timeline/{f}"
        if os.path.exists(src):
            _sh.copy2(src, f"{P['pkg']}/{f}")
    missing = [x for x in ("cover-3x4.png", "cover-4x3.png", "sources.md", "SCRIPT.md", "audio_meta.json",
                            "caption_groups.json", "publish-copy.md", "performance-record.md",
                            "prepublish-checklist.md", "quality-report.md", "STORYBOARD.md")
               if not os.path.exists(f"{P['pkg']}/{x}")]
    if missing:
        print(f"  ⚠ 包内待补: {', '.join(missing)}（copy/评审/分镜类文档为人工产出）")
    else:
        print("  ✓ 包完整性检查通过")
    print(f"\n★ 交付: {out} ({vd:.2f}s)")

def _voices_total(P):
    """Σ配音时长（秒）；读不到就返回 0（调用处需容忍）。"""
    import json as _json
    for _p in (f"{P['pkg']}/audio_meta.json", f"{P['ep']}/audio_meta.json"):
        try:
            if os.path.exists(_p):
                _am = _json.load(open(_p, encoding="utf-8"))
                if _am.get("voices"):
                    return sum(float(v["duration_s"]) for v in _am["voices"])
        except Exception:
            pass
    return 0.0


def verify_only(ep, proj, P):
    """秒级体检：不渲染，只跑门禁。"""
    print(f"=== verify EP.{ep} {proj} ===")
    try:
        stage_gates(ep, proj, P)
    except Gate as e:
        print(f"\n✗ {e}")
        return 1
    # 成品检查：优先 nobgm，其次 bgm
    final = None
    for suffix in ("nobgm", "bgm"):
        cand = f"{P['pkg']}/czbvideo-{ep}-{proj}-{suffix}.mp4"
        if os.path.exists(cand):
            final = cand
            break
    if final is None:
        # 2026-09-13（EP.179 复核轮次 1/2 两次点到此坑）：成片名写短了（缺完整工程名）时
        #   原来会**静默跳过**成品检查（等长/时长），manifest 却仍宣称"已检"。
        #   → 包里只要存在 czbvideo-*.mp4 但名字对不上契约，就**显式报错**，不再静默。
        import glob as _g
        _near = sorted(_g.glob(f"{P['pkg']}/czbvideo-*.mp4"))
        if _near:
            print("  X 成片文件名不符合契约，成品检查无法执行：")
            print(f"     期望：czbvideo-{ep}-{proj}-{{nobgm|bgm}}.mp4")
            for f in _near:
                print(f"     实际：{os.path.basename(f)}")
            print("     → 请改名后重跑 verify（本次**未**做等长/时长检查）")
            return 1
        print("  ! 包里还没有成片（czbvideo-*.mp4 不存在）→ 成品检查按未装配处理")
    if final:
        def stream_dur(f, sel):
            r = subprocess.run([FP, "-v", "error", "-select_streams", sel, "-show_entries",
                                "stream=duration", "-of", "csv=p=0", os.path.abspath(f)],
                               capture_output=True, text=True)
            return float(r.stdout.strip())
        vd, ad = stream_dur(final, "v"), stream_dur(final, "a")
        ok = abs(vd - ad) <= 0.1
        print(f"{'✓' if ok else '✗'} 成品流等长: v={vd:.2f} a={ad:.2f}")
        if not ok:
            return 1
        # ⚠️ 2026-09-12（EP.175 实证）：**带 BGM 的成片不能在成品上测语音终点**。
        #    BGM 垫底改到 −9dB 后，垫底自身 std≈0.03 就**高于**这里的 0.02 阈值
        #    → 检测器把**音乐淡出**当成人声终点 → 假报「收尾余量 0.59s ✗」。
        #    制作方做过控制变量隔离：同一条片子 −9dB→0.60s ✗ / −21dB→1.90s ✓ / 无BGM→1.90s ✓ /
        #    −9dB 且尾加长→仍 0.60s ✗ ⇒ 与语音无关，纯属测量口径。
        #    修法：**有 BGM 时按时间轴（audio_meta.json）算语音终点** —— 与 finalize_episode.py
        #    里「在混音前的人声轨上测」同一个道理。
        # ⚠️ 2026-09-12（EP.175 评审给的更优法）：**有 BGM 时优先在"渲染件"上测**——
        #    `videos/<proj>/renders/*render*.mp4` 就是"封面头 + 人声、无 BGM"的那一版，
        #    声学判据在它上面完全可用（实测语音终点 141.300s → 余量 1.900s，与 finalize 自己
        #    打印的 1.90s 一致）。**这样保留了原检查的覆盖度**（能抓"长度不变但人声被截"），
        #    比纯按时间轴对账更强。渲染件找不到时才回退到时间轴口径。
        is_bgm = final.endswith("-bgm.mp4")
        speech_end = None
        check_sr = 16000
        step = int(0.1 * check_sr)
        _src = None
        if is_bgm:
            # 2026-09-12（EP.175 复核轮次 2 的 P1-B）：不能只按 mtime 取最新
            #   —— 评审往 renders/ 里放了个临时件，本检查就静默改测错文件并给出假 PASS。
            #   现在优先按工程名匹配（文件名含工程 slug），匹配不到才退回 mtime 最新并告警。
            import glob as _glob
            _slug = os.path.basename(P['proj'].rstrip("/"))
            # ⚠️ P['ep'] 是**目录路径**（如 …/content/episode-175），不是期号 —— 实测踩过：
            #    直接拿它当期号 → 匹配永远失败 → 静默退回 mtime。这里改成"从两个来源里抽 3 位数字"。
            _m = re.search(r"(\d{3})", str(P.get('ep', ''))) or re.search(r"(\d{3})", _slug)
            _epno = _m.group(1) if _m else ""
            _all = _glob.glob(f"{P['proj']}/renders/*.mp4")
            # 2026-09-12（EP.175 复核轮次 2 的 P1-B 续）：光靠工程名不够——
            #   本工程的渲染件叫 `175-render.mp4`，**不含工程名** `nubia-naviax-ultra`，
            #   于是这条防线静默退回 mtime、等于没生效。改成**两级匹配**：
            #   ① 文件名含工程名（最强）→ ② 文件名含期号（如 175）→ ③ 才退回 mtime 并告警。
            def _pick(pred):
                c = [f for f in _all if pred(os.path.basename(f))]
                return sorted(c, key=lambda f: -os.path.getmtime(f))[0] if c else None
            _src = _pick(lambda n: _slug in n)
            _how_pick = "文件名含工程名"
            if _src is None and _epno:
                _src = _pick(lambda n: re.search(r"(^|\D)" + re.escape(_epno) + r"(\D|$)", n) is not None)
                _how_pick = "文件名含期号 %s" % _epno
            if _src is None and _all:
                _src = _pick(lambda n: True)
                _how_pick = "mtime 最新（**不可靠**）"
                print("  ! renders/ 里既没有含工程名 [%s] 也没有含期号 [%s] 的件，退回 mtime 最新：%s"
                      "（若这是临时件，本检查会判错）" % (_slug, _epno, os.path.basename(_src)))
            if _src is not None:
                print("  i 渲染件选择：%s（依据：%s）" % (os.path.basename(_src), _how_pick))
        if _src is not None:
            try:
                _pcm = afc_decode_path(_src, check_sr)
                _off = cover_hold_of(P["pkg"])   # 封面头时长（读包内 finalize-meta.json；旧包回退 0.4）
                # 2026-09-12（EP.175 复核轮次 2 的 P1-A）：尾余量量的是"尾部留白"，抓不到"人声被截"
                #   —— 评审给的对照实验：只砍渲染件 8.45s，本检查反而报 PASS（余量变大）；
                #   同时砍渲染件与成片时，余量恒 ~1.5s。所以这里**另加一条真正能抓截断的硬判据**：
                #   **渲染件时长必须 >= 0.4s 封面头 + Σ配音时长**（配音都装不下就是被截了）。
                _vd_render = None
                try:
                    _r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", os.path.abspath(_src)],
                                        capture_output=True, text=True)
                    _vd_render = float(_r.stdout.strip())
                except Exception:
                    pass
                if _vd_render is not None:
                    # 判据的正确形式：**渲染件的时长本身就是"配音时间轴"的长度**
                    #   （成片 = 0.4s 封面头 + 渲染件 + 尾帧，封面头是装配时加的，不在渲染件里）。
                    #   → 渲染件被截 ⇒ render_dur < Σ配音 ⇒ 报错。EP.175 的对照实验
                    #   （砍 8.45s）在这里必然被抓住：135.0 < 143.46。
                    _need = _voices_total(P)
                    if _need > 0 and _vd_render + 0.1 < _need:
                        print("  X 渲染件比配音短：渲染件 %.2fs < Σ配音 %.2fs -> 人声可能被截"
                              % (_vd_render, _need))
                        return 1
                    print("  OK 渲染件装得下配音：%.2fs >= Σ配音 %.2fs" % (_vd_render, _need))
                for i in range(_pcm.shape[0] - step, 0, -step):
                    if _pcm[i:i + step].std() > 0.02:
                        speech_end = (i + step) / check_sr + _off
                        break
                print(f"  i 有 BGM：语音终点在渲染件上测（{os.path.basename(_src)}），+{_off}s 封面头")
            except Exception as _e:
                print(f"  ! 渲染件测量失败（{_e}），回退到时间轴口径")
        if speech_end is None and is_bgm:
            try:
                import json as _json
                _am = None
                for _p in (f"{P['pkg']}/audio_meta.json", f"{P['ep']}/audio_meta.json"):
                    if os.path.exists(_p):
                        _am = _json.load(open(_p, encoding="utf-8"))
                        break
                if _am and _am.get("voices"):
                    speech_end = 0.4 + sum(float(v["duration_s"]) for v in _am["voices"])
            except Exception as _e:
                print(f"  ⚠ 读 audio_meta.json 失败（{_e}），回退到在成品上测语音终点")
        if speech_end is None:
            check_sr = 16000
            pcm = afc_decode_path(final, check_sr)
            step = int(0.1 * check_sr)
            for i in range(pcm.shape[0] - step, 0, -step):
                if pcm[i:i + step].std() > 0.02:
                    speech_end = (i + step) / check_sr
                    break
        margin = vd - (speech_end or 0)
        ok = margin >= 1.0
        _how = ("在渲染件上测·无BGM" if _src is not None else "按时间轴·混音前口径") if is_bgm else "在成品上测"
        print(f"{'✓' if ok else '✗'} 收尾余量: {margin:.2f}s（语音终于 {speech_end:.2f}s，{_how}）")
        # 2026-09-12（EP.175 复核轮次 2 遗留项的口径澄清）：
        #   声学检测器把「语音终点」读**早**约 0.4s（末段音节能量低，0.1s std 窗判不出），
        #   所以上面的余量是「声学终点→片尾」的距离，**比真实尾部留白偏大**。
        #   真实尾部留白 = 成片时长 − (封面头 + Σ配音时长)，可复算、无检测器噪声。
        #   ⚠️ 2026-09-14 起封面头由 finalize-meta.json 给出（默认 0＝封面不进成片）。
        #   两个数一起打印并**都要求 ≥1.0s**，避免再被单一数字误导。
        #   ⚠️ 这不是"漏算封面头"——已实测证否：把封面头显式补进人声轨测得 143.27s，
        #      与实际打印的语音终点逐位一致；漏算的话应差 0.4s。
        _tl = None
        try:
            _nv = _voices_total(P)
            if _nv > 0:
                _tl = vd - (cover_hold_of(P["pkg"]) + _nv)
        except Exception:
            pass
        if _tl is not None:
            _ok2 = _tl >= 1.0
            print(f"{'✓' if _ok2 else '✗'} 真实尾部留白（时间轴口径 = 成片 − {cover_hold_of(P['pkg'])}s封面头 − Σ配音）: "
                  f"{_tl:.2f}s")
            if not _ok2:
                print("  X 真实尾部留白不足 1.0s（上面那个声学余量偏大，以此为准）")
                return 1
        if not ok:
            print("  ✗ 结尾语音可能被截——用 finalize_episode.py 重新装配")
            return 1
    print("\n★ verify PASS")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["all", "verify"])
    ap.add_argument("--episode", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--from", dest="frm", default="sync",
                    choices=["sync", "gates", "check", "render", "motion", "package", "qaframes"])
    a = ap.parse_args()
    P = paths(a.episode, a.project)
    if a.mode == "verify":
        sys.exit(verify_only(a.episode, a.project, P))
    order = ["sync", "gates", "check", "render", "motion", "package", "qaframes"]
    started = order.index(a.frm)
    render = None
    if a.frm in ("motion", "package", "qaframes"):
        import glob as _g
        old = sorted(_g.glob(f"{P['proj']}/renders/*.mp4"))
        if old:
            render = old[-1]
            print(f"(复用最近渲染: {os.path.basename(render)})")
    for st in order[started:]:
        if st == "sync":
            stage_sync(a.episode, a.project, P)
        elif st == "gates":
            stage_gates(a.episode, a.project, P)
        elif st == "check":
            stage_check(a.episode, a.project, P)
        elif st == "render":
            render = stage_render(a.episode, a.project, P)
        elif st == "motion":
            stage_motion(a.episode, a.project, P, render)
        elif st == "qaframes":
            stage_qaframes(a.episode, a.project, P, render)
        elif st == "package":
            stage_package(a.episode, a.project, P, render)
    print("\n★ 全流程完成")

if __name__ == "__main__":
    main()
