#!/usr/bin/env python3
"""小红书文案门禁（XHS copy gate）。

目的：阻止「三平台同一段文案」——小红书正文与抖音/视频号逐字相同即不合格。
契约见 workflows/xhs-copy-template.md。

用法：
    python3 scripts/chai_xhs_copy_check.py <publish-copy.md>

退出码：0 = 无 ❌；1 = 有 ❌（不得提交小红书）；2 = 用法/解析错误。
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF"
    "\U00002190-\U000021FF\U00002B00-\U00002BFF\U0000FE0F\U00002049]"
)
HEADING = re.compile(r"^##\s*(.+?)\s*$", re.M)

MIN_TITLE, MAX_TITLE = 12, 30          # 单位为"显示宽度"：CJK/全角算 2，ASCII 算 1
MIN_TITLE_RAW, MAX_TITLE_RAW = 8, 20   # 同时限制原始字符数
MIN_BODY, MAX_BODY = 200, 420
MIN_BLANKS = 3
MIN_EMOJI = 3
MIN_TAGS, MAX_TAGS = 3, 6
MAX_PARA_CHARS = 40
MAX_OPEN_CHARS = 30


def display_width(s: str) -> int:
    """标题长度按显示宽度计：CJK/全角 = 2，其余 = 1（小红书标题按视觉长度感受）。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def split_sections(text: str) -> dict[str, str]:
    """按 '## 平台名' 切段，返回 {平台名: 正文}。"""
    sections: dict[str, str] = {}
    marks = list(HEADING.finditer(text))
    for i, m in enumerate(marks):
        name = m.group(1).strip()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        sections[name] = text[m.end():end]
    return sections


def pick(sections: dict[str, str], *keys: str) -> str | None:
    for name, body in sections.items():
        if any(k in name for k in keys):
            return body
    return None


def field(section: str, *labels: str) -> str | None:
    """取 **标题（选一）** 之后的第一个非空行，或 **正文** 段。"""
    for label in labels:
        m = re.search(r"\*\*" + label + r"[^*]*\*\*[^\n]*\n(.*?)(?=\n\*\*|\Z)", section, re.S)
        if m:
            return m.group(1).strip()
    return None


def title_of(section: str) -> str | None:
    raw = field(section, "标题")
    if not raw:
        return None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+[.、)]\s*", "", line)      # 去掉 "1. "
        line = line.strip("`*_ ")
        if line:
            return line
    return None


def body_of(section: str) -> str | None:
    raw = field(section, "正文")
    if raw is None:
        return None
    return raw.strip()


def tags_of(section: str) -> list[str]:
    raw = field(section, "话题") or ""
    return re.findall(r"#[^\s#]+", raw)


def clean(text: str) -> str:
    """比较用：去掉所有空白与标签。"""
    text = re.sub(r"#[^\s#]+", "", text)
    return re.sub(r"\s+", "", text)


def similar(a: str, b: str) -> float:
    """字符二元组 Dice 相似度（标准库实现，不依赖第三方）。"""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    bg = lambda s: {s[i:i + 2] for i in range(len(s) - 1)} or {s}
    A, B = bg(a), bg(b)
    return 2 * len(A & B) / (len(A) + len(B))


def check(md_path: Path) -> int:
    text = md_path.read_text(encoding="utf-8")
    sections = split_sections(text)
    xhs = pick(sections, "小红书", "XHS", "xhs")
    if xhs is None:
        print("❌ 未找到 `## 小红书` 段")
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    title = title_of(xhs)
    body = body_of(xhs)
    tags = tags_of(xhs)

    # ---- 标题 ----
    if not title:
        errors.append("标题缺失")
    else:
        n = display_width(title)
        nr = len(title)
        if nr > MAX_TITLE_RAW:
            errors.append(f"标题原始 {nr} 字，超过本账号预检上限 {MAX_TITLE_RAW} 字：{title}")
        elif nr < MIN_TITLE_RAW or not (MIN_TITLE <= n <= MAX_TITLE):
            warnings.append(f"标题较短或视觉较宽（{nr} 字 / 显示宽度 {n}），检查缩略图可读性")

    # ---- 正文 ----
    if not body:
        errors.append("正文缺失")
    else:
        n = len(body)
        if n < MIN_BODY:
            warnings.append(f"正文 {n} 字，检查是否已经给出观众需要的具体判断或步骤；无需凑字")
        if n > MAX_BODY:
            warnings.append(f"正文 {n} 字，检查首屏价值和可扫读性")
        if n > 1000:
            errors.append("正文超过本账号保守预检预算 1000 字；以发布页计数复核")
        if re.search(r"https?://|www\.", body, re.I):
            errors.append("公开正文包含网页链接；公开正文不附来源段，材料与 URL 留在内部 sources.md")

        blanks = len(re.findall(r"\n\s*\n", body))
        if blanks < MIN_BLANKS:
            warnings.append(f"空行分段只有 {blanks} 个，检查手机上是否便于扫读")

        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        logical_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        long_lines = [ln for ln in logical_lines if len(ln) > MAX_PARA_CHARS]
        if long_lines:
            warnings.append(f"{len(long_lines)} 行超过 {MAX_PARA_CHARS} 字，可按语义分段：{long_lines[0][:24]}…")

        first = logical_lines[0] if logical_lines else ""
        if len(first) > MAX_OPEN_CHARS:
            warnings.append(f"首句 {len(first)} 字，检查首屏能否看见具体价值")

    # ---- 标签 ----
    if not (MIN_TAGS <= len(tags) <= MAX_TAGS):
        warnings.append(f"标签 {len(tags)} 个，建议只保留相关话题，不凑数量")

    # ---- 跨平台去重（本门禁的核心） ----
    # 单平台文案文件（只给小红书一段）没有对照对象，跳过去重而不是报错。
    others = [(pick(sections, "抖音", "douyin"), "抖音"),
              (pick(sections, "视频号", "channels"), "视频号"),
              (pick(sections, "公众号", "wechat"), "公众号")]
    if not any(o for o, _ in others):
        warnings.append("文件里没有其它平台对照段，跨平台去重未执行（单平台文案属正常）")
    xhs_key = clean((title or "") + (body or ""))
    for other, label in others:
        if not other:
            continue
        other_key = clean((title_of(other) or "") + (body_of(other) or ""))
        if not xhs_key or not other_key:
            continue
        r = similar(xhs_key, other_key)
        if r >= 0.90:
            errors.append(f"小红书文案与{label}相似度 {r:.0%}（≥90% 即视为复制）—— 必须独立撰写")
        elif r >= 0.75:
            warnings.append(f"小红书文案与{label}相似度 {r:.0%}，接近复制，检查是否只是换了个开头")

    # ---- 输出 ----
    blank_n = len(re.findall(r"\n\s*\n", body or ""))
    emoji_n = len(EMOJI.findall(body or ""))
    print(f"小红书文案门禁 · {md_path}")
    print(f"  标题 {len(title) if title else 0} 字 | 正文 {len(body) if body else 0} 字 "
          f"| 空行 {blank_n} | emoji {emoji_n} | 标签 {len(tags)}")
    for w in warnings:
        print(f"  ⚠ {w}")
    for e in errors:
        print(f"  ❌ {e}")
    if not errors:
        print("  ✅ PASS —— 文案机械检查通过；仍需内容、封面和平台页面复核")
        return 0
    print(f"  → 共 {len(errors)} 项 ❌，修完重跑；契约见 workflows/xhs-copy-template.md")
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    p = Path(argv[1])
    if not p.exists():
        print(f"文件不存在：{p}")
        return 2
    return check(p)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
