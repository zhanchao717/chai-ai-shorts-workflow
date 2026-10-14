#!/usr/bin/env python3
"""Validate the maintained 柴主编 workflow/config contract before production."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflows" / "chai-editor-single-topic-workflow.md"
CONFIG = ROOT / "workflows" / "chai-editor-single-topic-config.json"
PERFORMANCE_TEMPLATE = ROOT / "workflows" / "chai-editor-performance-template.md"


def main() -> int:
    errors: list[str] = []

    for path in (WORKFLOW, CONFIG, PERFORMANCE_TEMPLATE):
        if not path.is_file():
            errors.append(f"missing required file: {path}")

    if errors:
        return fail(errors)

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    template_text = PERFORMANCE_TEMPLATE.read_text(encoding="utf-8")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    match = re.search(r"^版本：([^\s]+)", workflow_text, flags=re.MULTILINE)
    workflow_version = match.group(1) if match else None
    config_version = config.get("version")
    if not workflow_version:
        errors.append("workflow version is missing")
    elif workflow_version != config_version:
        errors.append(
            f"version mismatch: workflow={workflow_version}, config={config_version}"
        )

    if config.get("autoPublish") is not False:
        errors.append("autoPublish must be false")
    if config.get("overwriteExisting") is not False:
        errors.append("overwriteExisting must be false")

    duration = config.get("durationSeconds", {})
    minimum = duration.get("min")
    maximum = duration.get("max")
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        errors.append("durationSeconds.min/max must be numeric")
    elif not 0 < minimum < maximum:
        errors.append("durationSeconds must satisfy 0 < min < max")
    else:
        for name, profile in duration.get("profiles", {}).items():
            pmin = profile.get("min")
            pmax = profile.get("max")
            if not isinstance(pmin, (int, float)) or not isinstance(pmax, (int, float)):
                errors.append(f"duration profile {name} must have numeric min/max")
            elif not minimum <= pmin < pmax <= maximum:
                errors.append(f"duration profile {name} is outside the global range")

    video = config.get("video", {})
    expected_video = {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "videoCodec": "h264",
        "audioCodec": "aac",
    }
    for key, expected in expected_video.items():
        if video.get(key) != expected:
            errors.append(f"video.{key} must be {expected!r}")

    if not config.get("safeZones") or not config.get("speechBar"):
        errors.append("safeZones and speechBar are required")

    covers = config.get("covers", [])
    cover_names = {cover.get("name") for cover in covers}
    expected_covers = {"xiaohongshu-3x4", "landscape-4x3"}
    if cover_names != expected_covers:
        errors.append(f"covers must be exactly {sorted(expected_covers)}")
    for cover in covers:
        if not cover.get("safeZone"):
            errors.append(f"cover {cover.get('name', '<unnamed>')} is missing safeZone")

    required_workflow_terms = (
        "performance-record.md",
        "chai-editor-performance-template.md",
        "不自动发布",
        "不覆盖",
    )
    for term in required_workflow_terms:
        if term not in workflow_text:
            errors.append(f"workflow is missing required contract term: {term}")

    required_template_terms = (
        "24 小时数据",
        "72 小时数据",
        "每千次播放新增关注",
        "主页访问到关注转化率",
    )
    for term in required_template_terms:
        if term not in template_text:
            errors.append(f"performance template is missing: {term}")

    # 版本新鲜度提醒（不阻断）：workflow 或 skill references 里出现比版本号更新的日期标记，提示可能漏 bump。
    def _date_key(s: str):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
        return tuple(map(int, m.groups())) if m else None

    ver_m = re.match(r"(\d{4})-(\d{2})-(\d{2})", config_version or "")
    ver_key = tuple(map(int, ver_m.groups())) if ver_m else None
    scan_texts = [workflow_text]
    skill_refs = ROOT / "workflows" / "references"
    if skill_refs.is_dir():
        for f in skill_refs.glob("*.md"):
            scan_texts.append(f.read_text(encoding="utf-8", errors="replace"))
    if ver_key:
        newest = None
        for t in scan_texts:
            for m in re.finditer(r"20\d{2}-\d{2}-\d{2}", t):
                k = _date_key(m.group(0))
                if k and (newest is None or k > newest):
                    newest = k
        if newest and newest > ver_key:
            print(
                "注意：检测到比版本号更新的日期标记 "
                f"{newest[0]}-{newest[1]:02d}-{newest[2]:02d}，可能漏 bump 版本号。",
                file=sys.stderr,
            )

    if errors:
        return fail(errors)

    print(
        "OK: 柴主编 workflow/config contract is valid "
        f"(version {config_version}, duration {minimum}-{maximum}s)."
    )
    return 0


def fail(errors: list[str]) -> int:
    print("柴主编 workflow/config contract validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
