#!/usr/bin/env python3
"""柴主编 AI 日报的本地生产流水线。

负责可重复的机器步骤：Edge TTS、音频标准化、HyperFrames 渲染、音频合成、
媒体探测和发布包归档。新闻研究、dbs-suite 审校和 atutun 封面生成仍由
Codex 技能完成，脚本会检查对应产物，避免跳过质量门禁。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

SEGMENTS = ("hook", "lead", "brief1", "brief2", "brief3", "brief4", "verdict", "cta")


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def tool(project: Path, name: str) -> tuple[str, dict[str, str]]:
    binary = shutil.which(name)
    if binary:
        return binary, os.environ.copy()
    bundle = project / "node_modules" / "@remotion" / "compositor-darwin-arm64"
    candidate = bundle / name
    if candidate.is_file():
        env = os.environ.copy()
        env["DYLD_LIBRARY_PATH"] = str(bundle)
        return str(candidate), env
    raise SystemExit(f"找不到 {name}，请先安装系统 FFmpeg 或项目依赖。")


def paths_for(project: Path, issue: str) -> dict[str, Path]:
    content = project / "content" / f"episode-{issue}"
    hf = project / f"hyperframes-episode-{issue}"
    return {
        "content": content,
        "text": content / "audio-text",
        "public_audio": project / "public" / "audio",
        "hf": hf,
        "hf_audio": hf / "assets" / "audio",
        "out": project / "out",
    }


def check_copy_gate(paths: dict[str, Path]) -> None:
    required = [paths["content"] / name for name in ("sources.md", "publish-copy.md", "dbs-review.md")]
    required += [paths["text"] / f"{segment}.txt" for segment in SEGMENTS]
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise SystemExit("文案门禁未通过，缺少以下文件：\n" + "\n".join(missing))
    review = (paths["content"] / "dbs-review.md").read_text(encoding="utf-8")
    if "最终门禁" not in review or "通过" not in review:
        raise SystemExit("dbs-review.md 没有记录最终门禁通过，请先运行 dbs-suite。")


def tts(paths: dict[str, Path], issue: str, rate: str, pitch: str) -> None:
    project = paths["content"].parents[1]
    edge_tts = project / ".venv-tts" / "bin" / "edge-tts"
    if not edge_tts.is_file():
        raise SystemExit(f"找不到本地 TTS：{edge_tts}")
    paths["public_audio"].mkdir(parents=True, exist_ok=True)
    for segment in SEGMENTS:
        output = paths["public_audio"] / f"episode-{issue}-{segment}-xiaoxiao.mp3"
        run([str(edge_tts), "-f", str(paths["text"] / f"{segment}.txt"), "-v", "zh-CN-XiaoxiaoNeural", f"--rate={rate}", f"--pitch={pitch}", "--write-media", str(output)], cwd=project)


def normalize_audio(paths: dict[str, Path], issue: str) -> dict[str, float]:
    project = paths["content"].parents[1]
    ffmpeg, env = tool(project, "ffmpeg")
    ffprobe, probe_env = tool(project, "ffprobe")
    paths["hf_audio"].mkdir(parents=True, exist_ok=True)
    durations: dict[str, float] = {}
    for segment in SEGMENTS:
        source = paths["public_audio"] / f"episode-{issue}-{segment}-xiaoxiao.mp3"
        target = paths["hf_audio"] / f"{segment}.mp3"
        run([ffmpeg, "-y", "-i", str(source), "-filter:a", "atempo=1.24,loudnorm=I=-16:TP=-1.5:LRA=11", str(target)], cwd=project, env=env)
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(target)], cwd=project, env=probe_env, check=True, capture_output=True, text=True)
        durations[segment] = round(float(result.stdout.strip()), 3)
    return durations


def render_video(paths: dict[str, Path], issue: str, output: Path) -> None:
    if not paths["hf"].is_dir():
        raise SystemExit(f"找不到 HyperFrames 工程：{paths['hf']}")
    node = shutil.which("node")
    cached_clis = sorted(Path.home().glob(".npm/_npx/*/node_modules/hyperframes/dist/cli.js"))
    if cached_clis and node:
        hyperframes_command = [node, str(cached_clis[-1])]
    else:
        npx = shutil.which("npx")
        if not npx:
            raise SystemExit("找不到本地 HyperFrames CLI 或 npx。")
        hyperframes_command = [npx, "--yes", "hyperframes@0.7.87"]
    render_env = os.environ.copy()
    compositor_bin = paths["content"].parents[1] / "node_modules" / "@remotion" / "compositor-darwin-arm64"
    if compositor_bin.is_dir():
        render_env["PATH"] = str(compositor_bin) + os.pathsep + render_env.get("PATH", "")
        render_env["DYLD_LIBRARY_PATH"] = str(compositor_bin)
        render_env["HYPERFRAMES_FFMPEG_PATH"] = str(compositor_bin / "ffmpeg")
        render_env["HYPERFRAMES_FFPROBE_PATH"] = str(compositor_bin / "ffprobe")
    with tempfile.TemporaryDirectory(prefix=f"shiba-hf-{issue}-") as temp_dir:
        temp_project = Path(temp_dir) / paths["hf"].name
        shutil.copytree(paths["hf"], temp_project)
        index = temp_project / "index.html"
        html = index.read_text(encoding="utf-8")
        # 某些 HyperFrames 版本组装隐藏 audio 时无法推断 m4a；最终音频随后由 FFmpeg 合成。
        html = re.sub(r"\s*<audio\b[\s\S]*?</audio>", "", html, flags=re.IGNORECASE)
        index.write_text(html, encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        run([*hyperframes_command, "render", "--quality", "high", "--output", str(output)], cwd=temp_project, env=render_env)


def concat_audio(paths: dict[str, Path], output: Path) -> None:
    project = paths["content"].parents[1]
    ffmpeg, env = tool(project, "ffmpeg")
    inputs: list[str] = []
    for segment in SEGMENTS:
        inputs += ["-i", str(paths["hf_audio"] / f"{segment}.mp3")]
    streams = "".join(f"[{index}:a]" for index in range(len(SEGMENTS)))
    graph = f"{streams}concat=n={len(SEGMENTS)}:v=0:a=1[aout]"
    run([ffmpeg, "-y", *inputs, "-filter_complex", graph, "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(output)], cwd=project, env=env)


def mux(paths: dict[str, Path], video_only: Path, audio: Path, output: Path) -> None:
    project = paths["content"].parents[1]
    ffmpeg, env = tool(project, "ffmpeg")
    run([ffmpeg, "-y", "-i", str(video_only), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(output)], cwd=project, env=env)


def probe(paths: dict[str, Path], video: Path) -> dict[str, object]:
    project = paths["content"].parents[1]
    ffprobe, env = tool(project, "ffprobe")
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,codec_type,width,height", "-of", "json", str(video)], cwd=project, env=env, check=True, capture_output=True, text=True)
    report = json.loads(result.stdout)
    (paths["content"] / "production-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="柴主编 AI 日报一键生产流水线")
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--issue", required=True, help="三位数期号，如 005")
    parser.add_argument("--rate", default="+20%")
    parser.add_argument("--pitch", default="-1Hz")
    parser.add_argument("--skip-tts", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    issue = str(args.issue).zfill(3)
    paths = paths_for(project, issue)
    check_copy_gate(paths)
    paths["out"].mkdir(parents=True, exist_ok=True)
    if not args.skip_tts:
        tts(paths, issue, args.rate, args.pitch)
    durations = normalize_audio(paths, issue)
    (paths["content"] / "audio-durations.json").write_text(json.dumps(durations, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.skip_render:
        print(json.dumps({"issue": issue, "audio_durations": durations, "message": "已完成 TTS 和音频标准化，跳过视频渲染。"}, ensure_ascii=False, indent=2))
        return 0
    video_only = paths["out"] / f"episode-{issue}-video-only.mp4"
    audio = paths["content"] / "episode-audio.m4a"
    final = paths["out"] / f"episode-{issue}-auto.mp4"
    render_video(paths, issue, video_only)
    concat_audio(paths, audio)
    mux(paths, video_only, audio, final)
    report = probe(paths, final)
    print(json.dumps({"issue": issue, "video": str(final), "probe": report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
