#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const projectDir = path.resolve(process.argv[2] || "");
if (!projectDir || !fs.existsSync(projectDir)) {
  throw new Error("Usage: node scripts/build_xiaochao_video.mjs <episode-dir>");
}

const spec = JSON.parse(fs.readFileSync(path.join(projectDir, "video-spec.json"), "utf8"));
const narrationDir = path.join(projectDir, "narration");
const narrationFiles = fs.readdirSync(narrationDir).filter((name) => name.endsWith(".txt")).sort();
if (narrationFiles.length !== 5 || spec.durationsMs.length !== 5) {
  throw new Error(`${spec.slug}: expected exactly five narration files and durations`);
}

const captions = narrationFiles.map((name) =>
  fs.readFileSync(path.join(narrationDir, name), "utf8").trim().replace(/<#\d+(?:\.\d+)?#>/g, "")
);
const captionChunks = captions.map((caption) => {
  const chunks = caption.match(/[^。！？；!?]+[。！？；!?]?/g)?.map((part) => part.trim()).filter(Boolean) || [caption];
  return chunks;
});
const audioFiles = narrationFiles.map((name) => `voice/${name.replace(/\.txt$/, ".mp3")}`);
const sceneDurations = spec.durationsMs.map((ms) => ms / 1000 + 0.55);
const starts = [];
let cursor = 0;
for (const duration of sceneDurations) {
  starts.push(Number(cursor.toFixed(3)));
  cursor += duration;
}
const totalDuration = Number(cursor.toFixed(3));

const esc = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const titleHtml = spec.titleLines.map((line) => `<span>${esc(line)}</span>`).join("");
const sectionLines = (lines, fallback) => (lines || fallback).map((line) => esc(line)).join("<br />");

const captionBand = (index) => `
  <div class="caption-band" data-layout-allow-caption-zone>
    <div class="avatar"><img data-layout-allow-overflow src="assets/ip.png" alt="了不起的小超人" /></div>
    <div class="caption-pages">${captionChunks[index].map((chunk, chunkIndex) => `<div id="caption-${index + 1}-${chunkIndex + 1}" class="caption-page">${esc(chunk)}</div>`).join("")}</div>
  </div>`;

const header = `
  <header class="topbar">
    <div class="series"><span class="series-mark">超</span>了不起的小超人 · ${esc(spec.seriesName || "开源装备雷达")}</div>
    <div class="issue">ISSUE ${esc(spec.issue)}<span>${esc(spec.category)}</span></div>
  </header>`;

const scenes = [
  `<section id="scene-1" class="clip scene" data-start="${starts[0]}" data-duration="${sceneDurations[0]}" data-track-index="1">
    <div class="scene-bg"></div><div class="grain"></div><div class="scene-inner hook-layout">
      ${header}
      <div class="hook-copy"><div class="category-chip">${esc(spec.chipText || spec.category + " · 今天只讲一个工具")}</div><h1>${titleHtml}</h1><p>${esc(spec.kicker)}</p></div>
      <div class="media-frame media-hero"><img src="${esc(spec.media[0])}" alt="${esc(spec.project)} 官方素材" /></div>
      <div class="corner-note">先看结果<br />再讲工具</div>
      ${captionBand(0)}
    </div><div class="platform-safe">下方预留平台信息</div>
  </section>`,
  `<section id="scene-2" class="clip scene" data-start="${starts[1]}" data-duration="${sceneDurations[1]}" data-track-index="1">
    <div class="scene-bg"></div><div class="grain"></div><div class="scene-inner evidence-layout">
      ${header}
      <div class="section-title"><span>02 / 里面到底有什么</span><h2>${sectionLines(spec.section2TitleLines, ["不是功能清单", "是可执行的生产资料"])}</h2></div>
      <div class="stats-stack">${spec.stats.map((s, i) => `<div class="stat stat-${i + 1}"><b>0${i + 1}</b><span>${esc(s)}</span></div>`).join("")}</div>
      <div class="media-frame evidence-media"><img src="${esc(spec.media[1])}" alt="${esc(spec.project)} 官方素材" /></div>
      ${captionBand(1)}
    </div><div class="platform-safe">下方预留平台信息</div>
  </section>`,
  `<section id="scene-3" class="clip scene" data-start="${starts[2]}" data-duration="${sceneDurations[2]}" data-track-index="1">
    <div class="scene-bg"></div><div class="grain"></div><div class="scene-inner flow-layout">
      ${header}
      <div class="section-title"><span>03 / 实际怎么跑</span><h2>${sectionLines(spec.section3TitleLines, ["一次输入", "拆成四个动作"])}</h2></div>
      <div class="flow-list">${spec.flow.map((s, i) => `<div class="flow-step"><b>${i + 1}</b><span>${esc(s)}</span>${i < spec.flow.length - 1 ? "<i>↓</i>" : ""}</div>`).join("")}</div>
      <div class="media-frame flow-media"><img src="${esc(spec.media[2])}" alt="${esc(spec.project)} 官方素材" /></div>
      ${captionBand(2)}
    </div><div class="platform-safe">下方预留平台信息</div>
  </section>`,
  `<section id="scene-4" class="clip scene" data-start="${starts[3]}" data-duration="${sceneDurations[3]}" data-track-index="1">
    <div class="scene-bg"></div><div class="grain"></div><div class="scene-inner limit-layout">
      ${header}
      <div class="warning-label">先知道限制，再决定安装</div>
      <h2 class="warning-title">它不替你<br />承担这些风险</h2>
      <div class="limit-list">${spec.limits.map((s) => `<div><span>!</span><p>${esc(s)}</p></div>`).join("")}</div>
      <div class="media-frame limit-media"><img src="${esc(spec.media[3])}" alt="${esc(spec.project)} 官方素材" /></div>
      ${captionBand(3)}
    </div><div class="platform-safe">下方预留平台信息</div>
  </section>`,
  `<section id="scene-5" class="clip scene" data-start="${starts[4]}" data-duration="${sceneDurations[4]}" data-track-index="1">
    <div class="scene-bg"></div><div class="grain"></div><div class="scene-inner verdict-layout">
      ${header}
      <div class="verdict-stamp">结论</div>
      <h2>${esc(spec.verdict)}</h2>
      <div class="score-card"><span>小超人核验分</span><strong>${esc(spec.score)}</strong><i>用途明确 · 限制透明 · 仍在维护</i></div>
      <div class="repo-card"><div class="repo-icon">&lt;/&gt;</div><div><b>${esc(spec.project)}</b><span>${esc(spec.repo)}</span></div></div>
      <div class="media-frame verdict-media"><img src="${esc(spec.media[4])}" alt="${esc(spec.project)} 官方素材" /></div>
      ${captionBand(4)}
    </div><div class="platform-safe">下方预留平台信息</div>
  </section>`
];

const audio = audioFiles.map((src, i) => `<audio id="voice-${i + 1}" src="${src}" data-start="${starts[i]}" data-duration="${spec.durationsMs[i] / 1000}" data-track-index="10" data-volume="1"></audio>`).join("\n");

const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1920" />
  <title>${esc(spec.project)}｜了不起的小超人</title>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    @font-face{font-family:"Xiaochao Sans";src:url("assets/Hiragino-Sans-GB.ttc") format("truetype")}@font-face{font-family:"Xiaochao Mono";src:url("assets/CobaltMono.ttf") format("truetype")}
    :root{--paper:#F6F0E4;--ink:#1B1916;--orange:#FF5A36;--orange-dark:#D94426;--lime:#B9F227;--yellow:#FFD45A;--gray:#D8CEBF}
    *{box-sizing:border-box}html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:var(--paper);color:var(--ink);font-family:"Xiaochao Sans",sans-serif}
    #${esc(spec.slug)}{position:relative;width:1080px;height:1920px;overflow:hidden}.clip{position:absolute;inset:0}.scene{overflow:hidden}.scene-bg{position:absolute;inset:0;background-color:var(--paper);background-image:radial-gradient(circle at 13% 12%,rgba(255,212,90,.27) 0 125px,transparent 127px),radial-gradient(circle at 94% 67%,rgba(185,242,39,.18) 0 190px,transparent 192px),repeating-linear-gradient(0deg,rgba(27,25,22,.025) 0 1px,transparent 1px 7px)}
    .grain{position:absolute;inset:0;opacity:.12;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.72' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.19'/%3E%3C/svg%3E")}
    .scene-inner{position:absolute;inset:0;padding:70px 64px 320px}.topbar{height:116px;display:flex;align-items:flex-start;justify-content:space-between;border-top:5px solid var(--ink);padding-top:20px}.series{display:flex;align-items:center;gap:14px;font-size:29px;font-weight:950}.series-mark{width:42px;height:42px;border:4px solid var(--ink);border-radius:50%;display:grid;place-items:center;background:var(--orange);box-shadow:5px 5px 0 var(--ink);font-size:22px}.issue{font-family:"Xiaochao Mono",monospace;font-size:22px;font-weight:900;text-align:right;line-height:1.3}.issue span{display:block}.category-chip,.warning-label{width:max-content;padding:12px 22px;border:4px solid var(--ink);background:var(--lime);box-shadow:7px 7px 0 var(--ink);font-size:24px;font-weight:950;transform:rotate(-2deg)}
    h1,h2,p{margin:0}h1{margin-top:28px;font-size:80px;line-height:1.35;letter-spacing:-.055em;font-weight:1000}h1 span{display:block}h1 span:last-child{color:var(--orange-dark)}.hook-copy p{margin-top:12px;max-width:760px;font-size:32px;line-height:1.2;font-weight:850}.media-frame{overflow:hidden;border:5px solid var(--ink);background:#26231f;box-shadow:13px 13px 0 var(--orange)}.media-frame img{display:block;width:100%;height:100%;object-fit:contain;background:#f7f4ed}.media-hero{position:absolute;left:64px;right:64px;top:610px;height:690px;border-radius:22px 22px 55px 22px}.corner-note{position:absolute;right:66px;top:530px;padding:17px 19px;border:4px solid var(--ink);background:var(--yellow);box-shadow:8px 8px 0 var(--ink);font-size:25px;line-height:1.25;font-weight:950;transform:rotate(3deg)}
    .caption-band{position:absolute;left:64px;right:164px;top:1380px;height:220px;display:grid;grid-template-columns:145px 1fr;gap:28px;align-items:center;border-top:5px solid var(--ink);padding-top:20px}.avatar{width:138px;height:138px;overflow:hidden;border:5px solid var(--ink);border-radius:50%;background:var(--yellow);box-shadow:9px 9px 0 var(--lime)}.avatar img{display:block;width:100%;height:100%;object-fit:cover;object-position:50% 50%;margin:0;transform:none}.caption-pages{position:relative;width:100%;height:180px}.caption-page{position:absolute;inset:0;display:flex;align-items:center;opacity:0;font-size:38px;line-height:1.28;font-weight:950;letter-spacing:-.025em}.platform-safe{position:absolute;left:64px;right:64px;bottom:252px;border-top:3px dashed rgba(27,25,22,.42);padding-top:14px;text-align:right;color:rgb(108,105,99);font-family:"Xiaochao Mono",monospace;font-size:17px;font-weight:850}
    .section-title{position:absolute;left:64px;top:215px}.section-title>span{display:inline-block;padding:9px 14px;background:var(--ink);color:var(--paper);font-family:"Xiaochao Mono",monospace;font-size:20px;font-weight:900}.section-title h2{margin-top:23px;font-size:70px;line-height:1.02;letter-spacing:-.045em;font-weight:1000}.stats-stack{position:absolute;left:64px;top:520px;width:500px;display:grid;gap:20px}.stat{height:125px;display:flex;align-items:center;gap:22px;padding:0 26px;border:4px solid var(--ink);font-size:31px;font-weight:950;box-shadow:9px 9px 0 var(--ink)}.stat b{font-family:"Xiaochao Mono",monospace;font-size:25px}.stat-1{background:var(--lime)}.stat-2{background:var(--yellow);margin-left:35px}.stat-3{background:var(--orange);margin-left:10px}.evidence-media{position:absolute;right:64px;top:540px;width:390px;height:610px;border-radius:20px}.evidence-media img{object-fit:cover}.flow-list{position:absolute;left:64px;top:535px;width:510px}.flow-step{position:relative;height:128px;display:grid;grid-template-columns:70px 1fr;align-items:center;border-bottom:4px solid var(--ink);font-size:31px;font-weight:950}.flow-step b{width:54px;height:54px;display:grid;place-items:center;border:4px solid var(--ink);border-radius:50%;background:var(--lime);font-family:"Xiaochao Mono",monospace}.flow-step i{position:absolute;right:8px;bottom:-23px;width:43px;height:43px;border:3px solid var(--ink);border-radius:50%;display:grid;place-items:center;background:var(--yellow);font-style:normal;z-index:2}.flow-media{position:absolute;right:64px;top:555px;width:380px;height:560px;border-radius:20px}.flow-media img{object-fit:cover}.warning-label{position:absolute;left:64px;top:230px;background:var(--yellow)}.warning-title{position:absolute;left:64px;top:330px;width:740px;font-size:80px;line-height:1;letter-spacing:-.05em;font-weight:1000}.limit-list{position:absolute;left:64px;top:620px;width:610px;display:grid;gap:22px}.limit-list>div{min-height:128px;display:grid;grid-template-columns:72px 1fr;gap:18px;align-items:center;padding:18px 24px;border:4px solid var(--ink);background:var(--paper);box-shadow:9px 9px 0 var(--orange)}.limit-list span{width:55px;height:55px;display:grid;place-items:center;border:4px solid var(--ink);border-radius:50%;background:var(--orange);font-family:"Xiaochao Mono",monospace;font-size:30px;font-weight:1000}.limit-list p{font-size:30px;line-height:1.2;font-weight:900}.limit-media{position:absolute;right:64px;top:745px;width:260px;height:370px;border-radius:18px;transform:rotate(3deg)}.limit-media img{object-fit:cover}.verdict-stamp{position:absolute;left:64px;top:230px;width:130px;height:130px;border:7px solid var(--orange-dark);border-radius:50%;display:grid;place-items:center;color:var(--orange-dark);font-size:36px;font-weight:1000;transform:rotate(-11deg)}.verdict-layout h2{position:absolute;left:230px;right:64px;top:245px;font-size:74px;line-height:1.02;letter-spacing:-.045em;font-weight:1000}.score-card{position:absolute;left:64px;top:500px;width:560px;height:335px;padding:34px;border:5px solid var(--ink);background:var(--lime);box-shadow:13px 13px 0 var(--ink);display:flex;flex-direction:column}.score-card span{font-size:27px;font-weight:900}.score-card strong{margin-top:12px;font-family:"Xiaochao Mono",monospace;font-size:92px;line-height:1;font-weight:1000}.score-card i{margin-top:auto;padding-top:22px;border-top:4px solid var(--ink);font-size:23px;font-style:normal;font-weight:850}.verdict-media{position:absolute;right:64px;top:560px;width:320px;height:440px;border-radius:20px}.verdict-media img{object-fit:cover}.repo-card{position:absolute;left:64px;right:64px;top:1040px;height:150px;border:5px solid var(--ink);border-radius:18px;background:var(--yellow);display:flex;align-items:center;gap:24px;padding:0 30px;box-shadow:11px 11px 0 var(--orange)}.repo-icon{width:70px;height:70px;border-radius:50%;display:grid;place-items:center;background:var(--ink);color:var(--paper);font-family:"Xiaochao Mono",monospace;font-size:26px}.repo-card b{display:block;font-size:31px}.repo-card span{display:block;margin-top:7px;font-family:"Xiaochao Mono",monospace;font-size:20px}
  </style>
</head>
<body>
  <div id="${esc(spec.slug)}" data-composition-id="${esc(spec.slug)}" data-start="0" data-width="1080" data-height="1920" data-duration="${totalDuration}">
    ${scenes.join("\n")}
    ${audio}
  </div>
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({paused:true});
    const starts = ${JSON.stringify(starts)};
    const durations = ${JSON.stringify(sceneDurations)};
    const captionChunks = ${JSON.stringify(captionChunks.map((chunks) => chunks.length))};
    starts.forEach((start,index)=>{
      const id = '#scene-' + (index + 1);
      if(index===0){
        tl.set(id + ' .scene-inner',{opacity:1,y:0},0);
      }else{
        tl.fromTo(id + ' .scene-inner',{opacity:0,y:45},{opacity:1,y:0,duration:.5,ease:'power4.out'},start+.05);
      }
      tl.fromTo(id + ' .topbar',{opacity:0,x:-25},{opacity:1,x:0,duration:.38,ease:'power3.out'},start+.12);
      tl.fromTo(id + ' .caption-band',{opacity:0,x:35},{opacity:1,x:0,duration:.4,ease:'power3.out'},start+.26);
      const media = document.querySelector(id + ' .media-frame img');
      if(media){const zoomIn = index % 2 === 0; tl.fromTo(media,{scale:zoomIn?1.0:1.12},{scale:zoomIn?1.12:1.0,duration:Math.max(1,durations[index]-.2),ease:'none'},start+.1);}
      if(index===0){
        tl.fromTo(id + ' h1 span',{scale:.82,opacity:0,y:18},{scale:1,opacity:1,y:0,duration:.5,ease:'back.out(1.8)',stagger:.12},.08);
        tl.fromTo(id + ' .hook-copy p',{opacity:0,y:14},{opacity:1,y:0,duration:.35,ease:'power2.out'},.62);
        tl.fromTo(id + ' .corner-note',{opacity:0,scale:.6,rotation:3},{opacity:1,scale:1,rotation:3,duration:.45,ease:'back.out(2)'},.78);
      }
      // 场景内卡片逐个弹入：stats / flow / limit 条目（节奏抓手，0.7s 一个）
      const cardGroups = [
        id + ' .stats-stack > .stat',
        id + ' .flow-list > .flow-step',
        id + ' .limit-list > div'
      ];
      let cardCursor = start + .5;
      for (const sel of cardGroups) {
        const cards = Array.from(document.querySelectorAll(sel));
        if (cards.length === 0) continue;
        const stepDur = Math.min(.72, Math.max(.42, (durations[index]-.9)/cards.length));
        for (const card of cards) {
          tl.fromTo(card,{opacity:0,y:26,scale:.96},{opacity:1,y:0,scale:1,duration:.4,ease:'back.out(1.6)'},cardCursor);
          cardCursor += stepDur;
        }
      }
      // 字幕：上滑+弹出入场（替代原地淡入），跟语音 chunk 走
      const chunkDuration = Math.max(.9,(durations[index]-.55)/captionChunks[index]);
      for(let chunkIndex=0;chunkIndex<captionChunks[index];chunkIndex+=1){
        const captionId = '#caption-' + (index+1) + '-' + (chunkIndex+1);
        const chunkStart = start + .22 + chunkIndex*chunkDuration;
        tl.fromTo(captionId,{opacity:0,y:16,scale:.97},{opacity:1,y:0,scale:1,duration:.26,ease:'power2.out'},chunkStart);
        tl.to(captionId,{opacity:0,y:-10,duration:.2,ease:'power2.in'},Math.min(start+durations[index]-.05,chunkStart+chunkDuration-.22));
      }
    });
    window.__timelines['${esc(spec.slug)}'] = tl;
  </script>
</body>
</html>`;

fs.writeFileSync(path.join(projectDir, "index.html"), html);
fs.writeFileSync(path.join(projectDir, "hyperframes.json"), JSON.stringify({
  $schema: "https://hyperframes.heygen.com/schema/hyperframes.json",
  registry: "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
  paths: {blocks: "compositions", components: "compositions/components", assets: "assets"},
  media: {autoProxy: true},
  authoringSkill: "general-video"
}, null, 2));
fs.writeFileSync(path.join(projectDir, "frame.md"), `---\ncanvas: "#F6F0E4"\nink: "#1B1916"\naccent: "#FF5A36"\nresult: "#B9F227"\nsupport: "#FFD45A"\n---\n\n# 开源装备实验室\n\n暖米白、橙红、酸橙绿。底部固定预留 320px 平台安全区。\n`);
fs.writeFileSync(path.join(projectDir, "index.motion.json"), JSON.stringify({
  duration: totalDuration,
  assertions: [
    {kind: "appearsBy", selector: "#scene-1 h1", bySec: 1},
    {kind: "staysInFrame", selector: "#scene-1 .caption-band"},
    {kind: "keepsMoving", withinSelector: `#${spec.slug}`, maxStaticSec: 18}
  ]
}, null, 2));

console.log(JSON.stringify({projectDir, totalDuration, starts, sceneDurations}));
