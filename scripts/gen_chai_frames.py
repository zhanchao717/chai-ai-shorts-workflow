#!/usr/bin/env python3
"""柴主编视觉层生成器（Soft Slate 固定版式，2026-09-08 固化；2026-09-11 增 06/07 深度版场景）。

前置：工程骨架已就位（assets/fonts+brand、bin、hyperframes.json、package.json、
caption-overrides.json、captions.html 模板、publish-timeline/*.json、assets/voice/*.mp3）。

用法：python3 scripts/gen_chai_frames.py <spec.json>
spec 字段见 /Users/chao/Documents/dailyvideos/specs/146.example.json。
生成：compositions/frames/<spec 里每个场景>.html + captions.html 注入 + cover.html。
- 01–05（hook/facts/mechanism/action/verdict）为既有必填场景，版式与输出**逐字节不变**。
- 深度版（N=7）：**场景与音频段一一对应且顺序即角色**——01 hook / 02 facts / 03 mechanism /
  04 action / 05 config / 06 verify / 07 verdict。因此当 spec 的 "05" 带 lines、或 "06" 带
  checks 时，这两个新模板启用，末场改用 07-verdict（原 05 判词卡的版式不变）。
  只写 5 场景 = 老路径，输出逐字节不变；两个新场景各自独立可选（缺失不报错）。

════════ 05-config（配置逐行）spec 契约 ════════
  依赖：该场景必须排在 05 位（即 spec 里有 "06" 场景），否则会与 05-verdict 抢同一格。
  "scenes": {"05": {
    "hero_l1":  "把研究写成文件",        # 顶部小标题（30px，≤34 个中文字）
    "hero_em":  "先摆一行",              # 可选；{em} 占位符的强调串（强调色 #D1FF00）
    "lines": [                           # 6–12 行；不足 6 行按 6 行留白，超过 8 行自动降档字号
      {"t": "name: research-writer",     # 代码正文（等宽 CobaltMono，按字宽自适应 22→19px）
       "i": 0,                           # 缩进层级（整数，1 级 = 2 个半角空格，建议 0–2）
       "hl": true},                      # true = 本行高亮（强调色 + 淡底 + 左侧 3px 竖条），缺省 false
      {"t": "description: 深度调研时使用", "c": "什么时候用"}   # c = 右侧注释列（可选）
    ],
    "note": "SOURCE · 官方文档 xxx"      # 底部来源行（沿用 .note 皮肤）
  }}
  正文一律**不换行**：生成时复用 chai_layout_precheck.width_px 的同一宽度模型自动选字号
  （22px 起逐档降到 19px），并断言 缩进 + 代码列 + 注释列 ≤ 内容宽 860px，不会重蹈
  .fnode .t（26px + nowrap 无回退）的覆辙。注释列宽度按最长注释统一。

════════ 06-verify（三步验证清单）spec 契约 ════════
  依赖：该场景必须排在 06 位（即 spec 里有 "07" 场景）。
  "scenes": {"06": {
    "title": "三步验证它真的生效",       # 卡头标题（38px，可含 {em}）
    "sub":   "照做一遍就知道对不对",     # 可选；卡头副标题（23px 等宽），缺省整行不渲染
    "checks": [                          # **必须正好 3 步**（多/少显式报错，不静默）
      {"t": "重启一次会话",              # 步骤主文案（38px，≤17 个中文字）
       "s": "新开对话问它还记得你吗",    # 步骤说明（22px，≤34 个中文字，正常折行不溢出）
       "tag": "先关掉"}                  # 可选；右侧小标签（19px 等宽，≤14 个字符）
    ],
    "note": "SOURCE · 官方文档 xxx"
  }}
  版式：竖向编号徽章 + 左侧虚线导轨 + 横排步骤，刻意与 03-mechanism（横向 3 节点卡）区分；
  不用 nowrap，长文案换行即可，卡片 min-height 720px、随内容长高。
"""
from __future__ import annotations

import json, math, re, sys, os, subprocess, tempfile
import shutil
from pathlib import Path

ROOT = Path("/Users/chao/Documents/dailyvideos")
HEAD = '''@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@900&display=swap');
    @font-face{font-family:CobaltSans;src:url("assets/fonts/CobaltSans.ttc") format("truetype");font-weight:400 700}
    @font-face{font-family:CobaltMono;src:url("assets/fonts/CobaltMono.ttf") format("truetype");font-weight:400}
    @font-face{font-family:"PingFang SC";src:local("PingFang SC");font-weight:100 900}
    #root{position:relative;width:1080px;height:1920px;overflow:hidden;color:#F2EEE8;container-type:size;font-family:"Noto Sans SC","PingFang SC",sans-serif}
    .bg{position:absolute;inset:0;background:linear-gradient(160deg,#1F1F1F 0%,#101010 100%)}
    /* ⚠️ 2026-09-12（EP.174 起）：水印数字颜色 #4A4A4A → **#6A6A6A**。
       深色底 #1F1F1F 上 #4A4A4A 的对比度只有 **1.84:1**，EP.170/171/173 三次独立评审都把它记为
       "既有特征未修"，而 hyperframes 的 contrast 检查也一直报它。它只是**装饰性水印**（WCAG 对纯装饰
       豁免），但既然改一个色值就能消掉长期告警，就改掉。EP.170–173 保持旧色（已发布，不回改）。
       ⚠️ 取 **#787878** 而不是 #6A6A6A：计算上 #6A 是 3.05:1，但**独立评审在成片实际局部背景上量到 2.98:1（仍差一档）**，
       故留足余量：#78 在 #1F1F1F 上 3.73:1、在 #101010 上 4.31:1。 */
    .idx{position:absolute;right:110px;top:210px;font:900 200px/1 "Noto Sans SC";color:#787878;text-shadow:none;letter-spacing:-.02em}
    .note{position:absolute;left:110px;top:1408px;width:860px;line-height:1.4;font:20px CobaltMono;color:#C6C0B8;letter-spacing:.05em}
'''

DECOR_CSS = '''    .slash{position:absolute;left:50%;top:540px;width:1000px;height:1000px;transform:translate(-50%,-50%);background:radial-gradient(circle, rgba(209,255,0,0.12) 0%, rgba(255,255,255,0.06) 38%, transparent 68%);border-radius:50%;pointer-events:none}
    .rline{position:absolute;left:110px;top:356px;width:220px;height:9px;background:#D1FF00;z-index:6}
    .dash{position:absolute;left:110px;width:860px;border-top:2px dashed #5A5A5A;z-index:5;opacity:.6}
    .dash-t{top:120px}.dash-b{top:1332px}
    .cross{position:absolute;width:22px;height:22px;z-index:25;opacity:.75}
    .cross:before,.cross:after{content:"";position:absolute;background:#9A938A}
    .cross:before{left:10px;top:0;width:2px;height:22px}
    .cross:after{left:0;top:10px;width:22px;height:2px}
    .c-tl{left:56px;top:56px}.c-tr{right:56px;top:56px}
    .c-bl{left:56px;top:1320px}.c-br{right:56px;top:1320px}
'''
DECOR = '<div class="slash"></div><div class="rline"></div><div class="dash dash-t"></div><div class="dash dash-b"></div><div class="cross c-tl"></div><div class="cross c-tr"></div><div class="cross c-bl"></div><div class="cross c-br"></div>'
HEAD = HEAD + DECOR_CSS

GLASS = '''    .warn,#f1-card,#f2-repo,#f2-tag,.card,.flow3,.fnode,#f3-sw,#f4-strip,.well2,#f5-card{backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid rgba(176,176,176,0.22)}'''
HEAD = HEAD + GLASS

CSS1 = HEAD + '''    .warn{position:absolute;left:110px;top:440px;width:860px;height:130px;border-radius:28px;background:rgba(255,255,255,0.05);box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px #3A3A3A;display:flex;align-items:center;padding:0 44px}
    .warn span{font:700 34px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#D4CEC6}
    .warn span b{color:#FFFFFF}
    #f1-hero{position:absolute;left:110px;top:650px;font:700 118px/1.26 "Noto Sans SC","PingFang SC",sans-serif;letter-spacing:-.01em;color:#FFFFFF}
    #f1-hero .line{display:block}
    #f1-hero .em{color:#D1FF00}
    #f1-card{position:absolute;left:110px;top:1060px;width:860px;height:200px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);display:flex;align-items:center;gap:38px;padding:0 54px}
    #f1-card .big{font:900 52px/1 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF}
    #f1-card .lb .t{font:700 36px/1.2 "Noto Sans SC","PingFang SC",sans-serif;color:#F2EEE8;margin-bottom:10px}
    #f1-card .lb .s{font:22px/1.4 CobaltMono;color:#C6C0B8;letter-spacing:.04em}
'''
CSS2 = HEAD + '''    #f2-repo{position:absolute;left:110px;top:400px;width:860px;height:230px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);display:flex;align-items:center;gap:40px;padding:0 54px}
    #f2-repo .big{font:900 46px/1 CobaltMono,"PingFang SC",monospace;color:#FFFFFF;flex:0 0 auto}
    #f2-repo .lb .t{font:700 32px/1.25 "Noto Sans SC","PingFang SC",sans-serif;color:#F2EEE8;margin-bottom:10px}
    #f2-repo .lb .s{font:22px/1.4 CobaltMono;color:#C6C0B8;letter-spacing:.04em}
    .card{position:absolute;left:110px;width:860px;height:210px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);display:flex;align-items:center;gap:44px;padding:0 54px}
    #st-1{top:670px}
    #st-2{top:920px}
    .card .num{font:900 46px/1 "Noto Sans SC","PingFang SC",sans-serif;color:#D1FF00;flex:0 0 auto}
    .card .lb .t{font:700 30px/1.2 "Noto Sans SC","PingFang SC",sans-serif;color:#F2EEE8;margin-bottom:10px}
    .card .lb .s{font:21px/1.4 CobaltMono;color:#C6C0B8;letter-spacing:.04em}
    #f2-tag{position:absolute;left:110px;top:1180px;width:860px;height:96px;border-radius:28px;background:rgba(255,255,255,0.05);box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px #3A3A3A;display:flex;align-items:center;padding:0 44px}
    #f2-tag span{font:700 30px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#D4CEC6}
    #f2-tag span b{color:#D1FF00}
'''
CSS3 = HEAD + '''    .flow3{position:absolute;left:110px;top:470px;width:860px;height:340px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);display:flex;align-items:center;justify-content:center;gap:30px;padding:0 40px}
    .fnode{width:248px;height:200px;border-radius:28px;background:rgba(255,255,255,0.05);box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px #3A3A3A;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
    .fnode .t{font:700 26px/1.2 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;text-align:center;white-space:nowrap}
    .fnode .s{font:19px CobaltMono;color:#C0C0C0;letter-spacing:.06em;text-align:center}
    .farrow{font:900 40px/1 "Noto Sans SC";color:#8A8A8A}
    #f3-sw{position:absolute;left:110px;top:880px;width:860px;height:220px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px #3A3A3A;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px}
    #f3-sw .mm{font:900 44px/1.25 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;text-align:center}
    #f3-sw .mm .em{color:#D1FF00}
    #f3-sw .tag{font:20px CobaltMono;color:#C0C0C0;letter-spacing:.1em}
'''
CSS4 = HEAD + '''    #f4-strip{position:absolute;left:110px;top:430px;width:860px;height:170px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px #3A3A3A;display:flex;align-items:center;justify-content:center}
    #f4-strip .mm{font:900 46px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;text-align:center}
    #f4-strip .mm .em{color:#D1FF00}
    .well2{position:absolute;left:110px;width:860px;height:250px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);display:flex;align-items:center;gap:40px;padding:0 52px}
    #w-1{top:660px}
    #w-2{top:950px}
    .well2 .num{font:900 44px/1 "Noto Sans SC","PingFang SC",sans-serif;color:#D4CEC6;flex:0 0 auto;min-width:96px}
    .well2 .lb .t{font:700 38px/1.2 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;margin-bottom:10px}
    .well2 .lb .s{font:22px/1.35 "Noto Sans SC","PingFang SC",sans-serif;color:#D8D2CA}
'''
CSS5 = HEAD + '''    #f5-hero{position:absolute;left:110px;top:480px;font:900 110px/1.22 "Noto Sans SC","PingFang SC",sans-serif;letter-spacing:-.01em;color:#FFFFFF}
    #f5-hero .line{display:block}
    #f5-hero .em{color:#D1FF00}
    #f5-card{position:absolute;left:110px;top:920px;width:860px;height:230px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);display:flex;flex-direction:column;justify-content:center;gap:14px;padding:0 56px}
    #f5-card .tt{font:700 42px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#F2EEE8}
    #f5-card .tt .em{color:#D1FF00}
    #f5-card .ss{font:23px/1.4 CobaltMono;color:#C6C0B8;letter-spacing:.04em}
'''

# ── 深度版场景 06/07（2026-09-11 新增；既有 01–05 的 CSS 未做任何改动）─────────
# 05-config：一屏逐行讲配置。整体是「等宽代码块 + 右侧注释列」，行高由该场景 body 内联给。
# 2026-09-11：CSS6/CSS7 原先漏了 `HEAD +`，导致 05-config / 06-verify 两帧**整套皮肤家具缺失**
# （.rline 酸柠条 / .dash 虚线 / .cross 准星 / .idx 场号水印 / .bg / @font-face 全无），
# 且 `.note` 无规则 → 来源行以默认字体落在页面左上角 (x0,y21)，越出 110px 安全区。
# EP.167D 成片像素实测：旧模板 rline=(204,253,0) 在场，新模板 (24,26,26) 缺失。
# CSS1–CSS5 一直是 HEAD + 写法，故此处补齐；日更 5 场景路径不受影响（不产出 CSS6/CSS7）。
# 2026-09-11 同日第二处修复：两个新模板的 `.idx` 场号原为**硬编码 `06` / `07`**
# （沿用作者最初「配置=第 6 槽」的编号假设），导致 7 场景成片场号读作 01,02,03,04,<b>06,07</b>,07
# ——「05」缺失、「07」重复。两模板分别**只吃第 5 / 第 6 槽**（见下方 `_slots.get(5)` / `get(6)` 判定），
# 故改为与所在槽位一致的 `05` / `06`。
CSS6 = HEAD + '''    #f6-hero{position:absolute;left:110px;top:424px;width:860px;font:700 30px/1.25 "Noto Sans SC","PingFang SC",sans-serif;color:#F2EEE8}
    #f6-hero .em{color:#D1FF00}
    .pad{position:absolute;left:110px;width:860px;border-radius:30px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);padding:18px 34px;display:flex;flex-direction:column;justify-content:center;gap:6px}
    .pad .row{display:flex;align-items:center;gap:18px;border-radius:12px;padding:5px 12px 5px 6px}
    .pad .row.first{border-top-left-radius:20px;border-top-right-radius:20px}
    .pad .row.last{border-bottom-left-radius:20px;border-bottom-right-radius:20px}
    .pad .row.hl{background:rgba(209,255,0,0.10);box-shadow:inset 3px 0 0 #D1FF00, inset 0 0 0 1px rgba(209,255,0,.26)}
    /* 行号列是功能件（把 6 行对应到两次请求），不是装饰：hyperframes 的 Contrast
       门禁按 3:1 判。原色 #6E6E6E 实测只有 1.84–2.81:1（手机亮度下基本不可读），
       改 #A8A8A8（约 4.9:1 on #1F1F1F）并 +1px 字号。 */
    .pad .ct{flex:0 0 auto;text-align:right;font:21px/1 CobaltMono,"PingFang SC",monospace;color:#A8A8A8;letter-spacing:.06em}
    .pad .mono{flex:0 0 auto;font:22px/1.35 CobaltMono,"PingFang SC",monospace;color:#F2EEE8;letter-spacing:.01em}
    .pad .row.hl .mono{color:#D1FF00}
    .pad .tg{flex:0 0 auto;margin-left:auto;font:20px/1.3 CobaltMono,"PingFang SC",monospace;color:#A8A29A;letter-spacing:.03em;text-align:right}
'''

# 07-verify：三步验证清单（竖向徽章 + 左侧虚线导轨；与 03 的横向节点卡刻意区分）
CSS7 = HEAD + '''    #f7-card{position:absolute;left:110px;top:452px;width:860px;min-height:720px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);padding:32px 44px 34px;display:flex;flex-direction:column}
    #f7-card .hd{display:flex;flex-direction:column;gap:9px;padding-bottom:22px;margin-bottom:6px;border-bottom:1px solid rgba(176,176,176,0.22)}
    #f7-card .hd .h{font:700 38px/1.25 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF}
    #f7-card .hd .h .em{color:#D1FF00}
    #f7-card .hd .sub{font:23px/1.45 CobaltMono,"PingFang SC",monospace;color:#C6C0B8;letter-spacing:.04em}
    #f7-card .rails{position:relative;padding-left:90px;flex:1;display:flex;flex-direction:column;justify-content:space-evenly;gap:16px}
    #f7-card .rail{position:absolute;left:32px;top:46px;bottom:40px;width:2px;border-left:2px dashed #5A5A5A;opacity:.75}
    #f7-card .ck{position:relative;display:flex;gap:26px;align-items:flex-start;padding:6px 0 18px}
    #f7-card .ck:last-child{padding-bottom:0}
    #f7-card .bd{position:absolute;left:-71px;top:4px;width:44px;height:44px;border-radius:50%;background:rgba(0,0,0,.34);box-shadow:inset 0 0 0 2px #6A6A6A;display:flex;align-items:center;justify-content:center;font:900 23px/1 "Noto Sans SC","PingFang SC",sans-serif;color:#D4CEC6}
    #f7-card .ck.one .bd{background:#D1FF00;box-shadow:inset 0 0 0 2px #D1FF00;color:#101010}
    #f7-card .ck .bd .tick{font:900 23px/1 "Noto Sans SC","PingFang SC",sans-serif;color:#101010}
    #f7-card .ck .tx{min-width:0;display:flex;flex-direction:column;gap:11px}
    #f7-card .ck .tx .t{font:700 38px/1.25 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;overflow-wrap:anywhere}
    #f7-card .ck .tx .s{font:22px/1.5 "Noto Sans SC","PingFang SC",sans-serif;color:#C6C0B8}
    #f7-card .ck .chp{display:inline-flex;align-self:flex-start;padding:7px 16px;border-radius:14px;background:rgba(255,255,255,0.05);box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px #3A3A3A;font:19px/1 CobaltMono,"PingFang SC",monospace;color:#A8A29A;letter-spacing:.05em}
    #f7-card .ck.one .chp{color:#D1FF00;box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px rgba(209,255,0,.38)}
'''

# 06/07 的卡片同样进玻璃拟态清单（与既有 .card / .fnode / .well2 同一套皮肤）
HEAD = HEAD + CSS6 + CSS7
GLASS = GLASS.replace("#f5-card{", ".pad,#f7-card,#f5-card{")

# ═══════════════════════════════════════════════════════════════════════════════
# ── 长视频模板（2026-09-12 新增：chapter / quote / table / flow / case）─────────
# 目标：账号形态从「≤7 场景」升到「20–30 场景 + 章节结构」，需要 5 个新场景模板。
#
# 零回归保证（这是本节的硬约束，改这里前先读）：
#   · 既有 01–05 / 05-config / 06-verify / 07-verdict 的 CSS 常量（CSS1–CSS7）与
#     生成代码**一个字节都没动**；
#   · 新皮肤只加在 **LONG_CSS** 里，只被新模板的帧引用 —— 老帧的 <style> 里不会
#     出现一个字，所以老 5/7 场景输出逐字节不变；
#   · 玻璃拟态清单同理：老帧用 GLASS，新帧用 LONG_GLASS（老清单原文 + 新 ID）。
#
# 皮肤沿用与老模板完全相同的常量：深色底（#1F1F1F→#101010 渐变 + .bg）、
# 酸柠强调 #D1FF00、字体 CobaltMono + "Noto Sans SC"/"PingFang SC"、
# 底部来源行 .note（HEAD 里已带，位置 left:110px / top:1408px / 宽 860px）。
#
# 安全区：1080×1920 画布，内容左右各留 110px → 内容宽 **860px**（left:110px）。
# 每个模板的**生成期自检**都用 _estw()（与 chai_layout_precheck.width_px 同一宽度模型）
# 算宽度并逐档降字号，降到底还放不下就显式报错给改法 —— **绝不静默截断/溢出**。
# 所有新模板**一律不使用 `white-space:nowrap`**：历史事故 .fnode .t（26px + nowrap
# 无回退）被 flex 压到 191px 折出孤字；这里宁可降字号 + 换行。
#
# 竖向预算（1080×1920）：内容区上限 y=1332（.dash-b 虚线），.note 落在 y1408；
# 因此卡片底边必须 ≤1290，本表按 y≈500 起排，可用高 ≈790px。
# ───────────────────────────────────────────────────────────────────────────────

# 内容区几何（与 HEAD/DECOR_CSS 同源）
LONG_SAFE_W = 860        # 内容宽：1080 − 110×2
LONG_SAFE_X = 110        # 内容左缘
LONG_CONTENT_BOTTOM = 1290   # 卡片底边硬上限（.note 在 1408，留 118px 净空）
LONG_CARD_W = 860        # 卡片外宽（与外框同宽）
LONG_CARD_PAD_X = 34     # 卡片左右内边距

# ── 长片新模板的「入场秒数」口径（2026-09-12 EP.171）────────────────────────
# 背景：场景交接是 0.5s 的淡出/淡入（`gen_chai_index.py` 的 TRANS_DUR），到 t+0.5s
# 上一场已经淡完、下一场已经淡满。EP.170 第一版把新模板主内容排到 +1.4～2.9s，
# 于是场景边界处有一整段「上一场没了、这一场还没出现」的无字窗口（实测 14/24 场
# 开场 2.1–2.9s 画面是死的）；改成 clamp(dur*0.06,0.35,0.80) 后仍残留 ≈0.45s。
# EP.171 进一步**提前到 0.20–0.30s 并且把主内容的入场时长压到 0.22–0.26s**，
# 让主内容**与上一场的淡出重叠**，在 +0.5s 那一刻已经基本满不透明
# （0.5s 采样点量「内容区白字像素 R,G,B>195」时，透明度 <0.75 的文本会被判成 0）。
LONG_ENTRY_MIN = 0.20    # 入场最早秒数
LONG_ENTRY_MAX = 0.30    # 入场最晚秒数
LONG_ENTRY_K = 0.024     # first = clamp(dur*K, MIN, MAX)；12s 场 → 0.29s
LONG_ENTRY_DUR = 0.22    # 主内容容器的入场时长（≤0.30+0.22=0.52 时已接近满量）


def _long_entry_first(dur: float) -> float:
    """长片新模板主内容的入场秒数（0.20–0.30s）。"""
    return round(max(LONG_ENTRY_MIN, min(LONG_ENTRY_MAX, dur * LONG_ENTRY_K)), 2)

