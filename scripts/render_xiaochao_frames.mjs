import fs from "node:fs";
import path from "node:path";
import {pathToFileURL} from "node:url";
import puppeteer from "/Users/<you>/.npm/_npx/110f701c48e68d66/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js";

const [projectArg, framesArg, fpsArg = "15"] = process.argv.slice(2);
if (!projectArg || !framesArg) {
  throw new Error("usage: node render_xiaochao_frames.mjs <project> <frames-dir> [fps]");
}

const project = path.resolve(projectArg);
const framesDir = path.resolve(framesArg);
const fps = Number(fpsArg);
const html = fs.readFileSync(path.join(project, "index.html"), "utf8");
const durationMatch = html.match(/data-composition-id=[^>]+data-duration="([0-9.]+)"/);
if (!durationMatch) throw new Error("composition duration not found");
const duration = Number(durationMatch[1]);
const totalFrames = Math.ceil(duration * fps);

if (fs.existsSync(framesDir)) throw new Error(`refuse overwrite: ${framesDir}`);
fs.mkdirSync(framesDir, {recursive: false});

const browser = await puppeteer.launch({
  executablePath: "/Users/<you>/.cache/hyperframes/chrome/chrome-headless-shell/mac_arm-152.0.7928.2/chrome-headless-shell-mac-arm64/chrome-headless-shell",
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({width: 1080, height: 1920, deviceScaleFactor: 1});
  await page.goto(pathToFileURL(path.join(project, "index.html")).href, {waitUntil: "load", timeout: 60000});
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(Array.from(document.images).map((img) => img.complete ? null : new Promise((resolve) => {
      img.addEventListener("load", resolve, {once: true});
      img.addEventListener("error", resolve, {once: true});
    })));
    for (const audio of document.querySelectorAll("audio")) audio.remove();
  });

  for (let frame = 0; frame < totalFrames; frame += 1) {
    const time = frame / fps;
    await page.evaluate((t) => {
      const timeline = Object.values(window.__timelines || {})[0];
      if (!timeline) throw new Error("GSAP timeline unavailable");
      timeline.seek(t, false);
      const scenes = Array.from(document.querySelectorAll(".scene"));
      const active = scenes.find((scene) => {
        const start = Number(scene.dataset.start || 0);
        const duration = Number(scene.dataset.duration || 0);
        return t >= start && t < start + duration;
      }) || scenes.at(-1);
      for (const scene of scenes) scene.style.visibility = scene === active ? "visible" : "hidden";
    }, time);
    const file = path.join(framesDir, `frame-${String(frame).padStart(5, "0")}.jpg`);
    await page.screenshot({path: file, type: "jpeg", quality: 95, captureBeyondViewport: false});
    if (frame % 90 === 0 || frame + 1 === totalFrames) {
      process.stdout.write(`frame ${frame + 1}/${totalFrames}\n`);
    }
  }
} finally {
  await browser.close();
}

process.stdout.write(JSON.stringify({duration, fps, totalFrames, framesDir}) + "\n");
