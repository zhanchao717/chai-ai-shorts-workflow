#!/usr/bin/env python3
"""柴主编 · MiniMax H3 视频生成（reference-to-video）。

凭据：**只从系统钥匙串读**，服务名 `MINIMAX_API_KEY`（账号 `minimax`）。
    security add-generic-password -s MINIMAX_API_KEY -a minimax -w '<key>'
也可以用环境变量 MINIMAX_API_KEY 覆盖。脚本内不保存任何密钥。

⚠️ 前提：H3 需要 MiniMax 的 **Pay-as-you-go** 方案。
   网页版（hailuoai.video）的积分与 API 额度是两套，不能通用。
   余额不足时接口返回 402 insufficient_balance_error (1008)。

用法：
  # 用参考图生成（本项目主力场景：角色图 + 场景图）
  python3 scripts/chai_h3_generate.py \
      --character videos/chai-life-guide-comedy-v1/assets/character/chai-shiba-sprites.png \
      --scene     videos/chai-life-guide-comedy-v1/assets/scenes/office.png \
      --prompt-file scripts/h3-prompts/office-wave.txt \
      --duration 6 --resolution 768P --ratio 9:16 --out-dir output/h3/office-wave

  # 只提交不等（拿到 task_id 就走）
  python3 scripts/chai_h3_generate.py ... --no-wait

  # 查询 / 下载已有任务
  python3 scripts/chai_h3_generate.py --task-id <id> --out-dir output/h3/office-wave
"""
import argparse, base64, json, os, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

# 区域：国内与国际是**两套账号、互相不能通用**
#   cn   → api.minimaxi.com      钥匙串 dailyvideos-minimax-api-key（与配音同账号）
#   intl → api.minimax.io        钥匙串 MINIMAX_API_KEY
REGIONS = {
    "cn":   ("https://api.minimaxi.com", "dailyvideos-minimax-api-key"),
    "intl": ("https://api.minimax.io",   "MINIMAX_API_KEY"),
}
BASE = REGIONS["cn"][0]          # 由 --region 覆盖
CREATE = f"{BASE}/v2/video_generation"
QUERY = f"{BASE}/v2/query/video_generation/"     # + <task_id>
KEYCHAIN_SERVICE = REGIONS["cn"][1]
MODELS = ("MiniMax-H3", "MiniMax-H3-Max")


def set_region(region: str) -> None:
    global BASE, CREATE, QUERY, KEYCHAIN_SERVICE
    BASE, KEYCHAIN_SERVICE = REGIONS[region]
    CREATE = f"{BASE}/v2/video_generation"
    QUERY = f"{BASE}/v2/query/video_generation/"     # + <task_id>


def api_key() -> str:
    if os.environ.get("MINIMAX_API_KEY"):
        return os.environ["MINIMAX_API_KEY"]
    try:
        out = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
                              "-a", "minimax", "-w"], capture_output=True, text=True).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    sys.exit(f"取不到 API Key：请写入钥匙串（服务名 {KEYCHAIN_SERVICE}）或设置 MINIMAX_API_KEY")


def _req(url: str, key: str, payload=None, method="GET", timeout=180):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 402 or "insufficient_balance" in body:
            sys.exit(f"❌ 余额不足（402）：H3 需要 Pay-as-you-go 方案。\n   {body[:300]}")
        sys.exit(f"❌ HTTP {e.code}: {body[:400]}")


def as_data_url(path: Path, max_side: int = 1024) -> str:
    """把本地图转成 base64 data URL（H3 接受，请求体需 ≤64MB）。"""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        w, h = im.size
        if max(w, h) > max_side:
            r = max_side / max(w, h)
            im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
        buf = path.with_suffix(".h3tmp.jpg")
        im.save(buf, "JPEG", quality=88)
        raw = buf.read_bytes()
        buf.unlink(missing_ok=True)
    except ImportError:
        raw = path.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


def check_body_size(content) -> int:
    """H3 请求体上限 64MB。"""
    n = len(json.dumps({"content": content}).encode())
    if n > 64 * 1024 * 1024:
        sys.exit(f"❌ 请求体 {n/1048576:.1f}MB 超过 64MB 上限；请减少参考或改用公网 URL")
    return n


