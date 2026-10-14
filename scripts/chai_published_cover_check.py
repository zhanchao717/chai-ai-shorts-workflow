#!/usr/bin/env python3
"""门禁G：**校验已发布作品的封面，真的是我们那张竖封面**（2026-09-18 事故后新增）。

**为什么必须有它**（当天真实事故）：EP.190/191/192 发布时，发布日志里写着
「竖封面 → cover-3x4.png」「封面 → cover-4x3.png」，自检也读到两个封面槽都有图，
但**实际发出去的竖封面是平台拿 4:3 横封面中心裁出来的** —— 用户在自己号上肉眼发现
「3x4 封面好像上传的不对」。事后逐像素比对才确认：已发布封面与我们的 `cover-3x4.png`
灰度相关 -0.02，而与「`cover-4x3.png` 中心裁成 3:4」相关 **1.000**。

两个直接原因：
  ① 抖音封面 UI 兜底脚本的选择器写死了构建哈希 `[class*=filter-k_CjvJ]`，抖音改版后**静默失配**，
     整段兜底变成空转（日志里一句报错都没有）；
  ② 适配器字段路径里 `verticalCover` 没被真正应用，平台就把 `cover`（4:3）塞进了竖封面槽。
一句话：**发布成功 ≠ 封面正确；封面必须回到平台上量。**

做法：从创作者后台作品列表里取该作品的封面缩略图（`background-image` 里带 `sc=cover` 的那张），
下载后与本地 `cover-3x4.png`、以及「`cover-4x3.png` 中心裁 3:4」两张候选做灰度相关：

  · 与 3:4 相关 ≥ 0.9  → ✅ 竖封面正确
  · 与「4:3 中心裁」相关 ≥ 0.9 且与 3:4 相关 < 0.5 → ❌ 竖封面被 4:3 顶了（必须去后台改封面）
  · 都不像 → ❓ 人工看（可能平台换了缩略图裁剪策略）

用法：
  python3 scripts/chai_published_cover_check.py --ep 193 \\
      --pkg content/episode-193/publish-package-2026-09-18 --title "剪视频不用买会员" \\
      --gid group-xxxx        # 抖音任意已打开的 group（用来跑页面脚本，只读）
退出码：0 = 竖封面正确；1 = 不对/无法判定。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import subprocess
import sys
import time

import os
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOUYIN_ACC = os.environ.get('DOUYIN_ACCOUNT_ID', '')  # 从环境变量读，不写死

JS_FIND_COVER = """(async () => {
  // ⚠️ 作品列表的封面是**懒加载**的：页面刚到时 DOM 里一张封面都没有（n=0）。
  //    先滚一下、等一下，再收集（2026-09-22 EP.204 就是因此读不到列表）。
  window.scrollTo(0, 0);
  await new Promise(r => setTimeout(r, 1500));
  window.scrollTo(0, 600);
  await new Promise(r => setTimeout(r, 2500));
  await new Promise(r => setTimeout(r, 4000));
  // 2026-09-18 事故复盘后改成"列全部候选"：按标题定位卡片的三次尝试都踩了坑
  // （走过头拿到邻居作品的封面 / 几何同行挑错行 / 虚拟列表里节点归属漂移）。
  // 拿全部候选再逐个比对，就没有"定位卡片"这一步了 —— 每个作品的封面设计都是唯一的，
  // 能匹配上我们的 3:4 就说明它确实发出去了。
  const key = %s;
  const out = [];
  const seen = new Set();
  for (const e of document.querySelectorAll('*')) {
    const bg = getComputedStyle(e).backgroundImage;
    if (!bg || !bg.includes('sc=cover')) continue;
    const m = bg.match(/https?[^"'\\)]+/);
    if (!m) continue;
    const url = m[0];
    if (seen.has(url)) continue;
    seen.add(url);
    const r = e.getBoundingClientRect();
    if (r.width < 60 || r.height < 60) continue;
    const cardText = (e.closest('div') ? e.closest('div').innerText : '') || '';
    out.push({url, id: (url.match(/tos-cn-i-dy\/([0-9a-f]+)/) || [])[1] || '?',
              w: Math.round(r.width), h: Math.round(r.height), near: cardText.replace(/\s+/g, '').slice(0, 30)});
    if (out.length >= 24) break;
  }
  return JSON.stringify({key, n: out.length, covers: out});
})()"""


def load(p, n=(96, 128)):
    return np.asarray(Image.open(p).convert('RGB').resize(n)).astype('float32') / 255.0


def lum(a):
    return a @ np.array([0.299, 0.587, 0.114], dtype='float32')


def corr(a, b):
    return float(np.corrcoef(lum(a).ravel(), lum(b).ravel())[0, 1])


def centre_crop_43_to_34(path, out):
    im = Image.open(path).convert('RGB')
    W, H = im.size
    w = int(H * 0.75)
    left = (W - w) // 2
    im.crop((left, 0, left + w, H)).save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--ep', required=True)
    ap.add_argument('--pkg', required=True)
    ap.add_argument('--title', required=True, help='作品标题里的稳定片段（用于在列表里定位卡片）')
    ap.add_argument('--gid', required=True, help='抖音账号下任意已打开的 group（只读跑脚本用）')
    ap.add_argument('--account', default=DOUYIN_ACC)
    a = ap.parse_args()

    spec = importlib.util.spec_from_file_location('cpm', str(ROOT / 'scripts' / 'chai_publish_mcp.py'))
    m = importlib.util.module_from_spec(spec)
    sys.modules['cpm'] = m
    spec.loader.exec_module(m)

    # 先确保页面停在作品管理列表（否则卡片根本不在 DOM 里 → 'no card'）
    where = m.tool_call('execute_group_script',
                        {'accountId': a.account, 'groupId': a.gid,
                         'script': "(() => (location.href.includes('content/manage') ? 'ok' : location.href))()"},
                        timeout=60)
    if not (isinstance(where, str) and where.strip() == 'ok'):
        m.tool_call('execute_group_script',
                    {'accountId': a.account, 'groupId': a.gid,
                     'script': "(() => { location.assign('https://creator.douyin.com/creator-micro/content/manage'); return 'navigating'; })()"},
                    timeout=60)
        time.sleep(12)
    else:
        # ⚠️ 2026-09-20：已经在管理页时**也要刷新**。否则页面还是上一批发布后留下的旧列表，
        #    "读出 12 张候选封面"全是上一批的 —— 刚发的作品根本没进 DOM，判成「两者都不像」。
        m.tool_call('execute_group_script',
                    {'accountId': a.account, 'groupId': a.gid,
                     'script': "(() => { location.reload(); return 'reloading'; })()"}, timeout=60)
        time.sleep(14)

    raw = m.tool_call('execute_group_script',
                      {'accountId': a.account, 'groupId': a.gid,
                       'script': JS_FIND_COVER % json.dumps(a.title)}, timeout=150)
    payload = raw if isinstance(raw, dict) else json.loads(raw)
    covers = payload.get('covers') or []
    if not covers:
        print(f'❌ 作品列表里一张候选封面都没读到（页面可能不在管理页）：{str(raw)[:80]}')
        return 1

    pkg = pathlib.Path(a.pkg)
    ours34 = load(str(pkg / 'cover-3x4.png'))
    crop = centre_crop_43_to_34(str(pkg / 'cover-4x3.png'), f'/tmp/sim43_{a.ep}.png')
    ours43 = load(crop)

    best34, best43 = None, None
    for c in covers:
        tmp = pathlib.Path('/tmp') / f"pubcover_{a.ep}_{c['id'][:8]}.webp"
        subprocess.run(['curl', '-sL', '--max-time', '30', '-H', 'User-Agent: Mozilla/5.0',
                        '-o', str(tmp), c['url'] + ('&_ts=%d' % int(time.time()))], capture_output=True)
        if not tmp.exists() or tmp.stat().st_size < 5000:
            continue
        png = pathlib.Path('/tmp') / f"pubcover_{a.ep}_{c['id'][:8]}.png"
        Image.open(tmp).convert('RGB').save(png)
        im = load(str(png))
        v34, v43 = corr(im, ours34), corr(im, ours43)
        if best34 is None or v34 > best34[0]:
            best34 = (v34, c, str(png))
        if best43 is None or v43 > best43[0]:
            best43 = (v43, c, str(png))

    print(f'── EP.{a.ep} 页面上读到 {len(covers)} 张候选封面，逐张与本地封面比灰度相关')
    print(f'   最像我们 3:4 的：id {best34[1]["id"][:12]} · 相关 {best34[0]:.3f}（卡片附近文字：{best34[1]["near"][:18]}）')
    print(f'   最像「4:3 中心裁」的：id {best43[1]["id"][:12]} · 相关 {best43[0]:.3f}')
    if best34[0] >= 0.9:
        print('   ✅ 门禁G PASS：页面上确实挂着我们那张竖封面')
        return 0
    if best43[0] >= 0.9:
        print('   ❌ 门禁G FAIL：竖封面是横封面 4:3 被平台中心裁出来的 —— 去后台「编辑作品 → 竖封面」重传')
        return 1
    print('   ❓ 两者都不像：人工看一眼这张封面（可能是平台换了缩略图策略）')
    return 1


if __name__ == '__main__':
    sys.exit(main())
