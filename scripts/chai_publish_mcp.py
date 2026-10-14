#!/usr/bin/env python3
"""柴主编 · 本地 MultiPost Desktop MCP 发布器（2026-09-08）。

前置：MultiPost 桌面客户端运行中（自带本地 MCP 服务），三平台账号已登录。
Keychain service `dailyvideos-multipost-mcp-token` 存 Bearer token；
MCP_ENDPOINT 环境变量可覆盖默认 http://127.0.0.1:19528/mcp。

用法：
  python3 scripts/chai_publish_mcp.py <发布包目录>                # 填表后停在 ready（人工确认）
  python3 scripts/chai_publish_mcp.py <发布包目录> --submit       # 填表确认 ready 后自动提交发布
  python3 scripts/chai_publish_mcp.py <发布包目录> --auto-submit  # 填完直接发（不等确认）
流程：读 publish-copy.md 三平台文案 → 每平台一次 create_publish(VIDEO) → 轮询 get_publish_status
→ 全部 ready 后（--submit 时）submit_publish。置顶评论不代发。
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT", "http://127.0.0.1:19528/mcp")
KEYCHAIN_SERVICE = "dailyvideos-multipost-mcp-token"
DEFAULT_TOKEN = ""  # 不再硬编码：优先 MULTIPOST_MCP_TOKEN 环境变量，其次钥匙串

def mcp_token() -> str:
    if os.environ.get("MULTIPOST_MCP_TOKEN"):
        return os.environ["MULTIPOST_MCP_TOKEN"]
    try:
        out = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
                              "-a", "multipost", "-w"], capture_output=True, text=True).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return DEFAULT_TOKEN

def mcp_call(method, params, _id=1, timeout=60):
    body = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params}
    req = urllib.request.Request(MCP_ENDPOINT, method="POST",
        headers={"Authorization": f"Bearer {mcp_token()}",
                 "Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, data=json.dumps(body).encode(), timeout=timeout) as r:
        d = json.loads(r.read())
    if "error" in d:
        raise RuntimeError(f"MCP error: {d['error']}")
    return d["result"]

def tool_call(name, arguments, timeout=120):
    r = mcp_call("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
    txt = r.get("content", [{}])[0].get("text", "")
    try:
        return json.loads(txt)
    except Exception:
        return txt

def plain_md(s: str) -> str:
    """把发布文案里的 Markdown 强调标记去掉再上屏。

    ⚠️ 2026-09-12 修：`publish-copy.md` 是**给人读**的文档，正文用 `**加粗**` 和
    `` `代码` `` 标注重点；但 `parse_copy()` 取的是**原始文本**，而 MultiPost 的
    `create_publish.content` 是**逐字上屏**的 —— 于是 `**` 和反引号会**原样出现在
    抖音/小红书/视频号的正文里**（EP.164–169 一直如此）。这里在**送平台前**剥掉标记，
    保留文字本身与换行。只动发送内容，不改 `publish-copy.md` 的可读性。
    """
    if not s:
        return s or ""
    t = s
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t, flags=re.S)   # **加粗**
    t = re.sub(r"(?<!\w)__(.+?)__(?!\w)", r"\1", t, flags=re.S)  # __加粗__
    t = re.sub(r"`([^`]+)`", r"\1", t)                    # `行内代码`
    t = t.replace("**", "").replace("`", "")              # 兜底：落单的标记
    t = re.sub(r"[ \t]{2,}", " ", t)                      # 去重空格（不动换行）
    t = re.sub(r" \n", "\n", t)
    return t.strip()


def parse_copy(pkg: Path) -> dict:
    """与 chai_publish_multipost.parse_copy 相同逻辑：## 抖音/小红书/视频号 三节。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cpm", Path(__file__).resolve().parent / "chai_publish_multipost.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.parse_copy(pkg)

def pick_file(pkg: Path, *names: str) -> Path:
    for n in names:
        for p in sorted(pkg.glob(n)):
            return p.resolve()
    raise SystemExit(f"发布包缺文件：{names[0]}")

def _norm_title(s: str) -> str:
    """标题归一化：去空白与常见标点，只留实义字符（用于"同题"判定）。"""
    return re.sub(r"[\s，。、：:；;！!？?·\-—_/|｜\"'“”‘’()（）\[\]【】#]+", "", s or "")

