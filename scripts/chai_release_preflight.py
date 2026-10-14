#!/usr/bin/env python3
"""Offline release package checks. Never opens a browser or submits a video."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from chai_xhs_copy_check import body_of, clean, pick, similar, split_sections, title_of

REQUIRED = ("video", "portrait_cover", "landscape_cover", "copy", "script", "storyboard",
            "sources", "technical_qc", "editorial_review")
ROUTES = {
    "douyin": {"horizontal": "landscape_cover", "vertical": "portrait_cover"},
    "xiaohongshu": {"cover": "portrait_cover"},
    "weixinchannel": {"cover": "portrait_cover"},
}


def duration_bounds() -> tuple[float, float]:
    config = Path(__file__).resolve().parents[1] / "workflows/chai-editor-single-topic-config.json"
    limits = json.loads(config.read_text())["durationSeconds"]
    minimum, maximum = float(limits["min"]), float(limits["max"])
    if not 0 < minimum < maximum:
        raise ValueError("invalid durationSeconds contract")
    return minimum, maximum


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("artifact path must stay inside the package")
    return path


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        b = f.read(24)
    if len(b) != 24 or b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
        raise ValueError("cover must be a PNG with an IHDR chunk")
    return struct.unpack(">II", b[16:24])


def check(root: Path, ffprobe: str | None) -> dict:
    root = root.resolve()
    errors, warnings, paths = [], [], {}
    result = {"scope": "local_package_only", "platform_page_verified": False,
              "publish_authorized": False, "cover_routing": ROUTES,
              "errors": errors, "warnings": warnings}
    spec = json.loads((root / "release-spec.json").read_text())
    if spec.get("schema_version") != 1:
        errors.append("release-spec.schema_version must be 1")
    artifacts = spec.get("artifacts", {})
    for key in REQUIRED:
        item = artifacts.get(key)
        if not isinstance(item, dict):
            errors.append(f"missing artifact: {key}")
            continue
        try:
            p = inside(root, item["path"])
            if not p.is_file():
                raise ValueError("file missing")
            expected = item.get("sha256", "")
            if not re.fullmatch(r"[a-f0-9]{64}", expected) or sha256(p) != expected:
                errors.append(f"{key}: SHA-256 mismatch or missing")
            paths[key] = p
        except (KeyError, TypeError, ValueError, OSError) as e:
            errors.append(f"{key}: {e}")
    video_hash = artifacts.get("video", {}).get("sha256")
    for key in ("technical_qc", "editorial_review"):
        item = artifacts.get(key, {})
        if not video_hash or item.get("video_sha256") != video_hash:
            errors.append(f"{key}: review is not bound to this final video SHA-256")
    review = artifacts.get("editorial_review", {})
    if "editorial_review" in paths and video_hash not in paths["editorial_review"].read_text():
        errors.append("editorial_review: report text does not name this final video SHA-256")
    if type(review.get("p0_open")) is not int or review["p0_open"] != 0:
        errors.append("editorial_review: P0 count must be explicitly zero")
    for field in ("listened", "watched_continuously"):
        if not isinstance(review.get(field), bool):
            errors.append(f"editorial_review: record actual {field} as true/false")
        elif review[field] is False:
            warnings.append(f"{field}=false: this preflight does not replace audible/continuous review")
    for key, size in (("portrait_cover", (1080, 1440)), ("landscape_cover", (1440, 1080))):
        if key in paths:
            try:
                actual = png_size(paths[key])
                if actual != size:
                    errors.append(f"{key}: {actual}, expected {size}; do not swap cover slots")
            except (ValueError, OSError) as e:
                errors.append(f"{key}: {e}")
    if "technical_qc" in paths:
        qc = json.loads(paths["technical_qc"].read_text())
        if qc.get("status") != "PASS":
            errors.append("technical_qc must report PASS")
    if "copy" in paths:
        sections = split_sections(paths["copy"].read_text())
        data = {}
        for key, label, budget in (("douyin", "抖音", 30), ("xiaohongshu", "小红书", 20),
                                   ("weixinchannel", "视频号", 16)):
            sec = pick(sections, label) or ""
            title, body = title_of(sec) or "", body_of(sec) or ""
            data[key] = (title, body)
            if not title or not body:
                errors.append(f"{label}: missing title/body")
            if len(title) > budget:
                errors.append(f"{label}: title {len(title)} exceeds local budget {budget}")
            if re.search(r"https?://|www\.", sec, re.I):
                errors.append(f"{label}: public copy contains a webpage URL")
            if key == "weixinchannel" and re.search(r"[^\w\s\u4e00-\u9fff]", title):
                errors.append("视频号: title contains punctuation outside the conservative set tested on EP.227")
            if key == "xiaohongshu" and len(body) > 1000:
                errors.append("小红书: body exceeds local budget 1000")
        xhs = clean("".join(data["xiaohongshu"]))
        for key in ("douyin", "weixinchannel"):
            if similar(xhs, clean("".join(data[key]))) >= .90:
                errors.append(f"小红书: copy similarity to {key} >=90%; editorial rewrite needed")
    if "video" in paths:
        executable = ffprobe or os.environ.get("CHAI_FFPROBE") or shutil.which("ffprobe")
        if not executable:
            errors.append("ffprobe unavailable; install/provide --ffprobe, media specs not checked")
        else:
            proc = subprocess.run([executable, "-v", "error", "-show_streams", "-show_format",
                                   "-of", "json", str(paths["video"])], capture_output=True,
                                  text=True, timeout=45)
            if proc.returncode:
                errors.append("ffprobe failed on final video")
            else:
                probe = json.loads(proc.stdout)
                streams = probe.get("streams", [])
                v = next((s for s in streams if s.get("codec_type") == "video"), {})
                a = next((s for s in streams if s.get("codec_type") == "audio"), {})
                if (v.get("width"), v.get("height"), v.get("codec_name"), a.get("codec_name")) != (1080, 1920, "h264", "aac"):
                    errors.append("video must be 1080x1920 H.264 with AAC")
                rate = v.get("avg_frame_rate", "0/1").split("/")
                if len(rate) != 2 or float(rate[1]) == 0 or abs(float(rate[0])/float(rate[1]) - 30) > .01:
                    errors.append("video must be 30fps")
                duration = float(probe.get("format", {}).get("duration", 0))
                minimum, maximum = duration_bounds()
                if not minimum <= duration <= maximum:
                    errors.append(f"duration outside local {minimum:g}–{maximum:g}s contract")
                result["media"] = {"duration_s": duration, "video_sha256": sha256(paths["video"])}
    result["status"] = "FAIL" if errors else "PASS"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("package", type=Path)
    ap.add_argument("--ffprobe", help="ffprobe executable; never bundled as a machine-specific symlink")
    ap.add_argument("--out", type=Path, help="optional JSON report path")
    args = ap.parse_args()
    try:
        result = check(args.package, args.ffprobe)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, StopIteration, subprocess.SubprocessError) as e:
        result = {"status": "FAIL", "scope": "local_package_only", "errors": [str(e)], "warnings": []}
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
