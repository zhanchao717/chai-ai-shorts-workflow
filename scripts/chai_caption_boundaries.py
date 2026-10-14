#!/usr/bin/env python3
"""Find protected words split across adjacent caption groups; never rewrites timing."""
import argparse
import json
from pathlib import Path

DEFAULT_TERMS = ["用户", "普通用户", "开发者", "OpenAI", "Gemini", "Argon", "Ultra用户"]


def check(groups, terms):
    splits, short = [], []
    for i, g in enumerate(groups):
        if len(g["text"].strip()) <= 2 or float(g["end"]) - float(g["start"]) < .35:
            short.append({"group": g.get("id", i), "text": g["text"], "start": g["start"]})
    for a, b in zip(groups, groups[1:]):
        if a.get("frame") != b.get("frame") or float(b["start"]) - float(a["end"]) > .3:
            continue
        joined = a["text"] + b["text"]
        boundary = len(a["text"])
        for term in terms:
            offset = 0
            while True:
                pos = joined.find(term, offset)
                if pos < 0:
                    break
                if pos < boundary < pos + len(term):
                    splits.append({"term": term, "left": a["text"], "right": b["text"],
                                   "start": a["start"], "boundary": b["start"]})
                offset = pos + 1
    return {"protected_word_splits": splits, "short_groups": short,
            "note": "调整字幕组边界，保留原词时间；短组需人工结合停顿判断。此工具不判断口播发音。"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("captions", type=Path)
    ap.add_argument("--terms", nargs="*", default=[])
    ap.add_argument("--strict", action="store_true", help="exit 1 for protected words split across groups")
    args = ap.parse_args()
    data = json.loads(args.captions.read_text())
    result = check(data["groups"], list(dict.fromkeys(DEFAULT_TERMS + args.terms)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and result["protected_word_splits"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