def duplicate_guard(pkg: Path, copy: dict, allow: bool = False) -> None:
    """同日同题重发护栏（2026-09-13 加）。

    为什么加：逐条后台数据显示 **5 组 11 条**同题重复投稿（同一条在抖音发了 2–3 次，
    如「准备给 AI 工具充值的先停一下：B.AI…」发了 3 次：1353 / 165 / 548 播放）——
    同账号同题互相分流，还白占"新作品"名额。

    做法：扫描所有已发布包的 `publish-record.md`（mtime = 发布时间），取其 `publish-copy.md`
    的抖音/小红书/视频号标题，与本包标题比对；**同一天 + 标题归一化后相同** 即判为重复。
    """
    import datetime as _dt
    mine = {
        "抖音": _norm_title(copy.get("douyin_title")),
        "小红书": _norm_title(copy.get("xhs_title")),
        "视频号": _norm_title(copy.get("channels_title")),
    }
    today = _dt.date.today()
    hits = []
    for rec in pkg.parent.parent.glob("episode-*/publish-package-*/publish-record.md"):
        try:
            if rec.parent.resolve() == pkg.resolve():
                continue
            d = _dt.datetime.fromtimestamp(rec.stat().st_mtime).date()
            if abs((today - d).days) > 1:      # 只看最近两天（跨零点发布）
                continue
            pc = rec.parent / "publish-copy.md"
            if not pc.is_file():
                continue
            # ⚠️ parse_copy 收的是**包目录**（它自己去 glob publish-copy.md）；
            # 2026-09-13 首版误传了文件路径 → 每条比对都抛 NotADirectoryError 被 except 吞掉，
            # 护栏静默失效（"静默跳过"是本仓库反复踩的坑）。这里改成传目录，并且**不再吞异常**。
            other = parse_copy(rec.parent)
            for plat, t in mine.items():
                if not t:
                    continue
                o = {"抖音": other.get("douyin_title"), "小红书": other.get("xhs_title"),
                     "视频号": other.get("channels_title")}[plat]
                if o and _norm_title(o) == t:
                    hits.append((plat, rec.parent.name, d.isoformat(), o))
        except Exception as e:
            # 不静默：打印出来，但单条读失败不阻断发布
            print(f"  ⚠️ 重发护栏：跳过 {rec.parent.name}（读取失败：{type(e).__name__}: {e}）")
            continue
    if not hits:
        print("✓ 重发护栏：最近两天没有同题作品（本地发布记录比对通过）")
        return
    print("\n⚠️  检测到可能的重发（最近两天已发布过同题文案）：")
    for plat, p, d, o in hits:
        print(f"   · {plat}  同一标题已在 {p}（{d}）发布过：{o[:40]}")
    if allow:
        print("   → 你传了 --allow-duplicate，继续发布。")
        return
    raise SystemExit(
        "❌ 同题重发护栏拦下：同一天发同题会互相分流（实测 5 组 11 条）。\n"
        "   换选题，或确认要发就加 --allow-duplicate。")

VERIFY_JS = """(() => {
  const needle = window.__needle || '';
  // 标题/正文可能只存在于 input / textarea 的 value 里（**不进 innerText**）——
  // 2026-09-14 实测：只读 innerText 会把「已填好的标题」误判成没填（假阴性）。
  const fieldText = [...document.querySelectorAll('input,textarea')]
      .map(e => e.value || '').join(' ');
  const t = (document.body.innerText || '') + ' ' + fieldText;
  const imgs = [...document.querySelectorAll('img')].filter(i => i.naturalWidth > 150);
  // ⚠️ 2026-09-14 深夜修：**弹窗必须真的可见才算**。
  //    原来只看「有没有 [class*=dialog] 节点、节点文字里有没有字样」——视频号那个
  //    「切换视频号」弹窗实测是 `display:none`、getBoundingClientRect() 全 0，
  //    **它根本没挡人**，却被自检报成「有弹窗挡着」，白白让三期视频号停了一整天（误判）。
  //    现在用「有尺寸 且 在视口内」筛，隐藏节点一律不计。
  const blocks = [...document.querySelectorAll('[class*=dialog],[role=dialog]')]
      .map(d => {
        const r = d.getBoundingClientRect();
        if (r.width < 40 || r.height < 40) return null;         // display:none / 0 尺寸
        if (getComputedStyle(d).visibility === 'hidden') return null;
        const txt = (d.innerText || '').trim().slice(0, 60);
        return txt || null;
      }).filter(Boolean);
  const visModal = [...document.querySelectorAll('.weui-desktop-dialog__wrp,.semi-modal-wrap,.d-modal,[class*=modal]')]
      .some(d => { const r = d.getBoundingClientRect(); return r.width > 100 && r.height > 80 && getComputedStyle(d).display !== 'none'; });
  return {
    url: location.href.slice(0, 90),
    titleSeen: needle ? t.includes(needle) : null,
        coverSlots: (t.match(/(.{0,12}封面.{0,12})/g) || []).slice(0, 6),
hasCoverWord: t.includes('封面'),
    imgCount: imgs.length,
    sideImgs: imgs.map(i => i.naturalWidth + 'x' + i.naturalHeight).slice(0, 8),
    dialogs: blocks.slice(0, 3),
    visibleModal: visModal,   // 只有**真的可见**的弹窗才算数（见上方注释：视频号那次是假阳性）
    fileInputs: document.querySelectorAll('input[type=file]').length,
    videoEls: document.querySelectorAll('video').length,
    // 标题必须看**这个输入框自己**的值：只看整页文本会把「描述里带了标题」误判成「标题已填」（假阳性）
    titleField: (() => { const ti = document.querySelector('input[placeholder*="标题"]');
                         return ti ? ti.value : null; })(),
    coverImgs: [...document.querySelectorAll('img')].filter(i => i.naturalWidth > 400)
                 .map(i => i.naturalWidth + 'x' + i.naturalHeight),
  };
})()"""

