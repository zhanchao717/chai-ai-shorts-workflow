#!/usr/bin/env python3
"""柴主编 · 封面背景图生成（走 Codex CLI 内置生图，ChatGPT 订阅额度，不按张计费）

为什么这样接：
  - **文字绝不由图像模型生成**。中文经 AI 出图必然出现糊字/错字，那是 P0 级事故。
    所以：AI 只画「背景/氛围」，中文标题/标签/人物仍由 `cover.html` 用字体确定性渲染。
  - **一次生成、固定复用**：产物落到 `<proj>/assets/cover-bg.png`，之后每次出封面都读这个文件
    → 封面仍可逐字节复现（AI 每次出图都不同，不能在渲染时现生成）。
  - 生成通道 = `codex exec --enable image_generation`，走 ChatGPT 订阅（本机 `auth_mode=chatgpt`）。

用法：
  # 按 spec 生成（prompt 由 spec.cover 的 kicker/主题自动拼；已存在则跳过）
  python3 scripts/gen_chai_cover_bg.py --spec specs/169.json --proj videos/ai-deepfake-remedy

  # 手工给 prompt
  python3 scripts/gen_chai_cover_bg.py --proj videos/xxx --prompt "dark tech background ..."

  # 覆盖重生成
  python3 scripts/gen_chai_cover_bg.py --spec specs/169.json --proj videos/xxx --force

退出码：0 = 成功（或已存在而跳过）；2 = 环境不可用；3 = 生成失败（**含额度耗尽**）。
"""
from __future__ import annotations
import argparse, json, os, pathlib, shutil, subprocess, sys, time

CODEX_CANDIDATES = [
    pathlib.Path.home() / ".local/bin/codex",
    pathlib.Path.home() / ".codex/plugins/.plugin-appserver/codex",
]
TIMEOUT_S = 600          # codex exec 首轮会很慢（工具冷启）
SKEW_MS = 5_000          # 与 codex 落盘时间的容差


def codex_bin() -> pathlib.Path | None:
    for p in CODEX_CANDIDATES:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    found = shutil.which("codex")
    return pathlib.Path(found) if found else None


def codex_home() -> pathlib.Path:
    return pathlib.Path(os.environ.get("CODEX_HOME") or (pathlib.Path.home() / ".codex"))