# ── chapter（章节页）────────────────────────────────────────────────────────
# 与 01-hook 的刻意区分：01 是「顶部 warn 条 + 118px 双行大字 + 底部 52px 大数字卡」；
# chapter 是「超大号酸柠章节序号（左对齐出血小）+ 橙色 PART 标签 + 一条 860px title bar
# （左侧 14px 酸柠条）+ 三条 step 预览行」，**没有** 200px 右上场号水印、没有大数字卡。
LONG_CHAPTER_CSS = '''    #ch-rule{position:absolute;left:110px;top:356px;width:220px;height:9px;background:#D1FF00;z-index:6}
    #ch-body{position:absolute;left:110px;top:452px;width:860px;display:flex;gap:28px;align-items:flex-start}
    /* 序号 224px：比既有 .idx 场号水印（200px）更大 → 与 01-hook 的区分度保持；
       同时把标题列让宽（268px 时「把配置写成可验证的文件」在 40px 下也放不下一行）。 */
    #ch-no{flex:0 0 auto;font:900 224px/0.84 "Noto Sans SC","PingFang SC",sans-serif;color:#D1FF00;letter-spacing:-.05em;text-shadow:none}
    #ch-col{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:16px;padding-top:30px}
    #ch-tag{display:inline-flex;align-self:flex-start;padding:9px 20px;border-radius:14px;background:rgba(255,138,20,0.16);box-shadow:inset 0 0 0 1px rgba(255,138,20,0.45);font:700 24px/1 CobaltMono,"PingFang SC",monospace;color:#FF9F3A;letter-spacing:.14em}
    #ch-title{width:100%;position:relative;padding:22px 26px;border-radius:26px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04)}
    #ch-title:before{content:"";position:absolute;left:0;top:24px;bottom:24px;width:14px;border-radius:0 8px 8px 0;background:#D1FF00}
    #ch-title .tx{display:block;padding-left:22px;font:900 60px/1.2 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;letter-spacing:-.02em}
    #ch-steps{margin-top:8px;display:flex;flex-direction:column;gap:14px}
    #ch-steps .stp{display:flex;align-items:center;gap:20px;border-radius:18px;background:rgba(255,255,255,0.05);box-shadow:inset 0 1px 0 rgba(255,255,255,.04), inset 0 0 0 1px #3A3A3A;padding:17px 26px}
    #ch-steps .stp .n{flex:0 0 auto;font:900 22px/1 CobaltMono,"PingFang SC",monospace;color:#D1FF00;letter-spacing:.06em}
    #ch-steps .stp .tx{font:700 30px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#F2EEE8;min-width:0}
'''
# 进度指示（可选，spec 里 progress=false 或缺省 = 整块不渲染 → 与既有版式无差）
LONG_PROGRESS_CSS = '''    #ch-prog{position:absolute;right:110px;top:1184px;font:28px/1 CobaltMono,"PingFang SC",monospace;color:#A8A8A8;letter-spacing:.1em}
    #ch-prog .cur{color:#D1FF00}
'''

# ── quote（官方原文引用页）──────────────────────────────────────────────────
# 屏幕引用（不折 90°）；引号是**印刷件**（深色块 + 酸柠字形），不参与对比度门禁。
LONG_QUOTE_CSS = '''    #qt-rule{position:absolute;left:110px;top:356px;width:220px;height:9px;background:#D1FF00;z-index:6}
    /* 引号是**印刷件**：字形盒必须被元素盒包住，否则 layout 检查报 text_box_overflow
       （实测 2026-09-12：200px 字形盒高 300px，而元素盒只有 211px，高出 51px）。
       170px + line-height .76 + 上下内边距 40/30 → 字形盒 293px < 元素盒 299px；
       top 341 让视觉中心仍在 y≈490，与引文卡片顶（y≈460-660）错开不压字。 */
    #qt-mark{position:absolute;left:110px;top:341px;font:900 170px/0.76 "Noto Sans SC";color:#101010;background:#D1FF00;border-radius:26px;padding:40px 28px 30px 22px;box-shadow:0 14px 34px rgba(0,0,0,.55)}
    #qt-card{position:absolute;left:110px;width:860px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);padding:44px 52px;display:flex;flex-direction:column;gap:30px}
    #qt-card .q{font-weight:700;font-family:"Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;letter-spacing:.005em;overflow-wrap:break-word}
    #qt-card .q .em{color:#D1FF00}
    #qt-tail{display:flex;align-items:flex-end;justify-content:space-between;gap:30px;padding-top:24px;border-top:1px dashed #5A5A5A}
    #qt-tail .head{font:700 26px/1.35 "Noto Sans SC","PingFang SC",sans-serif;color:#E8E2DA;min-width:0}
    #qt-tail .src{flex:0 0 auto;padding:10px 20px;border-radius:16px;background:rgba(209,255,0,0.10);box-shadow:inset 0 0 0 1px rgba(209,255,0,.34);font:22px/1 CobaltMono,"PingFang SC",monospace;color:#D1FF00;letter-spacing:.05em;text-align:right}
'''

# ── table（2 列 × 4–6 行对照）────────────────────────────────────────────────
# ⚠️ 一律不用 nowrap：单元格正常折行，换行数由生成期宽度模型把住（见 _table_geom）。
LONG_TABLE_CSS = '''    #tb-rule{position:absolute;left:110px;top:356px;width:220px;height:9px;background:#D1FF00;z-index:6}
    #tb-card{position:absolute;left:110px;width:860px;border-radius:34px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);padding:26px 26px 30px}
    #tb-card .tb-hd{display:flex;flex-direction:column;gap:7px;padding:2px 8px 18px}
    #tb-card .tb-hd .t{font:700 32px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF}
    #tb-card .tb-hd .t .em{color:#D1FF00}
    #tb-card .tb-hd .s{font:22px/1.4 CobaltMono,"PingFang SC",monospace;color:#C6C0B8;letter-spacing:.04em}
    #tb-card .tb-grid{position:relative;border-radius:24px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(176,176,176,0.22)}
    #tb-card .tb-head{display:flex;background:rgba(255,255,255,0.07);box-shadow:inset 0 -1px 0 rgba(176,176,176,0.28)}
    #tb-card .tb-r{display:flex;box-shadow:inset 0 -1px 0 rgba(176,176,176,0.16)}
    #tb-card .tb-r:last-child{box-shadow:none}
    #tb-card .tb-c{padding:16px 22px;min-width:0;overflow-wrap:break-word}
    #tb-card .tb-c.k{font:700 25px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#F2EEE8}
    #tb-card .tb-c.v{font:700 27px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF}
    #tb-card .tb-head .tb-c{font:700 24px/1 CobaltMono,"PingFang SC",monospace;color:#D1FF00;letter-spacing:.1em;padding:20px 22px}
    #tb-card .tb-r.rh{background:rgba(209,255,0,0.10);box-shadow:inset 3px 0 0 #D1FF00, inset 0 -1px 0 rgba(176,176,176,0.16)}
    #tb-card .tb-r.rh .tb-c.k,#tb-card .tb-r.rh .tb-c.v{color:#D1FF00}
    #tb-card .tb-r.hl .tb-c.v{color:#D1FF00}
    #tb-card .tb-r.hl-r .tb-c.k{color:#D1FF00}
'''

# ── flow（横向进度条 / 时间线）──────────────────────────────────────────────
# 与既有两块的轴向区分（这是设计约束，不是审美偏好）：
#   · 03-mechanism = 横向 3 个 248×200 节点卡 + 卡间大箭头（离散卡片，无连续轴）
#   · 06-verify    = 竖向三步 + 左侧虚线导轨（离散步骤，无连续轴）
#   · flow         = **贯穿全宽的一条连续进度条 + 轴上圆点 + 已走过段酸柠填充 + 时间刻度**
FLOW_W = 860            # 轨道宽
FLOW_STEP_W = 172       # 每步文字列宽上限（860 / 5 = 172）
LONG_FLOW_CSS = '''    #fl-rule{position:absolute;left:110px;top:356px;width:220px;height:9px;background:#D1FF00;z-index:6}
    #fl-card{position:absolute;left:110px;width:860px;border-radius:36px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);padding:34px 20px 36px;display:flex;flex-direction:column;gap:26px}
    #fl-head{flex:0 0 auto;display:flex;flex-direction:column;gap:8px}
    #fl-head .t{font:700 34px/1.3 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF}
    #fl-head .t .em{color:#D1FF00}
    #fl-head .s{font:22px/1.4 CobaltMono,"PingFang SC",monospace;color:#C6C0B8;letter-spacing:.04em}
    /* 本模板最容易踩的两个坑，都是 2026-09-12 实测抓出来的，别改回去：
       ① `width` 必须有：子元素（.track/.fill/.dot/.lb）全是绝对定位，不给宽就
          shrink-to-fit 成 20px（= .dot 宽），步骤文案被压成每行 1 个字（实测 5 行孤字）；
       ② `position` 必须是 relative（不是 absolute）：absolute 会让 .dot/.lb 的
          offsetParent 变成 #fl-card 而不是本元素，整条轴的点与标签整体左移约 140px
          （实测首标签盒 [87,187]，越出 x110 安全线）。relative 让它留在文档流里，
          同时成为子元素的定位参照。 */
    /* 高度 162px：标签在 top:66 起、两行（29+7+20）到 122 —— 142px 时标签底缘会**伸出卡片**，
       被 hyperframes 的 layout 检查判为 text_box_overflow（实测 2026-09-12：标签底 733.98
       vs 卡底 684，溢出 50px）。162 是「最低可嵌套」值，与 chai_long_form.FLOW_AXIS_H 同源。 */
    /* flex:0 0 auto 是**必须**的：卡片声明了 height，轴又是带 height 的 flex item，
       一旦卡片高度算小了，flex 会把轴压扁（实测 162 → 51px），轴上的标签跟着伸出卡片，
       被 hyperframes 判成 text_box_overflow。宁可靠 flex:0 0 auto 顶出去，
       也不许安静地被压扁。 */
    #fl-axis{position:relative;flex:0 0 auto;left:26px;width:748px;height:162px;margin-top:20px}
    #fl-axis .track{position:absolute;left:6px;right:6px;top:23px;height:8px;border-radius:4px;background:rgba(255,255,255,0.12)}
    #fl-axis .fill{position:absolute;left:6px;top:23px;height:8px;border-radius:4px;background:#D1FF00}
    #fl-axis .dot{position:absolute;top:27px;width:30px;height:30px;border-radius:50%;background:#1C1C1C;box-shadow:inset 0 0 0 3px #6A6A6A;transform:translate(-50%,-50%)}
    #fl-axis .dot.on{background:#D1FF00;box-shadow:inset 0 0 0 3px #D1FF00, 0 0 0 9px rgba(209,255,0,0.16)}
    #fl-axis .dot.cur{background:#D1FF00;box-shadow:inset 0 0 0 3px #D1FF00, 0 0 0 12px rgba(209,255,0,0.22)}
    #fl-axis .lb{position:absolute;top:66px;transform:translateX(-50%);text-align:center;width:172px}
    /* 首尾标签锚边而不是居中：居中会让首标签左边缘 = 轴左缘 − 86px，直接越出 x110 安全线。
       中段标签继续居中，视觉节奏不变。 */
    #fl-axis .lb.first{transform:translateX(0);text-align:left}
    #fl-axis .lb.last{transform:translateX(-100%);text-align:right}
    #fl-axis .lb .t{font:700 20px/1.25 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;overflow-wrap:break-word}
    #fl-axis .lb .s{font:16px/1.35 CobaltMono,"PingFang SC",monospace;color:#A8A29A;letter-spacing:.02em;margin-top:7px;overflow-wrap:break-word}
    #fl-axis .lb.cur .t{color:#D1FF00}
'''

# ── case（现象 → 机制 → 结果 因果链）────────────────────────────────────────
# 与 flow 区分：flow 是**横轴**（3–5 步、连续进度条、无因果标记）；
# case 是**竖列**三张因果卡 + 竖向箭头 + 左侧 rail + 顶部「现象」徽章。
LONG_CASE_CSS = '''    #cs-rule{position:absolute;left:110px;top:356px;width:220px;height:9px;background:#D1FF00;z-index:6}
    #cs-head{position:absolute;left:110px;top:404px;width:860px;display:flex;flex-direction:column;gap:16px}
    #cs-kick{display:inline-flex;align-self:flex-start;padding:9px 20px;border-radius:14px;background:rgba(255,138,20,0.16);box-shadow:inset 0 0 0 1px rgba(255,138,20,0.45);font:700 23px/1 CobaltMono,"PingFang SC",monospace;color:#FF9F3A;letter-spacing:.14em}
    #cs-title{font:700 36px/1.28 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF}
    #cs-title .em{color:#D1FF00}
    #cs-chain{position:absolute;left:110px;width:860px;padding-left:96px}
    #cs-chain .rail{position:absolute;left:30px;top:18px;bottom:18px;width:3px;border-radius:2px;background:linear-gradient(180deg,rgba(209,255,0,0.65) 0%,rgba(209,255,0,0.12) 100%)}
    #cs-chain .nd{position:relative;border-radius:30px;background:rgba(255,255,255,0.05);box-shadow:0 12px 32px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);padding:24px 36px;display:flex;flex-direction:column;gap:10px}
    #cs-chain .nd .hd{font:700 25px/1.2 "Noto Sans SC","PingFang SC",sans-serif;color:#D1FF00}
    #cs-chain .nd .tx{font:700 30px/1.35 "Noto Sans SC","PingFang SC",sans-serif;color:#FFFFFF;overflow-wrap:break-word}
    #cs-chain .nd.plain .hd{color:#C6C0B8}
    #cs-chain .nd .n{position:absolute;left:-96px;top:22px;width:56px;height:56px;border-radius:50%;background:#1C1C1C;box-shadow:inset 0 0 0 3px #6A6A6A;display:flex;align-items:center;justify-content:center;font:900 24px/1 CobaltMono,"PingFang SC",monospace;color:#C6C0B8}
    #cs-chain .nd.first .n{background:#D1FF00;box-shadow:inset 0 0 0 3px #D1FF00;color:#101010}
    #cs-chain .arw{position:relative;height:44px;margin:2px 0}
    #cs-chain .arw i{position:absolute;left:-63px;top:0;bottom:14px;width:3px;border-radius:2px;background:#D1FF00;opacity:.5}
    #cs-chain .arw b{position:absolute;left:-70px;bottom:0;width:0;height:0;border-left:9px solid transparent;border-right:9px solid transparent;border-top:13px solid #D1FF00;opacity:.5}
'''

# 长视频帧的完整皮肤 = 老皮肤（HEAD，含 .bg/.idx/.note/.slash/.rline/.dash/.cross/@font-face）
# + 5 个新模板的规则。**只被新模板引用**，老帧的 <style> 里不会出现这些字。
LONG_CSS = (HEAD
            + LONG_CHAPTER_CSS + LONG_PROGRESS_CSS
            + LONG_QUOTE_CSS + LONG_TABLE_CSS + LONG_FLOW_CSS + LONG_CASE_CSS)

# 玻璃拟态清单：老清单原文照抄 + 新卡片 ID（老帧仍用 GLASS，逐字节不变）
LONG_GLASS = GLASS.replace(
    ".pad,#f7-card,#f5-card{",
    ".pad,#f7-card,#f5-card,#ch-title,#ch-steps .stp,#qt-card,#tb-card,#fl-card,#cs-chain .nd{")
assert LONG_GLASS != GLASS, "LONG_GLASS 未命中 GLASS 的 .pad 规则（GLASS 常量被改过？）"
LONG_CSS = LONG_CSS + LONG_GLASS

# ── 每个模板的「标签」：既用于帧内小注，也用于 index 的章节进度（见 gen_chai_index.py）
LONG_KINDS = ("chapter", "quote", "table", "flow", "case")

# ── 长视频模板的**版面常量单一来源**：scripts/chai_long_form.py ────────────────
# 生成期与 chai_layout_precheck.py 调用的是**同一个** geometry 函数（不是两份拷贝），
# 这样「预检说超宽、生成器说没事」这类不一致从结构上不可能发生。
# 按文件路径加载（脚本要能单独拷走运行，不做包结构）。
def _load_long_form():
    import importlib.util as _ilu
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chai_long_form.py")
    _spec = _ilu.spec_from_file_location("chai_long_form", _p)
    _m = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    return _m


LF = _load_long_form()

# ── 既有角色的生成函数要用的运行期状态 ─────────────────────────────────────────
# proj / beat / durs 原先是 main() 的局部量；把既有角色抽成函数后必须提升到模块级。
# _SPEC / _N_SLOTS 供章节进度指示与新模板几何使用。
_proj: str = ""
_SPEC: dict = {}
_N_SLOTS: int = 0
_beat_map: dict = {}
_durs: list = []


def _dur(slot: int) -> float:
    """槽位号（1 起）→ 该场时长。等价于抽取前的 durs[slot-1]，全流程只此一处口径。"""
    return _durs[slot - 1]


def beat(f, i, d):
    """槽位 f 的第 i 条字幕的相对起始时间（拿不到就用缺省 d）。与抽取前同义。"""
    g = _beat_map.get(f, [])
    return g[i][0] if i < len(g) else d



def _long_kind(scene: dict) -> str | None:
    """按**字段**判定该场景该用哪个新模板（不是按槽位号，槽位只是排片顺序）。

    优先级 = 版式专用性：一步走完的（chapter / quote）先判，再判结构化数据
    （table / flow），最后才是 case。字段缺失就返回 None = 不上新模板
    （老路径原样走 05-config / 06-verify / verdict）。
    """
    if not isinstance(scene, dict):
        return None
    if str(scene.get("kind", "") or "") in LONG_KINDS:
        return str(scene["kind"])
    if scene.get("no") is not None and scene.get("title"):
        return "chapter"
    if scene.get("quote"):
        return "quote"
    if scene.get("table"):
        return "table"
    if scene.get("steps"):
        return "flow"
    if scene.get("chain"):
        return "case"
    return None


def _find_slot(S: dict, slots: dict, field: str, prefer: int) -> int | None:
    """找出带某个字段的槽位（`lines` → 配置屏 / `checks` → 验证屏）。

    老路径（5/7 场景）里配置屏恒在第 5 槽、验证屏恒在第 6 槽，所以优先取 `prefer`；
    长视频形态下这两块可以落在任意中间槽位，则退回「唯一带该字段的槽位」。
    一个 spec 里出现两块同类型屏会显式报错（见 main 里的重复守卫），不静默选一个。
    """
    hits = [n for n in sorted(slots) if isinstance(S.get(slots[n]), dict) and field in S[slots[n]]]
    if not hits:
        return None
    if prefer in hits:
        return prefer
    if len(hits) > 1:
        raise SystemExit(f"FAIL: 有 {len(hits)} 个场景带 {field} 字段（槽位 {hits}）——"
                         f"一个 spec 只允许一块「{field}」屏。")
    return hits[0]


# ── 槽位 → 模板的**按字段路由**（2026-09-12）────────────────────────────────────
# 契约（两条路径严格分开，这是本次改造的核心）：
#   · spec **带 chapters**（长片）：槽位号只决定顺序，**不决定模板**。每一槽都按字段
#     选模板（含 01–04 与末场）。字段一个都对不上 → 显式报错并列出全部契约。
#   · spec **不带 chapters**（扁平，既有 5/7 场景各期）：行为完全不变 ——
#     01–04 固定模板、末场判词卡、config 在第 5 槽、verify 在第 6 槽，产物逐字节相同。
# 为什么必须按字段：EP.170 长片里 03=table、04=flow、05=facts、08=action，
#   旧代码把 01–04 写死（01 读 warn_a、03 读 mm）→ `KeyError: 'mm'` 直接崩。
#
# 每个角色的**必需字段**就是它的判别式（缺字段即不匹配，不猜）；
# 顺序 = 判别性从强到弱（越靠前越不会被别的角色抢走）。
ROLE_REQUIRED = {
    # 用**判别性字段**（不是「该模板用到的全部字段」）—— 否则会互相抢：
    #   · chapter 也有 steps，若 steps 先判成 flow，章节页会被做成流程条；
    #   · verdict 与 hook 都有 hero_l1 + note，靠 hook 独有的 warn_a/warn_b 区分；
    #   · verify 与 verdict 都有 title，但只有 verify 有 checks。
    "chapter":   ("no",),
    "table":     ("table",),
    "case":      ("chain",),
    "quote":     ("quote",),
    "flow":      ("steps",),
    "config":    ("lines",),
    "verify":    ("checks",),
    "action":    ("w1_t", "w2_t"),
    "mechanism": ("n1_t", "n2_t", "n3_t"),
    "facts":     ("repo_big",),
    "hook":      ("warn_a", "warn_b", "card_big"),
    "verdict":   ("hero_l1", "note"),     # 兜底：剩下的「大字 + 来源行」按判词卡
}
ROLE_ORDER = ("chapter", "table", "case", "quote", "flow", "config", "verify",
              "action", "mechanism", "facts", "hook", "verdict")
ROLE_EMIT = {}          # 由 _init_role_emit() 填（emit 函数定义在下方，导入时还不存在）
ROLE_TITLE = {          # 报错信息里给人看的模板名（中文 + 契约关键字）
    "chapter": "章节页（no + title）", "table": "2 列 × 3–6 行对照表（table）",
    "case": "现象→机制→结果 因果链（chain）", "quote": "官方原文引用页（quote）",
    "flow": "横向步骤条 3–5 步（steps）", "config": "配置逐行（lines）",
    "verify": "三步验证（checks）", "action": "行动两口井（w1_t/w2_t）",
    "mechanism": "机制三节点（n1_t/n2_t/n3_t）", "facts": "事实卡（repo_big…）",
    "hook": "首帧钩子（warn_a/warn_b/card_big）", "verdict": "判词卡（hero_l1 + note）",
}


def _init_role_emit() -> None:
    """把既有角色的发射函数登记进路由表（它们定义在文件更下方，导入时还不存在）。"""
    if ROLE_EMIT:
        return
    ROLE_EMIT.update({
        "hook": _emit_hook, "facts": _emit_facts, "mechanism": _emit_mech,
        "action": _emit_action, "verdict": _emit_verdict,
        "config": _emit_config, "verify": _emit_verify,
    })


def _classify_role(s: dict) -> str | None:
    """按字段判定该场景该用哪个模板；无匹配返回 None（调用方负责显式报错）。"""
    if not isinstance(s, dict):
        return None
    for role in ROLE_ORDER:
        if all(k in s for k in ROLE_REQUIRED[role]):
            return role
    return None


