#!/usr/bin/env node
// 小超人 · 苹果设计风 build 脚本（行业 × AI）
// 用法：node scripts/build_xiaochao_video_apple.mjs <episode-dir>
// 依赖：narration/*.txt（5 段）、video-spec.json、assets/{ip.png,Hiragino-Sans-GB.ttc,gsap-3.14.2.min.js}

import fs from "node:fs";
import path from "node:path";

const projectDir = path.resolve(process.argv[2] || "");
if (!projectDir || !fs.existsSync(projectDir)) {
  throw new Error("Usage: node scripts/build_xiaochao_video_apple.mjs <episode-dir>");
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

const header = `
  <div class="top">
    <div class="brand"><i>超</i> 了不起的小超人 · ${esc(spec.seriesName || "行业雷达")}</div>
    <div class="issue">ISSUE ${esc(spec.issue)} / ${esc(spec.category)}</div>
  </div>`;

const captionBand = (index) => `
  <div class="caption-band">
    <div class="av"><img src="assets/ip.png" alt="了不起的小超人" /></div>
    <div class="caption-pages">${captionChunks[index].map((chunk, chunkIndex) => `<div id="cap-${index + 1}-${chunkIndex + 1}" class="caption-page">${esc(chunk)}</div>`).join("")}</div>
  </div>`;

// 场景 2 的 before/after 对比卡（用官方真实图）
const compareCard = `
  <div class="compare">
    <div class="c-item"><div class="c-img"><img src="assets/car-1.jpg" alt="原图" /></div><span class="c-label">原图</span></div>
    <div class="c-arrow">→</div>
    <div class="c-item"><div class="c-img"><img src="assets/car-1.out.png" alt="抠图后" /></div><span class="c-label">一键白底图</span></div>
  </div>`;

const scenes = [
  // 1 钩子：标题 + 商品图
  `<section id="scene-1" class="clip scene" data-start="${starts[0]}" data-duration="${sceneDurations[0]}" data-track-index="1">
    ${header}
    <div class="chip">${esc(spec.chipText || spec.category)}</div>
    <div class="title"><h1>${spec.titleLines.map((l) => `<span>${esc(l)}</span>`).join("")}</h1><p class="kicker">${esc(spec.kicker)}</p></div>
    <div class="imgwrap"><div class="imgcard"><img src="${esc(spec.media[0])}" alt="示例" /></div></div>
    ${captionBand(0)}
    <div class="safe">标题与平台信息区</div>
  </section>`,
  // 2 三工具：三个工具卡
  `<section id="scene-2" class="clip scene" data-start="${starts[1]}" data-duration="${sceneDurations[1]}" data-track-index="1">
    ${header}
    <div class="sec-label">02 / 3 个免费工具</div>
    <h2 class="sec-title">${(spec.section2TitleLines || ["3 个免费工具", "对号入座"]).map((l) => `<span>${esc(l)}</span>`).join("")}</h2>
    <div class="toolgrid">${spec.stats.map((s, i) => `<div class="tool-card"><b>0${i + 1}</b><h3>${esc(s.split("·")[0])}</h3><p>${esc(s.split("·")[1] || "")}</p></div>`).join("")}</div>
    ${captionBand(1)}
    <div class="safe">标题与平台信息区</div>
  </section>`,
  // 3 用法：流程卡
  `<section id="scene-3" class="clip scene" data-start="${starts[2]}" data-duration="${sceneDurations[2]}" data-track-index="1">
    ${header}
    <div class="sec-label">03 / 实际怎么用</div>
    <h2 class="sec-title">${(spec.section3TitleLines || ["三条路", "对号入座"]).map((l) => `<span>${esc(l)}</span>`).join("")}</h2>
    <div class="flow">${spec.flow.map((s, i) => `<div class="f-step"><b>${i + 1}</b><span>${esc(s)}</span></div>`).join("")}</div>
    ${captionBand(2)}
    <div class="safe">标题与平台信息区</div>
  </section>`,
  // 4 限制
  `<section id="scene-4" class="clip scene" data-start="${starts[3]}" data-duration="${sceneDurations[3]}" data-track-index="1">
    ${header}
    <div class="sec-label warn">04 / 先知道限制</div>
    <h2 class="sec-title">它不替你<br/><span>背这些风险</span></h2>
    <div class="limits">${spec.limits.map((s) => `<div class="l-item"><span>!</span><p>${esc(s)}</p></div>`).join("")}</div>
    ${captionBand(3)}
    <div class="safe">标题与平台信息区</div>
  </section>`,
  // 5 结尾：结论
  `<section id="scene-5" class="clip scene" data-start="${starts[4]}" data-duration="${sceneDurations[4]}" data-track-index="1">
    ${header}
    <div class="verdict-wrap">
      <div class="verdict-badge">结论</div>
      <h2 class="verdict-title">${esc(spec.verdict)}</h2>
      <div class="verdict-card"><span>小超人核验分</span><strong>${esc(spec.score)}</strong><i>用途明确 · 限制透明 · 持续维护</i></div>
      <div class="repo-card"><b>${esc(spec.project)}</b><span>${esc(spec.repo)}</span></div>
    </div>
    ${captionBand(4)}
    <div class="safe">标题与平台信息区</div>
  </section>`
];

const audio = audioFiles.map((src, i) => `<audio id="voice-${i + 1}" src="${src}" data-start="${starts[i]}" data-duration="${spec.durationsMs[i] / 1000}" data-track-index="10" data-volume="1"></audio>`).join("\n");

const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1920" />
  <title>${esc(spec.project)}｜了不起的小超人</title>
  <script src="assets/gsap-3.14.2.min.js"></script>
  <style>
    @font-face{font-family:"SC";src:url("assets/Hiragino-Sans-GB.ttc") format("truetype")}
    *{box-sizing:border-box}html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000;color:#fff;font-family:"SC",sans-serif}
    #${esc(spec.slug)}{position:relative;width:1080px;height:1920px;overflow:hidden}
    .clip{position:absolute;inset:0}.scene{overflow:hidden}
    /* 极光背景 */
    .aurora{position:absolute;inset:0;overflow:hidden;background:radial-gradient(80% 60% at 15% 8%,rgba(255,94,58,.20) 0%,transparent 55%),radial-gradient(70% 50% at 88% 22%,rgba(90,200,250,.14) 0%,transparent 55%),radial-gradient(90% 70% at 50% 85%,rgba(120,90,255,.18) 0%,transparent 60%),#000}
    .blob{position:absolute;border-radius:50%;filter:blur(110px);opacity:.4;will-change:transform}
    .b1{width:600px;height:600px;left:-160px;top:-120px;background:radial-gradient(circle,#FF5E3A,transparent 70%)}
    .b2{width:660px;height:660px;right:-200px;top:320px;background:radial-gradient(circle,#5AC8FA,transparent 70%)}
    .b3{width:520px;height:520px;left:6%;bottom:-180px;background:radial-gradient(circle,#785AFF,transparent 70%)}
    .vignette{position:absolute;inset:0;background:radial-gradient(120% 100% at 50% 40%,transparent 50%,rgba(0,0,0,.65) 100%)}
    /* 顶部 */
    .top{position:absolute;left:64px;right:64px;top:64px;display:flex;justify-content:space-between;align-items:center}
    .brand{font-size:26px;font-weight:700;color:rgba(255,255,255,.85);letter-spacing:.02em}.brand i{color:#FF5E3A;font-style:normal;font-weight:900}
    .issue{font-size:20px;color:rgba(255,255,255,.5);font-weight:600;letter-spacing:.06em}
    /* 毛玻璃药丸标签 */
    .chip{position:absolute;left:64px;top:150px;padding:14px 28px;border-radius:999px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);color:rgba(255,255,255,.92);font-size:24px;font-weight:700;letter-spacing:.02em}
    /* 标题 */
    .title{position:absolute;left:60px;right:60px;top:210px}
    h1{margin:0;font-size:104px;line-height:1.06;letter-spacing:-.035em;font-weight:700}h1 span{display:block}h1 span:last-child{background:linear-gradient(90deg,#FF5E3A,#FF9A3D);-webkit-background-clip:text;background-clip:text;color:transparent}
    .kicker{margin-top:20px;font-size:34px;line-height:1.4;font-weight:600;color:rgba(255,255,255,.75)}
    /* 图片卡 */
    .imgwrap{position:absolute;left:56px;right:56px;top:780px;bottom:400px;display:flex;align-items:center;justify-content:center}
    .imgwrap.small{top:700px;bottom:300px}
    .imgcard{width:100%;max-height:100%;border-radius:32px;overflow:hidden;background:#111;box-shadow:0 40px 100px rgba(0,0,0,.6)}
    .imgcard img{display:block;width:100%;height:100%;object-fit:contain;background:#111}
    /* 字幕条（毛玻璃） */
    .caption-band{position:absolute;left:56px;right:56px;bottom:250px;display:flex;align-items:center;gap:24px;padding:22px 28px;border-radius:24px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);min-height:120px}
    .av{width:76px;height:76px;border-radius:50%;overflow:hidden;flex-shrink:0;border:1.5px solid rgba(255,255,255,.25)}.av img{width:100%;height:100%;object-fit:cover}
    .caption-pages{position:relative;flex:1;height:88px}.caption-page{position:absolute;inset:0;display:flex;align-items:center;opacity:0;font-size:30px;line-height:1.3;font-weight:600;color:rgba(255,255,255,.88)}
    /* 安全区 */
    .safe{position:absolute;left:120px;right:120px;bottom:110px;display:flex;justify-content:center;border-top:2px dashed rgba(255,255,255,.12);padding-top:18px;color:rgba(255,255,255,.25);font-size:20px;font-weight:600;letter-spacing:.12em}
    /* 场景2：数据卡 + 对比 */
    .sec-label{position:absolute;left:64px;top:170px;font-size:22px;font-weight:700;color:rgba(255,255,255,.45);letter-spacing:.14em}
    .sec-label.warn{color:#FF9A3D}
    .sec-title{position:absolute;left:60px;right:60px;top:220px;margin:0;font-size:78px;line-height:1.12;letter-spacing:-.03em;font-weight:700}.sec-title span{display:block;background:linear-gradient(90deg,#FF5E3A,#FF9A3D);-webkit-background-clip:text;background-clip:text;color:transparent}
    /* 三工具卡 */
    .toolgrid{position:absolute;left:56px;right:56px;top:520px;display:grid;gap:26px}
    .tool-card{display:flex;align-items:center;gap:26px;padding:30px 34px;border-radius:26px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(28px);-webkit-backdrop-filter:blur(28px)}
    .tool-card b{width:60px;height:60px;display:grid;place-items:center;border-radius:18px;background:rgba(255,94,58,.18);color:#FF9A6D;font-size:28px;font-weight:800;flex-shrink:0}
    .tool-card h3{margin:0;font-size:36px;font-weight:700;color:rgba(255,255,255,.92)}
    .tool-card p{margin:4px 0 0;font-size:26px;font-weight:600;color:rgba(255,255,255,.6)}
    .stat{display:flex;align-items:center;gap:20px;padding:22px 26px;border-radius:20px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px)}
    .stat b{width:52px;height:52px;display:grid;place-items:center;border-radius:14px;background:rgba(255,94,58,.18);color:#FF9A6D;font-size:24px;font-weight:800;flex-shrink:0}
    .stat span{font-size:30px;font-weight:700;color:rgba(255,255,255,.9)}
    .compare{position:absolute;right:56px;top:520px;width:420px;display:flex;align-items:center;gap:12px}
    .c-item{flex:1;text-align:center}.c-img{height:430px;border-radius:24px;overflow:hidden;background:#111;border:1px solid rgba(255,255,255,.15)}.c-img img{width:100%;height:100%;object-fit:contain;background:#111}
    .c-label{display:block;margin-top:14px;font-size:22px;font-weight:600;color:rgba(255,255,255,.65)}
    .c-arrow{font-size:40px;color:#FF9A3D;font-weight:800;flex-shrink:0}
    /* 场景3：流程 */
    .flow{position:absolute;left:56px;right:56px;top:560px;display:grid;gap:22px}
    .f-step{display:flex;align-items:center;gap:22px;padding:26px 30px;border-radius:22px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px)}
    .f-step b{width:56px;height:56px;display:grid;place-items:center;border-radius:50%;background:rgba(90,200,250,.18);color:#7FD4FF;font-size:26px;font-weight:800;flex-shrink:0}
    .f-step span{font-size:30px;font-weight:700;color:rgba(255,255,255,.9)}
    /* 场景4：限制 */
    .limits{position:absolute;left:56px;right:56px;top:560px;display:grid;gap:22px}
    .l-item{display:flex;align-items:flex-start;gap:22px;padding:24px 28px;border-radius:22px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px)}
    .l-item span{width:52px;height:52px;display:grid;place-items:center;border-radius:50%;background:rgba(255,154,61,.16);color:#FFB27D;font-size:28px;font-weight:900;flex-shrink:0}
    .l-item p{margin:0;font-size:29px;line-height:1.35;font-weight:600;color:rgba(255,255,255,.88)}
    /* 场景5：结论 */
    .verdict-wrap{position:absolute;left:56px;right:56px;top:170px;text-align:center}
    .verdict-badge{display:inline-block;padding:12px 28px;border-radius:999px;background:rgba(255,94,58,.16);border:1px solid rgba(255,94,58,.4);color:#FF9A6D;font-size:24px;font-weight:800;letter-spacing:.1em}
    .verdict-title{margin:28px 0 0;font-size:52px;line-height:1.3;letter-spacing:-.02em;font-weight:700;color:rgba(255,255,255,.92)}
    .verdict-card{margin:30px auto 0;width:500px;padding:26px;border-radius:28px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(28px);-webkit-backdrop-filter:blur(28px)}
    .verdict-card span{font-size:24px;font-weight:600;color:rgba(255,255,255,.55)}
    .verdict-card strong{display:block;margin-top:8px;font-size:76px;line-height:1;font-weight:800;background:linear-gradient(90deg,#FF5E3A,#FF9A3D);-webkit-background-clip:text;background-clip:text;color:transparent}
    .verdict-card i{margin-top:16px;display:block;padding-top:16px;border-top:1px solid rgba(255,255,255,.12);font-size:22px;font-style:normal;font-weight:600;color:rgba(255,255,255,.6)}
    .repo-card{margin:24px auto 0;width:500px;padding:20px 28px;border-radius:20px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12)}
    .repo-card b{display:block;font-size:28px;font-weight:700;color:rgba(255,255,255,.9)}
    .repo-card span{display:block;margin-top:6px;font-size:20px;color:rgba(255,255,255,.5)}
  </style>
</head>
<body>
  <div id="${esc(spec.slug)}" data-composition-id="${esc(spec.slug)}" data-start="0" data-width="1080" data-height="1920" data-duration="${totalDuration}">
    <div class="aurora">
      <div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div>
    </div>
    <div class="vignette"></div>
    ${scenes.join("\n")}
    ${audio}
  </div>
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({paused:true});
    const starts = ${JSON.stringify(starts)};
    const durations = ${JSON.stringify(sceneDurations)};
    const captionChunks = ${JSON.stringify(captionChunks.map((chunks) => chunks.length))};
    // 极光漂移（全片持续）
    tl.fromTo(".b1",{x:-60,y:-40},{x:80,y:60,duration:${totalDuration},ease:"sine.inOut"},0);
    tl.fromTo(".b2",{x:60,y:-50},{x:-70,y:70,duration:${totalDuration},ease:"sine.inOut"},0);
    tl.fromTo(".b3",{x:0,y:60},{x:-50,y:-40,duration:${totalDuration},ease:"sine.inOut"},0);
    starts.forEach((start,index)=>{
      const id = '#scene-' + (index + 1);
      if(index===0){tl.set(id,{opacity:1},0);}else{tl.fromTo(id,{opacity:0},{opacity:1,duration:.3,ease:'power2.out'},start+.05);}
      tl.fromTo(id + ' .top',{opacity:0,y:-20},{opacity:1,y:0,duration:.4,ease:'power3.out'},start+.1);
      if(index===0){
        tl.fromTo(id + ' .title h1 span',{y:50,opacity:0},{y:0,opacity:1,duration:.5,ease:'power3.out',stagger:.12},start+.2);
        tl.fromTo(id + ' .kicker',{y:24,opacity:0},{y:0,opacity:1,duration:.4,ease:'power2.out'},start+.75);
        tl.fromTo(id + ' .chip',{opacity:0,scale:.85},{opacity:1,scale:1,duration:.45,ease:'back.out(1.6)'},start+.95);
        tl.fromTo(id + ' .imgcard',{opacity:0,y:50,scale:.97},{opacity:1,y:0,scale:1,duration:.55,ease:'power3.out'},start+1.15);
      }else{
        tl.fromTo(id + ' .sec-label',{opacity:0,y:16},{opacity:1,y:0,duration:.4,ease:'power2.out'},start+.15);
        tl.fromTo(id + ' .sec-title span',{y:30,opacity:0},{y:0,opacity:1,duration:.45,ease:'power3.out',stagger:.1},start+.3);
        // 卡片逐个弹入
        const groups = [id+' .stat', id+' .f-step', id+' .l-item'];
        let cCursor = start + .55;
        for (const sel of groups) {
          const cards = Array.from(document.querySelectorAll(sel));
          if (!cards.length) continue;
          const step = Math.min(.7, Math.max(.45,(durations[index]-1)/cards.length));
          for (const card of cards) {
            tl.fromTo(card,{opacity:0,y:26,scale:.96},{opacity:1,y:0,scale:1,duration:.4,ease:'back.out(1.6)'},cCursor);
            cCursor += step;
          }
        }
        tl.fromTo(id + ' .compare',{opacity:0,y:30},{opacity:1,y:0,duration:.5,ease:'power3.out'},start+.7);
        tl.fromTo(id + ' .verdict-wrap',{opacity:0,y:30},{opacity:1,y:0,duration:.5,ease:'power3.out'},start+.4);
        tl.fromTo(id + ' .imgwrap.small',{opacity:0,y:30},{opacity:1,y:0,duration:.5,ease:'power3.out'},start+.9);
      }
      // 字幕
      const chunkDuration = Math.max(.9,(durations[index]-.55)/captionChunks[index]);
      for(let ci=0;ci<captionChunks[index];ci+=1){
        const capId = '#cap-' + (index+1) + '-' + (ci+1);
        const capStart = start + .25 + ci*chunkDuration;
        tl.fromTo(capId,{opacity:0,y:14,scale:.98},{opacity:1,y:0,scale:1,duration:.24,ease:'power2.out'},capStart);
        tl.to(capId,{opacity:0,y:-8,duration:.18,ease:'power2.in'},Math.min(start+durations[index]-.05,capStart+chunkDuration-.2));
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
fs.writeFileSync(path.join(projectDir, "frame.md"), `---\ncanvas: "#000000"\nink: "#FFFFFF"\naccent: "#FF5E3A"\nresult: "#5AC8FA"\nsupport: "#785AFF"\n---\n\n# 苹果设计风（行业 × AI）\n\n深黑底、极光光斑、毛玻璃卡片、大圆角、渐变强调色。底部预留 300px 平台安全区。\n`);
fs.writeFileSync(path.join(projectDir, "index.motion.json"), JSON.stringify({
  duration: totalDuration,
  assertions: [
    {kind: "appearsBy", selector: "#scene-1 h1", bySec: 1.5},
    {kind: "staysInFrame", selector: "#scene-1 .caption-band"},
    {kind: "keepsMoving", withinSelector: `#${spec.slug}`, maxStaticSec: 15}
  ]
}, null, 2));

console.log(JSON.stringify({projectDir, totalDuration, starts, sceneDurations}));
