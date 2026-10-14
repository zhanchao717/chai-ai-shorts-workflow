#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {execFileSync} from "node:child_process";

const projectDir = path.resolve(process.argv[2] || "");
if (!projectDir || !fs.existsSync(projectDir)) throw new Error("Usage: node scripts/build_xiaochao_video_final_v2.mjs <episode-dir>");

for (const required of ["video-spec-final.json", "narration-final-v2", "voice-final-v2", "assets"]) {
  if (!fs.existsSync(path.join(projectDir, required))) throw new Error(`Missing v2 final input: ${required}`);
}
for (const target of ["index.html", "hyperframes.json", "frame.md", "index.motion.json"]) {
  if (fs.existsSync(path.join(projectDir, target))) throw new Error(`Refusing to overwrite existing file: ${target}`);
}

const stage = fs.mkdtempSync(path.join(os.tmpdir(), "xiaochao-final-v2-"));
try {
  fs.symlinkSync(path.join(projectDir, "assets"), path.join(stage, "assets"));
  fs.symlinkSync(path.join(projectDir, "narration-final-v2"), path.join(stage, "narration"));
  fs.symlinkSync(path.join(projectDir, "voice-final-v2"), path.join(stage, "voice"));
  fs.symlinkSync(path.join(projectDir, "video-spec-final.json"), path.join(stage, "video-spec.json"));
  execFileSync(process.execPath, [path.resolve("scripts/build_xiaochao_video.mjs"), stage], {stdio: "inherit"});
  for (const target of ["hyperframes.json", "frame.md", "index.motion.json"]) {
    fs.copyFileSync(path.join(stage, target), path.join(projectDir, target), fs.constants.COPYFILE_EXCL);
  }
  const html = fs.readFileSync(path.join(stage, "index.html"), "utf8")
    .replace("https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js", "assets/gsap-3.14.2.min.js")
    .replaceAll('src="voice/', 'src="voice-final-v2/');
  fs.writeFileSync(path.join(projectDir, "index.html"), html, {flag: "wx"});
} finally {
  fs.rmSync(stage, {recursive: true, force: true});
}

console.log(JSON.stringify({projectDir, status: "built-final-v2"}));