def image_flag(bin_: pathlib.Path) -> str | None:
    """新 CLI 只有 image_generation；旧版还有 imagegenext（且拒绝新名字）。"""
    try:
        out = subprocess.run([str(bin_), "features", "list"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        return None
    if "imagegenext" in out:
        return "imagegenext"
    if "image_generation" in out:
        return "image_generation"
    return None


def auth_mode() -> str:
    f = codex_home() / "auth.json"
    try:
        return json.loads(f.read_text()).get("auth_mode", "unknown")
    except Exception:
        return "unknown"


def newest_image(since: float) -> pathlib.Path | None:
    """在 $CODEX_HOME/generated_images 下找 since 之后的最新图片（可能落在时间戳子目录里）。"""
    root = codex_home() / "generated_images"
    if not root.is_dir():
        return None
    floor = since - SKEW_MS / 1000
    best: tuple[float, pathlib.Path] | None = None
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        st = p.stat()
        if st.st_mtime < floor or st.st_size < 10_000:      # 缩略图/占位件太小
            continue
        if best is None or st.st_mtime > best[0]:
            best = (st.st_mtime, p)
    return best[1] if best else None


def build_prompt(spec: dict | None, extra: str) -> str:
    """背景 prompt：**明确禁文字**，只描述氛围与配色，并给足中央留白。"""
    theme = ""
    if spec:
        c = spec.get("cover", {})
        theme = f"topic hint (do NOT render any of this text): {c.get('kicker','')} / {c.get('act','')}"
    return (
        "Generate ONE image: an abstract, high-contrast tech-style BACKGROUND for a Chinese "
        "short-video cover, landscape 4:3 (1440x1080). Dark charcoal/navy base, subtle diagonal "
        "stripes, a soft radial glow, faint dot grid, cinematic vignette. Leave a large clean empty "
        "area in the middle for a later text overlay. Flat vector-meets-photographic, uncluttered, "
        "premium look. "
        "STRICT RULES: absolutely NO text, NO letters, NO numbers, NO logos, NO watermarks, "
        "NO UI mockups, NO people, NO animals, NO hands. Do not draw any typography of any language. "
        + (f"\n{theme}" if theme else "") + (f"\n{extra}" if extra else "") +
        "\nSave the result as a PNG file."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="specs/NNN.json（用过它的 cover 字段拼主题提示）")
    ap.add_argument("--proj", required=True, help="工程目录，产物写 <proj>/assets/cover-bg.png")
    ap.add_argument("--prompt", default="", help="额外的风格/主题描述")
    ap.add_argument("--force", action="store_true", help="已存在也重新生成")
    ap.add_argument("--timeout", type=int, default=TIMEOUT_S)
    a = ap.parse_args()

    proj = pathlib.Path(a.proj).resolve()
    assets = proj / "assets"
    out = assets / "cover-bg.png"
    if out.is_file() and not a.force:
        print(f"ℹ️ 已存在，跳过（封面可复现性优先）：{out}")
        return 0

    bin_ = codex_bin()
    if not bin_:
        print("❌ 找不到 codex CLI（试过 ~/.local/bin/codex 与插件目录）——本机无法生图", file=sys.stderr)
        return 2
    mode = auth_mode()
    if mode != "chatgpt":
        print(f"⚠️ auth_mode = {mode}（期望 chatgpt 订阅登录）；继续尝试，失败请 codex login", file=sys.stderr)
    flag = image_flag(bin_)
    if not flag:
        print("❌ 该 codex 版本的 features list 里没有 image_generation/imagegenext", file=sys.stderr)
        return 2

    spec = None
    if a.spec:
        spec = json.loads(pathlib.Path(a.spec).read_text())
    prompt = build_prompt(spec, a.prompt)
    started = time.time()
    print(f"▶ codex({bin_.name} {flag}) 生成封面背景 → {out}")

    env = dict(os.environ, PATH=str(bin_.parent) + os.pathsep + os.environ.get("PATH", ""))
    try:
        r = subprocess.run(
            [str(bin_), "exec", "-s", "workspace-write", "--skip-git-repo-check",
             "--enable", flag, "-"],
            input=prompt, capture_output=True, text=True, timeout=a.timeout, env=env)
    except subprocess.TimeoutExpired:
        print(f"❌ codex exec 超时（>{a.timeout}s）", file=sys.stderr)
        return 3

    blob = (r.stdout or "") + (r.stderr or "")
    # ⚠️ 关键：额度耗尽时 codex 仍然退出码 0，只在文本里报错 → 必须抓文本
    for needle in ("usage limit", "hit your usage limit", "quota", "rate limit", "insufficient_quota"):
        if needle.lower() in blob.lower():
            line = next((l for l in blob.splitlines() if needle.lower() in l.lower()), needle)
            print(f"❌ 额度/配额受限：{line.strip()[:200]}", file=sys.stderr)
            print("   → 走订阅额度，等额度恢复后重试；或改付费 OpenAI Images API", file=sys.stderr)
            return 3
    if "ERROR" in blob and "image" not in blob.lower():
        print(f"❌ codex 报错：{blob.strip()[-300:]}", file=sys.stderr)
        return 3

    got = newest_image(started)
    if not got:
        print("❌ 没找到新生成的图片（$CODEX_HOME/generated_images）", file=sys.stderr)
        print("   codex 输出尾部：", blob.strip()[-300:], file=sys.stderr)
        return 3

    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(got, out)
    print(f"✅ 已生成 {out}  （来源 {got}，{out.stat().st_size//1024} KB）")
    print("   ⚠️ 该文件要提交进工程：封面后续渲染都读它，保证可复现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