def verify_filled(platform: str, account_id: str, group_id: str, needle: str) -> dict:
    """提交后**进页面自检**：标题进没进、封面槽在不在、有没有弹窗挡着。

    为什么需要（2026-09-14 实测）：MCP 的 target 状态报 `ready` **不代表表单真的填好了** ——
    视频号那次页面被「切换视频号」弹窗整个挡住（没有 input、没有 video、没有"封面"字样），
    状态却仍是 `ready`。用户问"为什么没上传封面"时，我们没有证据可查。
    """
    try:
        return tool_call("execute_group_script",
                         {"accountId": account_id, "groupId": group_id,
                          "script": VERIFY_JS.replace("const needle = window.__needle || ''",
                                                      f"const needle = {json.dumps(needle)}")},
                         timeout=60) or {}
    except Exception as e:
        return {"error": str(e)[:120]}


# ── 抖音封面 UI 兜底（2026-09-14 实测固化）────────────────────────────────────
# 为什么需要：适配器字段路径（data.cover / data.verticalCover）**只把竖封面传进去了**，
# 平台仍判「横封面缺失」；而按用户提示"分两次点入上传"（点封面槽里的「编辑封面」→
# 上传 → 完成）**两条平台告警全部消失**。所以：字段路径照发（幂等），之后**无条件再走一遍 UI 路径**。
# 实测要点（都踩过）：
#   ① 槽位顺序：`[class*=coverControl]`[0] = 竖封面 3:4、[1] = 横封面 4:3；
#   ② 每个槽里有个**悬停才出现**的「编辑封面」：`[class*=filter-k_CjvJ]`；
#   ③ 弹窗标题「设置竖封面/横封面」，里面 `input[type=file][accept*=image]`；
#   ④ 文件要用 **base64 → File → DataTransfer → dispatch change（仅一次）**（页面里拿不到本地路径，
#      适配器自己也是用 fetch(url) 这一套）；**2MB PNG 必须先转 JPEG**（base64 才 ~480KB，否则 payload 过大）；
#   ⑤ React 受控输入要填标题必须走**原生 setter**；
#   ⑥ 导航到作品管理页要用 `location.assign`（`location.href=` 会被 SPA 拦掉）。
DOUYIN_COVER_SLOTS = [
    (1, "horizontal", "cover-4x3.png", "设置横封面"),
    (0, "vertical", "cover-3x4.png", "设置竖封面"),
]


def _safe(s) -> str:
    """页面回来的字符串里可能带**孤立代理对**（emoji，例如抖音封面弹窗里的「新春🍃」）。

    2026-09-18 实测：`print()` 这种字符串直接抛 `UnicodeEncodeError: surrogates not allowed`，
    而抖音封面 UI 兜底整段是包在 try/except 里的 → **异常被吞掉、封面一个都没上传**，
    发布日志里只留一行「⚠️ 抖音封面 UI 兜底出错（不影响发布主流程）」，
    结果竖封面又变成平台拿 4:3 裁的（门禁G 才抓出来）。
    """
    try:
        return str(s).encode('utf-8', 'replace').decode('utf-8')
    except Exception:
        return '<unprintable>'


def _cover_b64_jpeg(png_path: str, quality: int = 90) -> str:
    """封面 → JPEG → base64（缩小 payload；页面里只吃 base64/URL）。"""
    import base64 as _b64
    from PIL import Image
    out = os.path.join("/tmp", os.path.basename(png_path).replace(".png", ".cover.jpg"))
    Image.open(png_path).convert("RGB").save(out, "JPEG", quality=quality, optimize=True)
    return _b64.b64encode(open(out, "rb").read()).decode()


def _open_cover_editor(account_id: str, group_id: str, slot: int) -> str:
    # ⚠️ 2026-09-18 修：原来的选择器写死了 `[class*=filter-k_CjvJ]` —— 抖音换了构建哈希，
    #    该选择器**静默失配**，UI 兜底整段变成空转（发布日志里看不到任何报错），
    #    结果「竖封面」槽一直是平台拿横封面 4:3 中心裁出来的图（用户肉眼发现「3x4 上传的不对」）。
    #    现在改成：① 只认**可见**的「编辑封面」；② 先派发 mouseover/mouseenter（它是 hover 才显示的）；
    #    ③ 兜底再退到 `[class*=filter-]` / `[class*=hover-show]`；④ 回读弹窗标题。
    js = """(async () => {
      const boxes = [...document.querySelectorAll('[class*=coverControl]')];
      const box = boxes[%d];
      if (!box) return 'no box';
      const cands = [...box.querySelectorAll('*')].filter(e => (e.innerText||'').trim() === '编辑封面');
      const edit = cands.find(e => e.offsetHeight > 0) || cands[0]
                || box.querySelector('[class*=filter-]') || box.querySelector('[class*=hover-show]');
      if (!edit) return 'no edit control';
      edit.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
      edit.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
      await new Promise(r => setTimeout(r, 800));
      edit.click();
      await new Promise(r => setTimeout(r, 4000));
      const d = [...document.querySelectorAll('[class*=modal],[class*=dialog],[class*=Dialog],[class*=Modal]')]
          .filter(e => e.offsetHeight > 0)
          .map(e => (e.innerText||'').slice(0, 30)).filter(t => t.includes('封面')).pop();
      return d || 'dialog not found';
    })()""" % slot
    try:
        return _safe(tool_call("execute_group_script",
                              {"accountId": account_id, "groupId": group_id, "script": js}, timeout=90))
    except Exception as e:
        return f"error: {e}"


