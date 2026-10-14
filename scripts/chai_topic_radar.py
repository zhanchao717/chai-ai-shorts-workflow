#!/usr/bin/env python3
"""旧版工具雷达（2026-10-01 起只允许 --legacy；现行入口 chai_news_radar.py）。

以下为历史规则说明，不是现行编辑准则。
选题雷达：每天把「候选选题」从网上拉回来、按我们自己踩出来的规则打分排序。

**为什么是脚本、不是把判断交给一个模型**（2026-09-22 用户问「能不能让 jev 帮选选题」）：
  · jev 是**浏览器智能体**（官方原话：`a browser agent with a dynamic, indexed action space`，
    它只挑「操作 + 元素」）—— 它擅长的是**在没有 API 的页面上干活**，不是做编导判断；
  · 而这个频道的选题规则是从**自己 356 条作品数据**里归因出来的（见 `流量归因-2026-09-13.md`：
    TOP10 全是 ≤1 分钟 + 「清单 / 省钱 / 本地能跑 / 刚开源」这类"我马上能用"），
    这是**可编码的**，交给模型反而不可复现、且没法解释「为什么选它」。
  · 所以分工：**采集**可以自动化（本脚本 + 必要时用浏览器智能体补没有 API 的榜单页），
    **打分**用脚本（可复现、可解释），**拍板**留给人。

打分维度（都来自既有归因，不是拍脑袋）：
  ① 「三件套」可组性：能不能凑够 3 个同类工具（清单型是 TOP10 的第一共同点）
  ② 我马上能用：命中 本地跑 / 免费 / 不用买会员 / 刚开源 这些框架词
  ③ 数字好讲：有星标量级、有官方自述的硬指标
  ④ 一手源可得：README / LICENSE 能抓到（否则整期都是二手转述）
  ⑤ 去重：这个仓库/选题以前做过没有（扫历史 `sources.md` 的仓库地址）
  ⑥ 新鲜度：建仓时间与当前星标的比值（涨得快 = 平台愿意推）

用法：
  python3 scripts/chai_topic_radar.py                 # 默认：最近 45 天建仓、≥300 星
  python3 scripts/chai_topic_radar.py --days 14 --min-stars 800 --top 12
  python3 scripts/chai_topic_radar.py --json /tmp/radar.json
  # 合并浏览器侧榜单（HN / GitHub Trending / Product Hunt / 知乎热榜）的候选：
  python3 scripts/chai_topic_radar.py --with-web /tmp/hot-candidates.json

  一条龙（含浏览器采集）见 `scripts/daily_topics.sh`。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / 'content'

# 「我马上能用」框架词 —— 来自流量归因 §14（TOP10 的共同点）
FRAME_HINTS = [
    ('本地能跑', ['local', 'offline', 'self-host', 'on-device', 'local-first', '无需联网', '离线']),
    ('不用花钱', ['free', 'open-source', 'no subscription', 'without paying', '免费', '开源']),
    ('刚开源', ['just released', 'opensource', 'release', 'launch']),
    ('不用买会员', ['alternative to', 'replacement for', '代替', '替代', '无需账号']),
]
# 类目聚类用的关键词（用来判断"能不能凑三件套"）
CATEGORY_HINTS = [
    ('图片处理', ['image', 'photo', 'ocr', 'upscale', 'background', '图片', '照片', '抠图']),
    ('语音/音频', ['speech', 'audio', 'voice', 'tts', 'asr', 'whisper', '播客', '录']),
    ('文档/PDF', ['pdf', 'document', 'markdown', 'epub', 'office', '文档', '笔记']),
    ('浏览器智能体', ['browser', 'web agent', 'playwright', 'scrap', '浏览器', '爬']),
    ('编码智能体', ['coding agent', 'code', 'ide', 'copilot', '编程', '代码']),
    ('本地模型', ['llm', 'model', 'inference', 'quantiz', 'gguf', '推理', '模型']),
    ('备份/同步', ['sync', 'backup', 'cloud storage', 'rclone', '备份', '同步']),
    ('自建服务', ['self-hosted', 'server', 'docker', '自建', '私有部署']),
    ('视频/剪辑', ['video', 'edit', 'subtitle', '剪辑', '字幕']),
    ('知识库/RAG', ['rag', 'knowledge', 'embedding', 'retrieval', '知识库', '检索']),
    ('开发工具', ['cli', 'sdk', 'framework', 'linter', 'test', 'devtool', '插件', '工具链', 'desktop']),
    ('内容创作', ['canvas', 'design', 'ui', '主题', '排版', '写作', '绘图', '素材']),
    ('数据/分析', ['data', 'analytics', 'dashboard', 'visual', '报告', '抓取', '爬']),
    ('效率/自动化', ['automat', 'workflow', 'scheduler', 'agent', '自动化', '效率']),
]


def gh_search(days: int, min_stars: int, per_page: int = 60) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    # ⚠️ 查询串必须 URL 编码：`>` 和空格不编码时，GitHub 会当语法错误 → 返回 0 条（本脚本第一版就踩了）
    from urllib.parse import quote
    q = quote(f'created:>{since} stars:>{min_stars}')
    url = (f'https://api.github.com/search/repositories?q={q}'
           f'&sort=stars&order=desc&per_page={per_page}')
    r = subprocess.run(['curl', '-sL', '--max-time', '40', '-H',
                        'Accept: application/vnd.github+json', url], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return []
    if 'items' not in d:                      # 限流时（0/60）返回空，并说明原因
        print(f'⚠️ GitHub API 返回：{str(d.get("message"))[:70]}', file=sys.stderr)
        return []
    out = []
    for it in d['items']:
        out.append(dict(
            repo=it['full_name'], stars=it['stargazers_count'],
            created=(it.get('created_at') or '')[:10], pushed=(it.get('pushed_at') or '')[:10],
            license=((it.get('license') or {}).get('spdx_id') or ''),
            desc=(it.get('description') or '').strip(), url=it['html_url'],
        ))
    return out


def hf_trending(limit: int = 25) -> list[dict]:
    r = subprocess.run(['curl', '-sL', '--max-time', '30',
                        f'https://huggingface.co/api/models?sort=trendingScore&limit={limit}&full=true'],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return []
    out = []
    for x in d:
        tags = x.get('tags') or []
        lic = next((t.split(':', 1)[1] for t in tags if str(t).startswith('license:')), '')
        out.append(dict(repo=x.get('id', ''), stars=x.get('trendingScore', 0), created='', pushed='',
                        license=lic, desc=(x.get('pipeline_tag') or ''), url=f"https://huggingface.co/{x.get('id','')}"))
    return out


def ph_feed(limit: int = 30) -> list[dict]:
    """Product Hunt 的公开 Atom feed（curl，不用浏览器）。

    为什么不走浏览器采集：PH 首页会弹**通知权限框**，一弹任务空间就被浏览器收回给用户
    （2026-09-22 实测：空间 ownership 变 agentDelegatedToUser，后续页面全读不到），
    而它的 feed 用 curl 就够——没必要为了榜单页去碰弹窗。
    """
    r = subprocess.run(['curl', '-sL', '--max-time', '30', '-A', 'Mozilla/5.0',
                        'https://www.producthunt.com/feed'], capture_output=True, text=True)
    t = r.stdout or ''
    out = []
    for e in re.findall(r'<entry>(.*?)</entry>', t, re.S)[:limit]:
        m = re.search(r'<title>(.*?)</title>', e, re.S)
        if not m:
            continue
        title = re.sub(r'\s+', ' ', m.group(1)).strip()
        link = re.search(r'<link[^>]*href="([^"]+)"', e)
        body = re.search(r'<content[^>]*>(.*?)</content>', e, re.S)
        desc = ''
        if body:
            import html as _html
            desc = re.sub(r'<[^>]+>', ' ', _html.unescape(body.group(1)))
            desc = re.sub(r'\s+', ' ', desc).strip()
            desc = desc.split('Discussion')[0].strip()[:110]
        pub = re.search(r'<published>(.*?)</published>', e, re.S)
        out.append(dict(kind='web', repo=title, stars=0, license='', created='', pushed='',
                        desc=desc, url=(link.group(1) if link else ''),
                        source='ProductHunt', published=(pub.group(1)[:10] if pub else '')))
    return out


# 文件路径/分数（`posts/2026-09-10-x.md`、`15/20`）不是仓库名：裸名写法要过这道筛
_NOT_REPO = re.compile(r'\.(md|markdown|py|js|mjs|ts|tsx|json|ya?ml|txt|html?|css|toml|sh|go|rs|java|rb|php|sql|ipynb)$', re.I)


def _looks_like_repo(cand: str) -> bool:
    if cand.count('/') != 1:
        return False
    owner, repo = cand.split('/')
    if min(len(owner), len(repo)) < 2 or owner.startswith('_') or repo.startswith('_'):
        return False
    if owner.isdigit() or repo.isdigit():
        return False
    # 数字+单位（48k / 9.4k / 1.6万）不是仓库名
    if all(re.fullmatch(r'\d+(?:\.\d+)?[kKmMbB万亿]?', x) for x in (owner, repo)):
        return False
    if _NOT_REPO.search(repo) or '.' in owner:
        return False
    # 本地工程目录（videos/xxx、content/xxx）不是仓库名
    if owner in {'videos', 'content', 'specs', 'scripts', 'assets', 'docs', 'src', 'lib', 'data',
                 'public', 'static', 'tmp', 'build', 'dist', 'test', 'tests', 'node_modules'}:
        return False
    return bool(re.search(r'[a-z]', owner)) and bool(re.search(r'[a-z]', repo))


def used_repos() -> set[str]:
    """历史期做过哪些仓库。

    ⚠️ 2026-09-22 修（独立评审在 EP.205 上抓到的事故）：原来**只认 `github.com/<owner>/<repo>` 这一种写法**，
    而历史 `sources.md` 里大量仓库是**裸名/反引号**写法（如 EP.178 的 `| 7 | \`lnkiai/m3e-canvas\` | 本周新建榜 |`）
    → 去重表里根本没有它，于是 m3e-canvas 在 EP.178 上过一次，EP.205 又被当成"新"工具推了一遍。
    现在三种写法都收：① github.com/owner/repo ② 反引号里的 owner/repo ③ 表格里紧挨星标数字的 owner/repo。
    """
    used = set()
    for f in CONTENT.glob('episode-*/sources.md'):
        t = f.read_text(encoding='utf-8', errors='ignore')
        for m in re.finditer(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)', t):
            used.add(m.group(1).lower().rstrip('.').replace('.git', ''))
        for m in re.finditer(r'`([A-Za-z0-9_.\-]{2,40}/[A-Za-z0-9_.\-]{2,40})`', t):
            cand = m.group(1).lower().rstrip('.').replace('.git', '')
            if _looks_like_repo(cand):
                used.add(cand)
        # 2026-09-22 第二轮补：粗体名（**openbmb/VoxCPM2**）、npm scope（@orama/orama）、
        # 以及正文里的裸名 —— 评审实测这三类在历史 sources.md 里都存在，前两版规则全漏。
        for m in re.finditer(r'(?<![A-Za-z0-9_.\-/])([A-Za-z0-9_.\-]{2,40}/[A-Za-z0-9_.\-]{2,40})(?![A-Za-z0-9_.\-/])', t):
            cand = m.group(1).lower().rstrip('.').replace('.git', '')
            if _looks_like_repo(cand):
                used.add(cand)
    return used


# 去重时用来比对的通用词（避免 repo 名叫 code / app 时把无关标题全判成"做过"）
_GENERIC = {'code', 'app', 'apps', 'tools', 'tool', 'agent', 'agents', 'data', 'docs',
            'notes', 'video', 'image', 'audio', 'chat', 'core', 'web', 'ui', 'cli',
            'server', 'client', 'search', 'index', 'demo', 'sample', 'test', 'api'}


def used_urls() -> set[tuple[str, str]]:
    """历史期引用过哪些**网页**（扫 sources.md 里的 http 链接）→ (域名, path 末段)。"""
    used = set()
    for f in CONTENT.glob('episode-*/sources.md'):
        t = f.read_text(encoding='utf-8', errors='ignore')
        for m in re.finditer(r'https?://([^\s)（），,」"\'`]+)', t):
            host, _, path = m.group(1).partition('/')
            stem = path.rstrip('/').split('/')[-1].split('?')[0].split('#')[0].lower()
            used.add((host.lower().removeprefix('www.'), stem))
    return used


def web_candidates(path: str) -> list[dict]:
    """读浏览器采集器（scripts/collect_hot_topics.mjs）落盘的榜单候选。"""
    try:
        raw = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    except Exception as e:
        print(f'⚠️ 读不进 {path}（{type(e).__name__}）——本次只算 API 侧候选', file=sys.stderr)
        return []
    out, seen = [], set()
    for r in raw if isinstance(raw, list) else []:
        title, url = (r.get('title') or '').strip(), (r.get('url') or '').strip()
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        out.append(dict(kind='web', repo=title, stars=0, license='', created='', pushed='',
                        desc=(r.get('extra') or '').strip(), url=url,
                        source=r.get('source') or 'web'))
    return out


# 榜单站的可信度/适配度权重（知乎热榜多是社会新闻、Product Hunt 偏营销，都要打折）
SITE_WEIGHT = {'HackerNews': 1.0, 'GitHubTrending': 1.0, 'ProductHunt': 0.6, '知乎热榜': 0.35,
               'web': 0.5}


def category_of(text: str) -> str:
    t = text.lower()
    best, score = '其它', 0
    for name, kws in CATEGORY_HINTS:
        s = sum(1 for k in kws if k in t)
        if s > score:
            best, score = name, s
    return best


def score(cand: dict, pool: list[dict], used: set[str], same_cat: dict,
          used_url_set: set[tuple[str, str]] | None = None, used_names: set[str] | None = None
          ) -> tuple[float, list[str]]:
    why, pts = [], 0.0
    text = f"{cand['repo']} {cand['desc']}".lower()
    is_web = cand.get('kind') == 'web'

    # ⑤ 去重（最重的负分）
    if is_web:
        host, _, path = (cand.get('url') or '').split('://')[-1].partition('/')
        stem = path.rstrip('/').split('/')[-1].lower()
        if used_url_set and (host.removeprefix('www.'), stem) in used_url_set:
            pts -= 8
            why.append('做过（历史 sources 里有这个页面）')
        else:
            # 标题里出现历史做过的仓库名 → 是同一个工具的又一次热度，不值得再做一期
            hit = next((n for n in (used_names or set())
                        if n not in _GENERIC and re.search(rf'\b{re.escape(n)}\b', text)), None)
            if hit:
                pts -= 8
                why.append(f"做过相关工具（{hit}）")
    else:
        key = cand['repo'].lower()
        if key in used:
            pts -= 8
            why.append('做过（历史 sources 里有这个仓库）')

    # ① 三件套可组性
    cat = category_of(text)
    n_sib = same_cat.get(cat, 0)
    if cat == '其它':
        n_sib = 0                       # 「其它」不成类，不给三件套加分
    if n_sib >= 3:
        pts += 3
        why.append(f'同类候选 {n_sib} 个 → 能组「三件套」')
    elif n_sib == 2:
        pts += 1.5
        why.append('同类候选 2 个')

    # ② 我马上能用
    for label, kws in FRAME_HINTS:
        if any(k in text for k in kws):
            pts += 1
            why.append(label)

    if is_web:
        # 榜单候选没有星标/建仓时间：用**榜面热度**代替（HN/PH 的分值、榜单排名由 extra 带回来）
        src = cand.get('source') or 'web'
        w = SITE_WEIGHT.get(src, 0.5)
        m = re.search(r'(\d+)\s*points', cand['desc'], re.I)
        heat = int(m.group(1)) if m else 0
        if heat >= 300:
            pts += 2 * w
            why.append(f'{src} 榜面热议（{heat} 分）')
        elif heat >= 100:
            pts += 1.5 * w
            why.append(f'{src} 榜面热议（{heat} 分）')
        elif heat >= 30:
            pts += 1 * w
            why.append(f'{src} 上榜')
        else:
            pts += 0.4 * w
            why.append(f'{src} 榜上（热度未标）')
        if cand['desc']:
            pts += 0.5
    else:
        # ③ 数字好讲（星标）
        if cand['stars'] >= 20000:
            pts += 2
            why.append(f"{cand['stars']:,}★ 量级大")
        elif cand['stars'] >= 5000:
            pts += 1.5
            why.append(f"{cand['stars']:,}★")
        elif cand['stars'] >= 1000:
            pts += 1
            why.append(f"{cand['stars']:,}★")

        # ⑥ 涨得快（星标 / 建仓天数）
        try:
            days = max(1, (date.today() - datetime.strptime(cand['created'], '%Y-%m-%d').date()).days)
            per_day = cand['stars'] / days
            if per_day >= 300:
                pts += 2
                why.append(f'涨得快（≈{per_day:.0f}★/天）')
            elif per_day >= 80:
                pts += 1
                why.append(f'涨得快（≈{per_day:.0f}★/天）')
        except Exception:
            pass

        # ④ 一手源可得：许可清楚 + 有官方自述
        if cand['license']:
            pts += 0.5
            why.append(f"许可 {cand['license']}")
        else:
            pts -= 0.5
            why.append('仓库没标许可（要如实说）')
        if cand['desc']:
            pts += 0.5

    return round(pts, 2), why


def label_of(cand: dict) -> str:
    return f"〔{cand['source']}〕{cand['repo']}" if cand.get('kind') == 'web' else cand['repo']


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--legacy', action='store_true', help='显式运行旧版开源工具评分；不属于现行柴主编选题门')
    ap.add_argument('--days', type=int, default=45)
    ap.add_argument('--min-stars', type=int, default=300)
    ap.add_argument('--top', type=int, default=15)
    ap.add_argument('--json', default=None)
    ap.add_argument('--no-ph', action='store_true', help='不拉 Product Hunt 的 Atom feed')
    ap.add_argument('--with-web', dest='with_web', default=None,
                    help='浏览器采集器落盘的候选 JSON（scripts/collect_hot_topics.mjs → /tmp/hot-candidates.json）')
    a = ap.parse_args()

    if not a.legacy:
        print('旧评分已退出主链（含三件套、星数、热度加分）。请运行 python3 scripts/chai_news_radar.py；只有核验观众任务与证据后才做编辑评分。',file=sys.stderr)
        return 2

    cands = gh_search(a.days, a.min_stars) + hf_trending()
    web = web_candidates(a.with_web) if a.with_web else []
    if not a.no_ph:
        web += ph_feed()          # PH 走 feed，不占浏览器（见 ph_feed 注释）
    srcs = sorted({c['source'] for c in web})
    if not cands and not web:
        print('❌ 一个候选都没拉到（多半是 GitHub API 限流：60/小时；等一会儿或加 token 重跑）')
        return 1
    cands += web

    used = used_repos()
    used_names = {r.split('/')[-1].lower() for r in used}
    used_url_set = used_urls() if web else set()
    same_cat = defaultdict(int)
    for c in cands:
        same_cat[category_of(f"{c['repo']} {c['desc']}".lower())] += 1

    rows = []
    for c in cands:
        pts, why = score(c, cands, used, same_cat, used_url_set, used_names)
        rows.append((pts, c, why))
    rows.sort(key=lambda r: -r[0])

    print(f"── 选题雷达 · {date.today().isoformat()} · 候选 {len(cands)} 个"
          f"（GitHub 建仓 {a.days} 天内 ≥{a.min_stars}★ + HF trending"
          + (f" + 浏览器榜单 {len(web)} 条：{'、'.join(srcs)}" if web else '') + '）')
    print(f"   历史已做仓库 {len(used)} 个（用于去重）")
    if a.with_web and not web:
        print(f"   ⚠️ {a.with_web} 里没有浏览器侧候选 —— 浏览器采集这一半没跑成，今天只有 API 侧")
    print()
    for i, (pts, c, why) in enumerate(rows[:a.top], 1):
        cat = category_of(f"{c['repo']} {c['desc']}".lower())
        if c.get('kind') == 'web':
            print(f"{i:2d}. [{pts:5.1f}分] {cat:<10s} {label_of(c)[:66]}")
            print(f"      {c['url'][:100]}")
        else:
            print(f"{i:2d}. [{pts:5.1f}分] {cat:<10s} {c['repo']}  {c['stars']:,}★  {c['license'] or '许可未标'}")
        print(f"      {c['desc'][:88]}")
        print(f"      {' · '.join(why)}")
    # 按类目给「可组三件套」的建议
    print('\n── 按类目分组（每组≥3 个就能直接组一期「三件套」）')
    bycat = defaultdict(list)
    for pts, c, why in rows[:40]:
        bycat[category_of(f"{c['repo']} {c['desc']}".lower())].append((pts, c))
    for cat, lst in sorted(bycat.items(), key=lambda kv: -len(kv[1])):
        if len(lst) < 3:
            continue
        names = '、'.join(label_of(c).split('/')[-1][:28] for _, c in lst[:4])
        print(f"   {cat}（{len(lst)} 个）：{names}")

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            [dict(score=p, kind=c.get('kind', 'repo'), source=c.get('source', 'GitHub'),
                  title=label_of(c), repo=c['repo'], url=c.get('url', ''), stars=c['stars'],
                  license=c['license'], created=c['created'], desc=c['desc'], why=w)
             for p, c, w in rows],
            ensure_ascii=False, indent=1), encoding='utf-8')
        print(f"\n📝 明细写入 {a.json}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