def _role_contract_text(slot: int, fid: str) -> str:
    return (f"FAIL: 槽位 {slot:02d}（{fid}）的字段对不上任何模板 —— 长片 spec 里\n"
            f"  槽位号只决定顺序，模板一律按字段判定。各模板的必需字段：\n"
            + "".join(f"    {r:<10} {ROLE_TITLE[r]:<26} 需要 "
                      + " + ".join(ROLE_REQUIRED[r]) + "\n" for r in ROLE_ORDER)
            + f"  改法：① 按上表补齐字段；② 把该场景挪到别的槽位；"
              f"③ 删掉该场景与对应的 audio/{slot:02d}.mp3（1 段音频 = 1 个场景）。")


def _canon_frame_name(n: int, total: int, body: dict, chaptered: bool) -> str:
    """槽位号 → 帧文件名。**与 gen_chai_index.py 的 _canon 必须逐字一致**（两处都有注释标注）。

    扁平路径：与改造前的 CANON/_fid 表逐字一致（零回归的前提）。
    长片路径：纯数字键时按该槽位的**实际角色**起名（不是按槽位号猜）。
    """
    if not chaptered:
        if n == 1:
            return "01-hook"
        if n == 2:
            return "02-facts"
        if n == 3:
            return "03-mechanism"
        if n == 4:
            return "04-action"
        if n == total:
            return f"{n:02d}-verdict"
        if n == 5:
            return "05-verdict"
        if n == 6:
            return "06-verify"
        return f"{n:02d}-scene"
    return f"{n:02d}-{_classify_role(body) or 'scene'}"


def _assign_frame_ids(S: dict, slots: dict, total: int, chaptered: bool) -> dict:
    """槽位 → 帧文件名；重复帧名在这里就炸（不会写出残缺帧）。"""
    fid = {}
    for n, k in slots.items():
        fid[n] = k if not re.fullmatch(r"\d+", k) else _canon_frame_name(n, total, S[k], chaptered)
    rev = {}
    for n, f in fid.items():
        if f in rev:
            raise SystemExit(f"FAIL: 场景 id 归一后重名：槽位 {rev[f]:02d} 与 {n:02d} 都叫「{f}」\n"
                             f"  改法：给其中一个场景键加不同的角色后缀（如 05-facts / 12-facts）。")
        rev[f] = n
    return fid


def _validate_chapter_spec(S: dict, slots: dict, fid: dict, ordered: list) -> None:
    """长片 spec 的两条硬校验（只对 chapters 形态生效，扁平路径不看）。

    ① 首帧契约门禁（chai_hook_check.py）比的是 spec 的 `01` 槽文字与封面文字 ——
       01 槽不是钩子的话，那件常驻门禁就失效了；
    ② 判词卡是收尾（关注/下一期），且 #f5-hero 只认 hero_l1/hero_l2_pre/em/tail。
    两条都不静默放行。
    """
    r_first = _classify_role(S[slots[ordered[0]]])
    if r_first != "hook":
        raise SystemExit(
            f"FAIL: 长片 spec 的第 1 槽（{fid[ordered[0]]}）判定为「{r_first or '无匹配'}」，不是首帧钩子。\n"
            f"  首帧契约门禁比的是 spec 的 01 槽文字与封面文字，所以 01 槽必须是 hook\n"
            f"  （需要 warn_a + warn_b + hero_l1 + hero_l2 + card_big + card_t + card_s + note）。\n"
            f"  改法：把钩子场景放在第 1 槽，或把这一场的键改成 01-hook 并补齐上面的字段。")
    r_last = _classify_role(S[slots[ordered[-1]]])
    if r_last != "verdict":
        raise SystemExit(
            f"FAIL: 长片 spec 的末槽（{fid[ordered[-1]]}）判定为「{r_last or '无匹配'}」，不是判词卡。\n"
            f"  末槽固定是收尾判词（需要 hero_l1 + note，可选 hero_l2_pre/em/tail、card_tt…）。\n"
            f"  改法：把判词场景放在末槽；或去掉该场与判词冲突的字段（例如同时有 steps 会被判成 flow）。")


def _route_chaptered(S: dict, slots: dict, fid: dict, ordered: list, kinds: list) -> None:
    """长片路径：**每一槽**都按字段路由（含 01–04 与末场）。"""
    _init_role_emit()
    for n in ordered:
        s = S[slots[n]]
        role = _classify_role(s)
        if role is None:
            raise SystemExit(_role_contract_text(n, fid[n]))
        if role in ROLE_EMIT:
            ROLE_EMIT[role](s, fid[n], n)
        else:
            _css, body, script = LONG_BUILDERS[role](_SPEC, s, _dur(n), n, _N_SLOTS)
            open(f"{_proj}/compositions/frames/{fid[n]}.html", "w").write(
                frame(fid[n], _dur(n), _css, body, script, _dur(n)))
        kinds.append((n, fid[n], role))


def _em(raw, em: str = "") -> str:
    """把 `{em}` 占位符换成强调色 span（老模板一直是这么做的，这里只是统一出口）。"""
    t = str(raw or "")
    return t.replace("{em}", '<span class="em">' + str(em or "") + "</span>") if "{em}" in t else t


def _plain(s) -> str:
    """取「纯文本口径」用于宽度自检：去掉 {em} 占位符本身（em 串已单独计入）。"""
    return str(s or "").replace("{em}", "")


