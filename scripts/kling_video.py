#!/usr/bin/env python3
"""Generate vertical video clips with the Kling AI API 2.0.

The API key is read from KLING_API_KEY or the macOS Keychain. It is never
written to the project or included in command output.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_API_BASE = "https://api-beijing.klingai.com"
KEYCHAIN_SERVICE = "dailyvideos-kling-api-key"
FINAL_STATUSES = {"succeeded", "failed"}


def load_api_key() -> str:
    from_environment = os.environ.get("KLING_API_KEY", "").strip()
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
            "未找到可灵 API Key。请设置 KLING_API_KEY，或按 README 将密钥存入 macOS 钥匙串。"
        ) from exc

    key = result.stdout.strip()
    if not key:
        raise SystemExit(f"macOS 钥匙串项目 {KEYCHAIN_SERVICE!r} 为空")
    return key


def api_base() -> str:
    return os.environ.get("KLING_API_BASE", DEFAULT_API_BASE).rstrip("/")


def api_request(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        f"{api_base()}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {load_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "dailyvideos-kling-client/1.0",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"可灵 API 请求失败（HTTP {exc.code}）：{detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"无法连接可灵 API：{exc.reason}") from exc

    if not isinstance(result, dict):
        raise SystemExit("可灵 API 返回了无法识别的数据")
    if result.get("code") != 0:
        raise SystemExit(
            f"可灵 API 返回错误 {result.get('code')}：{result.get('message', '未知错误')}"
        )
    return result


def image_value(value: str) -> str:
    if value.startswith(("https://", "http://", "data:image/")):
        return value

    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"图片不存在：{path}")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise SystemExit(f"图片超过可灵 50MB 限制：{path}")

    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type not in {"image/jpeg", "image/png"}:
        raise SystemExit("可灵首尾帧只支持 JPG、JPEG 或 PNG")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    settings: Dict[str, Any] = {
        "resolution": args.resolution,
        "duration": args.duration,
        "audio": args.audio,
        "multi_shot": args.multi_shot,
    }
    options: Dict[str, Any] = {
        "watermark_info": {"enabled": args.watermark},
    }
    if args.external_task_id:
        options["external_task_id"] = args.external_task_id
    if args.callback_url:
        options["callback_url"] = args.callback_url

    if args.first_frame:
        contents: List[Dict[str, str]] = [
            {"type": "prompt", "text": args.prompt},
            {"type": "first_frame", "url": image_value(args.first_frame)},
        ]
        if args.last_frame:
            contents.append(
                {"type": "last_frame", "url": image_value(args.last_frame)}
            )
        return {"contents": contents, "settings": settings, "options": options}

    if args.last_frame:
        raise SystemExit("--last-frame 必须和 --first-frame 一起使用")
    settings["aspect_ratio"] = args.aspect_ratio
    return {"prompt": args.prompt, "settings": settings, "options": options}


def task_path(task_id: str) -> str:
    query = urllib.parse.urlencode({"task_ids": task_id})
    return f"/tasks?{query}"


def get_task(task_id: str) -> Dict[str, Any]:
    response = api_request("GET", task_path(task_id))
    tasks = response.get("data")
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit(f"没有找到任务：{task_id}")
    task = tasks[0]
    if not isinstance(task, dict):
        raise SystemExit("可灵任务数据格式异常")
    return task


def wait_for_task(
    task_id: str,
    poll_interval: float,
    timeout: float,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    previous_status = ""
    while True:
        task = get_task(task_id)
        status = str(task.get("status", "unknown"))
        if status != previous_status:
            print(f"任务 {task_id}：{status}", file=sys.stderr, flush=True)
            previous_status = status
        if status in FINAL_STATUSES:
            return task
        if time.monotonic() >= deadline:
            raise SystemExit(
                f"等待任务超时（{int(timeout)} 秒）。稍后可用 kling:status 继续查询：{task_id}"
            )
        time.sleep(poll_interval)


def video_url(task: Dict[str, Any], watermark: bool) -> str:
    outputs = task.get("outputs")
    if not isinstance(outputs, list):
        return ""
    for output in outputs:
        if not isinstance(output, dict) or output.get("type") != "video":
            continue
        preferred = "watermark_url" if watermark else "url"
        url = output.get(preferred) or output.get("url")
        if isinstance(url, str):
            return url
    return ""


def download_video(url: str, output: Path) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dailyvideos-kling-client/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            with temporary.open("wb") as file:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    file.write(chunk)
    except (urllib.error.URLError, OSError) as exc:
        if temporary.exists():
            temporary.unlink()
        raise SystemExit(f"下载可灵视频失败：{exc}") from exc

    if temporary.stat().st_size < 1024:
        temporary.unlink()
        raise SystemExit("下载到的视频文件异常小")
    temporary.replace(output)
    print(
        json.dumps(
            {"output": str(output), "bytes": output.stat().st_size},
            ensure_ascii=False,
        )
    )


def default_output() -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return Path("out") / f"kling-{timestamp}.mp4"


def handle_generate(args: argparse.Namespace) -> int:
    payload = build_payload(args)
    endpoint = (
        "/image-to-video/kling-3.0"
        if args.first_frame
        else "/text-to-video/kling-3.0"
    )
    if args.dry_run:
        printable = json.loads(json.dumps(payload))
        for content in printable.get("contents", []):
            url = content.get("url", "")
            if isinstance(url, str) and url.startswith("data:image/"):
                content["url"] = f"{url[: url.index(',') + 1]}<base64 omitted>"
        print(
            json.dumps(
                {"endpoint": f"{api_base()}{endpoint}", "payload": printable},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    response = api_request("POST", endpoint, payload)
    data = response.get("data", {})
    task_id = data.get("id") if isinstance(data, dict) else None
    if not isinstance(task_id, str) or not task_id:
        raise SystemExit("可灵 API 未返回任务 ID")
    print(json.dumps({"task_id": task_id, "status": data.get("status")}, ensure_ascii=False))
    if args.no_wait:
        return 0

    task = wait_for_task(task_id, args.poll_interval, args.timeout)
    if task.get("status") != "succeeded":
        raise SystemExit(f"可灵视频生成失败：{task.get('message', '未知原因')}")
    url = video_url(task, args.watermark)
    if not url:
        raise SystemExit("任务成功，但返回结果中没有视频下载地址")
    download_video(url, args.output or default_output())
    return 0


def handle_status(args: argparse.Namespace) -> int:
    task = get_task(args.task_id)
    summary = {
        "task_id": task.get("id"),
        "status": task.get("status"),
        "message": task.get("message"),
        "create_time": task.get("create_time"),
        "update_time": task.get("update_time"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.output and task.get("status") == "succeeded":
        url = video_url(task, args.watermark)
        if not url:
            raise SystemExit("任务成功，但返回结果中没有视频下载地址")
        download_video(url, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="可灵 AI 视频生成客户端")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="创建并下载视频")
    generate.add_argument("--prompt", required=True, help="视频提示词")
    generate.add_argument("--first-frame", help="首帧图片路径、URL 或 data URI")
    generate.add_argument("--last-frame", help="尾帧图片路径、URL 或 data URI")
    generate.add_argument("--output", type=Path, help="下载文件路径")
    generate.add_argument(
        "--resolution",
        choices=("720p", "1080p", "4k"),
        default="720p",
    )
    generate.add_argument(
        "--aspect-ratio",
        choices=("16:9", "9:16", "1:1"),
        default="9:16",
        help="文生视频画幅；图生视频沿用首帧画幅",
    )
    generate.add_argument("--duration", type=int, choices=range(3, 16), default=5)
    generate.add_argument("--audio", choices=("off", "native"), default="off")
    generate.add_argument("--multi-shot", action="store_true")
    generate.add_argument("--watermark", action="store_true")
    generate.add_argument("--external-task-id")
    generate.add_argument("--callback-url")
    generate.add_argument("--no-wait", action="store_true", help="提交后立即退出")
    generate.add_argument("--poll-interval", type=float, default=10)
    generate.add_argument("--timeout", type=float, default=1800)
    generate.add_argument("--dry-run", action="store_true", help="只显示请求，不调用 API")
    generate.set_defaults(handler=handle_generate)

    status = subparsers.add_parser("status", help="查询任务并可选下载视频")
    status.add_argument("task_id")
    status.add_argument("--output", type=Path)
    status.add_argument("--watermark", action="store_true")
    status.set_defaults(handler=handle_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
