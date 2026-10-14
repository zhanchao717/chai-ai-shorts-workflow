#!/usr/bin/env python3
"""Verify all allowlisted files against a workflow kit manifest."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_text())
    expected = manifest["files"]
    errors = []
    for name, info in expected.items():
        p = (root / name).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            errors.append(f"missing/unsafe: {name}")
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != info["sha256"] or p.stat().st_size != info["bytes"]:
            errors.append(f"changed: {name}")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.name != "manifest.json"}
    for name in sorted(actual - expected.keys()):
        errors.append(f"unexpected: {name}")
    print(json.dumps({"status": "FAIL" if errors else "PASS", "files": len(expected),
                      "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
