#!/usr/bin/env python3
"""Generate local Chinese narration with CosyVoice3 on Apple Silicon."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


DEFAULT_INSTRUCTION = (
    "使用自然、温暖、亲切的普通话女声，像朋友聊天一样流畅；"
    "语速稍快，停顿轻巧，重点词有适度强调，不要播音腔。"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--instruction", default=DEFAULT_INSTRUCTION)
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument("--variant", default="8bit-full", choices=("8bit", "8bit-full", "bf16"))
    args = parser.parse_args()

    project = Path(__file__).resolve().parent.parent
    executable = project / "tools" / "speech-local" / "libexec" / "speech"
    if not executable.is_file():
        raise SystemExit(f"CosyVoice executable is missing: {executable}")

    text = args.text if args.text is not None else args.input.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("Narration text is empty")

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(executable),
        "speak",
        text,
        "--engine",
        "cosyvoice",
        "--cosyvoice-variant",
        args.variant,
        "--language",
        "chinese",
        "--cosy-instruct",
        args.instruction,
        "--seed",
        str(args.seed),
        "--verbose",
        "--output",
        str(output),
    ]
    subprocess.run(command, cwd=project, check=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise SystemExit("CosyVoice produced no audio")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
