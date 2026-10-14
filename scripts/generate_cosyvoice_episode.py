#!/usr/bin/env python3
"""Generate every daily episode segment with the local CosyVoice runner."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SEGMENTS = ("hook", "lead", "brief1", "brief2", "brief3", "brief4", "verdict", "cta")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--issue", required=True)
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument("--variant", default="8bit-full", choices=("8bit", "8bit-full", "bf16"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    issue = str(args.issue).zfill(3)
    input_dir = project / "content" / f"episode-{issue}" / "audio-text"
    output_dir = project / f"hyperframes-episode-{issue}" / "assets" / "audio"
    runner = project / "scripts" / "generate_cosyvoice.py"
    output_dir.mkdir(parents=True, exist_ok=True)

    for index, segment in enumerate(SEGMENTS):
        source = input_dir / f"{segment}.txt"
        output = output_dir / f"{segment}.wav"
        if output.is_file() and output.stat().st_size > 4096 and not args.force:
            print(f"skip {segment}: {output}", flush=True)
            continue
        if not source.is_file() or source.stat().st_size == 0:
            raise SystemExit(f"Missing narration segment: {source}")
        command = [
            sys.executable,
            str(runner),
            "--input",
            str(source),
            "--output",
            str(output),
            "--seed",
            str(args.seed + index),
            "--variant",
            args.variant,
        ]
        print(f"generate {segment}", flush=True)
        subprocess.run(command, cwd=project, check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
