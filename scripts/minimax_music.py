#!/usr/bin/env python3
"""Generate and select MiniMax Music candidates for the Ancient Rap series.

The API key is read from MINIMAX_API_KEY or the macOS Keychain. It is never
written to the project or included in command output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_API_BASE = "https://api.minimaxi.com"
KEYCHAIN_SERVICE = "dailyvideos-minimax-api-key"
DEFAULT_PROMPT = (
    PROJECT / "content" / "ancient-rap" / "episode-001" / "music-prompt.txt"
)
DEFAULT_LYRICS = (
    PROJECT / "content" / "ancient-rap" / "episode-001" / "minimax-lyrics.txt"
)
DEFAULT_EPISODE = PROJECT / "src" / "data" / "ancient-rap-001.json"
DEFAULT_CANDIDATES = (
    PROJECT / "public" / "audio" / "ancient-rap" / "episode-001" / "candidates"
)
DEFAULT_OUTPUT = (
    PROJECT / "public" / "audio" / "ancient-rap" / "episode-001" / "final-track.mp3"
)


def load_api_key() -> str:
    from_environment = os.environ.get("MINIMAX_API_KEY", "").strip()
    if from_environment:
        return from_environment

    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                os.environ.get("USER", ""),
                "-s",
                KEYCHAIN_SERVICE,
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            "未找到 MiniMax API Key。请设置 MINIMAX_API_KEY，"
            "或按 README 将密钥存入 macOS 钥匙串。"
        ) from exc

    key = result.stdout.strip()
    if not key:
        raise SystemExit(f"macOS 钥匙串项目 {KEYCHAIN_SERVICE!r} 为空")
    return key


def api_base() -> str:
    return os.environ.get("MINIMAX_API_BASE", DEFAULT_API_BASE).rstrip("/")


def read_text(path: Path, label: str) -> str:
    try:
        value = path.expanduser().resolve().read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise SystemExit(f"{label}不存在：{path}") from exc
    if not value:
        raise SystemExit(f"{label}为空：{path}")
    return value


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    prompt = read_text(args.prompt_file, "音乐提示文件")
    lyrics = read_text(args.lyrics_file, "歌词文件")
    if len(prompt) > 2000:
        raise SystemExit(f"音乐提示超过 MiniMax 2000 字符限制：{len(prompt)}")
    if len(lyrics) > 3500:
        raise SystemExit(f"歌词超过 MiniMax 3500 字符限制：{len(lyrics)}")
    return {
        "model": args.model,
        "prompt": prompt,
        "lyrics": lyrics,
        "stream": False,
        "output_format": "url",
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 256000,
            "format": "mp3",
        },
        "aigc_watermark": False,
        "lyrics_optimizer": False,
        "is_instrumental": False,
    }


def api_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    request = urllib.request.Request(
        f"{api_base()}/v1/music_generation",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {load_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "dailyvideos-minimax-music-client/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"MiniMax Music API 请求失败（HTTP {exc.code}）：{detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"无法连接 MiniMax Music API：{exc.reason}") from exc

    if not isinstance(result, dict):
        raise SystemExit("MiniMax Music API 返回了无法识别的数据")
    base_resp = result.get("base_resp")
    if not isinstance(base_resp, dict) or base_resp.get("status_code") != 0:
        code = base_resp.get("status_code") if isinstance(base_resp, dict) else "?"
        message = (
            base_resp.get("status_msg", "未知错误")
            if isinstance(base_resp, dict)
            else "缺少 base_resp"
        )
        if code == 1008:
            message = (
                "账户余额不足；即使调用 *-free 模型，当前账户也需要先具备"
                "可用余额或获得免费额度"
            )
        elif code == 2056:
            message = (
                "Token Plan 音乐额度已用完；请升级套餐、购买积分，"
                "或等待套餐额度重置"
            )
        elif code == 2061:
            message = (
                "当前 API Key 或 Token Plan 不支持所选模型；"
                "普通 API Key 可用 *-free，Token Plan Key 请使用套餐支持的正式模型"
            )
        raise SystemExit(f"MiniMax Music API 返回错误 {code}：{message}")
    return result


def audio_url(result: Dict[str, Any]) -> str:
    data = result.get("data")
    if not isinstance(data, dict):
        return ""
    for field in ("audio", "audio_url", "url"):
        value = data.get(field)
        if isinstance(value, str) and value.startswith(("https://", "http://")):
            return value
    return ""


def download_audio(url: str, output: Path) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dailyvideos-minimax-music-client/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            with temporary.open("wb") as file:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    file.write(chunk)
    except (urllib.error.URLError, OSError) as exc:
        if temporary.exists():
            temporary.unlink()
        raise SystemExit(f"下载 MiniMax 音频失败：{exc}") from exc

    if not temporary.is_file() or temporary.stat().st_size < 1024:
        if temporary.exists():
            temporary.unlink()
        raise SystemExit("下载到的 MiniMax 音频文件异常小")
    temporary.replace(output)


def bundled_binary(name: str) -> Optional[Path]:
    candidates = [
        PROJECT / "node_modules" / "@remotion" / "compositor-darwin-arm64" / name,
        PROJECT / "node_modules" / "@remotion" / "compositor-darwin-x64" / name,
        PROJECT / "node_modules" / "@remotion" / "compositor-linux-arm64-gnu" / name,
        PROJECT / "node_modules" / "@remotion" / "compositor-linux-x64-gnu" / name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    located = shutil.which(name)
    return Path(located) if located else None


def media_environment(binary: Path) -> Dict[str, str]:
    environment = os.environ.copy()
    if sys.platform == "darwin":
        environment["DYLD_LIBRARY_PATH"] = str(binary.parent)
    return environment


def probe_duration(path: Path) -> float:
    ffprobe = bundled_binary("ffprobe")
    if ffprobe is None:
        raise SystemExit("未找到 ffprobe，无法检测音频时长")
    try:
        result = subprocess.run(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path.expanduser().resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=media_environment(ffprobe),
        )
        duration = float(json.loads(result.stdout)["format"]["duration"])
    except (
        KeyError,
        ValueError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        raise SystemExit(f"无法读取音频时长：{path}") from exc
    if duration <= 0:
        raise SystemExit(f"音频时长无效：{path}")
    return duration


def fit_audio(source: Path, output: Path, target_seconds: float) -> None:
    ffmpeg = bundled_binary("ffmpeg")
    if ffmpeg is None:
        raise SystemExit("未找到 ffmpeg，无法整理最终音频")
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.stem}.part{output.suffix}")
    if temporary.exists():
        temporary.unlink()
    try:
        subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source.expanduser().resolve()),
                "-af",
                "apad",
                "-t",
                f"{target_seconds:.3f}",
                "-ar",
                "44100",
                "-b:a",
                "256k",
                str(temporary),
            ],
            check=True,
            env=media_environment(ffmpeg),
        )
    except subprocess.CalledProcessError as exc:
        if temporary.exists():
            temporary.unlink()
        raise SystemExit("ffmpeg 无法整理最终音频") from exc
    if not temporary.is_file() or temporary.stat().st_size < 1024:
        raise SystemExit("ffmpeg 输出的最终音频异常小")
    temporary.replace(output)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def append_manifest(directory: Path, item: Dict[str, Any]) -> None:
    manifest = directory / "candidates.json"
    items: List[Dict[str, Any]] = []
    if manifest.is_file():
        try:
            loaded = json.loads(manifest.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                items = [entry for entry in loaded if isinstance(entry, dict)]
        except json.JSONDecodeError:
            pass
    items.append(item)
    manifest.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def handle_generate(args: argparse.Namespace) -> int:
    payload = build_payload(args)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "endpoint": f"{api_base()}/v1/music_generation",
                    "payload": payload,
                    "candidate_count": args.count,
                    "will_use_api_key": False,
                    "will_spend_or_use_quota": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = str(payload["prompt"])
    lyrics = str(payload["lyrics"])
    session = time.strftime("%Y%m%d-%H%M%S")

    for index in range(1, args.count + 1):
        print(
            f"正在生成候选曲 {index}/{args.count}（{args.model}）…",
            file=sys.stderr,
            flush=True,
        )
        result = api_request(payload)
        url = audio_url(result)
        if not url:
            raise SystemExit("MiniMax 返回成功，但没有可下载的音频 URL")
        output = output_dir / f"candidate-{session}-{index:02d}.mp3"
        download_audio(url, output)
        duration = probe_duration(output)
        extra_info = result.get("extra_info")
        item = {
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "model": args.model,
            "file": str(output.relative_to(PROJECT)),
            "durationSeconds": round(duration, 3),
            "bytes": output.stat().st_size,
            "traceId": result.get("trace_id"),
            "promptSha256": sha256_text(prompt),
            "lyricsSha256": sha256_text(lyrics),
            "apiDurationMs": (
                extra_info.get("music_duration")
                if isinstance(extra_info, dict)
                else None
            ),
        }
        append_manifest(output_dir, item)
        print(json.dumps(item, ensure_ascii=False))
        if index < args.count:
            time.sleep(21)
    return 0


def load_episode(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"分集数据不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"分集 JSON 格式错误：{path}:{exc.lineno}") from exc
    if not isinstance(data, dict):
        raise SystemExit("分集数据必须是 JSON object")
    return data


def candidate_model(path: Path) -> Optional[str]:
    manifest = path.parent / "candidates.json"
    if not manifest.is_file():
        return None
    try:
        items = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(items, list):
        return None
    try:
        relative = str(path.resolve().relative_to(PROJECT))
    except ValueError:
        return None
    for item in reversed(items):
        if isinstance(item, dict) and item.get("file") == relative:
            model = item.get("model")
            return model if isinstance(model, str) else None
    return None


def copy_audio(source: Path, output: Path) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.stem}.part{output.suffix}")
    if temporary.exists():
        temporary.unlink()
    shutil.copyfile(source, temporary)
    temporary.replace(output)


def rescale_episode_timeline(
    episode: Dict[str, Any],
    old_total: int,
    new_total: int,
) -> None:
    if old_total == new_total:
        return
    scale = new_total / old_total
    shots = episode.get("shots")
    if isinstance(shots, list):
        cursor = 0
        valid_shots = [shot for shot in shots if isinstance(shot, dict)]
        for index, shot in enumerate(valid_shots):
            old_start = shot.get("startFrame")
            old_duration = shot.get("durationInFrames")
            if not isinstance(old_start, int) or not isinstance(old_duration, int):
                continue
            old_end = old_start + old_duration
            new_end = (
                new_total
                if index == len(valid_shots) - 1
                else round(old_end * scale)
            )
            shot["startFrame"] = cursor
            shot["durationInFrames"] = max(1, new_end - cursor)
            cursor = new_end

    captions = episode.get("captions")
    if isinstance(captions, list):
        for caption in captions:
            if not isinstance(caption, dict):
                continue
            start = caption.get("startFrame")
            end = caption.get("endFrame")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            new_start = min(new_total - 1, max(0, round(start * scale)))
            new_end = min(new_total, max(new_start + 1, round(end * scale)))
            caption["startFrame"] = new_start
            caption["endFrame"] = new_end


def handle_select(args: argparse.Namespace) -> int:
    candidate = args.candidate.expanduser().resolve()
    if not candidate.is_file():
        raise SystemExit(f"候选音频不存在：{candidate}")
    episode_path = args.episode.expanduser().resolve()
    episode = load_episode(episode_path)
    fps = episode.get("fps")
    total_frames = episode.get("durationInFrames")
    if not isinstance(fps, int) or fps <= 0:
        raise SystemExit("分集 fps 无效")
    if not isinstance(total_frames, int) or total_frames <= 0:
        raise SystemExit("分集 durationInFrames 无效")
    target_seconds = total_frames / fps

    source_duration = probe_duration(candidate)
    if args.keep_duration:
        copy_audio(candidate, args.output)
        new_total_frames = math.ceil(source_duration * fps)
        rescale_episode_timeline(episode, total_frames, new_total_frames)
        episode["durationInFrames"] = new_total_frames
        target_seconds = new_total_frames / fps
    else:
        fit_audio(candidate, args.output, target_seconds)
    final_duration = probe_duration(args.output)
    model = candidate_model(candidate) or args.model

    try:
        audio_path = str(args.output.resolve().relative_to(PROJECT / "public"))
    except ValueError as exc:
        raise SystemExit("最终音频必须保存在项目 public 目录中") from exc
    episode["audio"] = audio_path
    episode["audioReady"] = True
    episode["musicProvider"] = "MiniMax"
    episode["musicModel"] = model
    episode["sourceMusicDurationSeconds"] = round(source_duration, 3)
    episode["finalMusicDurationSeconds"] = round(final_duration, 3)
    episode_path.write_text(
        json.dumps(episode, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "selected": str(candidate),
                "output": str(args.output.resolve()),
                "source_duration_seconds": round(source_duration, 3),
                "final_duration_seconds": round(final_duration, 3),
                "target_duration_seconds": target_seconds,
                "episode": str(episode_path),
                "model": model,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="MiniMax Music 候选生成与《假如古人也会说唱》选曲工具"
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="生成并下载候选歌曲")
    generate.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT)
    generate.add_argument("--lyrics-file", type=Path, default=DEFAULT_LYRICS)
    generate.add_argument("--output-dir", type=Path, default=DEFAULT_CANDIDATES)
    generate.add_argument("--model", default="music-3.0-free")
    generate.add_argument("--count", type=int, choices=range(1, 4), default=1)
    generate.add_argument("--dry-run", action="store_true")
    generate.set_defaults(handler=handle_generate)

    select = subparsers.add_parser("select", help="选中候选并整理为本期最终音频")
    select.add_argument("candidate", type=Path)
    select.add_argument("--episode", type=Path, default=DEFAULT_EPISODE)
    select.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    select.add_argument("--model", default="music-3.0-free")
    select.add_argument(
        "--keep-duration",
        action="store_true",
        help="保留完整歌曲，并按真实时长等比例调整分镜和字幕",
    )
    select.set_defaults(handler=handle_select)
    return root


def main() -> int:
    args = parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
