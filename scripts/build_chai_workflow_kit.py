#!/usr/bin/env python3
"""Build the curated, credential-free private 柴主编 workflow backup."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v2.2-2026-10-01"


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def scan(root):
    patterns = {
        "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "bearer": re.compile(r"Bearer\s+[A-Za-z0-9_\-.]{24,}"),
        "api_key": re.compile(r"\bsk-[A-Za-z0-9_\-]{24,}"),
        "credential_assignment": re.compile(r'''(?i)["']?(?:api_key|access_token|mcp_token|password|client_secret)["']?\s*[:=]\s*["'][^"']{16,}["']'''),
        "signed_url": re.compile(r"(?i)(?:[?&](?:x-amz-signature|x-goog-signature|access_token)=)"),
    }
    findings = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in {".json", ".py", ".md", ".html", ".js", ".yaml"}:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for name, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"file": p.relative_to(root).as_posix(), "type": name})
    return findings


def copy_file(src, dst):
    if src.is_symlink():
        raise ValueError(f"refusing symlink: {src.name}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build(out):
    out = out.resolve()
    if out.exists() or Path(str(out) + ".zip").exists():
        raise ValueError("output already exists; choose a new output name")
    out.mkdir(parents=True)
    for name in ("README.md", "SKILL.md"):
        copy_file(ROOT / "workflows/chai-daily-kit" / name, out / name)
    docs = ["端到端流程.md", "流程打包与优化-2026-10-01.md", "AI公众号与一手信源调研-2026-10-01.md"]
    workflows = ["chai-editor-single-topic-workflow.md", "chai-editor-single-topic-config.json",
                 "chai-editorial-brief-template.md", "chai-editor-performance-template.md",
                 "xhs-copy-template.md", "chai-platform-publish-playbook.md",
                 "publish-state-template.json", "chai-stage-cost-template.json",
                 "release-spec-template.json", "chai-news-radar-sources.json", "chai-news-radar-workflow.md"]
    scripts = ["validate_chai_editor_contract.py", "chai_xhs_copy_check.py",
               "chai_release_preflight.py", "chai_caption_boundaries.py", "chai_news_radar.py",
               "test_chai_news_radar.py", "daily_topics.sh"]
    for folder, names in (("docs", docs), ("workflows", workflows), ("scripts", scripts)):
        for name in names:
            copy_file(ROOT / folder / name, out / folder / name)
    copy_file(ROOT / "scripts/chai_verify_kit.py", out / "verify-kit.py")
    config = out / "workflows/chai-editor-single-topic-config.json"
    data = json.loads(config.read_text())
    for key in ("projectRoot", "referenceProject", "schedule"):
        data.pop(key, None)
    config.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    doc = out / "docs/端到端流程.md"
    s = doc.read_text()
    s = re.sub(r"旧流程保存在.*?\n", "历史调研与旧流程另存于原工作区；包内为现行规则快照。\n", s, count=1)
    s = s.replace("workflows/chai-daily-kit/README.md", "README.md")
    doc.write_text(s)
    workflow = out / "workflows/chai-editor-single-topic-workflow.md"
    workflow.write_text(workflow.read_text().replace("chai-daily-kit/README.md", "../README.md")
                        + "\n便携包不包含本机旧 chai_pipeline / chai_publish_mcp 脚本；生产与发布按本包手册和当前工具执行。\n")
    project = ROOT / "videos/gemini4-impact-227-v2"
    dst = out / "example/project"
    project_files = ["index.html", "build_video.py", "meta.json", "package.json", "hyperframes.json",
                     "hyperframes.lock.json", "audio_meta.json", "caption_groups.json",
                     "SCRIPT.md", "STORYBOARD.md", "sources.md", "design.md"]
    for name in project_files:
        copy_file(project / name, dst / name)
    # HyperFrames normalized DOCTYPE casing in the archived HTML. Match the
    # exported generator to those bytes without changing the published project.
    generator = dst / "build_video.py"
    generator.write_text(generator.read_text().replace("<!doctype", "<!DOCTYPE")
                         .replace(" data-layout-allow-overlap>", ' data-layout-allow-overlap="">'))
    for folder in ("assets", "compositions", "covers"):
        for p in sorted((project / folder).rglob("*")):
            if p.is_file() and "node_modules" not in p.parts and "__pycache__" not in p.parts:
                copy_file(p, dst / p.relative_to(project))
    (dst / "README.md").write_text("""# EP.227 参考工程

