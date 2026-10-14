#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = path.resolve("/Users/chao/Documents/dailyvideos");
const project = path.join(root, "videos/ai-sycophancy-question-first");
const ffprobe = path.join(project, "bin/ffprobe");
const audioNames = ["01", "02", "03", "04", "05"];
const gaps = [0.36, 0.36, 0.36, 0.36, 0.52];
const durations = audioNames.map((name, index) => {
  const file = path.join(project, "assets/voice", `${name}.mp3`);
  const value = Number(execFileSync(ffprobe, ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file], { encoding: "utf8" }).trim());
  return value + gaps[index];
});
const voiceDurations = audioNames.map((name) => {
  const file = path.join(project, "assets/voice", `${name}.mp3`);
  return Number(execFileSync(ffprobe, ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file], { encoding: "utf8" }).trim());
});
const starts = durations.map((_, index) => durations.slice(0, index).reduce((sum, value) => sum + value, 0));
const total = durations.reduce((sum, value) => sum + value, 0);

if (total < 45 || total > 60) throw new Error(`Timeline out of range: ${total.toFixed(3)}s`);

const phrasePlan = [
  ["AI总顺着你说，", "可能不是它没判断，", "而是你在提问前，", "先把立场塞进去了。"],
  ["Anthropic把这种迎合叫sycophancy：", "模型会顺着用户的信念，", "哪怕事实相反。", "OpenAI也曾因为GPT-4o过度讨好，", "回滚更新。"],
  ["一篇2026年的实验论文发现：", "只说“别讨好我”，", "效果有限。", "更有效的一招，", "是让AI先把你的陈述改写成一个中性问题，", "再回答。"],
  ["别问：", "“我这个方案是不是很好？”", "改成：", "“这个方案最可能失败在哪？", "需要什么证据才能成立？”"],
  ["柴主编判断：", "重要决定先改问法，", "再要反例和证据。", "它不能保证正确，", "但能少听几句顺耳的废话。"],
];

const normalize = (value) => value.replace(/\s+/g, "");
const isPunctuation = (value) => /^[\s，。；：、“”‘’！？,.!?:;()（）\-]+$/u.test(value);
const voices = [];
const allWords = [];
const groups = [];
const speechWords = [];