def _to_cjk_num(n: int) -> str:
    """1..30 → 汉字序号（章节页大号数字用；>30 直接给阿拉伯数字）。"""
    d = "零一二三四五六七八九"
    if not 1 <= n <= 30:
        return str(n)
    if n < 10:
        return d[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + d[n % 10]
    return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")


def _chapter_list(spec: dict) -> list:
    """返回 [{id,title,scenes}] 形式的章节表；spec 没有 `chapters` 时返回 []。

    ⚠️ 这里**只读**，不做任何扁平化/改写：扁平 `scenes` 路径的生成结果与改造前
    逐字节相同，是本次改造的硬约束。
    """
    ch = spec.get("chapters")
    if not ch:
        return []
    if not isinstance(ch, list):
        raise SystemExit("FAIL: spec 的 chapters 必须是数组"
                         "（形如 [{\"id\":1,\"title\":\"…\",\"scenes\":{…}}]）")
    out = []
    for i, c in enumerate(ch, 1):
        if not isinstance(c, dict):
            raise SystemExit(f"FAIL: chapters[{i}] 不是对象")
        sc = c.get("scenes") or {}
        if not isinstance(sc, dict):
            raise SystemExit(f"FAIL: chapters[{i}].scenes 不是对象（应为「场景键 → 场景体」的字典）")
        out.append({"id": c.get("id", i), "title": str(c.get("title", "") or ""), "scenes": sc})
    return out


def _chapter_map(spec: dict) -> dict:
    """场景键 → 章节号（1 起，按 chapters 数组顺序）。没有 chapters 时是空表。"""
    m = {}
    for i, c in enumerate(_chapter_list(spec), 1):
        for k in c["scenes"]:
            if k in m:
                raise SystemExit(f"FAIL: 场景键「{k}」同时出现在 chapters[{m[k]}] 与 chapters[{i}] —— "
                                 "一章一场景，同一个键只能出现一次。")
            m[k] = i
    return m


def _slot_chapter(slot: int) -> int:
    """槽位号 → 章节号（1 起）。chapters 里的场景键是全局槽位号，按键前两位对齐。"""
    for i, c in enumerate(_chapter_list(_SPEC), 1):
        for k in (c.get("scenes") or {}):
            m = re.match(r"^(\d+)", str(k))
            if m and int(m.group(1)) == slot:
                return i
    return 0


def _long_progress_html(spec: dict, slot: int, n_slots: int) -> str:
    """章节进度指示（如 02/04）——**缺省关闭**，spec 里显式开才渲染。

    契约（spec 顶层）：`"chapter_progress": true` 或
                       `"chapter_progress": {"mode":"slot"|"chapter"}`
      · mode "chapter"（缺省）：显示「当前章节 / 总章节」，需要 spec 有 chapters；
      · mode "slot"：显示「当前场景序号 / 总场景数」（没有 chapters 时也有用）。
    """
    cfg = _SPEC.get("chapter_progress")
    if not cfg:
        return ""
    mode = "chapter"
    if isinstance(cfg, dict):
        mode = str(cfg.get("mode", "chapter") or "chapter")
    ch = _chapter_list(_SPEC)
    if mode == "chapter" and ch:
        cur = _slot_chapter(slot)
        if not cur:
            return ""
        return (f'<div id="ch-prog"><span class="cur">{cur:02d}</span>'
                f' / {len(ch):02d}</div>')
    return f'<div id="ch-prog"><span class="cur">{slot:02d}</span> / {n_slots:02d}</div>'


def _slot_key(spec: dict, slot: int) -> str:
    """槽位号 → spec 里的场景键（chapters 形态下要先把章节里的场景键映射到全局槽位）。"""
    S = spec.get("scenes") or {}
    if S:
        for k in S:
            m = re.match(r"^(\d+)", str(k))
            if m and int(m.group(1)) == slot:
                return str(k)
        return f"{slot:02d}"
    for c in _chapter_list(spec):
        for k in c["scenes"]:
            m = re.match(r"^(\d+)", str(k))
            if m and int(m.group(1)) == slot:
                return str(k)
    return f"{slot:02d}"


def _wrap_est(text: str, font: float, max_w: float) -> list:
    """按 _estw 模型估算折行结果（返回每行文本）。生成期用它算换行数、判溢出。

    这是**保守估算**，不是浏览器排版：宁可低估容量（多算出一行）也不要少算 ——
    少算会把「其实放不下」判成放得下，那正是历史上返工的成因。
    """
    lines, cur = [], ""
    for ch in str(text):
        cand = cur + ch
        if cur and _estw(cand, font) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur = cand
    if cur or not lines:
        lines.append(cur)
    return lines


def _fit_font(texts: list, max_w: float, sizes: list, max_lines: int = 2) -> tuple:
    """在那几档字号里挑**最大**的、能让每条文案都 ≤ max_lines 行的字号。

    返回 (字号, {原文: 行数})；一档都不行返回 (None, {最坏那条: 行数})。
    """
    best = None
    for f in sizes:                                  # sizes 必须从大到小
        info = {t: len(_wrap_est(t, f, max_w)) for t in texts}
        if all(v <= max_lines for v in info.values()):
            best = (f, info)
            break
    if best:
        return best
    f = sizes[-1]
    info = {t: len(_wrap_est(t, f, max_w)) for t in texts}
    worst = max(info, key=lambda t: info[t])
    return None, {worst: info[worst]}


def _estw(t: str, font: float) -> float:
    """与 chai_layout_precheck.width_px **同一套宽度模型**（中文 1.0em / 拉丁数字 0.66em /
    空格 .33em / 中点 .55em），生成期先用它自检，避免"渲染后才发现溢出"。两处必须同步改。"""
    w = 0.0
    for ch in t:
        if ch == " ":
            w += font * 0.33
        elif ch in "·．":
            w += font * 0.55
        elif re.match(r"[A-Za-z0-9\.\-\+/%_]", ch):
            w += font * 0.66
        else:
            w += font * 1.0
    return w

def _config_geom(lines: list) -> tuple[float, int, int]:
    """05-config 的版面几何：返回 (代码字号, 最大缩进层级, 注释列宽)。
    宽度预算：内容宽 860 − 卡片左右内边距 34×2 − 计数器列 38 − 间距 18×2 − 注释列。
    绝不 nowrap 赌宽度：算不下就降字号，降到底还超就显式报错。"""
    ind_max = max(int(l.get("i", 0)) for l in lines)
    cs = max((_estw(str(l.get("c", "")), 20) for l in lines), default=0.0)
    col_c = int(round(cs)) + 12 if cs else 0
    inner = 860 - 68 - 38 - 36 - col_c
    for f in (22, 21, 20, 19):
        room = inner - 11.5 * ind_max
        if all(_estw(str(l.get("t", "")), f) <= room for l in lines):
            return f, ind_max, col_c
    worst = max(lines, key=lambda l: _estw(str(l.get("t", "")), 19))
    raise SystemExit(
        f"FAIL: 05-config 第 {lines.index(worst) + 1} 行在 19px 字号下仍超宽"
        f"（缩进 {int(worst.get('i', 0))} 级）：\n"
        f"  「{worst.get('t', '')}」≈ {_estw(str(worst.get('t', '')), 19) + 11.5 * int(worst.get('i', 0)):.0f}px"
        f" > 可用 {inner - 11.5 * ind_max:.0f}px\n"
        f"  改法：① 拆成两行；② 降低缩进层级 i；③ 缩短右侧注释 c（注释列按最长注释统一占宽）。")

def _cover_estw(t: str, f: float) -> float:
    """Cover-local width model. Used for the title-fit search and sticker padding.

    Only the CJK coefficient is calibrated here (1.0em, matching
    chai_layout_precheck.width_px). The ASCII coefficient is deliberately generous
    (0.62em): Calibri-style digit/letter pairs in this 900-weight face measure closer
    to 0.43-0.47em, and under-predicting ASCII is how EP.168's master title got sized
    for two lines but wrapped to three ("命中缓存省 90%" at 97px)."""
    return sum(0.62 * f if ord(ch) < 0x2E80 else f for ch in str(t))


def _cover_stickers(c: dict) -> list:
    """Resolve the sticker list.

    Contract: `stickers` is OPTIONAL. Each item is either a plain string (taken as
    the label) or an object:
        {"t": "文字", "icon": "db|bolt|shield|gear|plug",
         "bg": "lime|cyan|orange|cream|white",
         "on": ["l43"]}          # which ratios to show it on; default all three
    When the field is absent we fall back to the daily-spec fields so EP.165–167
    keep a series-consistent look without touching their spec.
    """
    raw = c.get("stickers")
    if raw is None:
        # 默认只派生 **1 枚** 强调标签（用户口径：多枚散落 = 乱七八糟）。
        # 优先用 act 的收益前段（「显式缓存命中 10%」），否则退到 kicker 的第二段。
        out = []
        act = str(c.get("act", "")).split("·")[0].strip()
        kick = str(c.get("kicker", ""))
        kparts = [x.strip() for x in kick.split("·") if x.strip()]
        t = act or (kparts[1] if len(kparts) > 1 else (kparts[0] if kparts else ""))
        if t:
            out.append({"t": t[:16], "icon": "bolt"})
        raw = out
    res = []
    for it in raw:
        if isinstance(it, str):
            it = {"t": it}
        t = str(it.get("t", "")).strip()
        if not t:
            continue
        res.append({
            "t": t,
            "icon": it.get("icon", "db"),
            "bg": it.get("bg", "lime"),
            "on": it.get("on") or ["l916", "l34", "l43"],
        })
    return res[:6]


def _cover_icons() -> dict:
    """Inline SVG sticker glyphs — geometric primitives only, no third-party marks."""
    P = {
        "db": '<ellipse cx="12" cy="6" rx="7.5" ry="3"/><path d="M4.5 6v12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V6"/>'
              '<path d="M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3"/>',
        "bolt": '<path d="M13.5 2 5 13h6l-1.5 9L18 10h-6l1.5-8z"/>',
        "shield": '<path d="M12 2.5 4.5 5.6v6c0 4.3 3 8.1 7.5 9.4 4.5-1.3 7.5-5.1 7.5-9.4v-6L12 2.5z"/>'
                  '<path d="M8.8 11.8l2.3 2.4 4.1-4.6"/>',
        "gear": '<circle cx="12" cy="12" r="3.2"/>'
                '<path d="M12 2.6v3M12 18.4v3M21.4 12h-3M5.6 12h-3M18.6 5.4l-2.1 2.1M7.5 16.5l-2.1 2.1'
                'M18.6 18.6l-2.1-2.1M7.5 7.5 5.4 5.4"/>',
        "plug": '<path d="M9 2.5v5.5M15 2.5v5.5"/><path d="M6.5 8h11v3.2a5.5 5.5 0 0 1-11 0V8z"/>'
                '<path d="M12 16.7V21.5"/>',
        "spark": '<path d="M12 2.5l2.3 6.2 6.2 2.3-6.2 2.3L12 19.5l-2.3-6.2L3.5 11l6.2-2.3L12 2.5z"/>',
    }
    return P


_COVER_CSS = '''
  @font-face{font-family:"PingFang SC";src:local("PingFang SC");font-weight:100 900}
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{overflow:hidden;background:#05070F}
  #root{position:relative;width:100vw;height:100vh;overflow:hidden;color:#FFFFFF;
    font-family:"Noto Sans SC","PingFang SC","Hiragino Sans GB",sans-serif;
    background:
      radial-gradient(120% 80% at 82% 6%, rgba(0,208,255,.30) 0%, rgba(0,208,255,0) 58%),
      radial-gradient(90% 60% at 8% 100%, rgba(255,138,20,.24) 0%, rgba(255,138,20,0) 62%),
      linear-gradient(164deg,#0A1130 0%,#04060F 62%,#0A0806 100%);}
  .stripes{position:absolute;inset:-25%;
    background:repeating-linear-gradient(122deg,rgba(255,255,255,.055) 0 24px,rgba(255,255,255,0) 24px 96px);
    pointer-events:none}
  .grid{position:absolute;inset:0;
    background-image:radial-gradient(rgba(255,255,255,.11) 1.6px, rgba(255,255,255,0) 1.7px);
    background-size:56px 56px;opacity:.5;pointer-events:none}
  .vig{position:absolute;inset:0;
    background:radial-gradient(115% 78% at 50% 42%, rgba(0,0,0,0) 46%, rgba(0,0,0,.62) 100%);
    pointer-events:none}
  .rule{position:absolute;height:12px;border-radius:6px;background:#D1FF00;
    box-shadow:0 6px 0 rgba(0,0,0,.55);pointer-events:none}
  .brand{position:absolute;font-weight:700;color:#D6DCE8;letter-spacing:.16em;white-space:nowrap}
  .idx{position:absolute;font-weight:900;color:#FF8A14;letter-spacing:-.03em;white-space:nowrap;
    -webkit-text-stroke:9px #05070F;paint-order:stroke fill;
    text-shadow:0 12px 0 rgba(0,0,0,.5)}
  .kicker{position:absolute;display:inline-flex;align-items:center;gap:14px;
    background:#D1FF00;color:#080B12;border:8px solid #05070F;border-radius:22px;
    font-weight:800;letter-spacing:.02em;white-space:nowrap;
    box-shadow:0 12px 0 rgba(0,0,0,.5);pointer-events:none}
  .kicker .dot{width:18px;height:18px;border-radius:50%;background:#080B12;flex:0 0 auto}
  .hero{position:absolute;font-weight:900;color:#FFFFFF;letter-spacing:-.018em;line-height:1.14;
    -webkit-text-stroke:7px #05070F;paint-order:stroke fill;pointer-events:none}
  .hero .em{color:#D1FF00}
  .hero .tl{display:block}
  .act{position:absolute;pointer-events:none}
  .act .line{font-weight:800;letter-spacing:.04em;white-space:nowrap;
    -webkit-text-stroke:6px #05070F;paint-order:stroke fill}
  .sun{position:absolute;border-radius:50%;pointer-events:none;
    background:repeating-conic-gradient(from 0deg,#FFFFFF 0deg 7deg,rgba(255,255,255,0) 7deg 22deg);
    -webkit-mask-image:radial-gradient(closest-side,#000 28%,rgba(0,0,0,0) 99%);
    mask-image:radial-gradient(closest-side,#000 28%,rgba(0,0,0,0) 99%)}
  .glow{position:absolute;border-radius:50%;pointer-events:none;
    background:radial-gradient(closest-side,rgba(255,150,40,.55) 0%,rgba(255,120,10,0) 72%)}
  .ava{position:absolute;pointer-events:none}
  .ava .frame{position:absolute;inset:0;border-radius:50%;overflow:hidden;
    box-shadow:0 0 0 12px #05070F, 0 0 0 20px rgba(209,255,0,.95), 0 26px 0 rgba(0,0,0,.5)}
  .ava img{width:100%;height:100%;object-fit:cover;display:block}
  .ava .ph{width:100%;height:100%;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(160deg,#FFB347,#E0741A);color:#3A1A00;font-weight:900}
  .st{position:absolute;display:inline-flex;align-items:center;gap:16px;
    border:8px solid #05070F;border-radius:26px;color:#080B12;
    box-shadow:0 14px 0 rgba(0,0,0,.5);pointer-events:none;white-space:nowrap}
  .st svg{flex:0 0 auto;stroke:#080B12;stroke-width:2.4;fill:none;
    stroke-linecap:round;stroke-linejoin:round}
  .st .tx{font-weight:800;letter-spacing:.02em}
  .st.lime{background:#D1FF00}
  .st.cyan{background:#3DE0FF}
  .st.orange{background:#FF8A14}
  .st.cream{background:#FFE6B0}
  .st.white{background:#FFFFFF}
  .cap{position:absolute;font-weight:700;color:#9FB0CC;letter-spacing:.1em;white-space:nowrap;
    pointer-events:none}

  /* ---------- 9:16 (1080x1920) ---------- */
  .l916 .brand{left:92px;bottom:70px;font-size:27px}
  .l916 .idx{right:80px;top:56px;font-size:170px}
  .l916 .kicker{left:88px;top:96px;font-size:38px;padding:16px 36px}
  .l916 .rule{left:92px;top:352px;width:208px}
  .l916 .hero{left:88px;top:426px;width:{w916}px;font-size:118px}
  .l916 .act{left:92px;top:1032px}
  .l916 .act .line{font-size:44px;color:#D1FF00}
  .l916 .cap{left:92px;bottom:116px;font-size:25px}
  .l916 .sun{right:-76px;bottom:250px;width:640px;height:640px;opacity:.30;
    animation:spin 74s linear infinite}
  .l916 .glow{right:-104px;bottom:170px;width:780px;height:780px}
  .l916 .ava{right:48px;bottom:150px;width:488px;height:488px}
  @keyframes spin{to{transform:rotate(360deg)}}

  /* 3:4 不再单独排版：它就是 4:3 主版的中心裁切（见下方「母版」段） */

  /* ---------- 4:3 (1440x1080) — 标题在左 · 人物在右 · 贴纸绕场 ---------- */
  /* ---------- 母版：4:3 主版 = 中央 3:4 裁切安全窗 ----------
     投放位主要按 4:3 展示，所以**先按 4:3 构图**；同一张图会被中心裁成 3:4，
     因此所有「内容」必须落在中央窗口内（装饰可以出窗、甚至出画布）。
       窗口 = 810 x 1080，居中 → 4:3 画布上的 x315..1125 / y0..1080
       3:4 输出 = 同一张母版按 1080/810 = 1.3333 放大 → 窗口正好铺满 1080x1440
     --ms 就是这把尺子：4:3 时 = 1，3:4 时 = 1.3333。两条比例共用**同一套布局**，
     所以「3:4 输出 = 4:3 的中心裁切」是构造性成立的，不靠肉眼对齐。
     窗口内可用宽 810；左栏文字 540 + 右栏人物 240（间隙 30）。 */
  :root{--ms:{ms}}
  /* 窗口左缘 = canvas 宽 1440 减去窗口宽 810 后居中，再按母版尺度缩放 */
  #root{--wx:calc(315px * var(--ms))}
  /* 母版几何（window 坐标以窗左缘为原点，窗内可用 810 宽 x 1080 高）：
       胶囊 y42 · 主标题 y210 · 行动条 y478 · 人物盘右侧 x=310 y=440 (250) 
       贴纸由求解器在窗内落座 · 小注 y962（贴底，保证没有空白带）
     垂直方向铺满 1080：内容从 y42 一直到 y1042，任何 1/10 高度带都有墨迹。 */
  /* 母版 = 少元素 + 全居中（2026-09-11 第三版）。
     元素只有 5 个：顶部胶囊 / 主标题 2 行 / 人物抠图 / 至多 1 枚标签 / 底部信息行，
     全部以窗中心 x=405 为轴左右居中，垂直自上而下均匀铺满 1080。
     竖向节拍：胶囊 70-166 · 标题 250-445 · 标签 470-562 · 人物 590-1010 · 底注 1024-1066。
     人物高 420 = 窗高 38.9%（30-45% 要求内），是画面主体。 */
  .l43 .brand,.l34 .brand{display:none}   /* 第五个元素之外的内容一律去掉，保持画面干净 */
  .l43 .idx,.l34 .idx{display:none}
  .l43 .rule,.l34 .rule{display:none}
  .l43 .kicker,.l34 .kicker{left:50%;transform:translateX(-50%);top:calc(72px * var(--ms));font-size:calc(28px * var(--ms));padding:calc(12px * var(--ms)) calc(26px * var(--ms))}
  .l43 .hero,.l34 .hero{left:calc(var(--wx));width:calc(810px * var(--ms));top:calc(232px * var(--ms));font-size:calc({f43}px * var(--ms));line-height:1.02;text-align:center}
  .l43 .act,.l34 .act{display:none}
  .l43 .st,.l34 .st{font-size:calc(28px * var(--ms));padding:calc(10px * var(--ms)) calc(24px * var(--ms))}
  .l43 .act .line,.l34 .act .line{font-size:calc(40px * var(--ms));color:#D1FF00}
  .l43 .ava,.l34 .ava{left:50%;transform:translateX(-50%);top:calc(640px * var(--ms));width:calc({ava43}px * var(--ms));height:calc({ava43}px * var(--ms))}
  .l43 .cap,.l34 .cap{left:calc(var(--wx));top:calc(1024px * var(--ms));width:calc(810px * var(--ms));font-size:calc(21px * var(--ms));text-align:center}
  .l43 .cap,.l34 .cap{white-space:normal;line-height:1.35}
  .l43 .sun,.l34 .sun{right:calc(-60px * var(--ms));top:calc(-40px * var(--ms));width:calc(700px * var(--ms));height:calc(700px * var(--ms));opacity:.26;
    animation:spin 74s linear infinite}
  .l43 .glow,.l34 .glow{right:calc(-90px * var(--ms));top:calc(-60px * var(--ms));width:calc(840px * var(--ms));height:calc(840px * var(--ms))}
'''


def _cover_css(title_w: dict, f43: int) -> str:
    """_COVER_CSS with the母版 substitutions filled in.

    `--ms` is the master scale: 4:3 renders at 1440x1080 with --ms=1; the 3:4 output
    uses the SAME layout at 1080x1440 with --ms=1080/810, so the centre 810x1080 of
    the 4:3 master maps exactly onto the whole 3:4 frame — "3:4 = centre crop of 4:3"
    holds by construction instead of by eye.
    (str.format is unusable here — the CSS is full of literal braces.)"""
    out = _COVER_CSS
    for key, val in (("w916", title_w["l916"]), ("w43", title_w["l43"]),
                     ("f43", f43), ("ava43", COVER_MASTER_AVA),
                     ("ms", round(1080 / 810, 6))):
        out = out.replace("{" + key + "}", str(int(val) if key != "ms" else val))
    return out


# ── 封面版式的「地籍图」：避让区与安全口径 ─────────────────────────────────
# 这些常数与 _COVER_CSS 里的绝对定位**同源**，改 CSS 必须同步改这里。
# 贴纸锚点由 _derive_anchor_table() 依据本表算出，所以锚点天然不压字；
# 渲染期校验（cover.html 内联 JS）再按**实测**盒复核一遍，两道关。
COVER_SAFE_MARGIN = 60      # 贴纸到画布边缘的最小留边
COVER_ST_CLEAR = 24         # 贴纸与任何文案/人物盘之间的最小净空（含旋转位移余量）
#   为什么是 24 而不是 6：贴纸要 rotate(-7°..7°)，transform-origin 居中，
#   旋转后包围盒会整体位移（实测可达 ~12px）。求解期不模拟这个位移，
#   就靠这条净空把误差吃进去 —— 净空 24 = 12px 位移 + 12px 视觉间隙。
COVER_ST_CARD_GAP = 26      # 贴纸与贴纸之间的最小净空（阴影不互压）
# 母版（4:3 主版）与其中心 3:4 裁切安全窗。投放位主要按 4:3 展示，所以 4:3 是主版；
# 同一张图会被中心裁成 3:4，因此「内容」必须全在窗内，「装饰」可以出窗。
COVER_MASTER_TEXT_W = 810   # 窗口内文字列宽 = 整窗宽（居中排版不能留单边内边距）
COVER_MASTER_FS_MAX = 106   # 主标题字号上限（保证折 2 行，给标签留出中间带）
COVER_MASTER_AVA = 390      # 人物抠图边长；390/1080 = 36.1% 窗高（口径要求 30–45%）
# 唯一标签的落座（窗内坐标，水平居中于窗）。3:4 是同一母版放大 4/3，
# 所以它的 y 也是 4/3 倍；x 用 405 = 窗宽/2 使其中心落在窗中心。
COVER_MASTER_SEAT = {"l43": {"x": 405, "y": 468}, "l34": {"x": 405, "y": 624}}
COVER_MASTER = {
    "canvas": (1440, 1080),        # 4:3 画布
    "window": (810, 1080),         # 中央 3:4 安全窗（x315..1125）
    "win_x": 315,
    "text_w": 540,                 # 窗内左栏（文字）
    "text_x": 20,                  # 相对窗口左缘
    "ava_x": 530, "ava_y": 270, "ava_size": 240,   # 窗内右栏（人物）
}
# (left, top, right, bottom)；right/bottom 是保守上限（宁可多让一点）
COVER_KEEPOUT = {
    "l916": {
        "W": 1080, "H": 1920, "hero_left": 88, "hero_top": 426, "kicker_w": 700,
        "boxes": [("kicker", 88, 96, 700, 202), ("act", 92, 1032, 606, 1094),
                  ("cap", 92, 1768, 600, 1804), ("brand", 92, 1812, 380, 1850),
                  ("idx", 632, 56, 1000, 294), ("ava", 544, 1282, 1032, 1770)],
    },
    "l34": {
        "W": 1080, "H": 1440, "hero_left": 84, "hero_top": 368, "kicker_w": 700,
        "boxes": [("kicker", 84, 80, 700, 176), ("act", 88, 840, 600, 896),
                  ("cap", 88, 1307, 600, 1340), ("brand", 88, 1345, 370, 1382),
                  ("idx", 684, 44, 1004, 251), ("ava", 604, 886, 1032, 1314)],
    },
    "l43": {
        "W": 1440, "H": 1080, "hero_left": 70, "hero_top": 356, "kicker_w": 700,
        "boxes": [("kicker", 70, 66, 700, 158), ("act", 74, 568, 600, 627),
                  ("cap", 74, 974, 600, 1006), ("brand", 72, 1010, 370, 1046),
                  ("idx", 1099, 40, 1380, 222), ("ava", 816, 178, 1336, 698)],
    },
}
# ── 静态断言：底部的「小注 cap」与「品牌字 brand」不许同行重叠（F-1 教训）──────
# 2026-09-11：4:3 曾把 .cap(bottom:38) 与 .brand(bottom:34) 放在同一行 → 重叠 259px，
# 而 render_covers.mjs 的硬门禁只校「贴纸↔文案/安全区」，**校不到文案↔文案**。
for _r, _d in COVER_KEEPOUT.items():
    _b = {n: (y0, y1) for (n, _x0, y0, _x1, y1) in _d["boxes"]}
    if "cap" in _b and "brand" in _b:
        (c0, c1), (b0, b1) = _b["cap"], _b["brand"]
        if not (c1 <= b0 or b1 <= c0):
            raise SystemExit(
                f"FAIL: 封面 {_r} 的 .cap(y{c0}-{c1}) 与 .brand(y{b0}-{b1}) 同行重叠——"
                "底注与品牌字必须分行（改 _COVER_CSS 的 bottom 值并同步 COVER_KEEPOUT）。")

# 贴纸实测宽度表：用 Chromium 1:1 渲染 .st 量出来的（font-weight 800，
# PingFang SC / Noto Sans SC 回落），单位 px。改 .st 的 padding/边框/图标尺寸
# 或换字体后必须重新标定（量法见 README §7.6）。
_COVER_ST_MEASURED = {
    "DSH": 154, "AI 账单": 197, "3 套代理": 221, "缓存省钱": 223, "官方三份": 223,
    "先看版本号": 260, "AGENT SKILLS": 285, "把标准写成文件": 305,
    "显式缓存命中 10%": 315, "SKILL.md + 三层加": 332, "永久记忆（深度版）": 370,
}


def _cover_sticker_box(text: str) -> tuple:
    """Rendered sticker size (w, h), matching the .st CSS.

    Table first (real measurements), then a conservative estimate. Being slightly
    too wide is safe — the seat solver will simply leave a bit more room; being too
    narrow is what caused the P0 (a seat computed for a narrow sticker let a wider
    one sit on the title). So the estimate rounds up.
    """
    t = str(text)
    n = len(t)
    f = 36 if n <= 6 else (32 if n <= 9 else 28)
    if t in _COVER_ST_MEASURED:
        w = _COVER_ST_MEASURED[t]
    else:
        # 标定得到的每字宽（含余量）：CJK 0.66em、ASCII 0.36em，再加 76px 固定件
        per = sum(0.36 * f if ord(ch) < 0x2E80 else 0.66 * f for ch in t)
        w = int(per + 76 + 0.5)
    h = max(92, int(f * 1.4 + 32))
    return w, h


def _cover_boxes_overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _inflate(b, k):
    return (b[0] - k, b[1] - k, b[2] + k, b[3] + k)


def _derive_anchor_table(sizes: list, title_w: dict, kicker_w: dict,
                         _want_targets: dict | None = None,
                         meas_zones: dict | None = None,
                         meas_sizes: dict | None = None,
                         meas_rot: dict | None = None,
                         meas_resolved: dict | None = None,
                         target_box: dict | None = None) -> dict:
    """Compute sticker seats from the layout constants.

    `sizes` carries the actual rendered sticker boxes, so a narrow sticker is not
    silently treated as a wide one (an early version assumed a fixed maximum width
    and produced seats that clipped the kicker).

    Search: for every sticker, enumerate candidate left/top positions on a grid,
    reject any box that leaves the safe margin, touches a keep-out zone (inflated
    by COVER_ST_CLEAR) or comes within COVER_ST_CARD_GAP of an already-placed
    sticker, then pick the candidate that scores best on an explicit art-direction
    preference. Everything is derived, so the render-time gate is a backstop
    rather than the thing that makes the layout work.
    """
    table = {}
    rot = {"l916": (-7, 6, -5), "l34": (-7, 6, -5), "l43": (-6, 7, -5)}
    for ratio, d in COVER_KEEPOUT.items():
        W, H = d["W"], d["H"]
        margin, clear = COVER_SAFE_MARGIN, COVER_ST_CLEAR
        if meas_zones and ratio in meas_zones:
            # 量测优先：避让区就是浏览器量出来的真实盒
            zones = [(z[1] - clear, z[2] - clear, z[3] + clear, z[4] + clear)
                     for z in meas_zones[ratio]]
        else:
            zones = [(x0 - clear, y0 - clear, x1 + clear, y1 + clear)
                     for _, x0, y0, x1, y1 in d["boxes"]]
        if not (meas_zones and ratio in meas_zones):
            # 没量测时用估算：标题盒（宽取该比例实际字号下的最长行宽）
            zones.append((d["hero_left"] - clear, d["hero_top"] - clear,
                          d["hero_left"] + title_w[ratio] + clear,
                          d["hero_top"] + d.get("hero_h", 0) + clear))

        # 候选位置：左右两条可贴边轨道 + 中间若干列，纵向往上优先
        if ratio in ("l43", "l34"):
            # 母版只有一个居中标签：锚点 = 窗中心，y 由 COVER_MASTER_SEAT 定
            _bx = COVER_MASTER["win_x"]
            xs_left = [_bx + COVER_MASTER_SEAT[ratio]["x"]]
        else:
            xs_left = [margin, d["hero_left"] + title_w[ratio] + 40, int(W * 0.52), int(W * 0.60)]
        placed, seats, intended = [], [], []
        use_sizes = (meas_sizes or {}).get(ratio) or sizes
        # 迭代校正：上一轮的「期望盒」与「浏览器实际盒」之差，本轮加回去。
        # 数学建模旋转包围盒总会差几个像素（实测 dy 差到 17.8px），
        # 用一轮反馈把它收敛掉，比继续推公式可靠。
        _tx = {}
        _rv = (meas_resolved or {}).get(ratio) or []
        _tg = (target_box or {}).get(ratio) or []
        for _i, _rbox in enumerate(_rv):
            if _rbox is None or _i >= len(_tg) or not _tg[_i]:
                continue
            _tx[_i] = (_tg[_i][0] - _rbox[0], _tg[_i][1] - _rbox[1])
        # 母版（4:3/3:4）的贴纸必须**完全落在中央安全窗内** —— 出窗的只能是纯氛围层
        # （光晕/斜纹/点阵/网格），贴纸跨窗缘会被裁成半截，按缺陷处理。
        if ratio in ("l43", "l34"):
            _mw, _mh = COVER_MASTER["canvas"]
            _ww, _wh = COVER_MASTER["window"]
            _wx = (COVER_MASTER["win_x"]) * (1.0 if ratio == "l43" else 1.0)
            bounds = (_wx, 0, _wx + _ww, _wh)
        else:
            bounds = (margin, margin, W - margin, H - margin)
        _maxn = 1 if ratio in ('l43', 'l34') else len(use_sizes)
        for idx, (sw0, sh0) in enumerate(use_sizes[:_maxn]):
            # 量到的是**未旋转**的盒；落座后要 rotate，包围盒会变大：
            #   W' = w·|cos| + h·|sin|,  H' = w·|sin| + h·|cos|
            # 不换算就会算出一条右侧轨道，旋转后右边缘溢出画布（实测 1020 → 1035）。
            _a = math.radians(abs(rot[ratio][min(idx, 2)]))
            sw = int(math.ceil(sw0 * math.cos(_a) + sh0 * math.sin(_a))) + 2
            bh = int(math.ceil(sw0 * math.sin(_a) + sh0 * math.cos(_a))) + 2
            # rotate 会让包围盒整体位移（transform-origin 居中），量测给出真实偏移
            rox, roy = 0.0, 0.0   # 按旋转盒落座，无需再模拟位移
            candidates = []
            _ys = ([COVER_MASTER_SEAT[ratio]["y"]] if ratio in ("l43", "l34")
                   else list(range(int(bounds[1]), int(bounds[3] - bh) + 1, 6)))
            for xi, x in enumerate(xs_left):
                for y in _ys:
                    for xa, side in ((x, "l"), (W - x, "r")):
                        # 锚点语义：'l' 用左边缘对齐 xa，'r' 用右边缘对齐 xa
                        # （渲染期 JS 就是这么摆的，求解必须同口径，否则右侧轨道会越界）
                        bx = xa - sw if side == "r" else xa
                        # 候选盒就是**旋转后**的包围盒（sw/bh 已按角度换算，
                        # 与渲染期「先量旋转盒再对齐边界」同一口径），
                        # 再加上上一轮学到的校正量
                        _dx, _dy = _tx.get(idx, (0.0, 0.0))
                        box = (bx + _dx, y + _dy, bx + sw + _dx, y + bh + _dy)
                        if (box[0] < bounds[0] or box[2] > bounds[2]
                                or box[1] < bounds[1] or box[3] > bounds[3]):
                            continue
                        if any(_cover_boxes_overlap(box, z) for z in zones):
                            continue
                        if any(_cover_boxes_overlap(box, _inflate(p, COVER_ST_CARD_GAP))
                               for p in placed):
                            continue
                        # 偏好：① 靠上（信息流首屏最容易被看到）② 左右交替
                        # ③ 离标题远一点（避免视觉上跟标题挤在一起）
                        score = (y + abs(bx - (margin if idx % 2 == 0 else W - margin - sw)) * 0.9
                                 + (400 if idx % 2 == 0 and bx > W / 2 else 0)
                                 + (400 if idx % 2 == 1 and bx < W / 2 else 0))
                        candidates.append((score, bx, y, xa, side))
            if not candidates:
                continue                      # 放不下就少放一张（宁可少，不许压字）
            candidates.sort(key=lambda c: (c[0], c[2], c[1]))
            _, bx, y, xa, side = candidates[0]
            bx_true = bx + _tx.get(idx, (0.0, 0.0))[0]
            by_true = y + _tx.get(idx, (0.0, 0.0))[1]
            placed.append((bx_true, by_true, bx_true + sw, by_true + bh))
            intended.append((bx_true, by_true))
            # 锚点 = 旋转包围盒的**中心**。中心对旋转不变（transform-origin:50% 50%），
            # 所以渲染期只要 left = cx - w/2、top = cy - h/2 就能精确落在我算的盒上。
            # 用左/右边缘当锚点时，旋转会把盒挪走 (rw-w)/2，正是贴纸漫进标题的原因。
            # 渲染期的锚点语义是「旋转包围盒的中心」（transform-origin 50% 50%）。
            # 母版只有一枚标签且必须严格居中：直接把锚点钉在窗中心，
            # 别走 box-left → 中心 的换算（那条路会因旋转盒宽度差把贴纸整体偏移）。
            if ratio in ("l43", "l34"):
                _wcx = COVER_MASTER["win_x"] + COVER_MASTER["window"][0] / 2.0
                seats.append((int(round(_wcx * (1.0 if ratio == "l43" else 1080 / 810.0))),
                              int(round(by_true + bh / 2.0)), side))
            else:
                seats.append((int(round(bx_true + sw / 2.0)),
                              int(round(by_true + bh / 2.0)), side))
        if _want_targets is not None:
            _want_targets[ratio] = intended
        out = []
        for i, (ax, ay, side) in enumerate(seats):
            out.append([ax, ay, rot[ratio][min(i, 2)], side])
        table[ratio] = out
    return table

def _cover_title_lines(c: dict) -> list:
    """Split the cover title into display lines. The concatenated text is exactly
    hero_l1 + hero_pre + hero_em + hero_tail so the first-frame gate
    (chai_hook_check.py) still sees the same characters."""
    l1 = str(c.get("hero_l1", ""))
    rest = str(c.get("hero_pre", "")) + "\x00" + str(c.get("hero_em", "")) + str(c.get("hero_tail", ""))
    return [l1, rest]


def _cover_title_html(c: dict) -> str:
    l1, rest = _cover_title_lines(c)
    pre, em = rest.split("\x00", 1)
    parts = []
    if l1:
        parts.append(f'<span class="tl">{l1}</span>')
    parts.append(f'<span class="tl">{pre}<span class="em">{em}</span></span>')
    return "".join(parts)


def _cover_title_nchars(c: dict) -> int:
    l1, rest = _cover_title_lines(c)
    pre, em = rest.split("\x00", 1)
    return max(len(l1), len(pre + em))


def _cover_fit(lines: list, box_w: float, hi: int, lo: int) -> int:
    """Largest font size (px) at which every title line fits box_w at 95% budget.
    Uses the same width model as chai_layout_precheck so a half-width "AI" is not
    charged as a full CJK glyph."""
    for f in range(hi, lo - 1, -1):
        if not lines or all(_cover_estw(ln, f) <= box_w * 0.90 for ln in lines):
            return f
    return lo


def _cover_geometry(spec: dict, proj: str, geom: dict | None = None) -> dict | None:
    """Two-round geometry: draft -> measure -> solve -> measure again.

    Round 1 measures the real element boxes and sticker sizes from a draft render.
    The solver then has to decide where a rotated sticker actually lands, and pure
    modelling kept drifting by a few px (measured dy error up to 17.8px — enough to
    walk a sticker onto the title, which is the bug this whole path exists to kill).
    So round 2 re-measures with the solved seats in place and returns the residual
    per sticker; the final render adds that residual back.

    If measuring is impossible (no node / no puppeteer) we return None, the caller
    falls back to estimates, and the render-time gate still hard-fails on collision.
    """
    if geom is not None:
        return geom
    if os.environ.get("CHAI_COVER_NO_MEASURE"):
        return None
    ratios = {"l916": [1080, 1920], "l34": [1920, 1440], "l43": [1440, 1080]}
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "measure_cover_geometry.mjs")
    if not os.path.exists(script):
        return None
    tmpdir = tempfile.mkdtemp(prefix="chai-cover-geom-")
    try:
        os.symlink(os.path.join(os.path.abspath(proj), "assets"),
                   os.path.join(tmpdir, "assets"))
        draft = os.path.join(tmpdir, "cover.html")

        def _measure(html: str) -> dict | None:
            open(draft, "w").write(html)
            req, out = os.path.join(tmpdir, "req.json"), os.path.join(tmpdir, "geom.json")
            json.dump({"cover": draft, "ratios": ratios}, open(req, "w"))
            r = subprocess.run(["node", script, req, out],
                               capture_output=True, text=True, timeout=240)
            if r.returncode != 0 or not os.path.exists(out):
                print(f"  ⚠️  封面几何量测失败：{r.stderr.strip()[:200]}")
                return None
            return json.load(open(out))

        g1 = _measure(_chai_cover_html(spec, proj, _draft=True))
        if g1 is None:
            return None
        # 解一遍，拿到「期望盒」
        want = {}
        _chai_cover_html(spec, proj, geom=g1, _want_targets=want)
        # 第二轮：带上期望盒，量出真实盒与残差
        for _r, _d in g1.items():
            _d["target"] = want.get(_r) or []
        g2 = _measure(_chai_cover_html(spec, proj, geom=g1, _want_targets={}))
        return g2 or g1
    except Exception as e:                                    # noqa: BLE001
        print(f"  ⚠️  封面几何量测异常（改用估算值）：{type(e).__name__}: {e}")
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _chai_cover_html(spec: dict, proj: str, geom: dict | None = None,
                     _draft: bool = False, _want_targets: dict | None = None) -> str:
    """Build cover.html: one page, three bespoke layouts, chosen at runtime by viewport.

    ───── 数据契约（向后兼容；新增字段全部可选） ─────
    既有字段（EP.165–167D 原样可用，缺字段静默回退）：
      cover.kicker    顶角胶囊；缺省 ""
      cover.hero_l1   主标题第一行
      cover.hero_pre / hero_em / hero_tail   主标题第二行（em 走强调色）
      cover.act       行动文案；缺省 ""（整块不渲染）
      cover.cap43     4:3 左下角小注；缺省 ""（整块不渲染）
      cover.font      主标题字号基准（px）；缺省 96。仅作基准，三比例各自收敛到安全宽度
    新增可选字段：
      cover.stickers  [ "文字" | {"t","icon","bg","on"} ]  贴纸徽章，≤6 个；
                      icon ∈ db|bolt|shield|gear|plug|spark，bg ∈ lime|cyan|orange|cream|white
                      on: 只在这些比例显示（["l916","l34","l43"]）；缺省三比例都显示
                      缺省时由 kicker/act 自动派生，保证系列一致
      cover.avatar    柴主编抠图开关，默认 true
      cover.avatar_src  相对工程根的抠图 PNG；缺省 assets/brand/chai-editor-avatar-cutout.png

    首帧契约：主标题文本始终来自 hero_l1/hero_pre/hero_em/hero_tail，不另起一套文案。
    """
    c = spec.get("cover", {}) or {}
    ep = str(spec.get("ep", ""))
    font = int(c.get("font", 96) or 96)
    # 三比例各自收敛：用与 chai_layout_precheck.width_px 同一套字宽模型（ASCII 0.55em、
    # CJK 1.0em）逐档降字号，取「最长一行 ≤ 该比例标题框宽 95%」的最大档。
    # 不能用「字符个数」当宽度——「AI 不再失忆，」的 AI 是半角，按整字算会把字号压小一档。
    sub1, sub2 = _cover_title_lines(c)
    pre2, em2 = sub2.split("\x00", 1)
    lines = [ln for ln in (sub1, pre2 + em2) if ln]
    if not lines:
        raise SystemExit(
            "FAIL: 封面主标题为空——hero_l1 / hero_pre / hero_em / hero_tail 至少要有一个非空。\n"
            "  首帧契约要求 9:16 封面文字与正片首帧大字对得上，空标题过不了 chai_hook_check。")
    # 旧 spec 的 font:74 是「卡片内小标题」口径，不能直接当大标题档位，所以夹到
    # 0.9–1.15 的窄区间；真正决定字号的是下面的宽度收敛（逐档降到放得下为止）。
    scale = max(0.90, min(1.15, font / 96.0))

    # 9:16 仍是视频首帧，用自己的一套（首帧契约不变）。
    f916 = _cover_fit(lines, 820, int(150 * scale), 64)
    # 母版：4:3 是唯一「真正被看到」的版面，主标题要在**安全窗**里尽量大。
    # 上限给到 118——窗口可用宽只有 810（左栏 540），字号由宽度收敛决定，
    # 比旧的 72–81px 明显大一档。
    MW, MH = COVER_MASTER["canvas"]
    f43 = _cover_fit(lines, COVER_MASTER_TEXT_W, min(int(150 * scale), COVER_MASTER_FS_MAX), 56)
    W43 = COVER_MASTER["text_w"]
    for _name, _fs, _bw in (("9:16", f916, 820), ("4:3 主版", f43, COVER_MASTER_TEXT_W)):
        if any(_cover_estw(ln, _fs) > _bw * 0.95 for ln in lines):
            _w = max(_cover_estw(ln, _fs) for ln in lines)
            raise SystemExit(
                f"FAIL: 封面主标题在 {_name} 放不下——最长行约 {_w:.0f}px > 可用 {_bw * 0.95:.0f}px。\n"
                f"  改法：① 缩短 hero_l1 / hero_pre+hero_em+hero_tail；② 拆成更多行（本模板固定两行）；"
                f"③ 调小 spec 的 cover.font 降整体档位。")
    # 3:4 = 4:3 的中心裁切放大 1080/810 倍
    f34 = f43

    brand = "柴主编｜只讲一件事"
    kicker = str(c.get("kicker", "") or "")
    act = str(c.get("act", "") or "")
    cap43 = str(c.get("cap43", "") or "")
    hero_html = _cover_title_html(c)

    avatar_on = c.get("avatar", True) is not False
    avatar_src = c.get("avatar_src", "assets/brand/chai-editor-avatar-cutout.png")
    has_avatar = avatar_on and os.path.exists(os.path.join(proj, avatar_src))
    if avatar_on and not has_avatar:
        print(f"  ⚠️  封面人物素材缺失（{avatar_src}），回退为色块占位")

    if has_avatar:
        ava_inner = f'<img src="{avatar_src}" alt="">'
    else:
        ava_inner = f'<div class="ph" style="font-size:{int(520*0.3)}px">{brand[0]}</div>'

    ICONS = _cover_icons()
    stickers = _cover_stickers(c)

    def st_html(i: int, s: dict) -> str:
        n = len(s["t"])
        f = 36 if n <= 6 else (32 if n <= 9 else 28)
        w = _cover_sticker_box(s["t"])[0]
        icon = ICONS.get(s["icon"], ICONS["db"])
        on = " ".join(s["on"])
        return (f'<div class="st {s["bg"]}" id="st{i}" data-on="{on}" data-w="{w}">'
                f'<svg width="44" height="44" viewBox="0 0 24 24">{icon}</svg>'
                f'<span class="tx" style="font-size:{f}px">{s["t"]}</span></div>')

    st_html_all = "".join(st_html(i, s) for i, s in enumerate(stickers))
    st_data = [{"on": s["on"]} for s in stickers]
    # 落座求解必须知道**真实**贴纸尺寸：左锚点贴纸以左边缘对齐 x=60，
    # 所以窄贴纸反而向右伸得更短、却仍占满 60..60+w —— 早期版本按固定的最大宽度
    # 估算，算出的锚点让窄贴纸贴到了顶角胶囊上（实测 box 56.7,256 撞 kicker）。
    st_sizes = [_cover_sticker_box(s["t"]) for s in stickers]

    # 标题盒尺寸：宽 = 最长行估宽（不再一律撑满 820/800/648，那样会白白吃掉右侧空白，
    # 逼得贴纸无处可放）；高 = 行数 × 字号 × 行高。行高见 _COVER_CSS（9:16 与 3:4 是
    # 1.14、4:3 显式 1.16），这里按同值复算，供落座求解与避让区使用。
    _lh = {"l916": 1.14, "l34": 1.14, "l43": 1.16}
    _fs = {"l916": f916, "l34": f34, "l43": f43}
    _pad = {"l916": 88, "l34": 84, "l43": 70}
    title_w, hero_h = {}, {}
    for _r in ("l916", "l34", "l43"):
        _w = max([_cover_estw(ln, _fs[_r]) for ln in lines] or [0.0])
        # +16 给字间负字距/描边留余量；上限仍是原来的盒宽，避免超宽标题破版
        # ⚠️ 已知项 F-1（2026-09-11）：_.cover_estw 与真实字形推进有误差（EP.168 实测
        # 估算 777px / 盒 793px / 真机 795px）→ 末段可能被折到下一行；表现为
        # 「主标题 3 行、末行是强调数字」——**无遮挡、无裁切**（贴纸净空 61px），
        # 视觉上是"关键数字独占一行"，暂按可接受处理。彻底修法见 README-deep §7 待办：
        # 让字号收敛与盒宽都以**浏览器实测行宽**为准（measure_cover_geometry.mjs 已在仓库）。
        _cap_w = COVER_MASTER_TEXT_W if _r in ("l43", "l34") else COVER_KEEPOUT[_r]["W"] - _pad[_r] - 60
        title_w[_r] = int(min(_w + 16, _cap_w))
        hero_h[_r] = int(len(lines) * _fs[_r] * _lh[_r] + 8)

    # 贴纸锚点：由 _derive_anchor_table 按真实几何求空位，天然不压字。
    # 仍然只是「首选」——渲染期会按实测盒再复核，被占就直接失败（不再偷偷挪）。
    if not _draft:
        geom = geom if geom is not None else _cover_geometry(spec, proj)
    meas_zones, meas_sizes, meas_rot = {}, {}, {}
    meas_resolved, meas_target = {}, {}
    for _r, _d in (geom or {}).items():
        if _d.get("target"):
            meas_target[_r] = [tuple(t) if t else None for t in _d["target"]]
    for _r, _d in (geom or {}).items():
        if _r not in COVER_KEEPOUT:
            continue
        zones = [[k.lstrip("."), v[0], v[1], v[2], v[3]] for k, v in _d.get("zones", {}).items()]
        # 把与标题盒相交的元素并进标题盒本身：4:3 里人物盘就压着标题盒，
        # 不合并的话「标题右侧」会被当成一块可用空地。
        hz = next((z for z in zones if z[0] == "hero"), None)
        if hz:
            for z in zones:
                if z is hz:
                    continue
                if z[1] < hz[3] and hz[1] < z[3] and z[2] < hz[4] and hz[2] < z[4]:
                    hz[1], hz[2] = min(hz[1], z[1]), min(hz[2], z[2])
                    hz[3], hz[4] = max(hz[3], z[3]), max(hz[4], z[4])
        meas_zones[_r] = zones
        _sz = []
        for st in _d.get("stickers") or []:
            if st and st.get("w"):
                _sz.append((int(st["w"] + 0.5), int(st["h"] + 0.5)))
        if _sz:
            meas_sizes[_r] = _sz
        # 量测把每个贴纸摆到草稿锚点后，回报它**实际占据**的旋转包围盒。
        # 求解期用它把「期望盒」校正到「真实盒」，避免渲染期再漂几像素。
        _res = []
        for rv in _d.get("resolved") or []:
            _res.append(None if not rv else (rv["x"], rv["y"], rv["bw"], rv["bh"]))
        if _res:
            meas_resolved[_r] = _res
        # 旋转位移：量测把贴纸摆到 (LEFT, TOP) 并套用真实 rotate，
        # 返回旋转后包围盒相对未旋转盒的偏移 —— 求解期加上它就能精确落位。
        _ro = []
        for st in _d.get("rotOffset") or []:
            if st:
                _ro.append((st["dx"], st["dy"]))
        if _ro:
            meas_rot[_r] = _ro
    _ko = {k: dict(v) for k, v in COVER_KEEPOUT.items()}
    for _r in _ko:
        _ko[_r]["hero_h"] = hero_h[_r]
    # 顶角胶囊宽度按实际文案算（363 = 2×8px 边框 + 2×padding + 圆点 18 + 间距 16 的实测值）
    _kicker_fs = {"l916": 38, "l34": 36, "l43": 34}
    _kick_w = {r: int(363 + _cover_estw(kicker, _kicker_fs[r]))
               for r in ("l916", "l34", "l43")} if kicker else {}
    anchor_table = _derive_anchor_table(
        st_sizes, title_w, _kick_w,
        meas_zones=meas_zones or None, meas_sizes=meas_sizes or None,
        meas_rot=meas_rot or None, meas_resolved=meas_resolved or None,
        target_box=meas_target or None, _want_targets=_want_targets)
    st_margin = COVER_SAFE_MARGIN

    kicker_html = (f'<div class="kicker"><i class="dot"></i><span>{kicker}</span></div>'
                   if kicker else "")
    act_html = f'<div class="act"><span class="line">{act}</span></div>' if act else ""
    cap_html = f'<div class="cap">{cap43}</div>' if cap43 else ""

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>{_cover_css(title_w, f43)}
  /* 各比例字号由 spec 与标题长度收敛得到（见 _chai_cover_html） */
  .l916 .hero{{font-size:{f916}px}}
  /* 4:3 与 3:4 共用母版（见 _COVER_CSS 的「母版」段），字号已由母版给出 */