def submit(args, key: str) -> str:
    prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if not prompt:
        sys.exit("提示词为空")
    if len(prompt) > 2000:
        print(f"  ⚠️ 提示词 {len(prompt)} 字符（官方上限 2000）", file=sys.stderr)

    content = [{"type": "text", "text": prompt}]
    if args.character:
        content.append({"type": "image_url", "role": "reference_image",
                        "image_url": {"url": as_data_url(Path(args.character))}})
    for p in args.ref_image or []:
        content.append({"type": "image_url", "role": "reference_image",
                        "image_url": {"url": as_data_url(Path(p))}})
    if args.scene:
        content.append({"type": "image_url", "role": "reference_image",
                        "image_url": {"url": as_data_url(Path(args.scene))}})
    # 参考图 ≤9；超出直接拦住，别等平台报错
    n_img = sum(1 for c in content if c["type"] == "image_url")
    if n_img > 9:
        sys.exit(f"❌ 参考图 {n_img} 张，超过 H3 上限 9 张")

    body = {"model": args.model, "resolution": args.resolution,
            "duration": args.duration, "ratio": args.ratio, "content": content}
    if args.callback_url:
        body["callback_url"] = args.callback_url
    size = check_body_size(content)
    print(f"  模型 {args.model} · {args.resolution} · {args.duration}s · {args.ratio} · 参考图 {n_img} 张 · 请求体 {size/1024:.0f}KB")

    d = _req(CREATE, key, body, "POST")
    br = d.get("base_resp") or d.get("error") or {}
    if not d.get("task_id") or br.get("status_code") not in (0, None):
        sys.exit(f"❌ 提交失败：{json.dumps(d, ensure_ascii=False)[:400]}")
    print(f"  ✅ 已提交 task_id = {d['task_id']}")
    return d["task_id"]


def _unwrap(d: dict) -> dict:
    """V2 响应把状态与结果嵌在 task 下；旧版是平铺。两种都兼容。"""
    return d.get("task") or d


def poll(task_id: str, key: str, interval: int = 10, timeout: int = 1800):
    t0 = time.time()
    while True:
        t = _unwrap(_req(f"{QUERY}{task_id}", key))   # 任务 ID 在路径里，不是查询参数
        st = (t.get("status") or "").lower()
        el = int(time.time() - t0)
        print(f"  [{el:>4}s] {st or '(等待中)'}", flush=True)
        if st in ("succeeded", "success"):
            return t
        if st in ("failed", "cancelled"):
            sys.exit(f"❌ 任务 {st}：{json.dumps(t, ensure_ascii=False)[:400]}")
        if time.time() - t0 > timeout:
            sys.exit(f"⏱ 超时（{timeout}s），task_id={task_id} 可稍后用 --task-id 续查")
        time.sleep(interval)


def download(d: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    d = _unwrap(d)
    url = ((d.get("content") or {}).get("url")
           or d.get("download_url") or d.get("video_url") or d.get("url"))
    if not url and d.get("file_id"):
        f = _req(f"{BASE}/v1/files/retrieve?file_id={d['file_id']}", os.environ.get("MINIMAX_API_KEY", ""))
        url = (f.get("file") or {}).get("download_url") or f.get("download_url")
    if not url:
        sys.exit(f"❌ 取不到下载地址：{json.dumps(d, ensure_ascii=False)[:300]}")
    dest = out_dir / "h3-output.mp4"
    urllib.request.urlretrieve(url, dest)
    (out_dir / "task.json").write_text(json.dumps(d, ensure_ascii=False, indent=2))
    print(f"  ✅ 已下载 {dest}（{dest.stat().st_size/1048576:.1f}MB）")
    return dest


def main():
    ap = argparse.ArgumentParser(description="MiniMax H3 reference-to-video 生成器")
    ap.add_argument("--character", help="角色参考图（identity-preserve）")
    ap.add_argument("--scene", help="场景参考图")
    ap.add_argument("--ref-image", action="append", help="额外参考图，可重复")
    ap.add_argument("--prompt-file", help="提示词文件（≤2000 字符）")
    ap.add_argument("--region", default="cn", choices=tuple(REGIONS),
                    help="cn=国内 api.minimaxi.com（与配音同账号，默认）；intl=国际 api.minimax.io")
    ap.add_argument("--model", default="MiniMax-H3", choices=MODELS)
    ap.add_argument("--duration", type=int, default=6, help="4-15（H3-Max 为 5-15）")
    ap.add_argument("--resolution", default="768P", choices=("768P", "2K", "480P"))
    ap.add_argument("--ratio", default="9:16", choices=("21:9", "16:9", "4:3", "1:1", "3:4", "9:16"))
    ap.add_argument("--callback-url")
    ap.add_argument("--task-id", help="只查询/下载已有任务")
    ap.add_argument("--out-dir", default="output/h3")
    ap.add_argument("--no-wait", action="store_true")
    args = ap.parse_args()

    set_region(args.region)
    print(f"  区域 {args.region} → {BASE}", flush=True)
    key = api_key()
    out = Path(args.out_dir)

    if args.task_id:
        d = poll(args.task_id, key)
        download(d, out)
        return

    if not args.prompt_file:
        ap.error("需要 --prompt-file（或 --task-id 查询已有任务）")
    tid = submit(args, key)
    if args.no_wait:
        print(f"  （未等待）task_id={tid}")
        return
    d = poll(tid, key)
    download(d, out)


if __name__ == "__main__":
    main()