def _upload_cover_in_dialog(account_id: str, group_id: str, orient: str, b64: str, dlg_name: str) -> str:
    js = """(async () => {
      const b64 = "%s";
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const file = new File([bytes], '%s.jpg', { type: 'image/jpeg' });
      const dlg = [...document.querySelectorAll('[class*=modal],[class*=dialog],[class*=Dialog],[class*=Modal]')]
          .filter(d => d.offsetHeight > 0 && (d.innerText||'').includes('%s')).pop();
      if (!dlg) return 'dialog gone';
      const inputs = [...dlg.querySelectorAll('input[type=file]')];
      const input = inputs.find(e => (e.accept||'').includes('image')) || inputs[0];
      if (!input) return 'no file input';
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      // File inputs upload on change. A second input event can start a duplicate upload.
      await new Promise(r => setTimeout(r, 5000));
      let done;
      const finishDeadline = Date.now() + 40000;
      do {
        done = [...dlg.querySelectorAll('button')].find(e => e.offsetHeight > 0
          && (e.innerText||'').trim() === '完成' && !e.disabled);
        if (done) break;
        await new Promise(r => setTimeout(r, 500));
      } while (Date.now() < finishDeadline);
      if (!done) return 'uploaded (完成 not found)';
      done.click();
      await new Promise(r => setTimeout(r, 4000));
      // 回读：这一槽现在的图（不同槽必须是不同的资源 id，2026-09-18 事故就是两槽同图）
      const boxes = [...document.querySelectorAll('[class*=coverControl]')];
      const ids = boxes.map(b => { const im = b.querySelector('img');
        const m = (im && im.src || '').match(/tos-cn-i-dy\/([0-9a-f]+)/); return m ? m[1].slice(0, 12) : 'none'; });
      return 'uploaded+done · 槽位资源 ' + JSON.stringify(ids);
    })()""" % (b64, orient, dlg_name)
    try:
        return _safe(tool_call("execute_group_script",
                              {"accountId": account_id, "groupId": group_id, "script": js}, timeout=180))
    except Exception as e:
        return f"error: {e}"


def set_schedule_ui(account_id: str, group_id: str, when: str) -> str:
    """在发布页设「定时发布 + 日期时间」。

    实测（2026-09-14）：抖音表单有「发布时间：立即发布 / 定时发布」，并提示
    「支持2小时后及14天内的定时发布」；定时输入框 `input[placeholder*="日期和时间"]` 默认值是"现在+2 小时"。
    React 受控输入必须走**原生 setter**。
    """
    js = """(async () => {
      const target = %s;
      let el = null;
      for (const e of document.querySelectorAll('label,div,span')) {
        if ((e.innerText||'').trim() === '定时发布') { el = e; break; }
      }
      if (!el) return 'no 定时发布 option (platform may not support scheduling)';
      (el.closest('label') || el).click();
      await new Promise(r => setTimeout(r, 1200));
      const inp = document.querySelector('input[placeholder*="日期和时间"]');
      if (!inp) return '定时发布 clicked but no date input';
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(inp, target);
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
      inp.blur();
      await new Promise(r => setTimeout(r, 1000));
      return 'schedule set: ' + inp.value;
    })()""" % json.dumps(when)
    try:
        return _safe(tool_call("execute_group_script",
                              {"accountId": account_id, "groupId": group_id, "script": js}, timeout=90))
    except Exception as e:
        return f"error: {e}"


def douyin_upload_covers_ui(account_id: str, group_id: str, pkg: Path) -> None:
    """在**已填好表**的抖音发布页上，把两个封面槽各点一次「编辑封面」并上传。"""
    for slot, orient, fname, dlg_name in DOUYIN_COVER_SLOTS:
        src = pkg / fname
        if not src.is_file():
            raise FileNotFoundError(f"缺少指定封面 {fname}，停止该平台准备")
        try:
            b64 = _cover_b64_jpeg(str(src))
        except Exception as e:
            raise RuntimeError(f"{fname} 转 JPEG 失败，停止该平台准备") from e
        opened = _open_cover_editor(account_id, group_id, slot)
        print(_safe(f"  槽{slot}（{dlg_name}）编辑器：{opened[:40]} → 上传 {fname}（{len(b64)//1024}KB base64）"))
        res = _upload_cover_in_dialog(account_id, group_id, orient, b64, dlg_name)
        print(_safe(f"    结果：{res[:80]}"))
        if not res.startswith('uploaded+done'):
            raise RuntimeError('Cover editor has not finished; inspect this slot before proceeding')