</style>
<script>
/* 先定比例再开画：布局是互斥类，贴在 <body> 之前设置，避免闪一下竖版 */
(function () {{
  var w = window.innerWidth, h = window.innerHeight;
  var cls = (w === 1440) ? 'l43' : ((w === 1920 && h === 1440) ? 'l34' : 'l916');
  document.documentElement.className = 'ar-' + cls;
  document.addEventListener('DOMContentLoaded', function () {{
    var root = document.getElementById('root');
    root.classList.add(cls);
    /* 母版尺度：4:3 主版 = 1；3:4 = 1080/810（同一套布局放大，窗口正好铺满画幅）。
       必须按**视口**逐次设，而不能写死在 CSS 里——同一条 CSS 服务两种输出。 */
    root.style.setProperty('--ms', cls === 'l34' ? (1080 / 810) : 1);

    /* ── 贴纸落座 + 硬校验（2026-09-11 修 P0：贴纸压主标题） ──────────────
       旧版三个错误，都是这次出 P0 的直接原因：
         ① 避让区是**手写死的常数**，比真实元素盒小（9:16 标题区底写 670，实际 672–711），
            贴纸正好落在写小的那 41px 里；
         ② 自检用 offsetWidth/offsetHeight（**未旋转**的盒）算，旋转后左边缘实测 55.2px
            已经越了 60px 安全线却没报出来；
         ③ 报了只 console.warn，照样出图 —— 评审说这才是放行的直接原因。
       现在：避让区**从真实元素量**（kicker/hero 两行/act/cap/brand/idx + 人物盘），
       贴纸盒用 getBoundingClientRect()（**含 rotate 变换**），越界即抛错 + 置全局错误标记，
       render_covers.mjs 读到标记就非零退出。宁可少放一张贴纸，也不许压字。 */
    var ST_MARGIN = {st_margin};
    /* 贴纸与任何文案/人物盘之间的最小净空（px）。取 6：贴纸有 8px 深色描边
       和 14px 硬阴影，净空小于这个数就算贴到字上了。 */
    var ST_CLEAR = 6;
    /* 先行贴纸的落座锚点（按系列审美手工定）；若该点被占，再在它附近搜一个空位，
       最后才报错。锚点本身也过一遍校验，所以写错了跑一次就知道。 */
    var ANCHOR = {json.dumps(anchor_table, ensure_ascii=False)};

    function boxesOverlap(a, b) {{
      return a.x < b.r && b.x < a.r && a.y < b.b && b.y < a.b;
    }}
    /* 把避让区外扩 k px：贴纸与文案必须留出净空，不能只判「不相交」。 */
    function inflate(rect, k) {{
      return {{ x: rect.left - k, y: rect.top - k, r: rect.right + k, b: rect.bottom + k }};
    }}
    /* 保护对象：所有正文文案 + 人物盘。装饰性的 .sun / .stripes / .grid 允许被压。 */
    function protectBoxes() {{
      var boxes = [], sel = ['.kicker', '.hero', '.act', '.cap', '.brand', '.idx'], i, j;
      for (i = 0; i < sel.length; i++) {{
        var el = document.querySelector(sel[i]);
        if (el && getComputedStyle(el).display !== 'none') boxes.push({{ k: sel[i], r: el.getBoundingClientRect() }});
      }}
      var tl = document.querySelectorAll('.hero .tl');
      for (j = 0; j < tl.length; j++) boxes.push({{ k: '.hero .tl[' + j + ']', r: tl[j].getBoundingClientRect() }});
      var ava = document.querySelector('.ava');
      if (ava) boxes.push({{ k: '.ava', r: ava.getBoundingClientRect() }});
      return boxes;
    }}

    function placeStickers() {{
      var W = window.innerWidth, H = window.innerHeight;
      var zones = protectBoxes();
      var items = {json.dumps(st_data, ensure_ascii=False)};
      var errs = [], placed = [];

      function fits(rect) {{
        /* 三个坑，都是这次 P0 的直接成因：
           ① 判「压字」必须把避让区**外扩 ST_CLEAR px**，不能只判「相交」。
              EP.168 的 9:16 出货版里，贴纸旋转后的盒与标题只差 **0.05px** ——
              浏览器算出的旋转盒比我手算的还小一点，于是「差一点点」被当成「没压」。
              可视觉上贴纸的深色描边 + 硬阴影已经贴到字上了，那就是压字。判定要求净空。
           ② 避让区不许用手写常数（旧版把标题区底写成 670，实际 672–711，贴纸正落那 41px）。
              现在一律从**真实元素**量（见 protectBoxes）。
           ③ 安全区判定才用 eps 容差：rotate(-6°) 会让盒左右各多出约 1px，
              60px 的锚点因此落到 59.9，属亚像素误差，不该判越界。 */
        var eps = 1.5;
        var bx = rect.left, by = rect.top, br = rect.right, bb = rect.bottom;
        if (bx + eps < ST_MARGIN || by + eps < ST_MARGIN
            || br - eps > W - ST_MARGIN || bb - eps > H - ST_MARGIN) return false;
        var box = {{ x: bx, y: by, r: br, b: bb }};
        for (var i = 0; i < zones.length; i++)
          if (boxesOverlap(box, inflate(zones[i].r, ST_CLEAR))) return false;
        for (var j = 0; j < placed.length; j++)
          if (boxesOverlap(box, inflate(placed[j], ST_CLEAR))) return false;
        return true;
      }}

      var used = 0;
      for (var i = 0; i < items.length; i++) {{
        var el = document.getElementById('st' + i);
        if (!el) continue;
        if (items[i].on.indexOf(cls) < 0) {{ el.style.display = 'none'; continue; }}
        var a = ANCHOR[cls] && ANCHOR[cls][used];
        used++;
        if (!a) {{ el.style.display = 'none'; continue; }}
        /* 真实未旋转宽度：data-w 是估算值，早期版本用它算锚点，结果右轨道越界 */
        var w = el.offsetWidth || parseInt(el.getAttribute('data-w'), 10) || 240;
        var h = el.offsetHeight || 90;
        /* 锚点 = 旋转包围盒的中心（求解器给的也是中心）。旋转围绕盒中心
           （transform-origin: 50% 50%），所以中心不动，直接反推 left/top 即可，
           落座位置与求解器的预测完全一致。 */
        var x = a[0] - w / 2, y = a[1] - h / 2;
        el.style.transform = 'rotate(' + a[2] + 'deg)';
        el.style.left = Math.round(x) + 'px';
        el.style.top = Math.round(y) + 'px';
        var ok = fits(el.getBoundingClientRect());

        if (!ok) {{
          /* 锚点被占：在锚点附近由近及远搜一个空位（10px 网格，四边都试） */
          var found = null;
          for (var rad = 10; rad <= 420 && !found; rad += 10) {{
            for (var dy = -rad; dy <= rad && !found; dy += 10) {{
              for (var dx = -rad; dx <= rad && !found; dx += 10) {{
                if (Math.max(Math.abs(dx), Math.abs(dy)) !== rad) continue;
                el.style.left = Math.round(x + dx) + 'px';
                el.style.top = Math.round(y + dy) + 'px';
                if (fits(el.getBoundingClientRect())) found = {{ x: x + dx, y: y + dy }};
              }}
            }}
          }}
          if (!found) {{
            el.style.left = Math.round(x) + 'px';
            el.style.top = Math.round(y) + 'px';
            errs.push('贴纸 ' + i + '「' + el.textContent + '」在 ' + cls + ' 找不到不压字的落点'
                      + '（锚点 ' + a.join(',') + '，盒 ' + w + 'x' + h + '）');
            continue;
          }}
        }}
        placed.push(el.getBoundingClientRect());
      }}
      return errs;
    }}

    var errs = [];
    if (document.fonts && document.fonts.ready) {{
      document.fonts.ready.then(function () {{ errs = placeStickers(); report(errs); }});
    }} else {{
      errs = placeStickers(); report(errs);
    }}

    /* ── 裁切安全校验（母版专属）──────────────────────────────────────────
       投放位主要按 4:3 展示，而同一张 4:3 会被中心裁成 3:4。所以「内容」必须全部
       落在中央窗口内：窗口 = 窗口宽 x 画布高，在 4:3 画布上居中。
       窗口 = (画布宽 - 窗宽)/2 .. (画布宽 + 窗宽)/2  → 1440x1080 上是 x315..1125。
       装饰（.sun/.glow/.stripes/.grid/.idx/.brand）允许出窗甚至出画布。
       容差 8px：描边/阴影的亚像素外溢不算越界。 */
    var MS_TOL = 8;
    function cropSafe() {{
      var errs2 = [];
      var isMaster = (cls === 'l43' || cls === 'l34');
      if (!isMaster) return errs2;
      var H2 = window.innerHeight;
      // 母版尺度：4:3 是 1、3:4 是 4/3 —— 直接读页面上那把尺子，别复算
      var ms = parseFloat(getComputedStyle(document.getElementById('root')).getPropertyValue('--ms')) || 1;
      var canvW = 1440 * ms;          // 母版画布宽（4:3 = 1440，3:4 = 1920）
      var winW = 810 * ms;            // 中央安全窗宽
      var x0 = (canvW - winW) / 2 + MS_TOL, x1 = (canvW + winW) / 2 - MS_TOL;
      var y0 = MS_TOL, y1 = H2 - MS_TOL;
      // 贴纸也在检查之列：母版里贴纸必须完整落在窗内，出窗的只能是纯氛围层
      // .hero / .cap 是母版的**满窗宽居中文本块**（宽度恒等于窗宽），
      // 它的盒必然「顶到」窗口两边，那是排版方式不是越界 —— 由居中校验去管它。
      // 这里只查有实际几何形状的元素：胶囊、人物盘、贴纸、行动条。
      var sel = ['.kicker', '.ava', '.st', '.act'];
      for (var i = 0; i < sel.length; i++) {{
        var el = document.querySelector(sel[i]);
        if (!el || getComputedStyle(el).display === 'none') continue;
        var r = el.getBoundingClientRect();
        if (r.width < 2) continue;
        if (r.left < x0 || r.right > x1 || r.top < y0 || r.bottom > y1) {{
          errs2.push('裁切不安全：' + sel[i] + ' 盒 [' + r.left.toFixed(1) + ',' + r.top.toFixed(1) + ','
            + r.right.toFixed(1) + ',' + r.bottom.toFixed(1) + '] 越出中央安全窗 ['
            + x0.toFixed(0) + ',0,' + x1.toFixed(0) + ',' + y1.toFixed(0) + ']'
            + '（窗口 ' + winW + 'x' + H2 + '，居中）');
        }}
      }}
      // 居中校验：主要元素（标题/人物/标签/底注）的中心 x 必须与窗中心对齐（≤8px）。
      // 用户口径：不居中 = 缺陷（第一版左右分栏被否）。
      var CX_TOL = 8;
      var centered = ['.hero', '.ava', '.st', '.cap'];
      var winCx = (x0 + x1) / 2;
      for (var q = 0; q < centered.length; q++) {{
        var ce = document.querySelector(centered[q]);
        if (!ce || getComputedStyle(ce).display === 'none') continue;
        var cr = ce.getBoundingClientRect();
        if (cr.width < 2) continue;
        var off = (cr.left + cr.right) / 2 - winCx;
        if (Math.abs(off) > CX_TOL) {{
          errs2.push('不居中：' + centered[q] + ' 中心 x = ' + ((cr.left + cr.right) / 2).toFixed(1)
            + '，窗中心 x = ' + winCx.toFixed(1) + '，偏差 ' + off.toFixed(1) + 'px（上限 ' + CX_TOL + 'px）');
        }}
      }}

      // 氛围层（光晕/斜纹/点阵/网格/光芒/集数）豁免：让它们出窗甚至出画布，
      // 但把它们藏掉之后，窗口四边各 4px 带里不许再有可辨别的形（贴纸/文字越缘）。
      var AMBIENT = ['.stripes', '.grid', '.vig', '.sun', '.glow'];
      var hidden = [];
      for (var a = 0; a < AMBIENT.length; a++) {{
        var ae = document.querySelector(AMBIENT[a]);
        if (ae && ae.style.visibility !== 'hidden') {{ ae.style.visibility = 'hidden'; hidden.push(ae); }}
      }}
      // 像素带检查需要一张画布截图。cover.html 是静态文件，自己拿不到位图；
      // render_covers.mjs 会把当前页截图通过 window.__coverShot 注入。
      var msk = window.__coverShot;
      if (msk && msk.width) {{
        var cw = msk.width, ch = msk.height;
        // 截图按母版画布 1:1 抓（render_covers.mjs 从 CDP 取），所以 k 恒为 1
        var k = cw / (1440 * ms);
        var B = Math.max(1, Math.round(4 * k));
        var wx0 = Math.round(x0 * k), wx1 = Math.round(x1 * k);
        var wy0 = Math.round(y0 * k), wy1 = Math.round(y1 * k);
        var bands = [
          ['左缘', wx0, wy0, wx0 + B, wy1],
          ['右缘', Math.max(0, wx1 - B), wy0, wx1, wy1],
          ['上缘', wx0, wy0, wx1, wy0 + B],
          ['下缘', wx0, Math.max(0, wy1 - B), wx1, wy1]
        ];
        for (var b2 = 0; b2 < bands.length; b2++) {{
          var bd = bands[b2], cnt = 0;
          for (var yy = bd[1]; yy < bd[3]; yy += 1) {{
            for (var xx = bd[0]; xx < bd[2]; xx += 1) {{
              var idx = (yy * cw + xx) * 4;
              if (mask.data[idx] > 40 || mask.data[idx + 1] > 40 || mask.data[idx + 2] > 40
                  || (mask.data[idx + 3] || 0) > 40) cnt++;
            }}
          }}
          if (cnt > 0) {{
            errs2.push('裁切不安全：窗' + bd[0] + '，' + bd[1] + '..' + bd[2] + '，' + bd[3]
              + ' 的 ' + B + 'px 带内有 ' + cnt + ' 个墨迹像素（贴纸/文字贴了窗缘；氛围层已豁免）');
          }}
        }}
      }}
      for (var h = 0; h < hidden.length; h++) hidden[h].style.visibility = '';
      // 主标题必须正好 2 行（3 行会让 4:3 版式失衡；真折 3 行要显式说明）
      var hEl = document.querySelector('.hero');
      if (hEl) {{
        var lh = parseFloat(getComputedStyle(hEl).lineHeight) || 0;
        if (lh > 0) {{
          var nl = Math.round(hEl.getBoundingClientRect().height / lh);
          if (nl !== 2) errs2.push('主标题折了 ' + nl + ' 行（母版要求 2 行）');
        }}
      }}
      return errs2;
    }}

    window.__coverRecheck = function (shot) {{
      window.__coverShot = shot;
      report(window.__lastPlaceErrs || []);
    }};

    function report(errs) {{
      window.__lastPlaceErrs = errs;
      var all = errs.concat(cropSafe());
      window.__coverLayoutErrors = all;
      for (var i = 0; i < all.length; i++) console.error('[cover] ' + cls + ' ' + all[i]);
      if (all.length) console.error('[cover] ' + cls + ' 封面校验失败 ' + all.length + ' 项');
    }}
  }});
}})();
</script>
</head>
<body>
<div id="root">
  <div class="stripes"></div>
  <div class="grid"></div>
  <div class="vig"></div>
  <div class="idx" data-layout-allow-overlap>{ep}</div>
  <div class="brand">{brand}</div>
  {kicker_html}
  <div class="rule"></div>
  <div class="hero">{hero_html}</div>
  {act_html}
  <div class="sun"></div>
  <div class="glow"></div>
  <div class="ava"><div class="frame">{ava_inner}</div></div>
  {st_html_all}
  {cap_html}
