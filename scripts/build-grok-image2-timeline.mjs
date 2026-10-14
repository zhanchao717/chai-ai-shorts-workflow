#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const project = path.resolve("videos/grok-image-2-editing");
const durations = [7.272, 10.512, 12.06, 8.46, 9.252];
const starts = durations.map((_, index) => durations.slice(0, index).reduce((sum, value) => sum + value, 0));
const total = durations.reduce((sum, value) => sum + value, 0);
const phrasePlan = [
  [
    "别被“全球第二”带跑偏。",
    "Imagine Image 2.0值得看的是：",
    "改一处，别处能不能稳住。",
  ],
  [
    "8月7日，xAI把它上线Grok网页和手机端。",
    "工具包括局部魔法棒、",
    "分区选择、去背景、",
    "五图参考和智能扩图。",
  ],
  [
    "它把“整张重抽”变成",
    "“只改设计稿的一层”：",
    "换商品颜色，",
    "尽量保住主体、构图和文字。",
    "做封面、电商图，",
    "比偶尔出神图更实用。",
  ],
  [
    "但第二名仍是初步结果，",
    "票数也少；",
    "xAI的API尚未开放，",
    "没承诺大陆可用或本地支付。",
  ],
  [
    "柴主编的判断：",
    "能用Grok，",
    "就拿同一张图连改三次，",
    "检查主体和中文字；",
    "其他人别为排名订阅。",
  ],
];

const normalize = (value) => value.replace(/\s+/g, "");
const isPunctuation = (value) => /^[\s，。；：、“”‘’！？,.!?:;()（）\-]+$/u.test(value);

const voices = [];
const allWords = [];
const groups = [];
const speechWords = [];

for (let segmentIndex = 0; segmentIndex < durations.length; segmentIndex += 1) {
  const id = String(segmentIndex + 1).padStart(2, "0");
  const subtitlePath = path.join(project, "assets", "voice", `${id}-words.json`);
  const payload = JSON.parse(fs.readFileSync(subtitlePath, "utf8"));
  const segment = payload[0];
  const collapsedEntries = [];
  for (const entry of segment.timestamped_words) {
    const previous = collapsedEntries.at(-1);
    if (previous && previous.word_begin === entry.word_begin && previous.word_end === entry.word_end) {
      previous.time_end = entry.time_end;
      continue;
    }
    collapsedEntries.push({ ...entry });
  }
  const words = collapsedEntries.map((entry, wordIndex) => ({
    id: `w${segmentIndex}-${wordIndex}`,
    text: entry.word,
    start: starts[segmentIndex] + entry.time_begin / 1000,
    end: starts[segmentIndex] + entry.time_end / 1000,
    local_start: entry.time_begin / 1000,
    local_end: entry.time_end / 1000,
  }));
  voices.push({
    id,
    path: `assets/voice/${id}.mp3`,
    duration_s: durations[segmentIndex],
    words,
  });
  allWords.push(...words);
  speechWords.push(...words.filter((entry) => !isPunctuation(entry.text)));

  let cursor = 0;
  for (const phrase of phrasePlan[segmentIndex]) {
    const target = normalize(phrase);
    const phraseWords = [];
    let assembled = "";
    while (cursor < words.length && normalize(assembled).length < target.length) {
      phraseWords.push(words[cursor]);
      assembled += words[cursor].text;
      cursor += 1;
    }
    if (normalize(assembled) !== target) {
      throw new Error(`Phrase mismatch in segment ${id}: expected ${target}, got ${normalize(assembled)}`);
    }
    const compact = [];
    for (const word of phraseWords) {
      if (isPunctuation(word.text) && compact.length) {
        compact[compact.length - 1].text += word.text;
        compact[compact.length - 1].end = word.end;
      } else {
        compact.push({ ...word });
      }
    }
    const groupIndex = groups.length;
    groups.push({
      id: `caption-group-${groupIndex}`,
      frame: segmentIndex + 1,
      start: phraseWords[0].start,
      end: phraseWords.at(-1).end + 0.12,
      text: phrase,
      words: compact.map((word, index) => ({
        id: `caption-word-${groupIndex}-${index}`,
        text: word.text,
        start: word.start,
        end: word.end,
      })),
    });
  }
  if (cursor !== words.length) {
    throw new Error(`Unused MiniMax word timings in segment ${id}: ${words.length - cursor}`);
  }
}