for (let segmentIndex = 0; segmentIndex < audioNames.length; segmentIndex += 1) {
  const id = String(segmentIndex + 1).padStart(2, "0");
  const subtitlePath = path.join(project, "assets/voice", `${audioNames[segmentIndex]}-words.json`);
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
    path: `assets/voice/${audioNames[segmentIndex]}.mp3`,
    duration_s: voiceDurations[segmentIndex],
    timeline_duration_s: durations[segmentIndex],
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

fs.writeFileSync(path.join(project, "audio_meta.json"), `${JSON.stringify({
  provider: "minimax",
  model: "speech-2.8-hd",
  voice_id: "male-qn-qingse",
  speed: 1.10,
  total_duration_s: total,
  voices,
  bgm: null,
  sfx: [],
}, null, 2)}\n`);
fs.writeFileSync(path.join(project, "word_timeline.json"), `${JSON.stringify({ total_duration_s: total, words: allWords, speech_windows: speechWindows }, null, 2)}\n`);
fs.writeFileSync(path.join(project, "sentence_timeline.json"), `${JSON.stringify({ total_duration_s: total, sentences: groups.map(({ id, frame, start, end, text }) => ({ id, frame, start, end, text })) }, null, 2)}\n`);
fs.writeFileSync(path.join(project, "caption_groups.json"), `${JSON.stringify({ total_duration_s: total, width: 1080, height: 1920, groups }, null, 2)}\n`);

const qwenCaptions = path.join(root, "videos/qwen38-max-explained/compositions/captions.html");
let captions = fs.readFileSync(qwenCaptions, "utf8");
captions = captions
  .replaceAll("53.172", total.toFixed(3))
  .replace("--paper: #F0EBDE;", "--paper: #07182C;")
  .replace("--paper-2: #E6E0CE;", "--paper-2: #0B2340;")
  .replace("--ink: #1F2BE0;", "--ink: #F4F7FB;")
  .replace("--ink-soft: #5560E5;", "--ink-soft: #13D7E8;")
  .replace("--grid: rgba(31,43,224,0.10);", "--grid: rgba(19,215,232,0.10);")
  .replace("--ink-faint: rgba(31,43,224,0.18);", "--ink-faint: rgba(19,215,232,0.18);")
  .replace("--cap-ink: #1F2BE0;", "--cap-ink: #13D7E8;")
  .replace("--cap-canvas: #F0EBDE;", "--cap-canvas: #07182C;")
  .replace("--cap-accent: #5560E5;", "--cap-accent: #FFB547;")
  .replace("--cap-accent-2: #E6E0CE;", "--cap-accent-2: #0B2340;")
  .replace(/var GROUPS = \[[\s\S]*?\];\n  var DURATION = [\d.]+;/, `var GROUPS = ${JSON.stringify(groups)};\n  var DURATION = ${total.toFixed(3)};`);
fs.mkdirSync(path.join(project, "compositions"), { recursive: true });
fs.writeFileSync(path.join(project, "compositions/captions.html"), captions);

const scenes = [
  ["01-wechat-hook", "01-wechat-hook.html"],
  ["02-evidence-stack", "02-evidence-stack.html"],
  ["03-harness-mechanism", "03-harness-mechanism.html"],
  ["04-missing-answers", "04-missing-answers.html"],
  ["05-verdict", "05-verdict.html"],
];
const sceneMarkup = scenes.map(([id, file], index) => {
  const sceneDuration = index < scenes.length - 1 ? durations[index] + 0.5 : durations[index];
  return `
      <div data-hf-id="ep19-scene-${index + 1}" id="scene-19-${index + 1}" class="clip scene" data-composition-id="${id}" data-composition-src="compositions/frames/${file}" data-start="${starts[index].toFixed(3)}" data-duration="${sceneDuration.toFixed(3)}" data-track-index="${index % 2}"></div>
      <audio data-hf-id="ep19-audio-${index + 1}" id="audio-18-${index + 1}" src="assets/voice/${audioNames[index]}.mp3" data-start="${starts[index].toFixed(3)}" data-duration="${voiceDurations[index].toFixed(3)}" data-track-index="10" data-volume="1"></audio>`;
}).join("\n");

const transitions = scenes.slice(1).map((_, index) => {
  const at = starts[index + 1].toFixed(3);
  if (index === 1) {
    return `tl.to("#scene-19-${index + 1}", { scale: 1.08, filter: "blur(8px)", opacity: 0, duration: 0.5, ease: "power3.inOut" }, ${at});\n        tl.fromTo("#scene-19-${index + 2}", { scale: 0.94, filter: "blur(8px)", opacity: 0 }, { scale: 1, filter: "blur(0px)", opacity: 1, duration: 0.5, ease: "power3.inOut" }, ${at});`;
  }
  if (index === 3) {
    return `tl.to("#scene-19-${index + 1}", { filter: "blur(10px)", scale: 1.03, opacity: 0, duration: 0.55, ease: "power3.inOut" }, ${at});\n        tl.fromTo("#scene-19-${index + 2}", { filter: "blur(10px)", scale: 0.97, opacity: 0 }, { filter: "blur(0px)", scale: 1, opacity: 1, duration: 0.55, ease: "power3.inOut" }, ${at});`;
  }
  return `tl.to("#scene-19-${index + 1}", { x: -1080, duration: 0.5, ease: "power3.inOut" }, ${at});\n        tl.fromTo("#scene-19-${index + 2}", { x: 1080, opacity: 1 }, { x: 0, duration: 0.5, ease: "power3.inOut" }, ${at});`;
}).join("\n        ");

const indexHtml = `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face { font-family: "CobaltSans"; src: url("assets/fonts/CobaltSans.ttc"); font-display: block; }
      @font-face { font-family: "CobaltMono"; src: url("assets/fonts/CobaltMono.ttf"); font-display: block; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #07182C; }
      #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #07182C; color: #F4F7FB; }
      .scene { position: absolute; inset: 0; width: 1080px; height: 1920px; }
      .fixed-headline { position: absolute; z-index: 60; left: 96px; right: 96px; top: 72px; height: 248px; pointer-events: none; }
      .fixed-headline::before { content: ""; position: absolute; inset: -28px -34px -18px; background: linear-gradient(180deg, #07182C 0%, #07182C 88%, rgba(7,24,44,.98) 100%); }
      .fixed-kicker { position: relative; font: 700 22px/1 "CobaltMono", monospace; letter-spacing: .18em; color: #13D7E8; margin-bottom: 18px; }
      .fixed-line-1, .fixed-line-2 { position: relative; font-family: "CobaltSans", sans-serif; font-weight: 900; letter-spacing: -.03em; }
      .fixed-line-1 { font-size: 70px; line-height: 1.05; color: #FFB547; }
      .fixed-line-2 { margin-top: 8px; font-size: 62px; line-height: 1.08; color: #F4F7FB; }
      .fixed-rule { position: relative; margin-top: 18px; width: 100%; height: 3px; background: linear-gradient(90deg, #13D7E8 0 72%, rgba(19,215,232,.15) 72%); transform-origin: left center; }
      .chai-speaker { position: absolute; top: 1490px; left: 190px; width: 110px; height: 110px; z-index: 70; border: 3px solid #13D7E8; border-radius: 50%; background: #07182C; box-shadow: 0 0 0 5px rgba(244,247,251,.92), 0 12px 28px rgba(0,0,0,.28); overflow: visible; will-change: transform; }
      .chai-crop { position: absolute; inset: 0; overflow: hidden; border-radius: 50%; }
      .chai-crop img { display: block; width: 100%; height: 100%; object-fit: cover; }
      .chai-mouth { position: absolute; left: 50%; top: 66.2%; width: 34px; height: 20px; margin-left: -17px; margin-top: -10px; border-radius: 48% 48% 54% 54%; background: radial-gradient(ellipse at 50% 76%, #d65a68 0 20%, #521e2a 22% 48%, #160b12 52% 100%); opacity: 0; will-change: transform, opacity; }
      .chai-mouth::before { content: ""; position: absolute; top: 1px; left: 5px; width: 24px; height: 5px; border-radius: 0 0 9px 9px; background: #f7eee0; }
      .chai-name { position: absolute; left: 50%; bottom: -23px; min-width: 84px; margin-left: -42px; padding: 4px 8px; border: 2px solid #13D7E8; background: #07182C; color: #F4F7FB; font: 700 14px/1 "CobaltMono", monospace; text-align: center; letter-spacing: .08em; white-space: nowrap; }
    </style>
  </head>
  <body>
    <div data-hf-id="ep19-main" id="root" data-composition-id="main" data-start="0" data-duration="${total.toFixed(3)}" data-width="1080" data-height="1920">
${sceneMarkup}
      <div data-hf-id="ep19-captions" id="captions-19" class="clip scene" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="${total.toFixed(3)}" data-track-index="20"></div>
      <div class="fixed-headline" id="fixed-headline-19">
        <div class="fixed-kicker">柴主编 · 只讲一件事</div>
        <div class="fixed-line-1">AI 总顺着你说？</div>
        <div class="fixed-line-2">先把陈述改成问题</div>
        <div class="fixed-rule" id="fixed-rule-19"></div>
      </div>
      <div data-hf-id="ep19-chai-speaker" id="chai-speaker-19" class="chai-speaker" data-layout-allow-caption-zone aria-label="柴主编说话头像">
        <div class="chai-crop"><img src="assets/brand/chai-editor-avatar.png" alt="柴主编"><div id="chai-mouth-19" class="chai-mouth"></div></div>
        <div class="chai-name">柴主编</div>
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      var tl = gsap.timeline({ paused: true });
      window.__timelines["main"] = tl;
      ${transitions}
      tl.fromTo("#fixed-headline-19", { y: -34, opacity: 0 }, { y: 0, opacity: 1, duration: 0.45, ease: "power3.out" }, 0.04);
      tl.fromTo("#fixed-rule-19", { scaleX: 0 }, { scaleX: 1, duration: 0.58, ease: "power3.out" }, 0.22);
      tl.fromTo("#chai-speaker-19", { scale: 0.7, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.5, ease: "power3.out" }, 0.18);
      var speechWindows = ${JSON.stringify(speechWindows)};
      var mouth = document.getElementById("chai-mouth-19");
      var avatar = document.getElementById("chai-speaker-19");
      var jawDriver = { progress: 0 };
      tl.to(jawDriver, { progress: 1, duration: ${total.toFixed(3)}, ease: "none", onUpdate: function () {
        var t = jawDriver.progress * ${total.toFixed(3)};
        var active = null;
        for (var i = 0; i < speechWindows.length; i += 1) { if (t >= speechWindows[i][0] && t <= speechWindows[i][1]) { active = speechWindows[i]; break; } }
        var openness = 0;
        if (active) { var local = t - active[0]; var attack = Math.min(1, local / .07); var release = Math.min(1, (active[1] - t) / .09); var syllable = .34 + .66 * Math.abs(Math.sin(local * 19.5)); openness = syllable * Math.max(0, Math.min(attack, release)); }
        gsap.set(mouth, { scaleX: .82 + openness * .22, scaleY: .12 + openness * .94, opacity: openness > .04 ? .98 : 0 });
        gsap.set(avatar, { y: active ? -2.2 * Math.sin(t * 5.8) : 0, rotation: active ? .6 * Math.sin(t * 2.9) : 0 });
      } }, 0);
      tl.to({}, { duration: ${total.toFixed(3)} }, 0);
    </script>
  </body>
</html>\n`;
fs.writeFileSync(path.join(project, "index.html"), indexHtml);

console.log(JSON.stringify({ project, voiceDurations, gaps, durations, starts, total, groups: groups.length, words: allWords.length, speechWindows: speechWindows.length }, null, 2));