</div>
</body>
</html>
'''


# ═══════════════════════════════════════════════════════════════════════════════
# ── 长视频 5 个模板的生成器（每个都是：几何自检 → 排版 → 入场动效）──────────────
# 统一约定：
#   · 所有宽度断言先用 _estw()（与 chai_layout_precheck.width_px 同一模型）在**生成期**
#     算，放不下就 SystemExit 并给出「① 缩短 ② 拆行 ③ 减项」的改法 —— 不静默截断；
#   · 一律不用 white-space:nowrap（历史事故：.fnode .t 被 flex 压到 191px）；
#   · 卡片底边 ≤ LONG_CONTENT_BOTTOM（1290），给 .note（y1408）留 118px；
#   · 节点/步骤的入场相位尽量跟着字幕 beat()，跟不到就用等比时间点。
# ───────────────────────────────────────────────────────────────────────────────

def _build_chapter(spec: dict, s: dict, dur: float, slot: int, n_slots: int) -> tuple:
    """chapter（章节页）：大号章节序号 + 章节标题 + 小注 + 可选三条预览行。"""
    no = s.get("no")
    title = str(s.get("title", "") or "")
    if not title:
        raise SystemExit(f"FAIL: 章节页（槽位 {slot:02d}）缺少 title —— chapter 模板要求 "
                         "no + title 至少两个字段（note 必填，见既有皮肤契约）。")
    # 几何（序号列宽 / 标题列可用宽 / 标题字号）全部来自共享模块 chai_long_form.py，
    # 与 chai_layout_precheck.py 是**同一次计算** —— 常量与 CSS 同源（见 §2A.1）。
    no_txt = _to_cjk_num(int(no)) if str(no).lstrip("-").isdigit() else str(no)
    _g = LF.chapter_geom(no, title, [str(x) for x in (s.get("steps") or [])])
    no_w, col_w, t_avail = _g["no_w"], _g["col_w"], _g["title_avail"]
    for _kind, _msg in _g["errors"]:
        if _kind in ("no", "title"):
            raise SystemExit(f"FAIL: {_msg}\n"
                             f"  改法：① 缩短标题（章节标题建议 ≤12 个中文字）；"
                             f"② 序号改成 1 位（1–30 会转汉字）；③ 用两个短标题拆章。")
    if col_w < 480:
        raise SystemExit(
            f"FAIL: 章节页序号「{no_txt}」太宽（≈{no_w:.0f}px），标题列只剩 {col_w:.0f}px < 480px。\n"
            f"  改法：① 序号写 1–2 位（1..30 会转汉字，如 12 → 十二）；"
            f"② 改用阿拉伯数字（no 传字符串，如 \"12\"）。")
    t_avail = col_w - 26 * 2 - 22          # #ch-title padding 26×2 + .tx padding-left 22px
    # 校准系数 CJK_ADV：_estw 按 1.0em 算 CJK，实测 Noto Sans SC 900 的推进约 1.13em
    # （2026-09-12 用浏览器 span 实测：「代理与缓存踩过的坑」60px 单行 535px，
    #   而 _estw 只算 460px —— 偏低 14%）。这里**不改 _estw**（它是与预检共用的常量），
    # 只给「必须一行放下」的标题加 15% 安全系数，宁可降一档字号也不许折行。
    fs = _g["title_fs"]
    steps = s.get("steps") or []
    if not isinstance(steps, list):
        raise SystemExit("FAIL: 章节页 steps 必须是字符串数组")
    steps = [str(x) for x in steps]
    for _kind, _msg in _g["errors"]:
        if _kind == "steps":
            raise SystemExit(f"FAIL: {_msg}\n"
                             "  改法：① 每条预览行 ≤16 个中文字（或 ≤32 个半角）；"
                             "② 减少条数（至多 3 条）。")
    rows = []
    if steps:
        sfs = _g["step_fs"]
    for i, t in enumerate(steps, 1):
        rows.append(f'''      <div class="stp"><div class="n">{i:02d}</div><div class="tx">{t}</div></div>''')
    steps_html = ("\n    <div id=\"ch-steps\">\n" + "\n".join(rows) + "\n    </div>") if rows else ""
    prog = _long_progress_html(spec, slot, n_slots)
    ttag = str(s.get("tag", "CHAPTER") or "CHAPTER")
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="ch-rule"></div>
    <div id="ch-body">
      <div id="ch-no">{no_txt}</div>
      <div id="ch-col">
        <div id="ch-tag">{ttag}</div>
        <div id="ch-title" style="font-size:{fs}px"><span class="tx">{title}</span></div>{steps_html}
      </div>
    </div>
    {prog}
    <div class="note" data-layout-allow-overlap>{s.get('note', '')}</div>'''
    n_st = max(1, len(steps))
    # 2026-09-12 修正：原来 first = dur/(步数+2)（12.8s 场 ≈2.57s）→ 开场 2-3 秒只见装饰件。
    # 改为固定早入场（≤0.75s）：主内容必须在场首 1 秒内出现（留存经验 + 「最高价值信息进画面主体」）。
    # 2026-09-12（EP.171）再提前：0.20–0.30s 入场 + 0.22s 时长，与上一场淡出重叠，
    # 消除场景边界那段「两边都没有」的无字窗口（+0.5s 采样点必须 24/24 有内容）。
    first = _long_entry_first(dur)
    stagger = round(max(0.1, (dur - first - 1.2) / n_st), 2)
    script = f'''    tl.fromTo("#ch-rule",{{scaleX:0,transformOrigin:"left center"}},{{scaleX:1,duration:.45,ease:"power2.out"}},0.05)
      .fromTo("#ch-no",{{x:-26,opacity:0}},{{x:0,opacity:1,duration:.3,ease:"power3.out"}},0.06)
      .fromTo("#ch-tag",{{y:-12,opacity:0}},{{y:0,opacity:1,duration:.18,ease:"power2.out"}},{round(first*0.5,2)})
      .fromTo("#ch-title",{{y:28,opacity:0}},{{y:0,opacity:1,duration:{LONG_ENTRY_DUR},ease:"power3.out"}},{first})
      .fromTo("#ch-steps .stp",{{x:-20,opacity:0}},{{x:0,opacity:1,duration:.4,ease:"power2.out",stagger:.18}},{round(first+0.35,2)});
    tl.fromTo("#ch-no",{{scale:1}},{{scale:1.03,duration:.45,ease:"power2.out",yoyo:true,repeat:1}},{round(first+0.5,2)});
    tl.to("#ch-body",{{y:-5,duration:1.5,ease:"sine.inOut",yoyo:true,repeat:1}},{round(max(2.2, dur-4.0),2)});
'''
    if prog:
        script = script.rstrip("\n") + f'''
    tl.fromTo("#ch-prog",{{opacity:0}},{{opacity:1,duration:.5,ease:"power2.out"}},{round(first+0.6,2)});
'''
    return LONG_CSS, body, script


def _build_quote(spec: dict, s: dict, dur: float, slot: int, n_slots: int) -> tuple:
    """quote（官方原文引用页）：大字引文 + 引号装饰 + 来源角标（含文档名/小节）。"""
    q = str(s.get("quote", "") or "")
    if not q:
        raise SystemExit(f"FAIL: 引用页（槽位 {slot:02d}）缺少 quote —— 该模板要求 quote + source。")
    if not str(s.get("source", "") or ""):
        raise SystemExit(f"FAIL: 引用页（槽位 {slot:02d}）缺少 source —— 官方原文必须带来源角标"
                         "（文档名 + 小节），这是本模板的硬契约。")
    if re.search(r"<[a-zA-Z/][^>]*>", q):
        raise SystemExit(f"FAIL: 引用页 quote 含 HTML 标签（本模板只做转义输出，不解析 HTML）：「{q[:40]}…」\n"
                         "  改法：引文要强调就用 {em} 占位符 + hero_em 字段。")
    # 几何（字号 / 行数 / 卡片高与 top）来自共享模块，与预检同一次计算
    _qg = LF.quote_geom(q, str(s.get("head", "") or ""))
    fs = _qg["fs"] or LF.QT_MIN_FS
    if _qg["errors"]:
        raise SystemExit(f"FAIL: {_qg['errors'][0][1]}\n"
                         f"  改法：① 把引文拆到 2–4 行（用 `\\n` 显式断行，模板按行渲染）；"
                         f"② 缩短引文；③ 一屏只引一处，长引文拆成两屏。\n  引文：「{q[:60]}…」")
    lines = q.split("\n") if "\n" in q else _wrap_est(q, fs, LF.QT_INNER)
    if "\n" in q:                      # 显式断行：生成期就 trim，别把行尾空格带进视觉
        _trimmed = [ln.strip() for ln in lines if ln.strip()]
        if _trimmed:
            lines = _trimmed
    else:                               # 自动折行：行尾空白会撑出视觉空洞（中文排版里不能留）
        lines = [ln.rstrip() for ln in lines if ln.strip()] or [""]
    q_html = "<br>".join(_em(ln, s.get("hero_em", "")) for ln in lines)
    head = str(s.get("head", "") or "")
    src = str(s.get("source", "") or "")
    src_w = _estw(src, 22) + 40                      # padding 20×2
    card_h, top = _qg["card_h"], _qg["top"]
    if top + card_h > LONG_CONTENT_BOTTOM:
        raise SystemExit(
            f"FAIL: 引用页卡片高 {card_h}px + top {top}px = {top + card_h}px 越过内容下限 {LONG_CONTENT_BOTTOM}px"
            f"（{len(lines)} 行 × {fs}px）。\n  改法：① 减少引文行数；② 去掉 head 字段；③ 拆成两屏。")
    head_html = f'\n      <div class="head">{head}</div>' if head else ""
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="qt-rule"></div>
    <div id="qt-mark">“</div>
    <div id="qt-card" style="top:{top}px;font-size:{fs}px">
      <div class="q">{q_html}</div>
      <div id="qt-tail">{head_html}
        <div class="src">{src}</div>
      </div>
    </div>
    <div class="note" data-layout-allow-overlap>{s.get('note', '')}</div>'''
    # 引文卡的入场也提前（原 dur*0.16，最多 1.4s；EP.171 起 0.20–0.30s + 0.22s 时长）
    b1 = _long_entry_first(dur)
    b2 = round(min(dur - 1.2, b1 + 0.30), 2)
    script = f'''    tl.fromTo("#qt-rule",{{scaleX:0,transformOrigin:"left center"}},{{scaleX:1,duration:.45,ease:"power2.out"}},0.05)
      .fromTo("#qt-mark",{{scale:.6,opacity:0,transformOrigin:"top left"}},{{scale:1,opacity:1,duration:.3,ease:"back.out(1.5)"}},0.06)
      .fromTo("#qt-card",{{y:34,opacity:0}},{{y:0,opacity:1,duration:{LONG_ENTRY_DUR},ease:"power3.out"}},{b1})
      .fromTo("#qt-tail",{{opacity:0,y:14}},{{opacity:1,y:0,duration:.22,ease:"power2.out"}},{b2});
    tl.fromTo("#qt-mark",{{rotate:-3}},{{rotate:3,duration:1.8,ease:"sine.inOut",yoyo:true,repeat:1}},{round(b1+0.4,2)});
    tl.to("#qt-card",{{y:-5,duration:1.6,ease:"sine.inOut",yoyo:true,repeat:1}},{round(max(2.4, dur-4.2),2)});
'''
    return LONG_CSS, body, script


def _table_rows(tbl) -> tuple:
    """把 table 字段归一成 (表头[2] 或 None, [[k,v,hl], …])。"""
    if isinstance(tbl, list):
        hd, rs = None, tbl
    elif isinstance(tbl, dict):
        hd, rs = tbl.get("head"), tbl.get("rows")
    else:
        raise SystemExit("FAIL: table 必须是「行数组」或 {head:[2], rows:[…]} 对象")
    if hd is not None and (not isinstance(hd, (list, tuple)) or len(hd) != 2):
        raise SystemExit(f"FAIL: table 的表头必须是正好 2 项（当前 {hd!r}）")
    if not isinstance(rs, list) or not (3 <= len(rs) <= 6):
        raise SystemExit(f"FAIL: table 的行数必须是 3–6 行（含表头共 4–6 行；当前 "
                         f"{len(rs) if isinstance(rs, list) else type(rs).__name__} 行）——"
                         "版式按 2 列 × 4–6 行设计，多了会压到 .note。")
    out = []
    for i, r in enumerate(rs, 1):
        if isinstance(r, (list, tuple)):
            if len(r) != 2:
                raise SystemExit(f"FAIL: table 第 {i} 行必须是 2 项（[行名, 值]），当前 {len(r)} 项")
            out.append([str(r[0]), str(r[1]), False, False])
        elif isinstance(r, dict):
            if not r.get("k") or not r.get("v"):
                raise SystemExit(f"FAIL: table 第 {i} 行缺 k 或 v 字段")
            out.append([str(r["k"]), str(r["v"]), bool(r.get("hl")),
                        str(r.get("hl", "")) == "col" or bool(r.get("hl_col"))])
        else:
            raise SystemExit(f"FAIL: table 第 {i} 行格式不对（应为 ([行名, 值]) 或 {{k,v,hl}}）")
    hd_out = [str(x) for x in hd] if hd is not None else None
    return hd_out, out


def _build_table(spec: dict, s: dict, dur: float, slot: int, n_slots: int) -> tuple:
    """table（2 列 × 4–6 行对照）：表头 + 行；某行/某列可高亮；**不用 nowrap 赌宽度**。"""
    hd, rows = _table_rows(s.get("table"))
    # 几何全部来自共享模块 chai_long_form.py（与预检同一次计算）
    _tg = LF.table_geom([[r[0], r[1]] for r in rows])
    k_avail, v_avail = _tg["k_avail"], _tg["v_avail"]
    kfs, vfs, row_h = _tg["k_fs"], _tg["v_fs"], _tg["row_h"]
    if _tg["errors"]:
        raise SystemExit(f"FAIL: {_tg['errors'][0][1]}\n"
                         f"  改法：① 缩短该单元格文案（行名列 ≤{k_avail/22:.0f} 个中文字、"
                         f"数值列 ≤{v_avail/24:.0f} 个中文字）；② 把一行拆成两行（行数上限 6）；"
                         f"③ 改用 quote / case 模板放长句。")
    card_h = LF.table_height(len(rows), bool(hd), bool(s.get("title")), row_h)
    top = 452
    if top + card_h > LONG_CONTENT_BOTTOM:
        raise SystemExit(
            f"FAIL: 对照表卡片高 {card_h}px + top {top}px = {top + card_h}px 越过内容下限 "
            f"{LONG_CONTENT_BOTTOM}px（{len(rows)} 行 × {row_h}px）。\n"
            f"  改法：① 行数降到 6 行以内；② 缩短 title/sub；③ 缩到单行文案让行高不涨。")
    rows_html = []
    for i, (k, v, hl, hl_col) in enumerate(rows):
        cls = "tb-r" + (" rh" if hl and not hl_col else "") + (" hl" if hl is True or hl_col else "")
        if hl_col:
            cls = cls.replace(" hl", "")
        cells = f'<div class="tb-c k">{k}</div><div class="tb-c v">{v}</div>'
        rows_html.append(f'''      <div class="{cls}">{cells}</div>''')
    head_html = (f'''      <div class="tb-head"><div class="tb-c k">{hd[0]}</div>'''
                 f'''<div class="tb-c v">{hd[1]}</div></div>''') if hd else ""
    hd_block = ""
    if s.get("title"):
        sub = s.get("sub")
        hd_block = (f'''      <div class="tb-hd"><div class="t">{_em(s["title"], s.get("hero_em", ""))}</div>'''
                    + (f'''<div class="s">{sub}</div>''' if sub else "") + "</div>\n")
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="tb-rule"></div>
    <div id="tb-card" style="top:{top}px;height:{card_h}px">
{hd_block}      <div class="tb-grid">
{head_html}
{chr(10).join(rows_html)}
      </div>
    </div>
    <div class="note" data-layout-allow-overlap>{s.get('note', '')}</div>'''
    # 同上：原 dur*0.14（12.5s 场 =1.6s）→ 主内容开场等 1.6-2.0s 才见。EP.171 起 0.20–0.30s。
    first = _long_entry_first(dur)
    stagger = round(max(0.09, min(0.42, (dur - first - 2.0) / max(1, len(rows)))), 2)
    script = f'''    tl.fromTo("#tb-rule",{{scaleX:0,transformOrigin:"left center"}},{{scaleX:1,duration:.45,ease:"power2.out"}},0.05)
      .fromTo("#tb-card",{{y:30,opacity:0}},{{y:0,opacity:1,duration:{LONG_ENTRY_DUR},ease:"power3.out"}},{first})
      .fromTo("#tb-card .tb-hd",{{opacity:0,y:-10}},{{opacity:1,y:0,duration:.18,ease:"power2.out"}},{round(first+0.02,2)})
      .fromTo("#tb-card .tb-head",{{opacity:0}},{{opacity:1,duration:.16,ease:"power2.out"}},{round(first+0.06,2)})
      .fromTo("#tb-card .tb-r",{{x:-16,opacity:0}},{{x:0,opacity:1,duration:.16,ease:"power2.out",stagger:{stagger}}},{round(first+0.10,2)});
    tl.fromTo("#tb-card .tb-r.rh",{{scale:1}},{{scale:1.008,duration:.4,ease:"power2.out",yoyo:true,repeat:1}},{round(first+0.9,2)});
    tl.to("#tb-card",{{y:-5,duration:1.6,ease:"sine.inOut",yoyo:true,repeat:1}},{round(max(2.4, dur-4.2),2)});
'''
    return LONG_CSS, body, script


