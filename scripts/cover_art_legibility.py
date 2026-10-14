"""封面底图可读性实测：按 CSS 的 scrim 公式逐像素复算，量「文字带」背后的背景亮度，
再算白字/柠檬绿字对它的 WCAG 对比度。

为什么这么算：视觉模型给的是印象，这里给的是可复现的数字。
输入 = assets/cover-art.png + cover.html 里的 scrim 公式；
文字带坐标 = cover.html 布局规则（窗口坐标 × --ms）。
输出 = 每条文字带的最小对比度（取带内背景亮度的 p95，即最亮的那部分背景 —— 最坏情况）。
"""
import numpy as np
from PIL import Image

ART = {
    "EP.178": ("/Users/chao/Documents/dailyvideos/videos/github-trending-top10/assets/cover-art.png",
               "/Users/chao/Documents/dailyvideos/content/episode-178/cover-gpt/out"),
    "EP.179": ("/Users/chao/Documents/dailyvideos/videos/ai-news-five-releases/assets/cover-art.png",
               "/Users/chao/Documents/dailyvideos/content/episode-179/cover-gpt/out"),
}
BG = (5, 7, 15)          # #05070F
DARK_RGB = np.array([5 / 255, 7 / 255, 15 / 255])


def rel_lum(rgb):
    """WCAG 相对亮度。rgb = 0..1 线性 sRGB 值。"""
    c = np.where(rgb <= 0.03928, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def scrim_alpha(W, H):
    """复算 cover.html 里的 scrim：radial(64% 50% at 50% 30%) → linear180 → 全局 30%。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    # A) 径向：椭圆中心(0.5W,0.30H)，半径(0.64W,0.50H)，alpha .52→0（78% 处为 0）
    nx = (xx - 0.5 * W) / (0.64 * W)
    ny = (yy - 0.30 * H) / (0.50 * H)
    t = np.sqrt(nx ** 2 + ny ** 2)
    a_rad = np.clip(0.52 * (1 - t / 0.78), 0, 0.52)
    # B) 垂直线性：0% .34 → 26% .30 → 62% .30 → 100% .72
    f = yy / max(H - 1, 1)
    a_lin = np.interp(f, [0, .26, .62, 1], [.34, .30, .30, .72])
    # C) 全局
    a_flat = np.full((H, W), 0.30)
    # 合成（CSS 里前面的层在上面）：结果 = art 上叠 flat，再叠 lin，再叠 radial
    a_total = a_flat + a_lin * (1 - a_flat)
    a_total = a_total + a_rad * (1 - a_total)
    return a_total


def cover_fit(art, W, H):
    """background-size:cover 的等价缩放（居中）。"""
    aw, ah = art.size
    k = max(W / aw, H / ah)
    nw, nh = max(1, round(aw * k)), max(1, round(ah * k))
    im = art.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - W) // 2, (nh - H) // 2
    return im.crop((left, top, left + W, top + H))


def bands(ms, out_w, out_h, clip_x0):
    """文字带（输出图坐标）。窗口坐标来自 cover.html 的 .l43/.l34 规则 × ms，再减去裁切偏移。"""
    def X(v):      # 窗口 x → 输出 x
        return v * ms - clip_x0
    win = 810 * ms
    return {
        "顶部胶囊": (X(315 * ms + 90), 72 * ms, X(315 * ms + win - 90), 170 * ms),
        "主标题第1行": (X(315 * ms + 20), 232 * ms, X(315 * ms + win - 20), 296 * ms),
        "主标题第2行": (X(315 * ms + 20), 296 * ms, X(315 * ms + win - 20), 360 * ms),
        "柠檬绿贴纸": (X(315 * ms + 200), 470 * ms, X(315 * ms + win - 200), 562 * ms),
        "底部小注": (X(315 * ms + 60), 1024 * ms, X(315 * ms + win - 60), 1074 * ms),
    }


def bands916():
    """.l916 布局是**左对齐**（胶囊/主标题/行动条/小注都靠左），人物盘在右下 488px。"""
    return {
        "顶部胶囊": (88, 96, 760, 190),
        "主标题两行": (88, 426, 880, 700),
        "柠檬绿行动条": (92, 1032, 700, 1090),
        "底部小注": (92, 1770, 700, 1815),
    }


def measure(art_path, ms, canvas_wh, out_wh, clip_x0, label, band_map=None):
    art = Image.open(art_path).convert("RGB")
    W, H = canvas_wh
    base = np.asarray(cover_fit(art, W, H), dtype=np.float64) / 255.0
    a = scrim_alpha(W, H)[..., None]
    bg = base * (1 - a) + DARK_RGB * a                     # scrim 之后观众看到的背景
    lum = rel_lum(bg)
    ow, oh = out_wh
    y0 = (H - oh) // 2
    cx0 = int(round(clip_x0))
    lum_o = lum[y0:y0 + oh, cx0:cx0 + ow]

    print(f"\n【{label}】{ow}×{oh}" + ("" if ms == 1 else f"（母版 {W}×{H} 中心裁切）"))
    print(f"  整幅背景亮度：中位 {np.median(lum_o):.3f} · p95 {np.percentile(lum_o,95):.3f}")
    worst = []
    for name, (x0, y0b, x1, y1b) in (band_map or bands(ms, ow, oh, clip_x0)).items():
        xi0, xi1 = int(max(0, x0)), int(min(ow, x1))
        yi0, yi1 = int(max(0, y0b)), int(min(oh, y1b))
        if xi1 <= xi0 or yi1 <= yi0:
            print(f"  {name}: 带不在输出范围内，跳过"); continue
        seg = lum_o[yi0:yi1, xi0:xi1]
        L95 = float(np.percentile(seg, 95))
        cw = (1.05) / (L95 + 0.05)                          # 白字对比度
        lime = rel_lum(np.array([209 / 255, 255 / 255, 0]) ** 1.0)   # 近似：直接用 sRGB 值
        cl = (max(lime, L95) + 0.05) / (min(lime, L95) + 0.05)
        verdict = "✅" if cw >= 4.5 else ("⚠️" if cw >= 3.0 else "❌")
        print(f"  {name}={seg.shape[1]}×{seg.shape[0]}px  背景p95 L={L95:.3f}  白字对比 {cw:.2f}:1 {verdict}"
              f"（柠檬绿字 {cl:.2f}:1）")
        worst.append(cw)
    print(f"  → 最差白字对比度 {min(worst):.2f}:1（WCAG AA 大字要求 3.0:1）")
    return min(worst)


if __name__ == "__main__":
    art916 = {k: v[0].replace("cover-art.png", "cover-art-916.png") for k, v in ART.items()}
    res = {}
    for ep, (art, out) in ART.items():
        res[(ep, "4:3")] = measure(art, 1.0, (1440, 1080), (1440, 1080), 0, f"{ep} 4:3 主版")
        res[(ep, "3:4")] = measure(art, 1080 / 810, (1920, 1440), (1080, 1440), 315 * (1080 / 810), f"{ep} 3:4")
        res[(ep, "9:16")] = measure(art916[ep], 1.0, (1080, 1920), (1080, 1920), 0, f"{ep} 9:16（专用竖版图）", bands916())
    print("\n结论：", "全部 ≥3.0:1 → 文字可读" if all(v >= 3.0 for v in res.values()) else "存在不达标项，需加强 scrim")