const speechWindows = [];
for (const word of speechWords) {
  const previous = speechWindows.at(-1);
  if (previous && word.start - previous[1] <= 0.045) {
    previous[1] = Math.max(previous[1], word.end);
  } else {
    speechWindows.push([word.start, word.end]);
  }
}

fs.writeFileSync(
  path.join(project, "audio_meta.json"),
  `${JSON.stringify({
    provider: "minimax",
    model: "speech-2.8-hd",
    voice_id: "male-qn-qingse",
    total_duration_s: total,
    voices,
    bgm: null,
    sfx: [],
  }, null, 2)}\n`,
);
fs.writeFileSync(
  path.join(project, "word_timeline.json"),
  `${JSON.stringify({ total_duration_s: total, words: allWords, speech_windows: speechWindows }, null, 2)}\n`,
);
fs.writeFileSync(
  path.join(project, "sentence_timeline.json"),
  `${JSON.stringify({ total_duration_s: total, sentences: groups.map(({ id, frame, start, end, text }) => ({ id, frame, start, end, text })) }, null, 2)}\n`,
);
fs.writeFileSync(
  path.join(project, "caption_groups.json"),
  `${JSON.stringify({ total_duration_s: total, width: 1080, height: 1920, groups }, null, 2)}\n`,
);

const qwenCaptions = path.resolve("videos/qwen38-max-explained/compositions/captions.html");
let captions = fs.readFileSync(qwenCaptions, "utf8");
captions = captions.replaceAll("53.172", total.toFixed(3));
captions = captions.replace(/var GROUPS = \[[\s\S]*?\];\n  var DURATION = [\d.]+;/, `var GROUPS = ${JSON.stringify(groups)};\n  var DURATION = ${total.toFixed(3)};`);
fs.mkdirSync(path.join(project, "compositions"), { recursive: true });
fs.writeFileSync(path.join(project, "compositions", "captions.html"), captions);

const scenes = [
  ["01-rank-hook", "01-rank-hook.html"],
  ["02-official-tools", "02-official-tools.html"],
  ["03-local-edit", "03-local-edit.html"],
  ["04-boundaries", "04-boundaries.html"],
  ["05-verdict", "05-verdict.html"],
];
const sceneMarkup = scenes.map(([id, file], index) => {
  const sceneDuration = index < 4 ? durations[index] + 0.5 : durations[index];
  return `
      <div data-hf-id="ep14-scene-${index + 1}" id="el-${id}" class="scene" data-composition-id="${id}" data-composition-src="compositions/frames/${file}" data-start="${starts[index].toFixed(3)}" data-duration="${sceneDuration.toFixed(3)}" data-track-index="${index % 2}"></div>
      <audio data-hf-id="ep14-audio-${index + 1}" id="el-${id}-voice" src="assets/voice/${String(index + 1).padStart(2, "0")}.mp3" data-start="${starts[index].toFixed(3)}" data-duration="${durations[index].toFixed(3)}" data-track-index="10" data-volume="1"></audio>`;
}).join("\n");

const transitions = scenes.slice(1).map(([id], index) => {
  const previousId = scenes[index][0];
  const at = starts[index + 1].toFixed(3);
  if (index === 3) {
    return `tl.to("#el-${previousId}", { filter: "blur(10px)", scale: 1.03, opacity: 0, duration: 0.6, ease: "power2.inOut" }, ${at});\n        tl.fromTo("#el-${id}", { filter: "blur(10px)", scale: 0.97, opacity: 0 }, { filter: "blur(0px)", scale: 1, opacity: 1, duration: 0.6, ease: "power2.inOut" }, ${at});`;
  }
  return `tl.to("#el-${previousId}", { x: -1080, duration: 0.5, ease: "power3.inOut" }, ${at});\n        tl.fromTo("#el-${id}", { x: 1080, opacity: 1 }, { x: 0, duration: 0.5, ease: "power3.inOut" }, ${at});`;
}).join("\n        ");