def _build_flow(spec: dict, s: dict, dur: float, slot: int, n_slots: int) -> tuple:
    """flow（横向步骤条 3–5 步）：连续进度条 + 轴上圆点 + 已走过段酸柠填充 + 刻度。"""
    steps = s.get("steps")
    if not isinstance(steps, list) or not (3 <= len(steps) <= 5):
        raise SystemExit(f"FAIL: flow 的 steps 必须是 3–5 步（当前 "
                         f"{len(steps) if isinstance(steps, list) else type(steps).__name__}）——"
                         "版式按 3–5 个轴点设计。")
    norm = []
    for i, st in enumerate(steps, 1):
        if isinstance(st, str):
            norm.append({"t": st, "s": ""})
        elif isinstance(st, dict) and st.get("t"):
            norm.append({"t": str(st["t"]), "s": str(st.get("s", "") or "")})
        else:
            raise SystemExit(f"FAIL: flow 第 {i} 步格式不对（应为字符串或 {{t, s?}}）")
    n = len(norm)
    # 几何全部来自共享模块（与预检同一次计算）
    _fg = LF.flow_geom(norm)
    if _fg["errors"]:
        _kind, _msg = _fg["errors"][0]
        _hint = ("  改法：① 每步标题缩到 ≤7 个中文字、说明缩到 ≤10 字；② 步数降到 4 步（列距会变宽）；"
                 "③ 长文案改用 table / case 模板。")
        raise SystemExit(f"FAIL: {_msg}\n{_hint}")
    tfs, sfs = _fg["t_fs"], _fg["s_fs"]
    # 轴与首末标签的水平占位自检：轴左缘 = 110 + 20 + 26 = 156；首标签锚左、末标签锚右，
    # 中段标签以各自轴点为中心（±86 = 172/2）→ 最坏左右边缘就是 156 与 156+748=904，
    # 都在 110..970 安全区内。这条断言是为了「改了内边距却忘了改轴偏移」时立刻炸。
    if _estw(s.get("title", ""), 34) > 860 - 80:
        raise SystemExit(f"FAIL: flow 的 title 太宽（≈{_estw(s['title'], 34):.0f}px > {860-80}px）"
                         "—— 缩短到 ≤22 个中文字。")
    span = _fg["span"]                 # 轴点间距（共享模块算，与预检同源）
    ax = _fg["axis_x"]                 # 轴左缘的绝对 x（用于自检与注释）
    dots, lbs, marks = [], [], []
    for i, x in enumerate(norm, 1):
        cx = round((i - 1) * span, 1)
        cls = "cur" if i == 1 else ("on" if i < n else "")
        edge = " first" if i == 1 else (" last" if i == n else "")
        dots.append(f'      <div class="dot {cls}" id="fl-d{i}" style="left:{cx}px"></div>')
        lbs.append(f'''      <div class="lb {cls}{edge}" id="fl-l{i}" style="left:{cx}px">'''
                   f'''<div class="t">{x["t"]}</div>'''
                   + (f'<div class="s">{x["s"]}</div>' if x["s"] else "") + "</div>")
        marks.append((i, cx))
    fill_w = 6 + round(span * (n - 1), 1)
    card_h = _fg["card_h"]
    head_block = ""
    if s.get("title"):
        head_block = (f'''      <div id="fl-head"><div class="t">{_em(s["title"], s.get("hero_em", ""))}</div>'''
                      + (f'''<div class="s">{s["sub"]}</div>''' if s.get("sub") else "") + "</div>\n")
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="fl-rule"></div>
    <div id="fl-card" style="top:{452}px;height:{card_h}px">
{head_block}      <div id="fl-axis">
        <div class="track"></div>
        <div class="fill" id="fl-fill" style="width:0px"></div>
{chr(10).join(dots)}
{chr(10).join(lbs)}
      </div>
    </div>
    <div class="note" data-layout-allow-overlap>{s.get('note', '')}</div>'''
    # 同上：原 dur*0.14（12.5s 场 =1.6s）→ 主内容开场等 1.6-2.0s 才见。EP.171 起 0.20–0.30s。
    first = _long_entry_first(dur)
    step_d = round(max(0.12, min(0.5, (dur - first - 2.0) / max(1, n))), 2)
    fills = []
    for i, cx in enumerate([m[1] for m in marks], 1):
        w = 6 if i == 1 else round(6 + cx, 1)
        fills.append(f'    tl.to("#fl-fill",{{width:{w}}},[{round(first + 0.18 + (i-1)*step_d,2)}]);')
    script = f'''    tl.fromTo("#fl-rule",{{scaleX:0,transformOrigin:"left center"}},{{scaleX:1,duration:.45,ease:"power2.out"}},0.05)
      .fromTo("#fl-card",{{y:30,opacity:0}},{{y:0,opacity:1,duration:{LONG_ENTRY_DUR},ease:"power3.out"}},{first})
      .fromTo("#fl-head",{{opacity:0,y:-10}},{{opacity:1,y:0,duration:.18,ease:"power2.out"}},{round(first+0.02,2)})
      .fromTo("#fl-axis .track",{{scaleX:0,transformOrigin:"left center"}},{{scaleX:1,duration:.18,ease:"power2.out"}},{round(first+0.06,2)})
      .fromTo("#fl-axis .dot",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:.18,ease:"back.out(1.8)",stagger:{step_d}}},{round(first+0.10,2)})
      .fromTo("#fl-axis .lb",{{opacity:0,y:12}},{{opacity:1,y:0,duration:.18,ease:"power2.out",stagger:{step_d}}},{round(first+0.16,2)});
{chr(10).join(fills)}
    tl.to("#fl-card",{{y:-5,duration:1.6,ease:"sine.inOut",yoyo:true,repeat:1}},{round(max(2.4, dur-4.2),2)});
'''
    return LONG_CSS, body, script


def _build_case(spec: dict, s: dict, dur: float, slot: int, n_slots: int) -> tuple:
    """case（案例页）：现象 → 机制 → 结果 的三段式**竖向**因果链（带箭头）。"""
    chain = s.get("chain")
    if not isinstance(chain, list) or len(chain) != 3:
        raise SystemExit(f"FAIL: case 的 chain 必须正好 3 段（现象 → 机制 → 结果；当前 "
                         f"{len(chain) if isinstance(chain, list) else type(chain).__name__} 段）。")
    norm = []
    for i, nd in enumerate(chain, 1):
        if not isinstance(nd, dict) or not nd.get("t"):
            raise SystemExit(f"FAIL: case 第 {i} 段缺 t 字段（应为 {{hd?, t}}）")
        if not nd.get("hd"):
            raise SystemExit(f"FAIL: case 第 {i} 段缺 hd 字段（段首标签，建议依次用 "
                             "现象 / 机制 / 结果）—— 三段式因果链必须每段都有标签。")
        norm.append({"hd": str(nd["hd"]), "t": str(nd["t"])})
    # 几何全部来自共享模块（与预检同一次计算）
    _cg = LF.case_geom(norm)
    if _cg["errors"]:
        raise SystemExit(f"FAIL: {_cg['errors'][0][1]}\n"
                         f"  改法：① 每段正文 ≤{_cg['avail']/26:.0f} 个中文字；"
                         f"② 缩短某一环（链必须正好 3 段）或把案例拆两屏。")
    tfs, inner = _cg["t_fs"], _cg["avail"]
    title = str(s.get("title", "") or "")
    if title and _estw(title, 36) > 860:
        raise SystemExit(f"FAIL: case 的 title 太宽（≈{_estw(title, 36):.0f}px > 860px）——缩短到 ≤23 个中文字。")
    head_h = (34 + 16 + (36 * 1.28 + 16 if title else 0)) if title else 34
    nd_h = _cg["nd_h"]
    chain_h = _cg["chain_h"]
    top = 404 + head_h + 24
    if top + chain_h > LONG_CONTENT_BOTTOM:
        raise SystemExit(
            f"FAIL: case 因果链高 {chain_h:.0f}px + top {top:.0f}px 越过内容下限 {LONG_CONTENT_BOTTOM}px。\n"
            f"  改法：① 去掉 title；② 每段正文缩到 ≤{(inner/26):.0f} 字（现在会折 {max(tinfo.values())} 行）。")
    blocks = []
    for i, nd in enumerate(norm, 1):
        cls = "nd first" if i == 1 else "nd plain"
        blocks.append(f'''      <div class="{cls}">
        <div class="n">{i:02d}</div>
        <div class="hd">{nd["hd"]}</div>
        <div class="tx">{nd["t"]}</div>
      </div>''')
        if i < 3:
            blocks.append('''      <div class="arw"><i></i><b></b></div>''')
    head_block = ""
    if title or s.get("kicker"):
        kick = str(s.get("kicker", "") or "")
        head_block = (f'''    <div id="cs-head">'''
                      + (f'''<div id="cs-kick">{kick}</div>''' if kick else "")
                      + (f'''<div id="cs-title">{_em(title, s.get("hero_em", ""))}</div>''' if title else "")
                      + "</div>\n")
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="cs-rule"></div>
{head_block}    <div id="cs-chain" style="top:{top:.0f}px">
      <div class="rail"></div>
{chr(10).join(blocks)}
    </div>
    <div class="note" data-layout-allow-overlap>{s.get('note', '')}</div>'''
    # 同上：原 dur*0.14（12.5s 场 =1.6s）→ 主内容开场等 1.6-2.0s 才见。EP.171 起 0.20–0.30s。
    first = _long_entry_first(dur)
    step_d = round(max(0.3, min(1.1, (dur - first - 2.2) / 4)), 2)
    script = f'''    tl.fromTo("#cs-rule",{{scaleX:0,transformOrigin:"left center"}},{{scaleX:1,duration:.45,ease:"power2.out"}},0.05)
      .fromTo("#cs-head",{{opacity:0,y:-12}},{{opacity:1,y:0,duration:{LONG_ENTRY_DUR},ease:"power2.out"}},{first})
      .fromTo("#cs-chain .rail",{{scaleY:0,transformOrigin:"top center"}},{{scaleY:1,duration:{round(step_d*2.2,2)},ease:"power2.out"}},{round(first+0.06,2)})
      .fromTo("#cs-chain .nd",{{x:-22,opacity:0}},{{x:0,opacity:1,duration:.22,ease:"power3.out",stagger:{step_d}}},{round(first+0.10,2)})
      .fromTo("#cs-chain .arw",{{opacity:0}},{{opacity:1,duration:.18,ease:"power2.out",stagger:{step_d}}},{round(first+0.24,2)});
    tl.fromTo("#cs-chain .nd.first .n",{{scale:1}},{{scale:1.06,duration:.34,ease:"power2.out",yoyo:true,repeat:1}},{round(first+0.7,2)});
    tl.to("#cs-chain",{{y:-5,duration:1.6,ease:"sine.inOut",yoyo:true,repeat:1}},{round(max(2.4, dur-4.2),2)});
'''
    return LONG_CSS, body, script


LONG_BUILDERS = {"chapter": _build_chapter, "quote": _build_quote, "table": _build_table,
                 "flow": _build_flow, "case": _build_case}


def frame(name, dur, css, body, script, total):
    return f'''<template>
  <style>
{css}  </style>
  <div id="root" data-composition-id="{name}" data-width="1080" data-height="1920" data-start="0" data-duration="{dur}">
{body}  </div>
  <script>
    window.__timelines=window.__timelines||{{}};
    var tl=gsap.timeline({{paused:true}});
    tl.to({{}},{{duration:{total}}},0);
{script}    window.__timelines["{name}"]=tl;
  </script>
</template>
'''

def _flat_scenes(spec: dict) -> dict:
    """spec 的场景表，**吃两种写法**：

      A) 扁平（既有形态，行为逐字节不变）：`"scenes": { "01": {...}, "02": {...}, … }`
      B) 分章（长视频新增）：`"chapters": [ {"id":1,"title":"…","scenes":{…}}, … ]`

    chapters 形态下每章内的 `scenes` 键仍是**全局槽位号**（01…24 连续），
    所以两种写法归一到同一张扁平表，下游（帧生成/index/门禁）不需要分支判断。
    两种写法都给时以 `scenes` 为准，并校验 chapters 里的键必须都在这张表里。
    """
    S = spec.get("scenes") or {}
    if not isinstance(S, dict):
        raise SystemExit("FAIL: spec 的 scenes 必须是「场景键 → 场景体」的字典")
    ch = _chapter_list(spec)
    if not ch:
        return S
    flat = {}
    for c in ch:
        for k, v in c["scenes"].items():
            if k in flat:
                raise SystemExit(f"FAIL: 场景键「{k}」在 chapters 里出现两次（一章一场景）。")
            flat[k] = v
    if S:
        missing = [k for k in flat if k not in S]
        if missing:
            raise SystemExit(
                f"FAIL: 同时给了 scenes 与 chapters，但 chapters 里的场景键 {missing} 不在 scenes 里。\n"
                f"  改法：两者只能二选一；若都要写，chapters 里的键必须是 scenes 的子集。")
        return S
    return flat


def _flat_chapters(spec: dict) -> list:
    """扁平场景表 + 每场所在章节号（没有 chapters 时章节号一律 0 = 不分章）。"""
    ch = _chapter_list(spec)
    if not ch:
        return []
    m = _chapter_map(spec)
    return [{"id": c["id"], "title": c["title"], "scenes": c["scenes"], "n": i}
            for i, c in enumerate(ch, 1)]


# ═══════════════════════════════════════════════════════════════════════════════
# ── 既有角色模板的「发射器」（2026-09-12 槽位路由改造时从 main() 机械抽出）───────
# 为什么抽：长视频（spec 带 chapters）里**槽位号只决定顺序、不决定模板** ——
#   EP.170 实测：03 是 table、04 是 flow、05 是 facts、08 是 action，
#   而旧代码把 01–04 的模板写死在 main() 里（01 取 s['warn_a']、03 取 s['mm']…），
#   于是 `python3 scripts/gen_chai_frames.py specs/170.json` 直接 KeyError: 'mm'。
# 抽成函数后由 _ROLE_EMIT 路由表按**字段**调用，槽位号只作为参数传进来。
# ⚠️ 函数体是**逐字照搬**原 main() 里的代码，只把字面量槽位号换成 slot 参数
#    （`durs[0]` → `_dur(slot)`、`beat(1,…)` → `beat(slot,…)`、`<div class="idx" data-layout-allow-overlap>01` →
#     `{slot:02d}`）。所以扁平 spec 的产物与改造前逐字节相同（§5/§9.1 有对拍证明）。
# ═══════════════════════════════════════════════════════════════════════════════

