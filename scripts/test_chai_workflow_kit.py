#!/usr/bin/env python3
"""Exercise the exported kit and real failure cases without publishing anything."""
from __future__ import annotations
import argparse
import ast
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd=None):
    p = subprocess.run([str(x) for x in args], cwd=cwd, text=True, capture_output=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("zip", type=Path)
    ap.add_argument("--ffprobe", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    rows = []
    def case(name, fn):
        try:
            detail = fn()
            rows.append({"name": name, "status": "PASS", "detail": detail})
        except Exception as e:
            rows.append({"name": name, "status": "FAIL", "detail": str(e)})
    with tempfile.TemporaryDirectory(prefix="chai-kit-check-") as t:
        temp = Path(t)
        with zipfile.ZipFile(args.zip) as z:
            assert z.testzip() is None
            for member in z.namelist():
                assert not Path(member).is_absolute() and ".." not in Path(member).parts
            z.extractall(temp / "unpacked")
        kit = next((temp / "unpacked").iterdir())
        release = kit / "example/release"
        probe = args.ffprobe.resolve()
        def cmd_ok(cmd, cwd=kit):
            code, out, err = run(cmd, cwd)
            assert code == 0, (code, out, err)
            summary = out.strip().replace(str(kit), "<解压目录>")
            return summary[:300]
        case("zip_integrity_and_file_hashes", lambda: cmd_ok([sys.executable, kit/"verify-kit.py"]))
        case("contract_in_fresh_directory", lambda: cmd_ok([sys.executable, kit/"scripts/validate_chai_editor_contract.py"]))
        case("valid_release_media_and_bindings", lambda: cmd_ok([sys.executable, kit/"scripts/chai_release_preflight.py", release, "--ffprobe", probe]))
        case("published_xhs_copy", lambda: cmd_ok([sys.executable, kit/"scripts/chai_xhs_copy_check.py", release/"publish-copy.md"]))
        def negative(name, mutate, needle):
            destination = temp / name
            shutil.copytree(release, destination)
            spec_path = destination / "release-spec.json"
            spec = json.loads(spec_path.read_text())
            mutate(destination, spec)
            spec_path.write_text(json.dumps(spec, ensure_ascii=False))
            code, out, err = run([sys.executable, kit/"scripts/chai_release_preflight.py", destination, "--ffprobe", probe])
            assert code == 1, out + err
            assert needle in out, out
            return {"correctly_rejected": needle}
        def swapped(p, s):
            s["artifacts"]["portrait_cover"], s["artifacts"]["landscape_cover"] = s["artifacts"]["landscape_cover"], s["artifacts"]["portrait_cover"]
        case("swapped_cover_roles_rejected", lambda: negative("swap", swapped, "do not swap"))
        def rewrite_copy(p, s, transform):
            f = p / "publish-copy.md"
            f.write_text(transform(f.read_text()))
            s["artifacts"]["copy"]["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        case("public_web_link_rejected", lambda: negative("url", lambda p,s: rewrite_copy(p,s,lambda x:x.replace("谷歌公布", "https://example.com 谷歌公布",1)), "webpage URL"))
        case("wx_title_too_long_rejected", lambda: negative("title-long", lambda p,s: rewrite_copy(p,s,lambda x:x.replace("Gemini4来了 你能用吗", "Gemini4开发者大会发布以后普通用户能不能使用")), "title 25 exceeds"))
        case("wx_punctuation_rejected", lambda: negative("punct", lambda p,s: rewrite_copy(p,s,lambda x:x.replace("Gemini4来了 你能用吗", "Gemini4来了，你能用吗")), "punctuation"))
        def stale_video(p,s):
            v = p / s["artifacts"]["video"]["path"]
            with v.open("ab") as f:
                f.write(b"changed-final-artifact")
            s["artifacts"]["video"]["sha256"] = hashlib.sha256(v.read_bytes()).hexdigest()
        case("changed_video_stale_review_rejected", lambda: negative("stale", stale_video, "review is not bound"))
        case("missing_cover_rejected", lambda: negative("missing-cover", lambda p,s:(p/s["artifacts"]["portrait_cover"]["path"]).unlink(), "file missing"))
        def copy_case(text, expected, needle):
            f = temp / "copy-fixture.md"
            f.write_text(text)
            code, out, err = run([sys.executable, kit/"scripts/chai_xhs_copy_check.py", f])
            assert code == expected and needle in out, out + err
            return {"expected_exit": code}
        short = "## 小红书\n\n**标题**\n先核对开放资格\n\n**正文**\n先核对自己的套餐有没有开放入口。官方还没有给出公众开放日期，别仅凭发布新闻提前升级。\n\n**话题**\n#AI\n"
        case("useful_copy_without_emoji_passes", lambda: copy_case(short,0,"✅"))
        case("duplicated_platform_copy_rejected", lambda: copy_case(short+short.replace("## 小红书","## 抖音"),1,"相似度"))
        def caption_case():
            code,out,err = run([sys.executable, kit/"scripts/chai_caption_boundaries.py", kit/"example/project/caption_groups.json", "--strict"])
            data = json.loads(out)
            assert code == 1 and any(x["term"] == "Ultra用户" and x["boundary"] == 29.2579 for x in data["protected_word_splits"])
            return {"known_split_detected_at_s": 29.2579, "original_video_untouched": True}
        case("known_caption_word_split_detected", caption_case)
        def project_rebuild():
            import re
            project = kit / "example/project"
            # The framework adds editing IDs when saving HTML. They are not
            # authored timing, text, styles, assets or animation instructions.
            def authored_digest(p):
                text = re.sub(r'\sdata-hf-id="[^"]+"', "", p.read_text())
                text = text.replace("<!DOCTYPE", "<!doctype")
                return hashlib.sha256(text.encode()).hexdigest()
            before = {str(p.relative_to(project)):authored_digest(p) for p in project.rglob("*.html")}
            cmd_ok([sys.executable, project/"build_video.py"],project)
            after = {str(p.relative_to(project)):authored_digest(p) for p in project.rglob("*.html")}
            assert before == after, "rebuilding HTML changed authored composition content"
            # Every src used by a composition must resolve to the archived local assets.
            for p in project.rglob("*.html"):
                for ref in re.findall(r'(?:src|data-composition-src)="([^"]+)"', p.read_text()):
                    if ref.startswith(("https:","data:")):
                        continue
                    assert (project/ref).exists() or (p.parent/ref).exists(), (p.name,ref)
            return {"html_files":len(before), "authored_markup_equal":True,
                    "framework_marker_ids_and_doctype_case_excluded":True, "render_tested":False}
        case("editable_project_rebuild_and_local_assets", project_rebuild)
    # Extract only relevant definitions; never import the authenticated publisher module.
    source = ast.parse((ROOT/"scripts/chai_publish_mcp.py").read_text())
    selected = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in {"main","douyin_upload_covers_ui"}]
    import argparse as argparse_module
    env = {"Path":Path,"argparse":argparse_module}
    exec(compile(ast.Module(body=selected,type_ignores=[]),"publisher-functions-only","exec"),env)
    def blocked_flag(flag):
        saved = sys.argv[:]
        sys.argv = ["publisher","dummy-package",flag]
        if flag == "--schedule":
            sys.argv += ["2026-10-02 12:00"]
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                try:
                    env["main"]()
                except SystemExit as e:
                    assert e.code == 2
                    return {"stopped_before_any_platform_call":True}
            raise AssertionError("unsafe flag was accepted")
        finally:
            sys.argv=saved
    for flag in ("--auto-submit","--submit","--schedule"):
        case("legacy_publisher_blocks_"+flag[2:],lambda f=flag:blocked_flag(f))
    def upload_failure_stops():
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/"cover-4x3.png").write_bytes(b"fixture")
            calls=[]
            env.update(DOUYIN_COVER_SLOTS=[(1,"horizontal","cover-4x3.png","设置横封面"),(0,"vertical","cover-3x4.png","设置竖封面")],
                       _cover_b64_jpeg=lambda _:"fixture",_open_cover_editor=lambda *a:"opened",_safe=str,
                       _upload_cover_in_dialog=lambda *a:calls.append(a[2]) or "still uploading")
            with redirect_stdout(io.StringIO()):
                try:env["douyin_upload_covers_ui"]("fixture","fixture",p)
                except RuntimeError:
                    assert calls==["horizontal"]
                    return {"stopped_after_first_cover_failure":True}
            raise AssertionError("unfinished cover did not stop")
    case("legacy_cover_failure_stops_next_slot",upload_failure_stops)
    report={"status":"PASS" if all(x["status"]=="PASS" for x in rows) else "FAIL", "cases":rows,
            "limits":["No live publishing or new UI automation tested","No audio listening or continuous playback","HTML rebuild checked; no fresh-machine HyperFrames re-render","Credential scan is pattern based, not a formal security audit"]}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
