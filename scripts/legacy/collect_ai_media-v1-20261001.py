#!/usr/bin/env python3
"""AI 媒体信源采集器（2026-09-28 新增）——把中文 AI 媒体当「今天的线索源」。

为什么要它（一句话）：现有雷达是**开发者雷达**（HackerNews + GitHub Trending + HF + 知乎热榜），
它看得见「哪个仓库在涨星」，看不见「今天谁发了什么模型 / 芯片 / 出了什么事故」。
实测对照（2026-09-27）：雷达选出来的是 4,851★ / 4,384★ / 2,541★ 的开源仓库，
而量子位同一天在讲 GPT-6 Astra 搓 3D、OpenAI Agent 失控、高通 2nm、平头哥开源芯片。
用户点名的 Muse 与 Claude Opus 5.5，**雷达两个都没抓到**。

⚠️ 纪律（不许破）：**这些媒体只当「线索源」，不当事实源。**
   本频道每条事实必须有**官方一手源**（发布页 / 仓库 / 文档）。媒体标题只能用来回答
   「今天有什么值得做」，最终仍要回官方源逐条核 —— 否则就是把二手转述当一手事实。

输出：/tmp/ai-media.json  —— [{source, title, url, hint}]
用法：python3 scripts/collect_ai_media.py [--json 路径] [--hours 48]
"""
import argparse, html, json, re, subprocess, sys, time, urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s))).strip()


def qbitai():
    """量子位：首页文章链接是 /YYYY/MM/<id>.html，静态可抓。"""
    t = fetch("https://www.qbitai.com")
    out, seen = [], set()
    for u, y, mo, inner in re.findall(
            r'<a[^>]+href="(https://www\.qbitai\.com/(\d{4})/(\d{2})/\d+\.html)"[^>]*>(.*?)</a>', t, re.S):
        ti = clean(inner)
        if len(ti) < 8 or u in seen:
            continue
        seen.add(u)
        out.append({"source": "量子位", "title": ti, "url": u, "hint": f"{y}-{mo}"})
    return out


def zhidx():
    """智东西：/p/<id>.html，静态可抓。"""
    t = fetch("https://zhidx.com")
    out, seen = [], set()
    for u, inner in re.findall(r'<a[^>]+href="(https?://zhidx\.com/p/\d+\.html)"[^>]*>(.*?)</a>', t, re.S):
        ti = clean(inner)
        if len(ti) < 8 or u in seen:
            continue
        seen.add(u)
        out.append({"source": "智东西", "title": ti, "url": u, "hint": ""})
    return out


def ithome_ai():
    """IT之家 AI 频道：列表项在同一屏，用标题长度 + 链接形态过滤侧栏。"""
    t = fetch("https://www.ithome.com/ai")
    out, seen = [], set()
    for u, inner in re.findall(r'<a[^>]+href="(https://www\.ithome\.com/0/\d+/\d+\.htm)"[^>]*>(.*?)</a>', t, re.S):
        ti = clean(inner)
        if len(ti) < 12 or u in seen:
            continue
        seen.add(u)
        out.append({"source": "IT之家·AI", "title": ti, "url": u, "hint": ""})
    return out


def jiqizhixin_browser():
    """机器之心是 JS 壳，curl 只拿到空模板 → 走本机 ego-browser 渲染（与 HN/GitHub 采集同一套）。"""
    script = r'''
import { chromium } from 'playwright';
const b = await chromium.launch({ channel: 'ego-lite' });
const ctx = b.contexts()[0] || await b.newContext();
const p = await ctx.newPage();
await p.goto('https://www.jiqizhixin.com/', { waitUntil: 'domcontentloaded', timeout: 45000 });
await p.waitForTimeout(4000);
const rows = await p.$$eval('a[href^="/articles/"]', as => as.map(a => ({t: (a.innerText||'').replace(/\s+/g,' ').trim(), h: a.getAttribute('href')})));
console.log('===JSON===');
console.log(JSON.stringify(rows.filter(r => r.t.length > 8).slice(0, 30)));
await b.close();
'''
    try:
        r = subprocess.run(["ego-browser", "nodejs"], input=script, capture_output=True, text=True, timeout=180)
    except Exception as e:
        print(f"  ⚠️ 机器之心浏览器采集失败：{e}", file=sys.stderr)
        return []
    m = re.search(r"===JSON===\s*(\[.*\])", r.stdout, re.S)
    if not m:
        print(f"  ⚠️ 机器之心没读到列表（{r.stdout[-120:].strip()[:120]}）", file=sys.stderr)
        return []
    return [{"source": "机器之心", "title": clean(x["t"]),
             "url": "https://www.jiqizhixin.com" + x["h"], "hint": ""} for x in json.loads(m.group(1))]


SOURCES = [("量子位", qbitai), ("智东西", zhidx), ("IT之家·AI", ithome_ai), ("机器之心", jiqizhixin_browser)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/ai-media.json")
    ap.add_argument("--hours", type=int, default=48, help="保留最近多少小时（仅用于报告提示，标题本身不带精确时间）")
    a = ap.parse_args()

    allrows = []
    for name, fn in SOURCES:
        try:
            rows = fn()
            print(f"  ✓ {name}: {len(rows)} 条")
            allrows += rows
        except Exception as e:
            print(f"  ❌ {name}: {type(e).__name__}: {str(e)[:80]}")

    # 去重（同标题）
    seen, keep = set(), []
    for r in allrows:
        k = re.sub(r"\W+", "", r["title"])[:40]
        if k in seen:
            continue
        seen.add(k)
        keep.append(r)

    open(a.json, "w", encoding="utf-8").write(json.dumps(keep, ensure_ascii=False, indent=1))
    print(f"\n共 {len(keep)} 条 → {a.json}")
    for r in keep[:20]:
        print(f"   [{r['source']}] {r['title'][:56]}")
    print(f"\n⚠️ 这些只是**线索**：每条事实仍须回官方一手源核对（见 sources.md 纪律）。")


if __name__ == "__main__":
    main()