def _emit_hook(s: dict, fid: str, slot: int) -> None:
    """既有 01-hook（顶部 warn 条 + 118px 双行大字 + 大数字卡）

    2026-09-12（EP.171）新增**可选**字段 `hero_fs`：`#f1-hero` 没有 max-width 也不换行，
    文案宽过内容区（860px）会直接向右溢出画布。当某期标题本来就长（例如 19 字标题
    两行各 9–10 字），就按这个字段把字号降下来。**不写这个字段时 CSS 与改造前逐字相同。**
    """
    _css = CSS1
    _hfs = s.get("hero_fs")
    if _hfs:
        _css = _css.replace('font:700 118px/1.26', f'font:700 {int(_hfs)}px/1.26')
    # 01
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{_dur(slot)}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div class="warn" id="f1-warn"><span>{s['warn_a']} · <b>{s['warn_b']}</b></span></div>
    <div id="f1-hero"><span class="line">{s['hero_l1']}</span><span class="line em">{s['hero_l2']}</span></div>
    <div id="f1-card">
      <div class="big">{s['card_big']}</div>
      <div class="lb"><div class="t">{s['card_t']}</div><div class="s">{s['card_s']}</div></div>
    </div>
    <div class="note" data-layout-allow-overlap>{s['note']}</div>'''
    script = f'''    tl.fromTo("#f1-warn",{{y:-16,opacity:.4}},{{y:0,opacity:1,duration:.4,ease:"power2.out"}},.08)
      .fromTo("#f1-hero .line",{{y:14,opacity:.5}},{{y:0,opacity:1,duration:.28,ease:"power2.out",stagger:.18}},0.04)
      .fromTo("#f1-card",{{y:36,opacity:0}},{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{beat(slot,2,1.8)})
      .fromTo(".idx",{{opacity:0}},{{opacity:1,duration:.7,ease:"power2.out"}},.3);
    tl.fromTo("#f1-hero .em",{{scale:1}},{{scale:1.03,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{beat(slot,3,2.4)});
    tl.to("#f1-warn",{{scale:1.015,duration:1.0,ease:"sine.inOut",yoyo:true,repeat:3}},0.6);
    tl.to("#f1-hero",{{y:-5,duration:1.2,ease:"sine.inOut",yoyo:true,repeat:1}},1.5);
    tl.to(".idx",{{opacity:0,duration:.25,ease:"power2.in"}},{round(_dur(slot)-0.34,2)});
'''
    open(f"{_proj}/compositions/frames/{fid}.html","w").write(frame(fid, _dur(slot), _css, body, script, _dur(slot)))


def _emit_facts(s: dict, fid: str, slot: int) -> None:
    """既有 02-facts（仓库名 + 两张 2 行卡 + 底部标签条）"""
    # 02
    # 仓库名过长时（如 UNIFOLM-WLA-1.0）在 860px 卡内会挤窄 .lb，导致标题/副标题折出孤字并撞上 .idx。
    # 需要时用 spec 的 `repo_big_font` 降一档字号（缺省 46 = 原样，不影响既有各期）。
    css2 = CSS2
    if s.get("repo_big_font"):
        css2 = CSS2.replace("font:900 46px/1 CobaltMono",
                            f'font:900 {s["repo_big_font"]}px/1 CobaltMono')
        assert css2 != CSS2, "repo_big_font 未命中 CSS2 的 #f2-repo .big 规则"
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{_dur(slot)}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="f2-repo">
      <div class="big">{s['repo_big']}</div>
      <div class="lb"><div class="t">{s['repo_t']}</div><div class="s">{s['repo_s']}</div></div>
    </div>
    <div class="card" id="st-1">
      <div class="num">{s['st1_num']}</div>
      <div class="lb"><div class="t">{s['st1_t']}</div><div class="s">{s['st1_s']}</div></div>
    </div>
    <div class="card" id="st-2">
      <div class="num">{s['st2_num']}</div>
      <div class="lb"><div class="t">{s['st2_t']}</div><div class="s">{s['st2_s']}</div></div>
    </div>
    <div id="f2-tag"><span>{s['tag_a']}<b> · {s['tag_b']}</b></span></div>
    <div class="note" data-layout-allow-overlap>{s['note']}</div>'''
    script = f'''    tl.fromTo("#f2-repo",{{y:56,opacity:0}},{{y:0,opacity:1,duration:.7,ease:"power3.out"}},.1)
      .fromTo("#st-1",{{y:56,opacity:0}},{{y:0,opacity:1,duration:.65,ease:"power3.out"}},{beat(slot,1,1.5)})
      .fromTo("#st-2",{{y:56,opacity:0}},{{y:0,opacity:1,duration:.65,ease:"power3.out"}},{beat(slot,2,2.8)})
      .fromTo("#f2-tag",{{y:40,opacity:0}},{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{beat(slot,3,4.2)})
      .fromTo(".idx",{{opacity:0}},{{opacity:1,duration:.7,ease:"power2.out"}},.35);
    tl.fromTo("#st-1 .num",{{scale:1}},{{scale:1.04,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{round(beat(slot,1,1.5)+0.05,2)});
    tl.fromTo("#st-2 .num",{{scale:1}},{{scale:1.04,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{round(beat(slot,2,2.8)+0.05,2)});
    tl.to("#f2-repo",{{y:-5,duration:1.8,ease:"sine.inOut",yoyo:true,repeat:2}},2.0);
    tl.to(".idx",{{opacity:0,duration:.25,ease:"power2.in"}},{round(_dur(slot)-0.34,2)});
'''
    open(f"{_proj}/compositions/frames/{fid}.html","w").write(frame(fid, _dur(slot), css2, body, script, _dur(slot)))


def _emit_mech(s: dict, fid: str, slot: int) -> None:
    """既有 03-mechanism（横向三节点卡 + 箭头 + 底部断言条）"""
    # 03
    mm = s["mm"].format(em='<span class="em">' + s["mm_em"] + "</span>") if "{em}" in s["mm"] else s["mm"]
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{_dur(slot)}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div class="flow3">
      <div class="fnode" id="fn1"><div class="t">{s['n1_t']}</div><div class="s">{s['n1_s']}</div></div>
      <div class="farrow">→</div>
      <div class="fnode" id="fn2"><div class="t">{s['n2_t']}</div><div class="s">{s['n2_s']}</div></div>
      <div class="farrow">→</div>
      <div class="fnode" id="fn3"><div class="t">{s['n3_t']}</div><div class="s">{s['n3_s']}</div></div>
    </div>
    <div id="f3-sw">
      <div class="mm">{mm}</div>
      <div class="tag">{s['tag']}</div>
    </div>
    <div class="note" data-layout-allow-overlap>{s['note']}</div>'''
    script = f'''    tl.fromTo(".flow3",{{y:50,opacity:0}},{{y:0,opacity:1,duration:.7,ease:"power3.out"}},.1)
      .fromTo("#fn1",{{scale:1}},{{scale:1.05,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{beat(slot,0,0.5)})
      .fromTo("#fn2",{{scale:1}},{{scale:1.05,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{beat(slot,1,2.5)})
      .fromTo("#f3-sw",{{opacity:0,y:36}},{{opacity:1,y:0,duration:.65,ease:"power3.out"}},{beat(slot,2,4.9)})
      .fromTo(".idx",{{opacity:0}},{{opacity:1,duration:.7,ease:"power2.out"}},.35);
    tl.fromTo("#f3-sw .em",{{scale:1}},{{scale:1.04,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{beat(slot,3,6.6)});
    tl.to("#f3-sw",{{y:-5,duration:1.5,ease:"sine.inOut",yoyo:true,repeat:1}},{round(_dur(slot)-2.2,2)});
    tl.to(".idx",{{opacity:0,duration:.25,ease:"power2.in"}},{round(_dur(slot)-0.34,2)});
'''
    open(f"{_proj}/compositions/frames/{fid}.html","w").write(frame(fid, _dur(slot), CSS3, body, script, _dur(slot)))


def _emit_action(s: dict, fid: str, slot: int) -> None:
    """既有 04-action（两口井 + 底部条）"""
    # 04
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{_dur(slot)}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div class="well2" id="w-1" style="top:660px">
      <div class="num" style="color:#D1FF00">01</div>
      <div class="lb"><div class="t">{s['w1_t']}</div><div class="s">{s['w1_s']}</div></div>
    </div>
    <div class="well2" id="w-2" style="top:950px">
      <div class="num">02</div>
      <div class="lb"><div class="t">{s['w2_t']}</div><div class="s">{s['w2_s']}</div></div>
    </div>
    <div id="f4-strip"><div class="mm">{s['strip'].format(em='<span class="em">' + s["strip_em"] + "</span>") if "{em}" in s["strip"] else s["strip"]}</div></div>
    <div class="note" data-layout-allow-overlap>{s['note']}</div>'''
    script = f'''    tl.fromTo("#w-1",{{y:56,opacity:0}},{{y:0,opacity:1,duration:.7,ease:"power3.out"}},.1)
      .fromTo("#w-2",{{y:56,opacity:0}},{{y:0,opacity:1,duration:.65,ease:"power3.out"}},{beat(slot,2,3.0)})
      .fromTo("#f4-strip",{{y:44,opacity:0}},{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{beat(slot,3,4.6)})
      .fromTo(".idx",{{opacity:0}},{{opacity:1,duration:.7,ease:"power2.out"}},.35);
    tl.fromTo("#f4-strip .em",{{scale:1}},{{scale:1.04,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{round(beat(slot,3,4.6)+0.6,2)});
    tl.to("#w-2",{{y:-4,duration:1.4,ease:"sine.inOut",yoyo:true,repeat:1}},{round(_dur(slot)-2.2,2)});
    tl.to(".idx",{{opacity:0,duration:.25,ease:"power2.in"}},{round(_dur(slot)-0.34,2)});
'''
    open(f"{_proj}/compositions/frames/{fid}.html","w").write(frame(fid, _dur(slot), CSS4, body, script, _dur(slot)))


def _emit_verdict(s: dict, fid: str, slot: int) -> None:
    """既有判词卡（5 场景的 05-verdict / 7 场景的 07-verdict）

    2026-09-12（EP.171）：与 `_emit_hook` 同一口径支持可选字段 `hero_fs` 覆盖 `#f5-hero` 字号；
    不写时 CSS 与改造前逐字相同。
    """
    _css = CSS5
    _hfs = s.get("hero_fs")
    if _hfs:
        _css = _css.replace('font:900 110px/1.22', f'font:900 {int(_hfs)}px/1.22')
    # 05（5 场景版 = 判词；深度版 = 07-verdict 判词，中间两格给 05-config / 06-verify）
    s6 = s          # 参数即该场景体（原先是 S[_slots[lk]] 的字面量查表）
    # 判词卡内容：spec 可用 card_tt / card_tt_em / card_tt_2 / card_ss 覆盖（缺省=原 CTA，保持向后兼容）
    _f5_tt = (s6.get("card_tt", "AI 更新太快，关注{em}<br>陪你一起跟上。")
              .replace("{em}", '<span class="em">' + s6.get("card_tt_em", "柴主编") + "</span>"))
    if "{2}" in _f5_tt:
        _f5_tt = _f5_tt.replace("{2}", s6.get("card_tt_2", ""))
    _f5_ss = s6.get("card_ss", "每期只讲一件事 · 下一期看需求点单")
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{_dur(slot)}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="f5-hero"><span class="line">{s6['hero_l1']}</span><span class="line">{s6['hero_l2_pre']}<span class="em">{s6['hero_l2_em']}</span>{s6['hero_l2_tail']}</span></div>
    <div id="f5-card">
      <div class="tt">{_f5_tt}</div>
      <div class="ss">{_f5_ss}</div>
    </div>
    <div class="note" data-layout-allow-overlap>{s6['note']}</div>'''
    script = f'''    tl.fromTo("#f5-hero .line",{{y:50,opacity:0}},{{y:0,opacity:1,duration:.6,ease:"power3.out",stagger:.35}},.08)
      .fromTo("#f5-card",{{y:56,opacity:0}},{{y:0,opacity:1,duration:.7,ease:"power3.out"}},{beat(slot,2,2.5)})
      .fromTo(".idx",{{opacity:0}},{{opacity:1,duration:.6,ease:"power2.out"}},.15);
    tl.fromTo("#f5-hero .em",{{scale:1}},{{scale:1.04,duration:.3,ease:"power2.out",yoyo:true,repeat:1}},{beat(slot,1,1.75)});
    tl.to("#f5-hero",{{y:-6,duration:1.3,ease:"sine.inOut",yoyo:true,repeat:1}},1.4);
    tl.to(".idx",{{opacity:0,duration:.25,ease:"power2.in"}},{round(_dur(slot)-0.3,2)});
'''
    open(f"{_proj}/compositions/frames/{fid}.html","w").write(frame(fid, _dur(slot), _css, body, script, _dur(slot)))


def _emit_config(s: dict, fid: str, slot: int) -> None:
    """既有 05-config（配置逐行；槽位号由调用方给，扁平路径恒为 5）"""
    fid = fid               # 参数即帧名（原先是 _fid[槽位] 的字面量查表）
    cf = s["lines"]
    assert isinstance(cf, list) and 1 <= len(cf) <= 12, \
        f"05-config 的 lines 必须是 1–12 行的数组（当前 {len(cf) if isinstance(cf, list) else type(cf).__name__}）"
    fsz, ind_max, col_c = _config_geom(cf)
    nrow = max(len(cf), 6)                       # 6 行起排，避免行数少时卡片扁成一条
    rows = []
    for k in range(nrow):
        if k >= len(cf):
            rows.append('      <div class="row"><div class="ct"></div><div class="mono" style="height:30px"></div></div>')
            continue
        L = cf[k]
        cls = "row" + (" first" if k == 0 else "") + (" last" if k == nrow - 1 else "") \
                    + (" hl" if L.get("hl") else "")
        ind = "&nbsp;" * (2 * int(L.get("i", 0)))
        c = str(L.get("c", ""))
        tg = f'\n        <div class="tg">{c}</div>' if c else ""
        rows.append(f'''      <div class="{cls}">
        <div class="ct">{k + 1:02d}</div>
        <div class="mono">{ind}{L.get('t', '')}</div>{tg}
      </div>''')
    pad_rows = "\n".join(rows)
    pad_h = 44 + nrow * (int(fsz * 1.35) + 18)
    pad_top = 500 if pad_h <= 692 else 470
    h1 = str(s.get("hero_l1", "配置逐行读"))
    if "{em}" in h1:
        h1 = h1.replace("{em}", '<span class="em">' + str(s.get("hero_em", "")) + "</span>")
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{_dur(slot)}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="f6-hero">{h1}</div>
    <div class="pad" id="f6-pad" style="top:{pad_top}px;height:{pad_h}px;font-size:{fsz}px">
{pad_rows}
    </div>
    <div class="note" data-layout-allow-overlap>{s['note']}</div>'''
    script = f'''    tl.fromTo("#f6-hero",{{y:-14,opacity:.4}},{{y:0,opacity:1,duration:.45,ease:"power2.out"}},.06)
      .fromTo("#f6-pad",{{y:36,opacity:0}},{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{beat(5,0,0.6)})
      .fromTo("#f6-pad .row",{{x:-18,opacity:0}},{{x:0,opacity:1,duration:.34,ease:"power2.out",stagger:.16}},{beat(5,0,0.9)})
      .fromTo(".idx",{{opacity:0}},{{opacity:1,duration:.7,ease:"power2.out"}},.3);
    tl.fromTo("#f6-pad .row.hl",{{scale:1}},{{scale:1.012,duration:.4,ease:"power2.out",yoyo:true,repeat:1}},{round(beat(5,0,0.9)+0.5,2)});
    tl.to("#f6-pad",{{y:-5,duration:1.6,ease:"sine.inOut",yoyo:true,repeat:1}},{round(max(2.2, _dur(slot)-4.0),2)});
    tl.to(".idx",{{opacity:0,duration:.25,ease:"power2.in"}},{round(_dur(slot)-0.34,2)});
'''
    open(f"{_proj}/compositions/frames/{fid}.html","w").write(
        frame(fid, _dur(slot), CSS6, body, script, _dur(slot)))


def _emit_verify(s: dict, fid: str, slot: int) -> None:
    """既有 06-verify（三步验证；槽位号由调用方给，扁平路径恒为 6）"""
    fid = fid               # 参数即帧名（原先是 _fid[槽位] 的字面量查表）
    cks = s["checks"]
    assert isinstance(cks, list) and len(cks) == 3, \
        f"06-verify 的 checks 必须是 3 步（当前 {len(cks) if isinstance(cks, list) else type(cks).__name__}）——版式按三步设计"
    hd = str(s.get("title", "三步验证"))
    if "{em}" in hd:
        hd = hd.replace("{em}", '<span class="em">' + str(s.get("hero_em", "")) + "</span>")
    sub = str(s.get("sub", "") or "")
    sub_row = f'\n      <div class="sub">{sub}</div>' if sub else ""
    glyph = {"circled": "①②③", "ascii": "123", "cjk": "一二三"}.get(
        str(s.get("num_style", "circled")), "①②③")
    ck_html = []
    for k, c in enumerate(cks):
        cls = "ck" + (" one" if k == 0 else "")
        tag = f'\n          <div class="chp">{c["tag"]}</div>' if c.get("tag") else ""
        ck_html.append(f'''        <div class="{cls}">
          <div class="bd">{glyph[k]}</div>
          <div class="tx">
            <div class="t">{c['t']}</div>
            <div class="s">{c['s']}</div>{tag}
          </div>
        </div>''')
    steps = "\n".join(ck_html)
    body = f'''    <div id="bg" class="bg clip" data-start="0" data-duration="{_dur(slot)}" data-track-index="0"></div>
    {DECOR}
    <div class="idx" data-layout-allow-overlap>{slot:02d}</div>
    <div id="f7-card">
      <div class="hd">
        <div class="h">{hd}</div>{sub_row}
      </div>
      <div class="rails">
        <div class="rail"></div>
{steps}
      </div>
    </div>
    <div class="note" data-layout-allow-overlap>{s['note']}</div>'''
    script = f'''    tl.fromTo("#f7-card",{{y:46,opacity:0}},{{y:0,opacity:1,duration:.6,ease:"power3.out"}},.06)
      .fromTo("#f7-card .hd",{{opacity:0,y:-12}},{{opacity:1,y:0,duration:.45,ease:"power2.out"}},.18)
      .fromTo("#f7-card .rail",{{scaleY:0,transformOrigin:"top center"}},{{scaleY:1,duration:.85,ease:"power2.out"}},0.34)
      .fromTo("#f7-card .ck",{{x:-20,opacity:0}},{{x:0,opacity:1,duration:.42,ease:"power2.out",stagger:.22}},{beat(6,0,0.7)})
      .fromTo(".idx",{{opacity:0}},{{opacity:1,duration:.7,ease:"power2.out"}},.3);
    tl.fromTo("#f7-card .ck.one .bd",{{scale:1}},{{scale:1.06,duration:.34,ease:"power2.out",yoyo:true,repeat:1}},{round(beat(6,0,0.7)+0.55,2)});
    tl.fromTo("#f7-card .ck .chp",{{opacity:.5}},{{opacity:1,duration:.4,ease:"power2.out",stagger:.22}},{round(beat(6,0,0.7)+0.9,2)});
    tl.to("#f7-card",{{y:-5,duration:1.6,ease:"sine.inOut",yoyo:true,repeat:1}},{round(max(2.4, _dur(slot)-4.2),2)});
    tl.to(".idx",{{opacity:0,duration:.25,ease:"power2.in"}},{round(_dur(slot)-0.34,2)});
'''
    open(f"{_proj}/compositions/frames/{fid}.html","w").write(
        frame(fid, _dur(slot), CSS7, body, script, _dur(slot)))

def main():
    global _proj, _beat_map, _durs, _SPEC, _N_SLOTS
    spec = json.load(open(sys.argv[1]))
    _proj = proj = spec["proj"]
    cg = json.load(open(f"{proj}/caption_groups.json"))
    am = json.load(open(f"{proj}/audio_meta.json"))
    starts, acc = [], 0.0
    for v in am["voices"]:
        starts.append(acc); acc += v["duration_s"]
    sg = {}
    for g in cg["groups"]:
        sg.setdefault(g["frame"], []).append((round(g["start"] - starts[g["frame"]-1], 2), g["text"]))
    _beat_map = sg           # beat() 已提升为模块级（见 _dur 上方）
    durs = [round(v["duration_s"]+0.5, 3) for v in am["voices"]]
    # ── N 场景容忍度守卫（2026-09-11）：5 场景路径行为不变，越界就显式报错，不静默出错 ──
    # 场景键必须以两位序号（01..N）开头；序号 = 场景槽位 = 音频段号（1 段音频 = 1 个场景）。
    # 键可以写纯数字（"01".."05"，既有各期的写法）也可以写「序号-角色」（"05-config"），
    # 两者的帧文件名归一到同一套（见下方 CANON）：既有 spec 一个字都不用改。
    S = _flat_scenes(spec)
    _slots = {}
    for _k in S:
        _m = re.match(r"^(\d+)", str(_k))
        if not _m or _k != str(_k):
            raise SystemExit(f"FAIL: spec 场景键「{_k}」不合法（须以数字序号开头，如 05 或 05-config）")
        if int(_m.group(1)) in _slots:
            raise SystemExit(f"FAIL: spec 场景键序号重复：{_slots[int(_m.group(1))]} 与 {_k}")
        _slots[int(_m.group(1))] = str(_k)
    for _e in (1, 2, 3, 4, 5):
        if _e not in _slots:
            raise SystemExit(f"FAIL: spec 缺场景 {_e:02d}（01–05 为既有必填场景）")
    if len(_slots) != len(S):
        raise SystemExit(f"FAIL: spec 场景键序号重复或不连续：{sorted(_slots)}")
    for _n in sorted(_slots):
        if _n > len(durs):
            raise SystemExit(
                f"FAIL: spec 有场景 {_slots[_n]}，但 audio_meta.voices 只有 {len(durs)} 段"
                f"（1 段音频 = 1 个场景；先补 audio/{_n:02d}.mp3 与 audio/{_n:02d}.txt 再跑 build_chai_timeline.py）")
    for _n in range(1, max(_slots) + 1):
        if _n not in _slots:
            raise SystemExit(f"FAIL: spec 场景序号必须从 01 连续到 {max(_slots):02d}，当前 {sorted(_slots)}")
    # 深度版（N≥6）：场景槽位与音频段一一对应，每场用自己那段的时长；只有**末场**不补 0.5
    # 呼吸量（与 5 场景路径同一口径，也让 index.html 的 data-duration 与本文件一致）。
    # durs[4]/durs[5] 只被 05-config / 06-verify / 07-verdict 使用，既有 01–04 不受影响。
    if len(S) >= 6:
        durs = [round(v["duration_s"] + (0.5 if i < len(S) - 1 else 0.0), 3)
                for i, v in enumerate(am["voices"])]
    _durs = durs              # _dur(slot) 的口径 = 本表（必须在上面那次修正之后）
    if len(durs) > len(S):
        raise SystemExit(
            f"FAIL: audio_meta.voices 有 {len(durs)} 段，但 spec 只声明了 {len(S)} 个场景 "
            f"（{[k for k in S]}）——多出来的音频段不会进片，请补齐 spec 场景或删掉多余音频。")
    # 场景 id / 帧文件名归一：键可以写成 "05"（既有各期的写法）也可以写成 "05-config"（便读），
    # 两种写法落到的文件名完全相同 —— 既有各期的 spec 一个字都不用改，输出逐字节不变。
    _chmap = _chapter_map(spec)
    _kind_log = []
    # 帧名归一（两条路径共用；重复帧名在这里就炸，不会写出残缺帧）
    _ordered = sorted(_slots)
    _chaptered = bool(_chapter_list(spec))
    _fid = _assign_frame_ids(S, _slots, len(S), _chaptered)

    # ═══════════════════════════════════════════════════════════════════════════
    # ── 排片：按路径分派（2026-09-12 槽位路由改造）──────────────────────────────
    # 两条路径**严格分开**，这是本次改造的核心契约：
    #   A) spec 带 chapters（长片）：**每一槽都按字段路由**（含 01–04 与末场），
    #      槽位号只决定顺序。EP.170 的 03=table / 04=flow / 05=facts / 08=action 就靠这条。
    #   B) spec 不带 chapters（扁平，既有 5/7 场景各期）：**行为完全不变** ——
    #      01–04 固定模板、末场判词卡、config 在第 5 槽、verify 在第 6 槽。
    # ═══════════════════════════════════════════════════════════════════════════
    _SPEC, _N_SLOTS = spec, len(S)
    # 末场（判词卡）所在槽位与它在 voices 里的下标 —— 与改造前逐字相同的三条分支：
    #   · 5 场景（老路径）：槽位 5、下标 4；· 7 场景（深度版）：槽位 7、下标 6；
    #   · N≥8（含长片）：槽位 N、下标 N-1（1 段音频 = 1 个场景，末场就是最后一段）。
    last_idx, lk = ((len(S) - 1, len(S)) if len(S) >= 8
                    else ((6, 7) if len(S) >= 7 else (4, 5)))

    if _chaptered:
        # A) 长片：按字段路由每一槽
        _validate_chapter_spec(S, _slots, _fid, _ordered)
        _route_chaptered(S, _slots, _fid, _ordered, _kind_log)
    else:
        # B) 扁平：与改造前完全同序 —— 01 → 02 → 03 → 04 → 末场 → config(5) → verify(6)
        _emit_hook(S[_slots[1]], _fid[1], 1)
        _emit_facts(S[_slots[2]], _fid[2], 2)
        _emit_mech(S[_slots[3]], _fid[3], 3)
        _emit_action(S[_slots[4]], _fid[4], 4)
        _emit_verdict(S[_slots[lk]], _fid[lk], lk)
        # config 恒在第 5 槽、verify 恒在第 6 槽（与改造前逐字相同）；
        # 槽位号由 _find_slot 给出（老路径下恒为 5/6），所以 emit 函数的场号/时长不变。
        _cfg_slot2 = _find_slot(S, _slots, "lines", prefer=5)
        _vfy_slot2 = _find_slot(S, _slots, "checks", prefer=6)
        if _cfg_slot2 is not None:
            _emit_config(S[_slots[_cfg_slot2]], _fid[_cfg_slot2], _cfg_slot2)
        if _vfy_slot2 is not None:
            _emit_verify(S[_slots[_vfy_slot2]], _fid[_vfy_slot2], _vfy_slot2)
        for _n in _ordered:
            if _n in (1, 2, 3, 4, lk) or _n == _cfg_slot2 or _n == _vfy_slot2:
                continue
            raise SystemExit(
                f"FAIL: 中间场景 {_fid[_n]}（槽位 {_n:02d}，第 {_n} 段音频）没有可识别的模板。\n"
                f"  该槽位既不是 config（要 lines）也不是 verify（要 checks），也没有长视频模板字段：\n"
                f"  chapter(no) / quote(quote) / table(table) / flow(steps) / case(chain)。\n"
                f"  改法：① 按上面任一契约补字段；② 给该 spec 加 chapters（长片路径下所有槽位\n"
                f"  都按字段路由，facts / action / mechanism 也能落在任意槽位）；"
                f"③ 删掉该场景与对应的 audio/{_n:02d}.mp3。")

    # captions 注入
    cap = open(f"{proj}/compositions/captions.html").read()
    cap = re.sub(r"var GROUPS = \[[^\n]*\];",
                 "var GROUPS = " + json.dumps(cg["groups"], ensure_ascii=False) + ";",
                 cap, count=1)
    # captions 子文档的时长口径（2026-09-11 修 P1-3）：
    # 模板里写死的 data-duration="37.728" 是脚手架的残留，与本期真实时长无关。
    # 任何按**子文档元数据**裁剪/复用的下游（Studio 预览、单场景重渲、hyperframes 快照）
    # 都会按它静默截断字幕。这里把根节点的 data-duration 与 var DURATION 统一到
    # 「最后一条字幕的实际结束时间」——字幕文档只承诺覆盖到最后一句话结束，
    # 而不是整片时长（末尾留白不在本文档职责内）。
    _cap_end = 0.0
    for _g in cg["groups"]:
        _e = _g.get("end")
        if _e is None:
            _e = float(_g["start"]) + float(_g.get("duration", 0) or 0)
        _cap_end = max(_cap_end, float(_e))
    # 口径修正（EP.168 第 2 轮评审建议）：取 max(末组 end, total_duration_s)。
    # 原因：父层 index.html 给该层的窗口就是 total_duration_s；子文档若写小，
    # 下游按子文档元数据裁剪会**静默截掉末尾那段**（风险不对称：写大只是无字幕的静止尾）。
    _cap_dur = round(max(_cap_end, float(cg["total_duration_s"])), 3)
    assert _cap_dur > 0, "captions 时长算出来是 0——caption_groups.json 的 start/duration/end 都不对"
    cap = re.sub(r"var DURATION = [\d.]+;",
                 "var DURATION = " + str(_cap_dur) + ";",
                 cap, count=1)
    cap, _nsub = re.subn(r'(id="captions-root"[^>]*?)data-duration="[\d.]+"',
                         r'\g<1>data-duration="' + str(_cap_dur) + '"',
                         cap, count=1)
    assert _nsub == 1, ("captions.html 根节点的 data-duration 没被替换——"
                        "模板结构变了（契约要求 id=\"captions-root\" 与 data-duration 同在一个标签上）")
    lb = spec.get("line_breaks", {})
    for gid, lines in lb.items():
        t = next(g["text"] for g in cg["groups"] if g["id"] == gid)
        assert "".join(lines) == t, (gid, repr("".join(lines)), repr(t))
    cap = re.sub(r"var LINE_BREAKS = \{.*?\};", "var LINE_BREAKS = " + json.dumps(lb, ensure_ascii=False) + ";", cap, count=1, flags=re.S)
    open(f"{proj}/compositions/captions.html","w").write(cap)

    # cover.html 三比例 —— 阿囤囤风格（2026-09-11 重做；契约见 _chai_cover_html 上方注释）
    cover = _chai_cover_html(spec, proj)
    open(f"{proj}/cover.html","w").write(cover)
    print(f"EP.{spec['ep']} {len(S)} 帧+captions+cover 生成完成, 场景时长: {durs}")
    if _chmap:
        _nc = len(_chapter_list(spec))
        print(f"  章节结构：{_nc} 章 · " + " / ".join(
            f"{c['id']}:{c['title']}（{len(c['scenes'])} 场）" for c in _flat_chapters(spec)))
    if _kind_log:
        print("  长视频模板：" + " · ".join(f"{s:02d}→{f}={k}" for s, f, k in
                                             sorted(_kind_log)))
    else:
        print("  长视频模板：未启用（老路径：01–0{} 场景模板原样）".format(len(S)))

def _cover_only(argv: list) -> int:
    """`--cover-only <spec.json> [--out <path>]` — emit just cover.html.

    Used by the two-pass geometry flow (draft -> measure -> final) and handy for
    tuning seats without regenerating frames.
    """
    spec = json.load(open(argv[0]))
    out = None
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    html = _chai_cover_html(spec, spec["proj"])
    if out:
        open(out, "w").write(html)
        print(f"{out} 写入完成")
    else:
        sys.stdout.write(html)
    return 0


if __name__ == "__main__":
    if "--cover-only" in sys.argv:
        i = sys.argv.index("--cover-only")
        sys.exit(_cover_only(sys.argv[i + 1:]))
    main()
