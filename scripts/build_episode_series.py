#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量构建柴主编单热点视频（蓝色 Cobalt Grid，5 段视觉）。

复用方式（做新一期）：
1. 先跑配音：minimax_tts.py 生成 assets/voice/*.mp3 和 /tmp/epXXX-voice/*-words.json（5 段）。
2. 在下方 CONF dict 里加一条新期号配置：proj（工程名）、audio（5 段 decode_audio 精确时长）、
   frames（5 个帧的 scare/hero/cards/punch/quote 文字）。
3. 跑：python3 scripts/build_episode_series.py

依赖：模板工程 videos/openai-astra-pause（蓝色 5 段骨架 + bin/captions.html）。
生成：videos/<proj>/ 的 5 帧 + captions/audio_meta + index.html。
之后仍需：hyperframes check → render → 封面 → 发布包（见 workflow）。

原始来源：/tmp/build_ep_multi.py（2026-08-19 迁移）。"""
import json, pathlib, re

ROOT = pathlib.Path("<REPO>")
TPL = ROOT / "videos/openai-astra-pause"

BLUE = "#1F2BE0"
BLUE_RGBA = "rgba(31,43,224"

FONT = """
    @font-face{font-family:CobaltSerif;src:url("assets/fonts/CobaltSerif.ttc") format("truetype");font-weight:400}
    @font-face{font-family:CobaltSans;src:url("assets/fonts/CobaltSans.ttc") format("truetype");font-weight:400 700}
    @font-face{font-family:CobaltMono;src:url("assets/fonts/CobaltMono.ttf") format("truetype");font-weight:400}
"""
BASE = f"""
    #root{{position:relative;width:1080px;height:1920px;overflow:hidden;color:{BLUE};container-type:size;font-family:CobaltSans,sans-serif}}
    .bg{{position:absolute;inset:0;background-color:#F0EBDE;background-image:linear-gradient({BLUE_RGBA},.1) 2px,transparent 2px),linear-gradient(90deg,{BLUE_RGBA},.1) 2px,transparent 2px);background-size:42px 42px}}
    .rule{{position:absolute;left:52px;right:52px;height:3px;background:{BLUE}}}.top{{top:58px}}.bottom{{top:1580px;opacity:0}}
    .brand{{position:absolute;right:58px;top:86px;font:700 23px/1 CobaltSans;letter-spacing:.12em}}
    .source{{position:absolute;left:58px;top:92px;font:22px CobaltMono}}
    .glitch{{position:absolute;right:36px;top:210px;width:116px;height:820px;background:repeating-linear-gradient(90deg,{BLUE} 0 6px,transparent 6px 20px);opacity:.14}}
    .note{{position:absolute;left:62px;top:1460px;font:20px CobaltMono;letter-spacing:.05em}}
    .asset{{position:absolute;left:70px;right:70px;top:240px;bottom:620px;border:3px solid {BLUE};background:#fff;overflow:hidden;box-shadow:8px 8px 0 rgba(31,43,224,.12)}}
    .asset img{{width:100%;height:100%;object-fit:contain;display:block;background:#fff}}
"""

def frame(name, ep, css, body, script, dur, imgs=None):
    img_html = ""
    if imgs:
        for k, v in imgs.items():
            img_html += f'    <div id="{k}" class="asset"><img src="{v}" alt=""></div>\n'
    return f"""<template>
  <style>
{FONT}{BASE}
{css}
  </style>
  <div id="root" data-composition-id="{name}" data-width="1080" data-height="1920" data-start="0" data-duration="{dur}">
    <div id="bg" class="bg clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
    <div class="rule top"></div><div class="rule bottom"></div>
    <div class="glitch"></div>
    <div class="source">AI EDIT / {ep}</div><div class="brand">柴主编｜只讲一件事</div>
{img_html}{body}
  </div>
  <script>
    window.__timelines=window.__timelines||{{}};
    var tl=gsap.timeline({{paused:true}});
{script}
    window.__timelines["{name}"]=tl;
  </script>
</template>
"""

# ---- 通用 5 帧 CSS ----
F1_CSS = """
    #f1-scare{position:absolute;left:76px;top:170px;font:700 42px CobaltSans;letter-spacing:.14em}
    #f1-hero{position:absolute;left:55px;right:55px;top:400px;text-align:center;font:400 260px/.9 CobaltSerif;letter-spacing:-.05em}
    #f1-hero .u{font:700 44px CobaltSans;letter-spacing:.12em;display:block;margin-top:10px}
    #f1-verdict{position:absolute;left:70px;right:70px;top:960px;font:400 84px/1.2 CobaltSerif;letter-spacing:-.02em}
    #f1-verdict span{display:block}
    #f1-verdict span+span{margin-top:10px}
"""
F2_CSS = """
    #f2-header{position:absolute;left:58px;right:58px;top:150px;display:flex;justify-content:space-between;border-bottom:3px solid #1F2BE0;padding-bottom:22px;font:22px CobaltMono}
    #f2-stack{position:absolute;left:62px;right:62px;top:250px}
    .f2-card{position:relative;border:3px solid #1F2BE0;background:#F0EBDE;padding:30px 32px;margin-bottom:40px;display:flex;justify-content:space-between;align-items:center}
    .f2-card small{font:20px CobaltMono;letter-spacing:.08em}.f2-card b{font:400 58px/.9 CobaltSerif;letter-spacing:-.03em}.f2-card span{font:700 30px CobaltSans;letter-spacing:.08em}
"""
F3_CSS = """
    #f3-header{position:absolute;left:58px;right:58px;top:150px;border-bottom:3px solid #1F2BE0;padding-bottom:22px;font:700 40px CobaltSans;letter-spacing:.1em}
    #f3-cards{position:absolute;left:70px;right:70px;top:320px}
    .f3-card{border:3px solid #1F2BE0;background:#F0EBDE;padding:32px 34px;margin-bottom:44px}
    .f3-card small{display:block;font:20px CobaltMono;letter-spacing:.08em;margin-bottom:18px}
    .f3-card b{display:inline-block;font:400 88px/1 CobaltSerif;letter-spacing:-.04em}
    .f3-card span{font:700 30px CobaltSans;letter-spacing:.08em;margin-left:14px}
    #f3-punch{position:absolute;left:70px;right:70px;top:1180px;text-align:center;font:400 54px/1.25 CobaltSerif;letter-spacing:-.02em}
"""
F4_CSS = """
    #f4-header{position:absolute;left:58px;right:58px;top:150px;border-bottom:3px solid #1F2BE0;padding-bottom:22px;font:700 40px CobaltSans;letter-spacing:.1em}
    #f4-cards{position:absolute;left:70px;right:70px;top:320px}
    .f4-card{border:3px solid #1F2BE0;background:#F0EBDE;padding:32px 34px;margin-bottom:44px}
    .f4-card small{display:block;font:20px CobaltMono;letter-spacing:.08em;margin-bottom:18px}
    .f4-card b{display:inline-block;font:400 80px/1 CobaltSerif;letter-spacing:-.04em}
    .f4-card span{font:700 30px CobaltSans;letter-spacing:.08em;margin-left:14px}
    #f4-punch{position:absolute;left:70px;right:70px;top:1100px;text-align:center;font:400 54px/1.25 CobaltSerif;letter-spacing:-.02em}
"""
F5_CSS = """
    #f5-hero{position:absolute;left:55px;right:55px;top:400px;text-align:center;font:400 220px/.95 CobaltSerif;letter-spacing:-.05em}
    #f5-hero .u{font:700 44px CobaltSans;letter-spacing:.16em;display:block;margin-top:10px}
    #f5-quote{position:absolute;left:70px;right:70px;top:1120px;text-align:center;font:400 54px/1.3 CobaltSerif;letter-spacing:-.02em}
    #f5-bar{position:absolute;left:70px;right:70px;top:1080px;height:3px;background:#1F2BE0}
"""

# 2026-08-27 起：新工作流要求每期至少两张一手主题素材。
# 证据帧把官方界面作为主体，Cobalt Grid 只负责框架与说明。
EVIDENCE_CSS = """
    #e-kicker{position:absolute;left:72px;top:170px;font:700 34px CobaltSans;letter-spacing:.12em}
    #e-title{position:absolute;left:70px;right:70px;top:245px;font:400 80px/1.05 CobaltSerif;letter-spacing:-.03em}
    #e-screen{position:absolute;left:70px;right:70px;top:470px;height:650px;border:4px solid #1F2BE0;background:#F0EBDE;overflow:hidden}
    #e-screen img{display:block;width:100%;height:100%;object-fit:contain;background:#F0EBDE}
    #e-badge{position:absolute;left:70px;top:1160px;border:3px solid #1F2BE0;background:#F0EBDE;padding:20px 28px;font:700 34px CobaltSans;letter-spacing:.08em}
    #e-caption{position:absolute;left:70px;right:70px;top:1260px;font:400 46px/1.25 CobaltSerif;letter-spacing:-.02em}
"""

def evidence_body(c):
    return f"""    <div id="e-kicker">{c['kicker']}</div>
    <div id="e-title">{c['title']}</div>
    <div id="e-screen"><img src="{c['image']}" alt="{c['alt']}"></div>
    <div id="e-badge">{c['badge']}</div>
    <div id="e-caption">{c['caption']}</div>
    <div class="note">SOURCE · {c['source']}</div>"""

def evidence_script():
    return """    tl.fromTo("#e-title",{x:-100,opacity:0},{x:0,opacity:1,duration:.75,ease:"power3.out"},0)
      .fromTo("#e-screen",{scale:.88,opacity:0},{scale:1,opacity:1,duration:1.0,ease:"back.out(1.25)"},.25)
      .fromTo("#e-screen img",{scale:1.08,x:20},{scale:1,x:0,duration:4.8,ease:"power1.inOut"},.5)
      .fromTo("#e-badge",{x:-70,opacity:0},{x:0,opacity:1,duration:.55,ease:"power3.out"},1.05)
      .fromTo("#e-caption",{y:50,opacity:0},{y:0,opacity:1,duration:.65,ease:"power3.out"},1.45);"""

def f1_body(c):  # scare, hero, unit, v1, v2
    return f"""    <div id="f1-scare">{c['scare']}</div>
    <div id="f1-hero">{c['hero']}<span class="u">{c['unit']}</span></div>
    <div id="f1-verdict"><span>{c['v1']}</span><span>{c['v2']}</span></div>"""
def f1_script():
    return """    tl.fromTo("#f1-hero",{y:200,opacity:0},{y:0,opacity:1,duration:1.2,ease:"power3.out"},0)
      .fromTo("#f1-scare",{x:-90,opacity:0},{x:0,opacity:1,duration:.7,ease:"power3.out"},.5)
      .fromTo("#f1-verdict span:first-child",{y:50,opacity:0},{y:0,opacity:1,duration:.6,ease:"power3.out"},1.4)
      .fromTo("#f1-verdict span:last-child",{y:50,opacity:0},{y:0,opacity:1,duration:.6,ease:"power3.out"},1.9);"""

def f2_body(c):  # h1, h2, cards[(small,b,span)*3]
    cards = "\n".join(f'      <div class="f2-card"><small>{a}</small><b>{b}</b><span>{s}</span></div>' for a,b,s in c['cards'])
    return f"""    <div id="f2-header"><span>{c['h1']}</span><span>{c['h2']}</span></div>
    <div id="f2-stack">
{cards}
    </div>
    <div class="note">SOURCE · {c['note']}</div>"""
def f2_script():
    return """    tl.fromTo("#f2-header",{y:-60,opacity:0},{y:0,opacity:1,duration:.7,ease:"power3.out"},0);
    var cards=document.querySelectorAll(".f2-card");
    for(var i=0;i<cards.length;i++){tl.fromTo(cards[i],{x:-120,opacity:0},{x:0,opacity:1,duration:.6,ease:"power3.out"},.4+i*1.1);}"""

def f3_body(c):  # header, cards[(small,b,span)*2], punch
    cards = "\n".join(f'      <div class="f3-card"><small>{a}</small><b>{b}</b><span>{s}</span></div>' for a,b,s in c['cards'])
    return f"""    <div id="f3-header">{c['header']}</div>
    <div id="f3-cards">
{cards}
    </div>
    <div id="f3-punch">{c['punch']}</div>"""
def f3_script():
    return """    tl.fromTo("#f3-header",{y:-60,opacity:0},{y:0,opacity:1,duration:.7,ease:"power3.out"},0);
    var c3=document.querySelectorAll(".f3-card");
    for(var i=0;i<c3.length;i++){tl.fromTo(c3[i],{x:-120,opacity:0},{x:0,opacity:1,duration:.6,ease:"power3.out"},.4+i*1.1);}
    tl.fromTo("#f3-punch",{y:60,opacity:0},{y:0,opacity:1,duration:.8,ease:"power3.out"},3.0);"""

def f4_body(c):  # header, cards[(small,b,span)*2], punch
    cards = "\n".join(f'      <div class="f4-card"><small>{a}</small><b>{b}</b><span>{s}</span></div>' for a,b,s in c['cards'])
    punch = f'    <div id="f4-punch">{c["punch"]}</div>' if c.get('punch') else ''
    return f"""    <div id="f4-header">{c['header']}</div>
    <div id="f4-cards">
{cards}
    </div>
{punch}"""
def f4_script():
    return """    tl.fromTo("#f4-header",{y:-60,opacity:0},{y:0,opacity:1,duration:.7,ease:"power3.out"},0);
    var c4=document.querySelectorAll(".f4-card");
    for(var i=0;i<c4.length;i++){tl.fromTo(c4[i],{x:-120,opacity:0},{x:0,opacity:1,duration:.6,ease:"power3.out"},.4+i*1.1);}
    var p=document.getElementById("f4-punch"); if(p){tl.fromTo(p,{y:60,opacity:0},{y:0,opacity:1,duration:.8,ease:"power3.out"},2.8);}"""

def f5_body(c):  # hero, unit, q1, q2
    return f"""    <div id="f5-hero">{c['hero']}<span class="u">{c['unit']}</span></div>
    <div id="f5-bar"></div>
    <div id="f5-quote"><span>{c['q1']}</span><span>{c['q2']}</span></div>"""
def f5_script():
    return """    tl.fromTo("#f5-hero",{y:120,opacity:0},{y:0,opacity:1,duration:1.0,ease:"power3.out"},.3)
      .fromTo("#f5-bar",{scaleX:0},{scaleX:1,duration:.5,ease:"power3.inOut"},1.8)
      .fromTo("#f5-quote",{y:50,opacity:0},{y:0,opacity:1,duration:.8,ease:"power3.out"},2.2);"""

# ---- 图片证据帧（首帧有主体/证据 + 每期至少 2 张主题素材）----
FI_CSS = """
    #fi-header{position:absolute;left:58px;right:58px;top:150px;border-bottom:3px solid #1F2BE0;padding-bottom:20px;font:700 40px CobaltSans;letter-spacing:.1em}
    #fi-caption{position:absolute;left:70px;right:70px;top:1300px;font:400 48px/1.2 CobaltSerif;letter-spacing:-.02em}
    #fi-note{position:absolute;left:70px;right:70px;top:1405px;font:26px CobaltMono;letter-spacing:.05em;color:#1F2BE0}
"""
def fi_body(c):  # header, caption, note
    return f"""    <div id="fi-header">{c['header']}</div>
    <div id="fi-caption">{c['caption']}</div>
    <div id="fi-note">{c['note']}</div>"""
def fi_script():
    return """    tl.fromTo("#fi-header",{y:-60,opacity:0},{y:0,opacity:1,duration:.7,ease:"power3.out"},0)
      .fromTo(".asset",{y:40,opacity:0},{y:0,opacity:1,duration:.8,ease:"power3.out"},.3)
      .fromTo("#fi-caption",{y:40,opacity:0},{y:0,opacity:1,duration:.6,ease:"power3.out"},1.2)
      .fromTo("#fi-note",{opacity:0},{opacity:1,duration:.6,ease:"power3.out"},1.8);"""

# ---- 四期配置 ----
CONF = {
 "051": dict(proj="glm53-posttrain", audio=[4.2, 11.377812, 11.6, 7.697438, 6.1], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="国产开源", hero="60", unit="AA 综合指数", v1="第一次摸到", v2="闭源旗舰门槛")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="智谱 GLM-5.3", h2="今天上线", note="智谱 AI 官方", cards=[("对标","Claude Fable 5","同一档"),("对标","GPT-5.6 Sol","同一档"),("开源","Kimi K3","并列第一")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="怎么做到的", punch="没堆参数，靠调教顶上去", cards=[("基础模型","GLM-5.2","没换"),("后训练","+50%","榨出 60 分")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="现在能用吗", punch="定价没变", cards=[("API","今天","就能调"),("权重","下周五","开源")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="参数", unit="不再是唯一", q1="当开源靠后训练追上闭源旗舰", q2="参数不再是你唯一要看的数字")), script=f5_script()),
 }),
 "052": dict(proj="alipay-aha", audio=[3.9, 12.0, 9.5, 8.6, 5.445125], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="智能体", hero="办事", unit="不是只会聊天", v1="智能体开始", v2="真的替你办事")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="支付宝阿宝", h2="万余服务", note="新华网 / 蚂蚁集团", cards=[("生活","交水电费","一句话"),("生活","订宠物服务","一句话"),("出行","找充电桩","一句话")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="AHA 协议", punch="跨智能体、跨设备", cards=[("一句话","拆成多智能体","协作"),("最后","交易办结","安全履约")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="一次接入", punch="智能体成了新入口", cards=[("手机","车机","AI 眼镜"),("商家","一次接入","多端分发")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="入口", unit="换了", q1="当 AI 开始替你下单付费", q2="入口从 App 换成智能体")), script=f5_script()),
 }),
 "053": dict(proj="anthropic-bubble", audio=[4.377, 12.7, 14.733063, 4.45825, 4.144812], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="AI 泡沫", hero="650亿", unit="反而跌", v1="好数字", v2="为什么让股价跌")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Anthropic", h2="周末透露", note="Yahoo Finance", cards=[("实际","650 亿","年化收入"),("传闻","800 亿","硅谷想象"),("结果","跌 10%","光通信股")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="为什么好数字反而跌", punch="市场怕账算不过来", cards=[("定价","按 800 亿","早就涨满"),("落地","650 亿","挤水分")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="但要分清", punch="", cards=[("基本面","没变","业绩还在"),("跌的是","预期","不是业绩")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="泡沫", unit="真相", q1="泡沫从来不是 AI 不行了", q2="是想象跑得比现实快")), script=f5_script()),
 }),
 "076": dict(proj="free-ai-video-tools", audio=[4.458250, 7.221438, 7.400000, 7.186625, 6.800000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="做 AI 视频", hero="3", unit="个免费工具", v1="别人充会员", v2="我用免费的")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="即梦", h2="字节家", note="字节跳动 · 官方", cards=[("免费额度","三家里最大","即梦"),("登录","抖音剪映账号","直接登"),("互通","跟剪映","无缝")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="海螺 AI", punch="中文提示词最懂你", cards=[("中文 prompt","最准","MiniMax 出品"),("写「氛围感」「情绪」","它最懂","描述更自然")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="可灵", punch="国产天花板，就是额度少点", cards=[("出品","快手","快手家"),("画质","天花板","免费档就能打")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="先免费试", unit="再决定充不充", q1="三个免费额度叠着用", q2="一周做几条不发愁")), script=f5_script()),
 }),
 "077": dict(proj="chatgpt-plus-pay", audio=[4.934250, 7.778688, 8.370812, 8.400000, 6.300000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="充 ChatGPT", hero="3", unit="个办法不被卡", v1="别人被风控卡住", v2="我用这 3 个")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="官方直付", h2="有外币卡首选", note="OpenAI · 官方支付", cards=[("Visa","海外发行","最稳"),("万事达","海外发行","最稳"),("Amex","美国运通","不会被误伤")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="美区 App Store", punch="苹果用户正规路", cards=[("美区 ID","加礼品卡","官方 App 里订"),("订阅","不折腾","完全合规")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="代充激活码", punch="只认激活码，不给密码", cards=[("拿卡密","官方页面","自己激活"),("账号密码","谁都不给","安全底线")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="不交密码", unit="是底线", q1="有卡走官方，没卡选不交密码", q2="虚拟卡能不碰就不碰")), script=f5_script()),
 }),
 "078": dict(proj="free-speech-to-text", audio=[4.100000, 8.600000, 8.289563, 8.962938, 7.800000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="录音转文字", hero="3", unit="个免费的", v1="别人充会员", v2="我用免费的")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="手机自带", h2="本地离线", note="Apple / Google · 内置", cards=[("iPhone","语音备忘录","本地转写"),("Pixel","Google 录音机","不限时长"),("随手记","够用","不用联网")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="本地 Whisper", punch="开源免费，批量转", cards=[("开源","免费","几乎无限量"),("中文长音频","批量转","准确")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="云端免费档", punch="短会英文最省事", cards=[("Otter","每月免费分钟","短会省事"),("长音频","会撞上限","提前看清")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="先看清", unit="免费在哪断", q1="随手记用手机，批量转用 Whisper", q2="短会用云端，免费工具看清边界")), script=f5_script()),
 }),
 "079": dict(proj="free-ai-writing", audio=[4.800000, 7.384000, 8.486937, 8.962938, 6.400000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="写文案", hero="3", unit="个免费的", v1="别人报课买会员", v2="我用免费的")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="豆包", h2="字节家", note="字节跳动 · 官方", cards=[("写文案","改标题","最顺手"),("免费服务","一直升级","字节免费")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="Kimi", punch="长文摘要续写强", cards=[("长文摘要","强项","月之暗面"),("基础写作","免费","够用")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="腾讯元宝", punch="一句话生成文件", cards=[("接混元","新模型","对话生成"),("PPT / 表格","PDF","直接给")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="叠着用", unit="先别充会员", q1="文案豆包、长文 Kimi、文件元宝", q2="三个免费叠着用，先别急着充会员")), script=f5_script()),
 }),
 "080": dict(proj="bytedance-doubao-merge", audio=[6.100000, 9.079062, 7.400000, 9.200000, 7.300000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="写代码 搭智能体", hero="1", unit="个入口就够", v1="别人装三个 App", v2="字节合成一个")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="TRAE", h2="AI 编程", note="字节跳动 · 官方", cards=[("编程","IDE 命令行","继续更新"),("并入","豆包品牌","独立产品线")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="扣子 Coze", punch="智能体平台并进豆包", cards=[("搭智能体","并进豆包","工作场景直接用"),("原平台","团队整体","并入豆包体系")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="豆包工作", punch="最快这周上线", cards=[("工作入口","200+ 技能","连接器"),("远程控制","云电脑","侧边工作台")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="一个豆包", unit="就够", q1="三个免费工具合成一个入口", q2="你以前装的东西，权益不变")), script=f5_script()),
 }),
 "081": dict(proj="aliyun-wan3-video", audio=[5.500000, 8.962938, 7.337562, 9.700000, 6.500000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="做 AI 视频", hero="30", unit="秒一步到位", v1="别人一次 15 秒", v2="阿里这个模型")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Wan3.0", h2="时长翻倍", note="阿里云百炼 · 官方", cards=[("时长","30 秒","一步到位"),("画质","1080P","高清"),("音画","一起出","不用单独配音")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="全模态输入", punch="什么都能喂", cards=[("图片/视频/音频","丢进去","照着做"),("文档/网页","链接","自动解析")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="按秒计费", punch="失败不花钱", cards=[("480P","三毛一秒","够试水"),("1080P","一块二一秒","高清")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="失败", unit="不计费", q1="30 秒一步到位", q2="先拿失败不计费试试水")), script=f5_script()),
 }),
 "082": dict(proj="free-ai-office", audio=[4.853000, 9.400000, 9.079062, 7.267875, 6.900000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="做 PPT 整表格", hero="3", unit="个免费的", v1="别人熬夜", v2="我用免费的")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="腾讯元宝", h2="接混元", note="腾讯 · 官方", cards=[("PPT","一句话生成","免费"),("表格/PDF","直接给","够用")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="千问表格 Agent", punch="对话生成改 Excel", cards=[("生成编辑","带真实公式","阿里千问"),("传照片","识别成表","全端免费")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="Kimi", punch="逻辑最强", cards=[("深度内容","大纲汇报","强项"),("写材料","逻辑清楚","月之暗面")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="叠着用", unit="先别充会员", q1="PPT 元宝、表格千问、内容 Kimi", q2="三个免费叠着用，先别急着充会员")), script=f5_script()),
  }),
 "083": dict(proj="sora-shutdown-migrate", audio=[4.736875, 8.500000, 9.400000, 8.370812, 7.581375], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="Sora 停服", hero="3", unit="个替代的", v1="数据还要删光", v2="我用这 3 个")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Veo 3.1", h2="谷歌家", note="Gemini API · 官方", cards=[("最像 Sora","自然语言","音画同出"),("按秒计价","0.15-0.4 美元","参考价")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="Seedance 2.5", punch="社交流量走量最便宜", cards=[("便宜草稿","最长 30 秒","走量"),("原生音频","默认就开","省事")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="MiniMax H3", punch="对白口型强项", cards=[("对白同步","角色视频","强项"),("参考一致性","好","口型准")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="先导出", unit="再迁移", q1="最像 Veo、走量 Seedance、对白 H3", q2="先导出你的 Sora 作品，再迁移")), script=f5_script()),
 }),
 "084": dict(proj="stripe-openrouter", audio=[6.431938, 8.684313, 8.000000, 7.500000, 6.300000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="400+ 模型怎么选", hero="几十亿", unit="买台路由器", v1="别人一个个试", v2="Stripe 直接买")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="OpenRouter", h2="模型网关", note="Stripe · 官方公告", cards=[("400+","模型","一个口接"),("80+","供应商","聚合")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="它干嘛的", punch="自动挑最划算的模型", cards=[("按任务难度","价格","速度"),("发一个请求","自动路由","最优模型")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="谁在用", punch="外媒说七十几亿", cards=[("英伟达 / Zoom","Lovable","都在用"),("金额","约 75 亿","外媒推测")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="中间层", unit="最值钱", q1="模型越来越多", q2="最值钱的是帮你选模型的中间层")), script=f5_script()),
 }),
 "085": dict(proj="huggingface-sale", audio=[6.199750, 9.500000, 10.000000, 8.800000, 5.839875], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="不造模型", hero="130亿", unit="可能卖", v1="全球最大 AI 模型仓库", v2="要卖了")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Hugging Face", h2="模型仓库", note="SiliconANGLE · 引 BI", cards=[("300万+","模型","堆在这"),("100万+","数据集","开源平台")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="它多值钱", punch="45 亿涨到 130 亿", cards=[("三年前","融资 45 亿","估值"),("现在","传闻 130 亿","翻近三倍")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="为什么现在卖", punch="赶上平台收购潮", cards=[("已请银行","接触买家","早期"),("Stripe 刚买","OpenRouter","75 亿")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="分发平台", unit="最值钱", q1="造模型的不一定是赢家", q2="让大家分发模型的平台反而最值钱")), script=f5_script()),
 }),
 "086": dict(proj="anthropic-model-leak", audio=[5.758563, 7.662625, 7.534937, 8.092187, 6.037250], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="Claude 下一代", hero="2", unit="个代号", v1="棉花糖", v2="和甜瓜")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Marshmallow", h2="棉花糖", note="Anthropic API · 泄露", cards=[("表现","超 Opus 5","据说"),("被猜","Opus 5.1","下一代")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="Melon", punch="甜瓜·性价比", cards=[("比棉花糖","弱一点","被猜 Sonnet"),("路线","5.1","性价比")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="eap 内测", punch="正式发布可能下月", cards=[("两个都带","eap 后缀","早期内测"),("只对","少数开发者","开放")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="稳扎稳打", unit="不是革命", q1="先别抱革命性期待", q2="大概率是升级，不是下一代旗舰")), script=f5_script()),
 }),

 "087": dict(proj="mac-mini-m6", audio=[6.675750, 11.800000, 8.997750, 10.344500, 9.500000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="本地跑大模型", hero="6999", unit="起步", v1="别人攒显卡", v2="苹果这台")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="M6", h2="首款 2 纳米", note="苹果 · 官方发布", cards=[("制程","2 纳米","首款 M 系列"),("12 核 CPU","12 核 GPU","AI 顶到 M4 四倍")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="跑模型快", punch="LM Studio 提速", cards=[("M1 版","13.5 倍","提示词"),("M4 版","4.8 倍","提示词")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="内存管够", punch="16GB 起步", cards=[("16GB 起","最高 32GB","小模型随便跑"),("带宽","170GB/秒","统一内存")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="6999", unit="起", q1="27 号预购、22 号发货", q2="想本地跑 AI 不攒显卡，先看这条")), script=f5_script()),
 }),
 "088": dict(proj="us-ai-chinese-models", audio=[4.700000, 9.868500, 8.730750, 6.675750, 7.581375], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="美国律所独角兽", hero="Kimi", unit="中国底座", v1="底座不是 GPT", v2="是中国的 Kimi")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Harvey", h2="法律 AI", note="Harvey 官方 · 110 亿美元", cards=[("110 亿","估值","独角兽"),("10 万","律师","在用"),("Tenet","Kimi K3 底座","完成数翻倍")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="Cursor / Devin", punch="硅谷编程工具", cards=[("Cursor","Kimi K2.5","底座"),("Devin","Kimi K2.7","底座")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="Thinking Machines", punch="Murati 120 亿", cards=[("架构","DeepSeek V3","参考"),("启动","Kimi K2.5","合成数据")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="中国芯", unit="被用进去", q1="卖的不再是 API", q2="是被用进美国产品")), script=f5_script()),
 }),
 "089": dict(proj="dm05-robodojo", audio=[4.887812, 9.984625, 11.700000, 9.195125, 7.000000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="机器人评测榜", hero="4B", unit="开源第一", v1="模型只有 4B", v2="还全开源")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="DM0.5", h2="综合第一", note="原力灵机 · RoboDojo", cards=[("综合得分","24.90","第一"),("成功率","19.34%","甩开第二")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="记忆最狠", punch="60 秒长记忆", cards=[("Memory","47.74 分","远超第二"),("成功率","47.44%","靠长记忆")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="能自己跑", punch="4090 单卡可微调", cards=[("4B 主干","680M 动作专家","VLA"),("全开源","权重+框架","单卡可跑")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="门", unit="敞开了", q1="4B 登顶、单卡可跑", q2="先 clone 再说")), script=f5_script()),
 }),

 "090": dict(proj="ilya-ssi-model", audio=[6.300000, 7.976063, 10.700000, 7.697438, 6.200000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="Ilya 新模型", hero="320亿", unit="估值", v1="两年没出产品", v2="终于要来了")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="爆料", h2="a16z Casado", note="机器之心 · 8/26", cards=[("原话","今年最重要发布","没有之一"),("线索","指向 Ilya","SSI")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="SSI 是谁", punch="神秘两年无产品", cards=[("2025","20 亿融资","320 亿估值"),("英伟达","投 50 亿","给最新芯片")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="卖点是啥", punch="传闻持续学习", cards=[("不是练完固定","边用边学","突破"),("8 月","可能发布","未官宣")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="别当八卦", unit="8 月见分晓", q1="能力与安全能不能同路", q2="当成一次路线检验")), script=f5_script()),
 }),
 "091": dict(proj="nvidia-vera-rubin", audio=[5.300000, 9.700000, 7.384000, 11.296563, 7.200000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="同样的电", hero="30", unit="倍", v1="别人干一份活", v2="英伟达这台")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Vera Rubin", h2="吞吐翻 30 倍", note="英伟达 · 首测", cards=[("每兆瓦吞吐","上代 30 倍","DeepSeek 实测"),("GB300","主力机皇","被比下去")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="成本降 35 倍", punch="每百万 Token", cards=[("同样 100 万","成本","砍到 1/35"),("同电力","干 30 倍活","算力资产")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="基准换了", punch="AgentX 测智能体", cards=[("旧聊天基准","测不出","失效"),("实测对象","开源 DeepSeek","V4-Pro")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="每度电", unit="产出", q1="比谁每度电干的活多", q2="AI 工厂的新竞赛开始了")), script=f5_script()),
 }),

 "092": dict(proj="chatgpt-free-scheduled-tasks", audio=[3.564, 6.840, 5.688, 7.668, 4.968], frames={
   "01-hook": dict(css=EVIDENCE_CSS, body=evidence_body(dict(kicker="CHATGPT FREE", title="免费版，也能定时干活", image=".media/images/image_002.webp", alt="OpenAI 官方重复任务面板", badge="最多 3 个活动任务", caption="能跑一次，也能每天跑一次", source="OpenAI · 2026-08-25")), script=evidence_script()),
   "02-facts": dict(css=EVIDENCE_CSS, body=evidence_body(dict(kicker="SCHEDULED", title="入口就在侧边栏", image=".media/images/image_003.webp", alt="OpenAI 官方任务通知与管理入口", badge="灵活时间窗口", caption="先让它整理待办，或晚上提醒复盘", source="OpenAI Help Center")), script=evidence_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="三步建一个", punch="先用一个任务验证需求", cards=[("01","打开 Scheduled","侧边栏"),("02","写清任务","一次 / 每天"),("03","保存后查看","可随时管理")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="免费版边界", punch="精确时间和外部触发要付费", cards=[("能用","每天一次","灵活窗口"),("不能","精确分钟","小时级"),("不能","Gmail / Slack","GitHub 触发")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="先建 1 个", unit="真会看的任务", q1="三个免费名额够验证需求", q2="别先塞满提醒")), script=f5_script()),
 }),

 "093": dict(proj="claude-memory-controls", audio=[2.556, 7.056, 9.828, 7.056, 5.400], frames={
   "01-hook": dict(css=EVIDENCE_CSS, body=evidence_body(dict(kicker="CLAUDE MEMORY", title="记忆，默认开了", image=".media/images/image_002.png", alt="Anthropic 官方 Memory Topics 列表", badge="Free / Pro / Max", caption="先看它到底记住了什么", source="Anthropic · 2026-08-25")), script=evidence_script()),
   "02-facts": dict(css=EVIDENCE_CSS, body=evidence_body(dict(kicker="ONE MEMORY", title="Chat 和 Cowork 共用", image=".media/images/image_003.png", alt="Anthropic 官方 Memory 设置界面", badge="同一份记忆", caption="每条都能读、改、删", source="Anthropic 官方博客")), script=evidence_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="先打开 Topics", punch="看清内容，再决定开关", cards=[("读","它记了什么","逐条检查"),("改 / 删","错的内容","立即修正"),("暂停 / 重置","需要时","保留控制")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="两个隐私边界", punch="别夸大，也别放任", cards=[("敏感主题","默认不保存","官方说明"),("一次性私聊","用无痕聊天","不进历史")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="删错的", unit="留有用的", q1="记忆能省掉重复解释", q2="第一步，先检查 Topics")), script=f5_script()),
 }),

 "094": dict(proj="openai-jalapeno-chip", audio=[5.642500, 11.493937, 8.765562, 7.186625, 6.900000], frames={
   "01-hook": dict(css=FI_CSS, body=fi_body(dict(header="OpenAI 自研芯片", caption="700 瓦，追平英伟达 1400 瓦", note="SOURCE · OpenAI 官方 · Hot Chips")), script=fi_script(), imgs={"fi-img":"assets/source/01-chip.png"}),
   "02-facts": dict(css=FI_CSS, body=fi_body(dict(header="跑分三模型", caption="DeepSeek · Kimi · 每瓦 1.5–1.9 倍", note="SOURCE · SemiAnalysis InferenceX")), script=fi_script(), imgs={"fi-img":"assets/source/02-bench.jpg"}),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="只做推理", punch="9 个月从设计到流片", cards=[("博通合作","台积电 3 纳米","专用 ASIC"),("不训练","只跑推理","HBM 高带宽")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="只自用", punch="年底小规模，明年铺开", cards=[("不对外卖","只给 OpenAI","砍采购成本"),("第二代","已在后期开发","多代路线")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="推理效率", unit="新战场", q1="OpenAI 没说要弃用英伟达", q2="真正信号是效率成了竞争点")), script=f5_script()),
 }),
 "095": dict(proj="xiaomi-ai-cube", audio=[6.000000, 9.984625, 8.400000, 6.234563, 5.085187], frames={
   "01-hook": dict(css=FI_CSS, body=fi_body(dict(header="小米 AI Cube", caption="本地跑 120B 大模型", note="SOURCE · 小米玄戒发布会")), script=fi_script(), imgs={"fi-img":"assets/source/01-cube.jpg"}),
   "02-facts": dict(css=FI_CSS, body=fi_body(dict(header="玄戒三芯", caption="旗舰 SoC + 加速 + 智驾", note="SOURCE · IT之家 · 8/24")), script=fi_script(), imgs={"fi-img":"assets/source/02-chip.jpg"}),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="快慢双模型", punch="整机才 150 瓦", cards=[("120B","管难活","大模型"),("3B","管快活","低延迟")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="先看方向", punch="工程版未量产", cards=[("未公布","价格","上市时间"),("O100/D100","明年","才量产")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="国产", unit="有答案了", q1="本地跑大模型不用攒显卡", q2="先看方向，别急着掏钱")), script=f5_script()),
 }),
 "096": dict(proj="aws-duckdb", audio=[6.397125, 8.057375, 7.800000, 8.881687, 6.700000], frames={
   "01-hook": dict(css=FI_CSS, body=fi_body(dict(header="AWS 收编 DuckDB", caption="每天百万次下载的数据库", note="SOURCE · DuckLabs 官方公告")), script=fi_script(), imgs={"fi-img":"assets/source/01-duckdb.jpg"}),
   "02-facts": dict(css=FI_CSS, body=fi_body(dict(header="开源不变", caption="MIT 许可 · 基金会托管", note="SOURCE · Amazon 官方")), script=fi_script(), imgs={"fi-img":"assets/source/02-aws.svg"}),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="团队加入 AWS", punch="项目照常开源", cards=[("DuckDB/DuckLake","Quack","继续开发"),("基金会","继续托管","MIT 不变")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="对开发者", punch="用法不变", cards=[("本地该用还用","代码不改","单机快查"),("AWS","拿去做云服务","数据服务")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="许可证", unit="没变", q1="开源被巨头收编不一定是坏事", q2="关键是你的用法也没变")), script=f5_script()),
 }),
 "097": dict(proj="glm-5.3-flash", audio=[6.153313, 10.820500, 9.300000, 7.024063, 8.569500], frames={
   "01-hook": dict(css=FI_CSS, body=fi_body(dict(header="GLM-5.3-Flash", caption="320B 总参，只激活 18B", note="SOURCE · 智谱官方文档")), script=fi_script(), imgs={"fi-img":"assets/source/01-flash.png"}),
   "02-facts": dict(css=FI_CSS, body=fi_body(dict(header="原生视觉", caption="主动看界面、看反馈", note="SOURCE · 智谱 · z.ai")), script=fi_script(), imgs={"fi-img":"assets/source/02-logo.png"}),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="高效架构", punch="又大又省", cards=[("线性+稀疏","注意力","320B 总参"),("激活","18B","KV 缓存大砍")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="适合谁", punch="高并发低延迟", cards=[("Office 文档","金融研究","工作流"),("1M 上下文","原生调用工具","思考模式")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="不比参数", unit="比效率", q1="国产开源内卷方向很清楚", q2="用更少算力干更多活")), script=f5_script()),
 }),

 "098": dict(proj="glm-oxalpha-reveal", audio=[6.000000, 10.379375, 12.167312, 7.662625, 7.100000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="匿名模型", hero="1/40", unit="的价", v1="谜底揭晓", v2="是国产的")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Ox-Alpha", h2="牛来", note="科创板日报 · 官方", cards=[("首日调用","登顶","OpenRouter"),("终结","DeepSeek 56 天","霸榜"),("单日","62T token","全球")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="谜底是谁", punch="智谱 GLM-5.3-Flash", cards=[("320B","激活 18B","高效"),("智能指数","57 分","= Opus 4.8")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="价格屠夫", punch="只有 Opus 的 1/40", cards=[("输入","0.8 元/百万","token"),("输出","2.8 元/百万","token")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="国产算力", unit="出海", q1="10 万张国产卡扛全部流量", q2="顶级智能不用省着用")), script=f5_script()),
 }),
 "099": dict(proj="glm-5.3-flash-detail", audio=[8.452125, 7.662625, 9.079062, 9.868500, 7.465250], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="320B", hero="18B", unit="只激活", v1="和 Opus 4.8 打平", v2="参数掰开看看")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="混合架构", h2="开源首创", note="智谱官方文档", cards=[("稀疏+线性","注意力","混合"),("第一个","开源前沿","这么干")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="省在哪", punch="注意力砍 3 倍", cards=[("计算量","降 3.01 倍","注意力"),("KV 缓存","省 4.44 倍","1M 上下文")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="能力强", punch="原生多模态", cards=[("看图改代码","Office","金融研究"),("智能指数","57 分","= Opus 4.8")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="前沿智能", unit="不用省着用", q1="参数/架构/成本三样压倒性", q2="这就是效率革命")), script=f5_script()),
 }),

 "100": dict(proj="free-local-llm-tools", audio=[4.900000, 8.300000, 9.276375, 10.200000, 10.971438], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="本地跑大模型", hero="4", unit="个免费工具", v1="不用买会员", v2="全免费")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="LM Studio", h2="图形界面", note="开源免费 · 入门首选", cards=[("下载即用","点几下","就能跑"),("不折腾","适合新手","最省心")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="Ollama", punch="程序员最顺手", cards=[("一行命令","装模型","CLI 友好"),("12 万星","接 API","GitHub")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="vLLM / llama.cpp", punch="高并发 vs 省内存", cards=[("vLLM","高吞吐","给服务用"),("llama.cpp","最省内存","给旧电脑")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="第 100 期", unit="先存一步", q1="入门 LM Studio、开发 Ollama", q2="高并发 vLLM、省内存 llama.cpp")), script=f5_script()),
 }),

 "101": dict(proj="local-llm-hardware", audio=[5.100000, 7.000000, 8.800000, 10.623188, 7.500000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="本地跑大模型", hero="省一半", unit="钱", v1="别按配置单买", v2="看准一个数")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="记一个公式", h2="参数×字节", note="Simplico · 2026 实测", cards=[("参数量","×字节数","基础占用"),("再留","2 成 5","余量")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="入门级", punch="8–16G 能跑 8B", cards=[("M4 Mac","3060 12G","日常聊天"),("Q4 量化","7B≈4.2G","够用")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="进阶 24G", punch="能上 14B–32B", cards=[("二手 3090","24G","性价比王"),("全新 4090","24G","更省心")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="够用", unit="最香", q1="按量化占用配，留给系统 4G", q2="不是越贵越好")), script=f5_script()),
 }),
 "102": dict(proj="local-vs-cloud", audio=[6.791875, 6.300000, 5.800000, 8.173500, 7.700000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="本地还是云端", hero="不分", unit="胜负", v1="不是二选一", v2="看用途")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="选本地", h2="三件事", note="Simplico · 实用口径", cards=[("数据","不出本机","隐私"),("离线","可用","不用网"),("省钱","长期费用","可控")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="选云端", punch="两种情况", cards=[("要顶配","模型能力","更大"),("要规模","大量并发","不死机")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="戳个误区", punch="本地跑起来不知干嘛", cards=[("本地最大价值","隐私+离线","别只顾拼能力"),("日常够用","70B 量化","可掰手腕")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="分清用途", unit="最重要", q1="私密事本地跑、顶配上云", q2="别纠结二选一")), script=f5_script()),
 }),

 "103": dict(proj="tencent-hy4", audio=[6.200000, 9.949813, 7.100000, 8.684313, 6.791875], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="770B 大模型", hero="两周", unit="免费", v1="腾讯开源了", v2="限时免费")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Hy4 preview", h2="开源第一梯队", note="腾讯官方 · 8/28", cards=[("770B","总参","49B 激活"),("上下文","突破 1M","生产力强")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="哪能免费用", punch="两周限时免费", cards=[("WorkBuddy","CodeBuddy","元宝"),("开放","API","OpenRouter")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="价格普惠", punch="每百万 6 元", cards=[("盲测","略胜 GLM-5.3","Kimi K3"),("输入","6 元/百万","输出 18 元")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="趁两周", unit="免费", q1="国产开源第一梯队再进一位", q2="想试趁现在，过了按量付费")), script=f5_script()),
 }),
 "104": dict(proj="bytedance-lance-3b", audio=[7.662625, 8.900000, 8.300000, 9.589875, 7.800000], frames={
   "01-hook": dict(css=F1_CSS, body=f1_body(dict(scare="看懂图 生成视频", hero="3B", unit="全干了", v1="以前拼好几个模型", v2="现在一个小的")), script=f1_script()),
   "02-facts": dict(css=F2_CSS, body=f2_body(dict(h1="Lance 3B", h2="原生统一", note="字节研究院 · 开源", cards=[("激活","30 亿","轻量"),("看/写/编","图像+视频","一个模型")])), script=f2_script()),
   "03-mech": dict(css=F3_CSS, body=f3_body(dict(header="不是拼装", punch="双流专家互不打架", cards=[("理解","一套专家","生成"),("边界","MaPE 机制","不混淆")])), script=f3_script()),
   "04-impact": dict(css=F4_CSS, body=f4_body(dict(header="超 7B 专用", punch="Apache 2.0 开源", cards=[("视频生成","85 分","超专业模型"),("视频理解","62 分","超 7B")])), script=f4_script()),
   "05-verdict": dict(css=F5_CSS, body=f5_body(dict(hero="3B", unit="装下看写编", q1="做 AI 短片/智能体", q2="可能不用拼一堆模型")), script=f5_script()),
 }),

}

def load_words(ep, i):
    raw = json.loads((pathlib.Path(f"/tmp/ep{ep}-voice") / f"{i:02d}-words.json").read_text(encoding="utf-8"))
    tw = raw[0]["timestamped_words"]
    return [(w["word_begin"], w["word_end"], w["time_begin"], w["time_end"]) for w in tw]

def split_clauses(text):
    parts = re.split(r"([，。；：——、！？])", text)
    clauses, buf = [], ""
    for p in parts:
        buf += p
        if p in "，。；：——、！？":
            clauses.append(buf); buf = ""
    if buf.strip(): clauses.append(buf)
    return [c for c in clauses if c.strip()]

import sys as _sys
_only = set(a for a in _sys.argv[1:] if a in CONF)
_iter = ((ep, CONF[ep]) for ep in (_only if _only else CONF))

for ep, C in _iter:
    proj = C["proj"]; audio_dur = C["audio"]
    DST = ROOT / "videos" / proj
    # 复制基础
    for rel in ["assets/fonts", "assets/brand", ".hyperframes", "hyperframes.json", "package.json", "frame.md", "caption-overrides.json"]:
        s = TPL / rel; d = DST / rel
        if d.exists(): continue
        if s.is_dir():
            import shutil; shutil.copytree(s, d)
        else:
            d.parent.mkdir(parents=True, exist_ok=True); import shutil; shutil.copy2(s, d)
    import shutil
    if not (DST / "bin").exists():
        shutil.copytree(TPL / "bin", DST / "bin")
    (DST / "compositions").mkdir(parents=True, exist_ok=True)
    shutil.copy2(TPL / "compositions/captions.html", DST / "compositions/captions.html")

    starts = [0.0]
    for d in audio_dur[:-1]:
        starts.append(round(starts[-1] + d, 6))
    TOTAL = round(starts[-1] + audio_dur[-1], 6)
    scene_dur = [round(d + 0.5, 4) for d in audio_dur]
    DUR = [round(d, 6) for d in audio_dur]
    ST = [round(s, 6) for s in starts]
    names = list(C["frames"].keys())

    (DST / "compositions/frames").mkdir(parents=True, exist_ok=True)
    for i, (nm, fc) in enumerate(C["frames"].items()):
        (DST / "compositions/frames" / f"{nm}.html").write_text(
            frame(nm, ep, fc["css"], fc["body"], fc["script"], scene_dur[i], imgs=fc.get("imgs")), encoding="utf-8")

    AUDIO_TXT = ROOT / "content" / f"episode-{ep}" / "audio-text"
    caption_groups, speech_windows = [], []
    gid = 0
    for i in range(1, 6):
        text = (AUDIO_TXT / f"{i:02d}.txt").read_text(encoding="utf-8").strip()
        syl = load_words(ep, i); base = starts[i-1]
        for (cb, ce, tb, te) in syl:
            ws = base + tb/1000.0; we = base + te/1000.0
            if speech_windows and ws - speech_windows[-1][1] < 0.28:
                speech_windows[-1][1] = we
            else: speech_windows.append([round(ws,3), round(we,3)])
        pos = 0
        for cl in split_clauses(text):
            cstart = pos; cend = pos + len(cl)
            inrange = [s for s in syl if s[1] > cstart and s[0] < cend]
            if not inrange: pos = cend; continue
            t0 = base + inrange[0][2]/1000.0; t1 = base + inrange[-1][3]/1000.0
            caption_groups.append({"id": f"caption-group-{gid}", "frame": i,
                "start": round(t0,3), "end": round(t1+0.12,3), "text": cl,
                "words": [{"id": f"caption-word-{gid}-0", "text": cl, "start": round(t0,3), "end": round(t1,3)}]})
            gid += 1; pos = cend

    audio_meta = {"bgm": None, "bgm_pending": False, "voices": [], "sfx": []}
    for i in range(1, 6):
        text = (AUDIO_TXT / f"{i:02d}.txt").read_text(encoding="utf-8").strip()
        syl = load_words(ep, i); words = []; wid = 0; pos = 0
        for cl in split_clauses(text):
            cstart = pos; cend = pos + len(cl)
            inrange = [s for s in syl if s[1] > cstart and s[0] < cend]
            if not inrange: pos = cend; continue
            words.append({"id": wid+1, "text": cl, "start": round(inrange[0][2]/1000.0,2), "end": round(inrange[-1][3]/1000.0,2)})
            wid += 1; pos = cend
        audio_meta["voices"].append({"frame": i, "path": f"assets/voice/{i:02d}.mp3", "duration_s": DUR[i-1], "words": words})
    (DST / "audio_meta.json").write_text(json.dumps(audio_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (DST / "caption_groups.json").write_text(json.dumps(
        {"total_duration_s": TOTAL, "width": 1080, "height": 1920, "groups": caption_groups},
        ensure_ascii=False, indent=2), encoding="utf-8")

    cap = (DST / "compositions/captions.html").read_text(encoding="utf-8")
    cap = re.sub(r"var GROUPS = \[.*?\];", "var GROUPS = " + json.dumps(caption_groups, ensure_ascii=False) + ";", cap, count=1, flags=re.S)
    cap = re.sub(r"var DURATION = [0-9.]+;", f"var DURATION = {TOTAL};", cap, count=1)
    cap = re.sub(r'data-duration="[0-9.]+"', f'data-duration="{TOTAL}"', cap, count=1)
    (DST / "compositions/captions.html").write_text(cap, encoding="utf-8")

    # index.html
    trans = []
    for i in range(4):
        t = ST[i+1]
        if i < 3:
            trans.append(f'        tl.to("#el-{names[i]}", {{ x: -1080, duration: 0.5, ease: "power3.inOut" }}, {t});')
            trans.append(f'        tl.fromTo("#el-{names[i+1]}", {{ x: 1080, opacity: 1 }}, {{ x: 0, duration: 0.5, ease: "power3.inOut" }}, {t});')
        else:
            trans.append(f'        tl.to("#el-{names[i]}", {{ filter: "blur(10px)", scale: 1.03, opacity: 0, duration: 0.6, ease: "power2.inOut" }}, {t});')
            trans.append(f'        tl.fromTo("#el-{names[i+1]}", {{ filter: "blur(10px)", scale: 0.97, opacity: 0 }}, {{ filter: "blur(0px)", scale: 1, opacity: 1, duration: 0.6, ease: "power2.inOut" }}, {t});')
    scenes, audios = [], []
    for i in range(5):
        nm = names[i]
        scenes.append(f'      <div id="el-{nm}" class="scene" data-composition-id="{nm}" data-composition-src="compositions/frames/{nm}.html" data-start="{ST[i]}" data-duration="{scene_dur[i]}" data-track-index="{0 if i%2==0 else 1}"></div>')
        audios.append(f'      <audio id="el-{nm}-voice" src="assets/voice/{i+1:02d}.mp3" data-start="{ST[i]}" data-duration="{DUR[i]}" data-track-index="{10+i}" data-volume="1"></audio>')
    sw_lines = ",\n".join(f"          [{a},{b}]" for a, b in speech_windows)
    html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js" integrity="sha384-sG0Hv1tP1lZCk9KQmrIbY/XNwi+OY84GQqhMscbnsoBFqAz8KNCil1kvfL3Hbbk2" crossorigin="anonymous"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #F0EBDE; }}
      .scene {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
      .chai-speaker {{
        position: absolute; top: 1490px; left: 190px; width: 110px; height: 110px; z-index: 40;
        border: 3px solid #2639e8; border-radius: 50%; background: #06143f;
        box-shadow: 0 8px 20px rgba(19,31,135,.2), 0 0 0 5px rgba(240,235,222,.94);
        overflow: visible; will-change: transform;
      }}
      .chai-speaker__crop {{ position: absolute; inset: 0; overflow: hidden; border-radius: 50%; }}
      .chai-speaker__crop img {{ display: block; width: 100%; height: 100%; object-fit: cover; }}
      .chai-speaker__mouth-anchor {{ position: absolute; left: 50%; top: 66.2%; width: 34px; height: 20px; margin-left: -17px; margin-top: -10px; pointer-events: none; }}
      .chai-speaker__mouth {{
        position: absolute; inset: 0; border-radius: 48% 48% 54% 54%;
        background: radial-gradient(ellipse at 50% 76%, #d65a68 0 20%, #521e2a 22% 48%, #160b12 52% 100%);
        box-shadow: inset 0 3px 2px rgba(255,255,255,.25), 0 1px 2px rgba(0,0,0,.45);
        opacity: 0; will-change: transform, opacity;
      }}
      .chai-speaker__mouth::before {{ content: ""; position: absolute; top: 1px; left: 5px; width: 24px; height: 5px; border-radius: 0 0 9px 9px; background: #f7eee0; }}
      .chai-speaker__name {{
        position: absolute; left: 50%; bottom: -23px; min-width: 84px; margin-left: -42px; padding: 4px 8px;
        border: 2px solid #2639e8; background: #f0ebde; color: #2639e8;
        font: 700 14px/1 "CobaltMono", "PingFang SC", sans-serif; text-align: center; letter-spacing: .08em; white-space: nowrap; opacity: 0;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0.0" data-duration="{TOTAL}" data-width="1080" data-height="1920">
{chr(10).join(scenes)}
{chr(10).join(audios)}

      <div id="el-captions" class="scene" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0.0" data-duration="{TOTAL}" data-track-index="2"></div>

      <div id="chai-speaker" class="chai-speaker" aria-label="柴主编说话头像">
        <div class="chai-speaker__crop">
          <img src="assets/brand/chai-editor-avatar.png" alt="柴主编">
          <div class="chai-speaker__mouth-anchor">
            <div id="chai-speaker-mouth" class="chai-speaker__mouth"></div>
          </div>
        </div>
        <div class="chai-speaker__name">柴主编</div>
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
      (function () {{ var tl = window.__timelines["main"];
{chr(10).join(trans)}
        tl.fromTo("#chai-speaker", {{ scale: 0, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.55, ease: "back.out(1.7)" }}, 0.18);
        var speechWindows = [
{sw_lines}
        ];
        var mouth = document.getElementById("chai-speaker-mouth");
        var avatar = document.getElementById("chai-speaker");
        var jawDriver = {{ progress: 0 }};
        tl.to(jawDriver, {{
          progress: 1, duration: {TOTAL}, ease: "none",
          onUpdate: function () {{
            var t = jawDriver.progress * {TOTAL};
            var active = null;
            for (var i = 0; i < speechWindows.length; i++) {{
              if (t >= speechWindows[i][0] && t <= speechWindows[i][1]) {{ active = speechWindows[i]; break; }}
            }}
            var openness = 0;
            if (active) {{
              var local = t - active[0];
              var attack = Math.min(1, local / 0.07);
              var release = Math.min(1, (active[1] - t) / 0.09);
              var syllable = 0.34 + 0.66 * Math.abs(Math.sin(local * 18.5));
              openness = syllable * Math.max(0, Math.min(attack, release));
            }}
            gsap.set(mouth, {{ scaleX: 0.82 + openness * 0.22, scaleY: 0.12 + openness * 0.94, opacity: openness > 0.04 ? 0.98 : 0 }});
            gsap.set(avatar, {{ y: active ? -2.5 * Math.sin(t * 5.4) : 0, rotation: active ? 0.7 * Math.sin(t * 2.7) : 0 }});
          }}
        }}, 0);
        tl.to({{}}, {{ duration: {TOTAL} }}, 0);
      }})();
    </script>
  </body>
</html>
"""
    (DST / "index.html").write_text(html, encoding="utf-8")
    print(f"EP.{ep} ({proj}) done: TOTAL={TOTAL:.2f}s frames={len(names)} groups={len(caption_groups)}")
