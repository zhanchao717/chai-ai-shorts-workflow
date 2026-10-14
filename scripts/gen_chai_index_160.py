#!/usr/bin/env python3
"""EP.160 专用 index.html 构建（7 段配音映射到 5 场景）。

为什么不是 gen_chai_index.py：它的唯一语音模型是「1 段配音 = 1 场景」（voices 必须 5 段）。
EP.160 有 7 段配音（含反面段与判词段共用场景 5），映射为：
  frame1=[v1] frame2=[v2] frame3=[v3] frame4=[v4] frame5=[v5,v6,v7]
场景时长 = 该场景覆盖的配音总时长（前 4 场景 +0.5s 叠化余量），与 gen_chai_frames.py
的 durs 完全一致（后者按 voices 顺序消费 beat 索引）。其余模板（皮肤、家具、嘴型驱动）
逐字节沿用 scripts/gen_chai_index.py 的版本。
"""
import json, re, sys
from pathlib import Path

ROOT = Path("/Users/chao/Documents/dailyvideos")
IDS = ["01-hook", "02-facts", "03-mechanism", "04-action", "05-verdict"]
FRAME_MAP = [[1], [2], [3], [4], [5, 6, 7]]


def main() -> int:
    proj = ROOT / sys.argv[1]
    episode_dir = ROOT / sys.argv[2]
    furniture = sys.argv[3]

    src = (ROOT / "scripts" / "gen_chai_index.py").read_text(encoding="utf-8")
    tpl = src.split('TPL = """', 1)[1].split('"""', 1)[0]

    meta = json.loads((episode_dir / "publish-timeline" / "audio_meta.json").read_text("utf-8"))
    voices = meta["voices"]
    durs = [round(v["duration_s"], 3) for v in voices]
    vstarts, acc = [], 0.0
    for d in durs:
        vstarts.append(round(acc, 3))
        acc = round(acc + d, 3)
    total = round(acc, 3)

    sstarts, sdurs = [], []
    for i, frames in enumerate(FRAME_MAP):
        s0 = vstarts[frames[0] - 1]
        s1 = vstarts[frames[-1] - 1] + durs[frames[-1] - 1]
        sstarts.append(s0)
        sdurs.append(round(s1 - s0 + (0.5 if i < 4 else 0.0), 3))

    scenes = []
    for i, sid in enumerate(IDS):
        scenes.append(f'      <div id="el-{sid}" class="scene" data-composition-id="{sid}" '
                      f'data-composition-src="compositions/frames/{sid}.html" data-start="{sstarts[i]}" '
                      f'data-duration="{sdurs[i]}" data-track-index="{i}"></div>')
    for i, _ in enumerate(voices):
        sid = IDS[[k for k, f in enumerate(FRAME_MAP) if (i + 1) in f][0]]
        scenes.append(f'      <audio id="el-voice-{i+1:02d}" src="assets/voice/{i+1:02d}.mp3" '
                      f'data-start="{vstarts[i]}" data-duration="{durs[i]}" '
                      f'data-track-index="{10+i}" data-volume="1"></audio>')

    trans = []
    for i in range(4):
        trans.append(f'        tl.to("#el-{IDS[i]}", {{ opacity: 0, y: -14, scale: 0.985, duration: 0.5, ease: "power2.inOut" }}, {sstarts[i+1]});')
        trans.append(f'        tl.fromTo("#el-{IDS[i+1]}", {{ opacity: 0, y: 24, scale: 0.99 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "power2.inOut" }}, {sstarts[i+1]});')

    windows = [[round(s + 0.04, 3), round(s + d - 0.04, 3)] for s, d in zip(vstarts, durs)]

    html = (tpl.replace("@SCENES@", "\n".join(scenes))
               .replace("@TRANSITIONS@", "\n".join(trans))
               .replace("@WINDOWS@", json.dumps(windows))
               .replace("@FURNITURE@", furniture)
               .replace("@TOTAL@", str(total)))
    leftovers = [p for p in ("@TOTAL@", "@SCENES@", "@FURNITURE@", "@TRANSITIONS@", "@WINDOWS@") if p in html]
    assert not leftovers, f"模板占位符未全部替换: {leftovers}"
    # 场景用了 track 0..4（EP.160 允许同类元素叠放），字幕挪到 track 5 避免与场景 5 重叠
    html = html.replace('id="el-captions" class="scene" data-composition-id="captions" '
                        'data-composition-src="compositions/captions.html" data-start="0.0" '
                        f'data-duration="{total}" data-track-index="2"',
                        'id="el-captions" class="scene" data-composition-id="captions" '
                        'data-composition-src="compositions/captions.html" data-start="0.0" '
                        f'data-duration="{total}" data-track-index="5"')
    assert 'data-track-index="5"' in html, "字幕轨道改写失败"
    (proj / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html 已写入 {proj}")
    print(f"  配音时长 {durs}")
    print(f"  场景 start {sstarts}")
    print(f"  场景 dur   {sdurs}")
    print(f"  总时长 {total}s ({total+1.9:.1f}s 成片)")
    for i, f in enumerate(FRAME_MAP):
        assert abs(sstarts[i] - vstarts[f[0]-1]) < 1e-6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
