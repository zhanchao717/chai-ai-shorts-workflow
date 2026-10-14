#!/usr/bin/env python3
"""柴主编 · 三平台标题门禁（发布前必过）

背景：视频号标题只允许 书名号《》/引号/冒号/加号/问号/百分号/摄氏度℃；逗号要写空格；
**小数点、连字符、括号、斜杠都不行**（`DeepSeek V4.1` 在视频号必须写 `DeepSeek 4点1`）。
这条坑 2026-09-10 记进交接文档第 1 条，此脚本把它变成门禁。

用法：
  python3 scripts/chai_title_check.py <publish-copy.md> [--json out.json]

退出码：0 = 无 ❌；1 = 有 ❌。只用标准库。
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

PLATFORMS = {"抖音": "douyin", "小红书": "xiaohongshu", "视频号": "weixin"}

# 平台标题字数上限（release-package.md「标题候选」段）
TITLE_MAX = {"douyin": 30, "xiaohongshu": 20, "weixin": 14}

# 视频号标题禁止字符（ASCII 与全角）
WEIXIN_BANNED = {
    ".": "小数点", "．": "小数点", "。": "句号",
    "-": "连字符", "－": "连字符", "—": "破折号", "–": "连字符",
    "(": "括号", ")": "括号", "（": "括号", "）": "括号",
    "[": "方括号", "]": "方括号", "【": "方括号", "】": "方括号",
    "/": "斜杠", "\\": "反斜杠", "|": "竖线",
    ",": "英文逗号", "，": "中文逗号（应改空格）",
    ";": "分号", "；": "分号", "!": "感叹号", "！": "感叹号",
    "&": "与号", "#": "井号", "*": "星号", "@": "At 号",
    "_": "下划线", "=": "等号", "\"": "引号（请用中文引号）", "'": "引号（请用中文引号）",
    "<": "尖括号", ">": "尖括号", "~": "波浪号", "`": "反引号",
}
# 视频号标题允许的 ASCII（其余 ASCII 一律可疑）
WEIXIN_OK_ASCII = set(" +?%℃")
# 建议替换表
SUGGEST = {".": "点", "．": "点", "-": " ", "－": " ", "(": "", ")": "", "（": "", "）": "",
           "/": "或", "，": " ", ",": " ", "：": "：", "!": "。", "！": "。"}


def parse_copy(text: str) -> dict[str, dict]:
    """把 publish-copy.md 解析成 {platform_key: {titles:[...], body:str, tags:[...]}}"""
    out: dict[str, dict] = {}
    cur = None
    mode = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = re.match(r"^##\s*(抖音|小红书|视频号)\s*$", line.strip())
        if m:
            cur = PLATFORMS[m.group(1)]
            out[cur] = {"name": m.group(1), "titles": [], "body": "", "tags": []}
            mode = None
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("**标题"):
            mode = "title"; continue
        if s.startswith("**正文"):
            mode = "body"; continue
        if s.startswith("**话题"):
            mode = "tags"; continue
        # 「**正文**」之后可能紧跟平台尾部标签（#…），此处不切换模式，正文继续累积
        if s.startswith("**"):
            mode = None; continue
        if not s:
            continue
        if mode == "title":
            t = re.sub(r"^\d+[.、)]\s*", "", s)
            if t:
                out[cur]["titles"].append(t)
        elif mode == "body":
            # 正文行累积；若该行以 # 开头（平台话题行），同时记为 tags 但不进正文
            if s.startswith("#"):
                out[cur]["tags"] += re.findall(r"#[^\s#]+", s)
            else:
                out[cur]["body"] += ("\n" if out[cur]["body"] else "") + s
        elif mode == "tags":
            out[cur]["tags"] += [x for x in re.findall(r"#[^\s#]+", s)]
    return out


def suggest(title: str) -> str:
    s = title
    for bad, good in SUGGEST.items():
        s = s.replace(bad, good)
    return re.sub(r"\s{2,}", " ", s).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("copy_md")
    ap.add_argument("--json")
    a = ap.parse_args()

    p = pathlib.Path(a.copy_md).resolve()
    if not p.exists():
        print(f"❌ 找不到 {p}"); return 2
    plats = parse_copy(p.read_text(encoding="utf-8"))

    checks: list[dict] = []
    def add(level, where, msg, fix=""):
        checks.append({"level": level, "where": where, "msg": msg, "fix": fix})

    if not plats:
        add("FAIL", "文件", "没解析到任何平台小节（需为 `## 抖音` / `## 小红书` / `## 视频号`）")
    for key, d in plats.items():
        name = d["name"]
        if not d["titles"]:
            add("FAIL", name, "没有标题（需 `**标题（选一）**` 下 1. 2. …）")
        if not d["body"].strip():
            add("FAIL", name, "正文为空")
        if not d["tags"]:
            add("WARN", name, "没有解析到话题标签（#…）")
        # 视频号正文也扫一遍禁用字符（2026-09-11 加：评审发现只有标题被扫 → 正文违规会让门禁"假绿"）
        if key == "weixin" and d["body"].strip():
            # 正文只扫"真正危险"的符号（中文句读标点在正文里是正常的，不报）
            BODY_BANNED = {k: v for k, v in WEIXIN_BANNED.items()
                           if v not in ("中文逗号（应改空格）", "句号", "分号", "感叹号")}
            body_hits = sorted({BODY_BANNED[c] for c in d["body"] if c in BODY_BANNED})
            if body_hits:
                add("WARN", f"{name}·正文",
                    "正文含标题级禁用字符：" + "、".join(body_hits),
                    "正文若也受平台限制，请改写（如 `V4.1`→`4点1`、`ABot-Earth`→`ABot Earth`）")
        for t in d["titles"]:
            lim = TITLE_MAX.get(key)
            if lim and len(t) > lim:
                add("FAIL", f"{name}·标题「{t}」",
                    f"{len(t)} 字超过平台上限 {lim} 字", f"压缩到 {lim} 字内")
            if key == "weixin":
                hits = sorted({WEIXIN_BANNED[c] for c in t if c in WEIXIN_BANNED})
                ascii_odd = sorted({c for c in t if ord(c) < 128 and c not in WEIXIN_OK_ASCII
                                    and not c.isalnum() and not c.isspace()})
                if hits or ascii_odd:
                    add("FAIL", f"{name}·标题「{t}」",
                        "视频号禁用字符：" + "、".join(hits + [f"ASCII {c!r}" for c in ascii_odd]),
                        f"建议改为「{suggest(t)}」")
            else:
                # 抖音/小红书允许，但同一标题组跨平台复用时提醒统一
                if re.search(r"[0-9]\.[0-9]", t):
                    add("WARN", f"{name}·标题「{t}」",
                        "含小数点版本号；视频号不能这么写 —— 若三平台共用同一标题组，视频号须改写为「…4点1…」",
                        f"视频号版可写「{suggest(t)}」")

    icon = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
    fails = [c for c in checks if c["level"] == "FAIL"]
    warns = [c for c in checks if c["level"] == "WARN"]
    print(f"三平台标题门禁 · {p.name}")
    for c in checks:
        print(f"  {icon[c['level']]} [{c['where']}] {c['msg']}" + (f"\n        → {c['fix']}" if c["fix"] else ""))
    print(f"\n结论：{'PASS' if not fails else 'FAIL'}（❌ {len(fails)} · ⚠️ {len(warns)}）")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            {"file": str(p), "verdict": "PASS" if not fails else "FAIL", "checks": checks},
            ensure_ascii=False, indent=2))
        print(f"[written] {a.json}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