def douyin_cover_state(account_id: str, group_id: str, tries: int = 3) -> dict:
    """回读抖音封面两槽的图尺寸 + 平台封面告警 + 标题栏值。

    ⚠️ 2026-09-14 实测：**上传刚结束时立刻读会抛错**（弹窗关闭的动画期里 DOM 不稳），
    所以这里① JS 内部每段各自 try ② 失败自动重试 2 次（间隔 2s）——单独读稳、连读要稳。
    """
    js = """(() => {
      const out = { boxes: [], advice: '', title: null, err: '' };
      try {
        out.boxes = [...document.querySelectorAll('[class*=coverControl]')].map(b => {
          try {
            const im = b.querySelector('img');
            const label = (b.innerText || '').replace(/\s+/g, '').slice(0, 12);
            return label + ':' + (im ? im.naturalWidth + 'x' + im.naturalHeight : 'none');
          } catch (e) { return 'err'; }
        });
      } catch (e) { out.err += 'boxes:' + e.message + ';'; }
      try {
        const t = document.body.innerText || '';
        const i = t.indexOf('封面优化建议');
        out.advice = i >= 0 ? t.slice(i, i + 100).replace(/\s+/g, ' ') : '';
      } catch (e) { out.err += 'advice:' + e.message + ';'; }
      try {
        const ti = document.querySelector('input[placeholder*="标题"]');
        out.title = ti ? ti.value : null;
      } catch (e) { out.err += 'title:' + e.message + ';'; }
      return out;
    })()"""
    last = {}
    for k in range(tries):
        try:
            r = tool_call("execute_group_script",
                          {"accountId": account_id, "groupId": group_id, "script": js}, timeout=60)
            if isinstance(r, dict) and r.get("boxes") is not None:
                return r
            last = r if isinstance(r, dict) else {"error": str(r)[:160]}
        except Exception as e:
            last = {"error": str(e)[:160]}
        time.sleep(2)
    return last if isinstance(last, dict) else {"error": str(last)[:160]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg")
    ap.add_argument("--auto-submit", action="store_true", help="已禁用：自动提交可能早于封面核对")
    ap.add_argument("--submit", action="store_true", help="已禁用：请在已有任务中核对后提交，勿再次创建")
    ap.add_argument("--keep-open", action="store_true", help="发布后不关发布窗口（缺省会关）")
    ap.add_argument("--close-delay", type=float, default=25.0, help="看到 ready/success 后再等几秒才关窗（给 autoSubmit 留点发布动作时间，缺省 25s）")
    ap.add_argument("--wait", type=int, default=120, help="填表等待秒数")
    ap.add_argument("--only", help="只发某平台 douyin|xiaohongshu|weixinchannel")
    ap.add_argument("--manual", default="",
                    help="逗号分隔的平台：这些平台只填表不自动提交，留给用户手点"
                         "（默认 xiaohongshu 因 MultiPost 封面选择器 bug 需手点；传 'none' 表示全部自动）")
    ap.add_argument("--no-cover", default="",
                    help="逗号分隔的平台：这些平台不传封面，让平台取视频首帧"
                         "（如 --no-cover douyin,weixinchannel）。默认全传。")
    ap.add_argument("--schedule", default="",
                    help='定时发布（平台侧）："YYYY-MM-DD HH:MM"（抖音支持 2 小时后 ~ 14 天内）。'
                         '⚠️ 给了定时就**不走 autoSubmit** —— 脚本填完表、传完封面、设好时间后才显式提交一次。'
                         '不支持的平台会打印警告。')
    ap.add_argument("--no-cover-ui", action="store_true",
                    help="跳过抖音的封面 UI 兜底（默认会对两个封面槽各点一次「编辑封面」并上传）")
    ap.add_argument("--allow-duplicate", action="store_true",
                    help="跳过「同日同题重发」护栏（默认拦下：同题并发会互相分流）")
    a = ap.parse_args()

    # 旧入口会创建新 group；不能用再次运行来提交或恢复已有任务。
    # autoSubmit 在下方封面核对前就可能触发，故该入口仅保留准备模式。
    if a.auto_submit or a.submit or a.schedule:
        ap.error("此旧入口仅用于准备草稿。请复核原 group 的实际标题、正文、两个封面槽、AI 标识及可见性后，在同一发布页提交一次；不要重新建任务。见 workflows/chai-platform-publish-playbook.md")
    if a.no_cover:
        ap.error("本流程要求指定比例封面；不允许静默改用首帧。")

    pkg = Path(a.pkg).resolve()
    copy = parse_copy(pkg)
    duplicate_guard(pkg, copy, allow=a.allow_duplicate)
    video = pick_file(pkg, "czbvideo-*-bgm.mp4", "czbvideo-*-nobgm.mp4", "*.mp4")
    # 必须提供指定比例封面，不用另一比例回退
    def _cover_or_fallback(name: str) -> str:
        if (pkg / name).is_file():
            return name
        raise SystemExit(f"缺少指定比例封面 {name}；请补齐，禁止用另一比例回退。")
    nocover = {x.strip() for x in a.no_cover.split(",") if x.strip()}
    _m = {x.strip() for x in (a.manual or "xiaohongshu").split(",") if x.strip()}
    manual = set() if "none" in _m else _m

    accounts = tool_call("list_accounts", {})
    by_platform = {x["platform"]: x for x in accounts if x.get("isLoggedIn")}
    targets = [
        # ⚠️ 抖音**要两张封面**（2026-09-14 读 MultiPost 适配器源码 + 实测确认）：
        #    data["cover"]         → uploadHorizontalCover() → 页面上的「横封面 4:3」
        #    data["verticalCover"] → uploadVerticalCover()   → 页面上的「竖封面 3:4」（信息流显示位）
        #    此前只传了 cover（=4:3），所以竖封面一直是平台自抽帧。下面单独为抖音补 verticalCover。
        #    同时封面不再拼进成片（finalize --no-cover），改为这里按平台单独上传。
        # ⚠️ 2026-09-14 实测更正：抖音发布页有**两个封面槽**——「竖封面 3:4」（信息流里显示的就是它）
        #    与「横封面 4:3」。给 4:3 只会进横槽，**竖槽留给平台自抽帧**，抖音还会提示
        #    「你的作品封面可能存在以下问题，会影响作品的流量」。→ 主位必须给 **3:4**。
        ("douyin",     copy.get("douyin_title"),   copy.get("douyin_body"),   copy.get("douyin_tags"),   "cover-4x3.png"),
        ("xiaohongshu", copy.get("xhs_title"),     copy.get("xhs_body"),      copy.get("xhs_tags"),      "cover-3x4.png"),
        ("weixinchannel", copy.get("channels_title"), copy.get("channels_body"), copy.get("channels_tags"), "cover-3x4.png"),
    ]
    targets = [(pl, ti, bo, tg, _cover_or_fallback(cv)) for pl, ti, bo, tg, cv in targets]
    if a.only:
        targets = [t for t in targets if t[0] == a.only]

    groups = {}
    for platform, title, body, tags, cover_name in targets:
        acc = by_platform.get(platform)
        if not acc:
            print(f"⚠ {platform}: 无已登录账号，跳过")
            continue
        tag_list = [t.lstrip("#").strip() for t in (tags or "").split() if t.lstrip("#")]
        data = {"title": plain_md(title or ""), "content": plain_md(body or ""),
                "video": str(video), "tags": tag_list}
        # ── 抖音标题：适配器**不填标题栏**（2026-09-14 实测）──────────────────
        # 实测（只填表不提交，进页面读表单）：
        #   · 「作品描述」= 我们给的 content ✓
        #   · 「填写作品标题…」input 的 value = **空**（页面计数 0/30）→ 我们备好的标题从来没上过
        # 后果：抖音信息流里的标题取的是**描述的第一行**，所以后台作品名一直是正文首句。
        # 修法：把标题作为描述的**第一行**拼进去（这样标题就是我们写的，而不是正文首句）。
        if platform == "douyin" and data["title"]:
            first_line = (data["content"] or "").strip().split("\n")[0].strip()
            if data["title"].strip() != first_line:
                data["content"] = data["title"].strip() + "\n" + (data["content"] or "")
                print(f"  ℹ {platform}: 标题栏适配器不填 → 已把标题并入描述首行：「{data['title'][:22]}」")
        # 抖音：横封面（cover）+ 竖封面（verticalCover）**两张都要传**
        if platform == "douyin" and "verticalCover" not in data:
            try:
                v = pick_file(pkg, "cover-3x4.png")
                data["verticalCover"] = str(v)
                print(f"  竖封面 → cover-3x4.png（{v.stat().st_size // 1024} KB）")
            except SystemExit:
                print("  ⚠️ 包里没有 cover-3x4.png，抖音竖封面将留空（平台会自抽帧）")
        if platform in nocover:
            print(f"ℹ {platform}: --no-cover，不传封面（由平台取视频首帧）")
        else:
            cov = pick_file(pkg, cover_name)
            data["cover"] = str(cov)
            # 回显实际用的封面（2026-09-14 加：用户问"为什么没上传封面"，当时无从确认到底传了什么）
            print(f"  封面 → {cover_name}（{cov.stat().st_size // 1024} KB · {cov}）")
        if a.schedule and a.auto_submit:
            print("  ℹ 传了 --schedule → 本次不用 autoSubmit（填完/封面/时间设好后再显式提交一次）")
        auto = bool(a.auto_submit) and platform not in manual and not a.schedule
        if a.auto_submit and platform in manual:
            print(f"ℹ {platform}: 只填表不自动提交（--manual），留给用户手点")
        r = tool_call("create_publish", {"contentType": "VIDEO", "accountIds": [acc["id"]],
                                         "data": data, "autoSubmit": auto})
        gid = r.get("groupId") if isinstance(r, dict) else None
        print(f"▶ {platform}: groupId={gid}")
        if gid:
            groups[platform] = gid

    if not groups:
        raise SystemExit("没有任何平台创建成功")

    # 轮询到 terminal
    deadline = time.time() + a.wait
    states = {}
    while time.time() < deadline:
        states = {}
        for pf, gid in groups.items():
            try:
                st = tool_call("get_publish_status", {"groupId": gid})
                states[pf] = st
            except Exception as e:
                states[pf] = {"error": str(e)}
        line = " | ".join(f"{pf}={json.dumps(s, ensure_ascii=False)[:90]}" for pf, s in states.items())
        print(f"[{int(a.wait - (deadline - time.time())):3d}s] {line}")
        def _terminal(s):
            j = json.dumps(s, ensure_ascii=False)
            return any(t in j for t in ('"ready"', '"success"', '"failed"', '"cancelled"'))
        if states and all(_terminal(s) for s in states.values()):
            break
        time.sleep(6)

    print("\n== 最终状态 ==")
    # ── 提交后自检（2026-09-14 加）：MCP 的 ready 不等于"真的填好了" ──
    print("\n== 提交前自检（进页面核实标题/封面）==")
    _needles = {"douyin": copy.get("douyin_title"), "xiaohongshu": copy.get("xhs_title"),
                "weixinchannel": copy.get("channels_title")}
    for platform, gid in groups.items():
        acc_id = (by_platform.get(platform) or {}).get("id")
        # 抖音：**无条件走一遍 UI 兜底**（字段路径只保证竖封面，横封面平台会判缺失）。
        # 封面失败必须保持草稿，不能进入提交；本入口不再自动提交。
        if platform == "douyin" and acc_id and not getattr(a, "no_cover_ui", False):
            try:
                print("\n== 抖音封面 UI 兜底（横 4:3 → 竖 3:4，竖槽最后）==")
                douyin_upload_covers_ui(acc_id, gid, pkg)
                st = douyin_cover_state(acc_id, gid)
                print(_safe(f"  回读：封面槽 {st.get('boxes')}"))
                if st.get("title") in (None, ""):
                    # 标题兜底也放这里：封面兜底跑完顺手把标题补上
                    title = (_needles.get(platform) or "")
                    js_title = ("(() => { const el = document.querySelector('input[placeholder*=\"标题\"]'); "
                                "if (!el) return 'no title input'; "
                                "const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; "
                                "setter.call(el, " + json.dumps(title) + "); "
                                "el.dispatchEvent(new Event('input',{bubbles:true})); "
                                "el.dispatchEvent(new Event('change',{bubbles:true})); "
                                "return el.value; })()")
                    r2 = tool_call("execute_group_script",
                                   {"accountId": acc_id, "groupId": gid, "script": js_title}, timeout=60)
                    print(f"  标题兜底：{str(r2)[:60]}")
                    st = douyin_cover_state(acc_id, gid)
                print(f"  最终：封面槽 {st.get('boxes')} · 标题栏 {st.get('title')!r} · "
                      f"封面告警 {st.get('advice') or '（无 → 封面通过）'}")
            except Exception as _e:
                print(f"  ❌ 抖音封面准备失败，保留原任务待修复，禁止提交：{type(_e).__name__}: {_e}")
                states[platform] = {"status": "blocked", "reason": "cover verification failed"}
                continue
        v = verify_filled(platform, acc_id, gid, (_needles.get(platform) or "")[:12])
        if not isinstance(v, dict) or v.get("error"):
            print(f"  ⚠️ {platform}: 自检执行失败 {str(v)[:120]}")
            continue
        _tf = v.get("titleField")
        if _tf is None:
            ok_title = "❌ 找不到标题输入框"
        elif _tf == "":
            ok_title = "❌ 标题栏是空的"
        else:
            ok_title = "✅ 标题栏已填"
        ok_cover = "✅" if v.get("hasCoverWord") else "❌ 页面里没有'封面'字样"
        print(f"  {platform}: {ok_title} · {ok_cover} · 文件输入框 {v.get('fileInputs')} 个 · "
              f"video 元素 {v.get('videoEls')} 个")
        print(f"     标题栏值：{v.get('titleField')!r}")
        print(f"     封面大图：{v.get('coverImgs')}")
        if v.get("coverSlots"):
            print(f"     封面槽位：{v['coverSlots']}")
        if v.get("dialogs") or v.get("visibleModal"):
            print(f"     ⚠️ 有弹窗挡着（已按「真的可见」筛过）：{v.get('dialogs')} visibleModal={v.get('visibleModal')}")
        # 标题兜底：**看标题输入框自己**是不是空的（适配器的 fillTitle 实测没生效）→ 自己填一次
        if v.get("titleField") in (None, ""):
            title = (_needles.get(platform) or "")
            js = ("(() => { const el = document.querySelector('input[placeholder*=\"标题\"]') "
                  "|| document.querySelector('input[placeholder*=\"填写作品标题\"]'); "
                  "if (!el) return {ok:false, why:'title input not found'}; "
                  "const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; "
                  "setter.call(el, " + json.dumps(title) + "); "
                  "el.dispatchEvent(new Event('input',{bubbles:true})); "
                  "el.dispatchEvent(new Event('change',{bubbles:true})); "
                  "return {ok:true, val: el.value.slice(0,40)}; })()")
            r2 = (tool_call("execute_group_script",
                            {"accountId": acc_id, "groupId": gid, "script": js}, timeout=60)
                  if acc_id else {"error": "no accountId"})
            print(f"     ↳ 标题兜底：{str(r2)[:140]}")
        if not (v.get("titleSeen") and v.get("hasCoverWord")):
            print(f"     ❗{platform} 这条**不要当作发成功** —— 请人工确认后再决定重发")

    for pf, s in states.items():
        print(f"-- {pf}: {json.dumps(s, ensure_ascii=False)[:400]}")

    # ── 定时发布（顺序关键：填表 → 封面 UI 兜底 → 标题兜底 → **设定时** → 显式提交一次）──
    if a.schedule:
        print(f"\n== 设定时发布：{a.schedule} ==")
        for pf, gid in groups.items():
            acc_id_ = (by_platform.get(pf) or {}).get("id")
            if not acc_id_:
                continue
            print(f"  {pf}: {set_schedule_ui(acc_id_, gid, a.schedule)[:90]}")
        print("== 设定时后**显式提交一次** ==")
        for pf, gid in groups.items():
            r = tool_call("submit_publish", {"groupId": gid})
            print(f"  {pf}: {json.dumps(r, ensure_ascii=False)[:150]}")
        time.sleep(8)
        for pf, gid in groups.items():
            st = tool_call("get_publish_status", {"groupId": gid})
            print(f"-- {pf} 提交后: {json.dumps(st, ensure_ascii=False)[:260]}")

    ready = [pf for pf, s in states.items() if '"ready"' in json.dumps(s)]
    if a.auto_submit:
        print("\n== autoSubmit 已开启，客户端会自动提交 ==")
    elif a.submit and ready:
        print(f"\n== 提交发布: {ready} ==")
        for pf in ready:
            r = tool_call("submit_publish", {"groupId": groups[pf]})
            print(f"  {pf}: {json.dumps(r, ensure_ascii=False)[:200]}")
        time.sleep(8)
        for pf in ready:
            st = tool_call("get_publish_status", {"groupId": groups[pf]})
            print(f"-- {pf} 提交后: {json.dumps(st, ensure_ascii=False)[:300]}")
    elif ready and not a.schedule:
        print(f"\n已就绪待人工确认: {ready}")
        print("确认无误后执行: python3 scripts/chai_publish_mcp.py --submit  需配合同一包目录定位 groupId，")
        print("或直接在 MultiPost 客户端里点发布。")

    # 发布后关闭窗口（2026-09-09 用户要求「发布完记得关窗口」）
    # ⚠️ 2026-09-12 修：**旧判断只看 `"success"`，而这一版 MultiPost 提交成功后组状态仍停在
    # `preparing` / 目标状态停在 `ready`** → 条件永不成立，窗口一直留着（用户反馈）。
    # 现在改成：只要是「已填好并可提交」的终态（`ready` / `success` / `completed`）就关，
    # 但 **先等 `--close-delay` 秒**，否则会把 autoSubmit 客户端的"点发布"动作打断。
    # 失败目标（小红书那个封面触发器 bug）**保留窗口**，方便人工接着点。
    if a.keep_open or not (a.auto_submit or a.submit or a.schedule):
        print("\nℹ --keep-open：保留发布窗口不关")
    else:
        time.sleep(max(0, a.close_delay))
        for pf, gid in groups.items():
            try:
                st = tool_call("get_publish_status", {"groupId": gid})
                j = json.dumps(st, ensure_ascii=False)
                tg = (st.get("targets") or [{}])[0]
                tstat = tg.get("status", "")
                if '"failed"' in j or tstat == "failed":
                    print(f"ℹ {pf} 失败（表单保留供人工处理，不关窗口）")
                    continue
                if ('"ready"' in j or '"success"' in j or tstat in ("ready", "success", "completed")
                        or st.get("status") in ("completed", "success")):
                    tool_call("close_publish", {"groupId": gid})
                    print(f"✓ 已关闭 {pf} 发布窗口")
                else:
                    print(f"ℹ {pf} 状态 {st.get('status')}/{tstat}，未达可关闭终态，保留窗口")
            except Exception as e:
                print(f"⚠ {pf} 关窗失败：{e}")

if __name__ == "__main__":
    main()