保留原配音、字幕与画面。`python3 build_video.py` 可从本目录数据重建 HTML；`npm run check` / `npm run render` 使用原固定 HyperFrames 版本。
旧 build_timeline.py / verify_final.py 依赖原工作区和 macOS afconvert，未打入便携包；成片检查使用包根 scripts/chai_release_preflight.py。新配音的词时间须重新生成，不得沿用本期时间轴。
字幕原件有已记录的 Ultra用户 拆词 P1；这是已发布工程备份。
""")
    release_src = ROOT / "content/episode-227/publish-package-gemini4-v2-2026-10-01"
    release = out / "example/release"
    release_files = ["gemini4-impact-227-v2.mp4", "cover-3x4.png", "cover-4x3.png", "publish-copy.md",
                     "SCRIPT.md", "STORYBOARD.md", "sources.md", "technical-qc.json",
                     "final-independent-review.md", "caption_groups.json", "audio_meta.json",
                     "visual-contact-sheet.jpg", "copy-review.md"]
    for name in release_files:
        copy_file(release_src / name, release / name)
    # Copy is an archival example; the stale draft heading is corrected only in this export.
    cp = release / "publish-copy.md"
    cp.write_text(cp.read_text().replace("EP227 替换候选｜平台文案，未发布", "EP227｜已提交平台文案参考（2026-10-01）"))
    names = {"video": "gemini4-impact-227-v2.mp4", "portrait_cover": "cover-3x4.png",
             "landscape_cover": "cover-4x3.png", "copy": "publish-copy.md", "script": "SCRIPT.md",
             "storyboard": "STORYBOARD.md", "sources": "sources.md", "technical_qc": "technical-qc.json",
             "editorial_review": "final-independent-review.md"}
    artifacts = {key: {"path": name, "sha256": digest(release / name)} for key, name in names.items()}
    for key in ("technical_qc", "editorial_review"):
        artifacts[key]["video_sha256"] = artifacts["video"]["sha256"]
    artifacts["editorial_review"].update(p0_open=0, listened=False, watched_continuously=False)
    (release / "release-spec.json").write_text(json.dumps({"schema_version": 1, "artifacts": artifacts,
         "note": "归档例子；P0=0 仅限原独评的抽帧与资料审查范围，未做听音或连续观看。"}, ensure_ascii=False, indent=2))
    (release / "publication-summary.json").write_text(json.dumps({"episode": 227, "checked_date": "2026-10-01",
        "douyin": {"time": "17:28", "status": "已发布"},
        "xiaohongshu": {"time": "17:26", "status": "审核中"},
        "weixinchannel": {"time": "17:32", "status": "原创审核中"},
        "note": "当时平台侧回查快照；未再刷新当前审核结果。已省略账号、group、签名图片 URL。"}, ensure_ascii=False, indent=2))
    # Preserve provenance, but replace workstation-only prose paths in the exported example.
    for p in out.rglob("*"):
        if p.is_file() and p.suffix in {".md", ".json", ".html", ".py"}:
            s = p.read_text()
            if "<REPO>" in s:
                p.write_text(s.replace("<REPO>", "<原制作工作区>"))
    # Export sanitization can change prose reports; bind the final exported bytes.
    spec_path = release / "release-spec.json"
    final_spec = json.loads(spec_path.read_text())
    for item in final_spec["artifacts"].values():
        item["sha256"] = digest(release / item["path"])
    spec_path.write_text(json.dumps(final_spec, ensure_ascii=False, indent=2))
    (out / "ASSET-NOTES.md").write_text("""# 素材与依赖说明

本包为柴主编个人流程/工程备份。品牌头像与配音是原期制作素材；官方 Gemini 图片来源见 example/project/assets/proof/capture-provenance.json，原句来源见 sources.md。官方 key art 未改原图，合成中有缩放/裁切；原句排版明确标注归属，不是网页截图或产品操作实录。

DM_Mono 字体、GSAP 与 HyperFrames 按各原项目许可使用；本包不提供额外转授权。第三方素材不是新一期的通用素材库，复用时替换为本期材料并记录来源。API 服务、网络调研连接器、浏览器登录状态需在目标环境配置；不包含授权凭据。
""")
    findings = scan(out)
    if findings:
        raise ValueError("credential-like patterns found: " + json.dumps(findings, ensure_ascii=False))
    return out


def seal(out):
    files = {p.relative_to(out).as_posix(): {"sha256": digest(p), "bytes": p.stat().st_size}
             for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}
    (out / "manifest.json").write_text(json.dumps({"version": VERSION, "files": files}, ensure_ascii=False, indent=2))
    archive = Path(str(out) + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name in [*files, "manifest.json"]:
            z.write(out / name, arcname=out.name + "/" + name)
    return {"directory": str(out), "zip": str(archive), "files": len(files), "zip_bytes": archive.stat().st_size,
            "zip_sha256": digest(archive)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seal-existing", action="store_true", help="seal after verification report is added")
    a = ap.parse_args()
    out = a.out.resolve() if a.seal_existing else build(a.out)
    if scan(out):
        raise ValueError("credential-like patterns found; archive refused")
    print(json.dumps(seal(out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