const indexHtml = `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js" integrity="sha384-sG0Hv1tP1lZCk9KQmrIbY/XNwi+OY84GQqhMscbnsoBFqAz8KNCil1kvfL3Hbbk2" crossorigin="anonymous"></script>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #000; }
      #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #F0EBDE; }
      .scene { position: absolute; inset: 0; width: 100%; height: 100%; }
      .chai-speaker { position: absolute; top: 1490px; left: 190px; width: 110px; height: 110px; z-index: 40; border: 3px solid #2639e8; border-radius: 50%; background: #06143f; box-shadow: 0 8px 20px rgba(19,31,135,.2), 0 0 0 5px rgba(240,235,222,.94); overflow: visible; will-change: transform; }
      .chai-speaker__crop { position: absolute; inset: 0; overflow: hidden; border-radius: 50%; }
      .chai-speaker__crop img { display: block; width: 100%; height: 100%; object-fit: cover; }
      .chai-speaker__mouth-anchor { position: absolute; left: 50%; top: 66.2%; width: 34px; height: 20px; margin-left: -17px; margin-top: -10px; pointer-events: none; }
      .chai-speaker__mouth { position: absolute; inset: 0; border-radius: 48% 48% 54% 54%; background: radial-gradient(ellipse at 50% 76%, #d65a68 0 20%, #521e2a 22% 48%, #160b12 52% 100%); box-shadow: inset 0 3px 2px rgba(255,255,255,.25), 0 1px 2px rgba(0,0,0,.45); opacity: 0; will-change: transform, opacity; }
      .chai-speaker__mouth::before { content: ""; position: absolute; top: 1px; left: 5px; width: 24px; height: 5px; border-radius: 0 0 9px 9px; background: #f7eee0; }
      .chai-speaker__name { position: absolute; left: 50%; bottom: -23px; min-width: 84px; margin-left: -42px; padding: 4px 8px; border: 2px solid #2639e8; background: #f0ebde; color: #2639e8; font: 700 14px/1 "CobaltMono", "PingFang SC", sans-serif; text-align: center; letter-spacing: .08em; white-space: nowrap; }
    </style>
  </head>
  <body>
    <div data-hf-id="ep14-main" id="root" data-composition-id="main" data-start="0" data-duration="${total.toFixed(3)}" data-width="1080" data-height="1920">
${sceneMarkup}
      <div data-hf-id="ep14-captions" id="el-captions" class="scene" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="${total.toFixed(3)}" data-track-index="2"></div>
      <div data-hf-id="ep14-chai-speaker" id="chai-speaker" class="chai-speaker" aria-label="柴主编说话头像">
        <div class="chai-speaker__crop"><img src="assets/brand/chai-editor-avatar.png" alt="柴主编"><div class="chai-speaker__mouth-anchor"><div id="chai-speaker-mouth" class="chai-speaker__mouth"></div></div></div>
        <div class="chai-speaker__name">柴主编</div>
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = gsap.timeline({ paused: true });
      (function () { var tl = window.__timelines["main"];
        ${transitions}
        tl.fromTo("#chai-speaker", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.55, ease: "back.out(1.7)" }, 0.18);
        var speechWindows = ${JSON.stringify(speechWindows)};
        var mouth = document.getElementById("chai-speaker-mouth");
        var avatar = document.getElementById("chai-speaker");
        var jawDriver = { progress: 0 };
        tl.to(jawDriver, { progress: 1, duration: ${total.toFixed(3)}, ease: "none", onUpdate: function () {
          var t = jawDriver.progress * ${total.toFixed(3)}; var active = null;
          for (var i = 0; i < speechWindows.length; i++) { if (t >= speechWindows[i][0] && t <= speechWindows[i][1]) { active = speechWindows[i]; break; } }
          var openness = 0;
          if (active) { var local = t - active[0]; var attack = Math.min(1, local / .07); var release = Math.min(1, (active[1] - t) / .09); var syllable = .34 + .66 * Math.abs(Math.sin(local * 18.5)); openness = syllable * Math.max(0, Math.min(attack, release)); }
          gsap.set(mouth, { scaleX: .82 + openness * .22, scaleY: .12 + openness * .94, opacity: openness > .04 ? .98 : 0 });
          gsap.set(avatar, { y: active ? -2.5 * Math.sin(t * 5.4) : 0, rotation: active ? .7 * Math.sin(t * 2.7) : 0 });
        } }, 0);
        tl.to({}, { duration: ${total.toFixed(3)} }, 0);
      })();
    </script>
  </body>
</html>\n`;
fs.writeFileSync(path.join(project, "index.html"), indexHtml);
console.log(JSON.stringify({ project, durations, starts, total, groups: groups.length, words: allWords.length, speechWindows: speechWindows.length }));
