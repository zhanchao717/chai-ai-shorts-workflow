#!/usr/bin/env python3
"""Generate speech with OpenAI TTS without storing an API key in the project."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


KEYCHAIN_SERVICE = "dailyvideos-openai-api-key"


def load_api_key() -> str:
    from_environment = os.environ.get("OPENAI_API_KEY", "").strip()
    if from_environment:
        return from_environment

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
    key = result.stdout.strip()
    if not key:
        raise RuntimeError(f"Keychain item {KEYCHAIN_SERVICE!r} is empty")
    return key


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--instructions", type=Path, required=True)
    parser.add_argument("--voice", required=True, choices=("marin", "cedar"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-4o-mini-tts")
    args = parser.parse_args()

    payload = json.dumps(
        {
            "model": args.model,
            "voice": args.voice,
            "input": args.input.read_text(encoding="utf-8").strip(),
            "instructions": args.instructions.read_text(encoding="utf-8").strip(),
            "response_format": "mp3",
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=payload,
        headers={
            "Authorization": f"Bearer {load_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI TTS request failed ({exc.code}): {detail}") from exc

    if len(audio) < 1024:
        raise SystemExit("OpenAI TTS returned an unexpectedly small audio file")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(audio)
    print(json.dumps({"voice": args.voice, "model": args.model, "output": str(args.output), "bytes": len(audio)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
