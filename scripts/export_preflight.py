#!/usr/bin/env python3
"""导出前自检：确认仓库可被人原样使用，而不是只在作者本机能跑。

检查四类问题，每类都是「本地能开、传上去就断」的那种：

  1. 失效相对链接   markdown 里指向 content/、research/ 等未导出目录的 [text](path)
  2. 硬编码本机路径 /Users/<name>/... 之类，别人 clone 下来直接跑不动
  3. 幻影文件       README 让你运行的文件根本不在仓库里
  4. skill 契约     SKILL.md 的 frontmatter 缺 name/description，或同仓重名

用法：
    python3 scripts/export_preflight.py            # 只报告
    python3 scripts/export_preflight.py --fix      # 就地修可自动修的两类
    python3 scripts/export_preflight.py --root .   # 指定仓库根

退出码：0 全通过；1 仍有问题（--fix 修完仍残留的）；2 参数/路径错误。

--fix 只做两件事，且都是幂等的：
  · 失效链接 -> 保留文字、去掉链接，标注「本地工作区路径」
  · 本机绝对路径 -> 替换为 <原制作工作区> 占位符
不能自动修的（幻影文件、frontmatter）只报告，由人判断。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

# 允许「故意不存在」的示例路径：模板占位符、变量路径等
PLACEHOLDER = re.compile(
    r"(NNN|XXX|<[^>]+>|\{|\$|\.\.\.|episode-NNN|publish-package-YYYY|/你的/)"
)

LOCAL_PATH = re.compile(r"(/Users/[A-Za-z0-9._-]+/[^\s`'\"\)]*)")
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
# 命令行里出现的裸文件名才算「让你运行的文件」；正文里的 sources.md 是每期产物，不算
RUNNABLE = re.compile(r"(?:python3?|pip3?|bash|sh|node|npx|\./)\s+\S*?([\w.-]+\.(?:py|sh|mjs|js|json))")
# 只有长得像文件路径的反引号内容才算（排除 `GET /v1/accounts`、`n/1000`、`raw/*.json` 这类）
FILE_LIKE = re.compile(r"^[\w][\w./-]*\.(?:py|sh|mjs|js|json|md|txt|ya?ml)$|^[\w][\w./-]*/$")

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".venv-tts"}
# 这些目录是**故意不导出**的本机工作产物；引用它们不算幻影
NOT_EXPORTED = (
    "content/", "videos/", "videos-with-bgm/", "output/", "copy/", "qa/",
    "research/", "specs/", "renders/", "qc/", "assets_work/", "dailyvideos/", ".media/",
)
# 这些文件的职责就是**搜索**本机路径再替换，改了会把工具本身弄坏
LOCAL_PATH_EXCLUDE = {"build_chai_workflow_kit.py", "export_preflight.py"}


def load_ignore(root: Path) -> list[str]:
    """仓库级例外：.export-preflight.json 里的 {"ignore": ["docs/旧版*.md", ...]}"""
    cfg = root / ".export-preflight.json"
    if not cfg.exists():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"警告: {cfg.name} 解析失败: {exc}", file=sys.stderr)
        return []
    return [str(p) for p in data.get("ignore", [])]


def is_ignored(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch(rel_path, pat) or fnmatch(Path(rel_path).name, pat) for pat in patterns)


IGNORE: list[str] = []


def iter_files(root: Path, suffixes: tuple[str, ...], ignore: list[str] | None = None):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        pats = IGNORE if ignore is None else ignore
        if pats and is_ignored(rel(p, root), pats):
            continue
        if p.suffix.lower() in suffixes:
            yield p


def rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def check_broken_links(root: Path, fix: bool) -> list[str]:
    problems: list[str] = []
    for md in iter_files(root, (".md",)):
        text = md.read_text(encoding="utf-8")
        out = text
        for m in MD_LINK.finditer(text):
            label, target = m.group(1), m.group(2)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0].strip()
            if not path_part or PLACEHOLDER.search(path_part):
                continue
            if (md.parent / path_part).resolve().exists():
                continue
            problems.append(f"断链  {rel(md, root)}  ->  {path_part}")
            if fix:
                out = out.replace(
                    m.group(0), f"{label}（本地工作区路径：{path_part}，仓库内不含）"
                )
        if fix and out != text:
            md.write_text(out, encoding="utf-8")
    return problems


def check_local_paths(root: Path, fix: bool) -> list[str]:
    problems: list[str] = []
    suffixes = (".py", ".sh", ".mjs", ".js", ".json", ".md")
    for f in iter_files(root, suffixes):
        if f.name in LOCAL_PATH_EXCLUDE:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits = [m.group(1) for m in LOCAL_PATH.finditer(text)]
        if not hits:
            continue
        problems.append(
            f"本机路径  {rel(f, root)}  x{len(hits)}  (例: {hits[0]})"
        )
        if fix:
            # 先换掉生产线根，再把剩余家目录收成 ~（保留 Downloads/、.npm/ 等语义）
            new = text.replace(
                str(Path.home() / "Documents" / "dailyvideos"), "<原制作工作区>"
            )
            new = re.sub(r"/Users/[A-Za-z0-9._-]+(?=/)", "~", new)
            if new != text:
                f.write_text(new, encoding="utf-8")
    return problems


def check_phantom_artifacts(root: Path) -> list[str]:
    """文档让你运行/装/复制，但仓库里没有的东西。

    只认两类强信号，避免把 API 字段清单和每期产物误判成缺失文件：
      · 命令行里出现的脚本：`python3 verify-kit.py`
      · 「- `example/project/`：…」这种包内容清单项（带 / 的路径），
        或带「包内/安装/解压/复制」等字样的行里点名的 .py/.json
    """
    problems: list[str] = []
    KEYWORD = re.compile(r"包内|包里|安装|解压|复制|运行|执行|git clone")
    ITEM = re.compile(r"^\s*[-*]\s*`([^`\n]+)`")
    # 文档自己已声明「不在仓库 / 跳过 / 在 /tmp」的行，不算幻影
    SUPPRESS = re.compile(r"不在公开仓库|不在仓库|仓库内不含|跳过即可|只留在|本地工作区路径|/tmp/")

    for doc in iter_files(root, (".md",)):
        where = rel(doc, root)
        seen: set[str] = set()
        for line in doc.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = ITEM.match(line)
            has_kw = bool(KEYWORD.search(line))
            if SUPPRESS.search(line):
                continue

            for m in RUNNABLE.finditer(line):
                name = m.group(1)
                if name in seen:
                    continue
                if (root / name).exists() or any(root.rglob(name)):
                    continue
                seen.add(name)
                problems.append(f"幻影文件  {where} 让你运行 {name}，仓库里没有")

            if not (item or has_kw):
                continue
            for token in re.findall(r"`([^`\n]+)`", line):
                token = token.strip()
                if not token or token in seen:
                    continue
                if PLACEHOLDER.search(token) or token.startswith(("http",) + NOT_EXPORTED):
                    continue
                if "/" in token:
                    if not FILE_LIKE.match(token):
                        continue
                elif not re.search(r"\.(py|sh|mjs)$" if item else r"\.(py|json)$", token):
                    continue
                seen.add(token)
                if (root / token).exists():
                    continue
                base = token.rstrip("/").rsplit("/", 1)[-1]
                if base and any(root.rglob(base)):
                    continue
                problems.append(f"幻影文件  {where} 提到 {token}，仓库里没有")
    return problems


def check_skill_frontmatter(root: Path) -> list[str]:
    problems: list[str] = []
    names: dict[str, str] = {}
    for skill in iter_files(root, (".md",)):
        if skill.name != "SKILL.md":
            continue
        head = skill.read_text(encoding="utf-8")[:600]
        m = re.match(r"^---\n(.*?)\n---", head, re.S)
        if not m:
            problems.append(f"frontmatter  {rel(skill, root)} 缺少 --- 头")
            continue
        block = m.group(1)
        name = re.search(r"^name:\s*(.+)$", block, re.M)
        desc = re.search(r"^description:\s*(.+)$", block, re.M)
        if not name or not name.group(1).strip():
            problems.append(f"frontmatter  {rel(skill, root)} 缺 name")
        else:
            n = name.group(1).strip()
            if n in names:
                problems.append(
                    f"frontmatter  {rel(skill, root)} 与 {names[n]} 重名: {n}"
                )
            names[n] = rel(skill, root)
        if not desc or not desc.group(1).strip():
            problems.append(f"frontmatter  {rel(skill, root)} 缺 description")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="导出前自检")
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--fix", action="store_true", help="就地修可自动修的问题")
    args = ap.parse_args()

    global IGNORE
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"不是目录: {root}", file=sys.stderr)
        return 2
    IGNORE = load_ignore(root)

    checks = [
        ("失效相对链接", lambda: check_broken_links(root, args.fix)),
        ("硬编码本机路径", lambda: check_local_paths(root, args.fix)),
        ("幻影文件", lambda: check_phantom_artifacts(root)),
        ("skill 契约", lambda: check_skill_frontmatter(root)),
    ]

    total = 0
    print(f"导出前自检: {root}{'  (--fix)' if args.fix else ''}\n")
    for title, fn in checks:
        found = fn()
        total += len(found)
        mark = "OK " if not found else f"{len(found):>2} "
        print(f"[{mark}] {title}")
        for line in found[:20]:
            print(f"        {line}")
        if len(found) > 20:
            print(f"        … 另有 {len(found) - 20} 条")
    print()
    if total:
        print(f"共 {total} 项问题。" + ("已自动修复可修部分，请复查。" if args.fix else "加 --fix 修可自动修的部分。"))
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
