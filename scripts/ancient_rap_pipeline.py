#!/usr/bin/env python3
"""Validate and run the Kling stage of the Ancient Rap series pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from kling_video import (
    api_request,
    download_video,
    image_value,
    video_url,
    wait_for_task,
)


PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_EPISODE = PROJECT / "src" / "data" / "ancient-rap-001.json"
DEFAULT_STATE = (
    PROJECT / "content" / "ancient-rap" / "episode-001" / "kling-tasks.json"
)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"数据文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON 格式错误：{path}:{exc.lineno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise SystemExit("期数数据必须是 JSON object")
    return data


def public_file(relative: str) -> Path:
    return PROJECT / "public" / relative


def validate_episode(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    warnings: List[str] = []
    required = (
        "seriesTitle",
        "episodeNumber",
        "poet",
        "poemTitle",
        "fps",
        "durationInFrames",
        "captions",
        "shots",
    )
    for field in required:
        if field not in data:
            errors.append(f"缺少字段：{field}")

    if errors:
        return errors

    fps = data["fps"]
    total = data["durationInFrames"]
    if fps != 30:
        errors.append("当前模板要求 fps=30")
    if not isinstance(total, int) or total <= 0:
        errors.append("durationInFrames 必须是正整数")

    shots = data["shots"]
    if not isinstance(shots, list) or not shots:
        errors.append("shots 必须是非空数组")
    else:
        cursor = 0
        ids = set()
        for index, shot in enumerate(shots, start=1):
            label = f"shot[{index}]"
            if not isinstance(shot, dict):
                errors.append(f"{label} 必须是 object")
                continue
            shot_id = shot.get("id")
            if not isinstance(shot_id, str) or not shot_id:
                errors.append(f"{label} 缺少 id")
            elif shot_id in ids:
                errors.append(f"镜头 id 重复：{shot_id}")
            else:
                ids.add(shot_id)
            start = shot.get("startFrame")
            duration = shot.get("durationInFrames")
            if start != cursor:
                errors.append(f"{shot_id or label} 应从 {cursor} 帧开始，实际为 {start}")
            if not isinstance(duration, int) or duration <= 0:
                errors.append(f"{shot_id or label} 的 durationInFrames 无效")
                continue
            seconds = duration / fps
            if seconds < 3 or seconds > 15:
                errors.append(f"{shot_id or label} 时长 {seconds:g}s 超出可灵 3–15s")
            cursor += duration
            for key in ("prompt", "firstFrame", "clip"):
                if not shot.get(key):
                    errors.append(f"{shot_id or label} 缺少 {key}")
        if cursor != total:
            errors.append(f"镜头总帧数 {cursor} 与成片 {total} 不一致")

    captions = data["captions"]
    if not isinstance(captions, list):
        errors.append("captions 必须是数组")
    else:
        allowed_kinds = {"original", "originalHook", "adaptation", "hook", "cta"}
        for index, caption in enumerate(captions, start=1):
            if not isinstance(caption, dict):
                errors.append(f"caption[{index}] 必须是 object")
                continue
            start = caption.get("startFrame")
            end = caption.get("endFrame")
            if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= total:
                errors.append(f"caption[{index}] 时间范围无效")
            if caption.get("kind") not in allowed_kinds:
                errors.append(f"caption[{index}] kind 无效")

    audio = data.get("audio")
    if isinstance(audio, str) and audio and not public_file(audio).is_file():
        warnings.append(f"音乐尚未就位：public/{audio}")
    for shot in data.get("shots", []):
        if isinstance(shot, dict):
            first_frame = shot.get("firstFrame")
            if isinstance(first_frame, str) and not public_file(first_frame).is_file():
                warnings.append(f"关键帧尚未就位：public/{first_frame}")

    for warning in warnings:
        print(f"警告：{warning}", file=sys.stderr)
    return errors


def command_validate(args: argparse.Namespace) -> int:
    data = load_json(args.episode)
    errors = validate_episode(data)
    if errors:
        for error in errors:
            print(f"错误：{error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "episode": data["episodeNumber"],
                "poem": f"{data['poet']}《{data['poemTitle']}》",
                "duration_seconds": data["durationInFrames"] / data["fps"],
                "shots": len(data["shots"]),
                "captions": len(data["captions"]),
                "structure": "valid",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def sync_assets(episode_path: Path) -> Dict[str, int]:
    data = load_json(episode_path)
    audio = data.get("audio")
    audio_ready = (
        isinstance(audio, str) and bool(audio) and public_file(audio).is_file()
    )
    data["audioReady"] = audio_ready
    keyframes = 0
    clips = 0
    shots = data.get("shots", [])
    if isinstance(shots, list):
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            first_frame = shot.get("firstFrame")
            clip = shot.get("clip")
            shot["keyframeReady"] = (
                isinstance(first_frame, str)
                and bool(first_frame)
                and public_file(first_frame).is_file()
            )
            shot["clipReady"] = (
                isinstance(clip, str)
                and bool(clip)
                and public_file(clip).is_file()
            )
            keyframes += int(shot["keyframeReady"])
            clips += int(shot["clipReady"])
    episode_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "audio": int(audio_ready),
        "keyframes": keyframes,
        "clips": clips,
    }


def command_sync(args: argparse.Namespace) -> int:
    result = sync_assets(args.episode)
    print(
        json.dumps(
            {"episode": str(args.episode), **result},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_plan(args: argparse.Namespace) -> int:
    data = load_json(args.episode)
    errors = validate_episode(data)
    if errors:
        for error in errors:
            print(f"错误：{error}", file=sys.stderr)
        return 1
    for shot in data["shots"]:
        frame = public_file(shot["firstFrame"])
        clip = public_file(shot["clip"])
        print(f"\n[{shot['id']}] {shot['durationInFrames'] / data['fps']:g}s")
        print(f"关键帧：{frame} {'✓' if frame.is_file() else '（缺失）'}")
        print(f"输出：  {clip}")
        print(f"提示词：{shot['prompt']}")
    return 0


def command_submit(args: argparse.Namespace) -> int:
    if not args.yes_spend_credits:
        raise SystemExit(
            "未提交：该操作会消耗可灵额度。确认后添加 --yes-spend-credits。"
        )
    data = load_json(args.episode)
    errors = validate_episode(data)
    if errors:
        for error in errors:
            print(f"错误：{error}", file=sys.stderr)
        return 1

    missing = [
        public_file(shot["firstFrame"])
        for shot in data["shots"]
        if not public_file(shot["firstFrame"]).is_file()
    ]
    if missing:
        joined = "\n".join(str(path) for path in missing)
        raise SystemExit(f"以下关键帧缺失，不能提交：\n{joined}")

    tasks: List[Dict[str, Any]] = []
    for shot in data["shots"]:
        duration = round(shot["durationInFrames"] / data["fps"])
        external_id = (
            f"ancient-rap-{data['episodeNumber']}-{shot['id']}"
        )
        payload = {
            "contents": [
                {"type": "prompt", "text": shot["prompt"]},
                {
                    "type": "first_frame",
                    "url": image_value(str(public_file(shot["firstFrame"]))),
                },
            ],
            "settings": {
                "resolution": args.resolution,
                "duration": duration,
                "audio": "off",
                "multi_shot": False,
            },
            "options": {
                "external_task_id": external_id,
                "watermark_info": {"enabled": False},
            },
        }
        response = api_request("POST", "/image-to-video/kling-3.0", payload)
        result = response.get("data", {})
        task_id = result.get("id") if isinstance(result, dict) else None
        if not isinstance(task_id, str) or not task_id:
            raise SystemExit(f"{shot['id']} 未返回 task id")
        task = {
            "shot_id": shot["id"],
            "task_id": task_id,
            "status": result.get("status"),
            "output": shot["clip"],
        }
        tasks.append(task)
        print(json.dumps(task, ensure_ascii=False))

    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(
        json.dumps(
            {
                "episode": data["episodeNumber"],
                "episode_file": str(args.episode.resolve().relative_to(PROJECT)),
                "created_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
                "tasks": tasks,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"任务清单：{args.state}")
    return 0


def command_collect(args: argparse.Namespace) -> int:
    state = load_json(args.state)
    tasks = state.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit(f"任务清单为空：{args.state}")

    failures = 0
    for record in tasks:
        if not isinstance(record, dict):
            continue
        shot_id = str(record.get("shot_id", "unknown"))
        task_id = str(record.get("task_id", ""))
        output = record.get("output")
        if not task_id or not isinstance(output, str):
            print(f"{shot_id} 任务记录无效", file=sys.stderr)
            failures += 1
            continue
        output_path = public_file(output)
        if output_path.is_file() and not args.overwrite:
            print(f"{shot_id} 已存在，跳过：{output_path}")
            continue
        task = wait_for_task(task_id, args.poll_interval, args.timeout)
        if task.get("status") != "succeeded":
            print(
                f"{shot_id} 生成失败：{task.get('message', '未知原因')}",
                file=sys.stderr,
            )
            failures += 1
            continue
        url = video_url(task, watermark=False)
        if not url:
            print(f"{shot_id} 没有视频下载地址", file=sys.stderr)
            failures += 1
            continue
        download_video(url, output_path)
    episode_file = state.get("episode_file")
    if isinstance(episode_file, str):
        result = sync_assets(PROJECT / episode_file)
        print(json.dumps({"synced_assets": result}, ensure_ascii=False))
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="《假如古人也会说唱》流水线")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="检查期数数据和素材")
    validate.add_argument("--episode", type=Path, default=DEFAULT_EPISODE)
    validate.set_defaults(handler=command_validate)

    sync = subparsers.add_parser("sync-assets", help="同步本地素材就绪状态")
    sync.add_argument("--episode", type=Path, default=DEFAULT_EPISODE)
    sync.set_defaults(handler=command_sync)

    plan = subparsers.add_parser("kling-plan", help="预览可灵镜头计划")
    plan.add_argument("--episode", type=Path, default=DEFAULT_EPISODE)
    plan.set_defaults(handler=command_plan)

    submit = subparsers.add_parser("kling-submit", help="提交全部可灵镜头")
    submit.add_argument("--episode", type=Path, default=DEFAULT_EPISODE)
    submit.add_argument("--state", type=Path, default=DEFAULT_STATE)
    submit.add_argument("--resolution", choices=("720p", "1080p", "4k"), default="720p")
    submit.add_argument("--yes-spend-credits", action="store_true")
    submit.set_defaults(handler=command_submit)

    collect = subparsers.add_parser("kling-collect", help="等待并下载全部镜头")
    collect.add_argument("--state", type=Path, default=DEFAULT_STATE)
    collect.add_argument("--poll-interval", type=float, default=10)
    collect.add_argument("--timeout", type=float, default=1800)
    collect.add_argument("--overwrite", action="store_true")
    collect.set_defaults(handler=command_collect)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
