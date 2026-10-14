#!/usr/bin/env python3
"""柴主编成品装配器（2026-09-07 深夜固化）——封面首帧 + 正片 + 尾帧定格 + 可选 BGM，采样级无拉伸。

背景：concat -c copy 拼 AAC 会累积 priming 空隙把音轨内部拉伸（142 实测 ~0.6s，
三段拼接 ~3.2s），`-t` 裁齐后等于切掉结尾语音——「话没说完就结束」事故根因。
本脚本：视频轨 concat 拷贝（视频时间戳无此问题），音频轨 numpy 采样级拼接后
afconvert 编码，杜绝拉伸。语音说完默认留 1.5s 定格收尾。

用法：
  python3 scripts/finalize_episode.py <render.mp4> <cover.png> <out.mp4> [--bgm] \
      [--cover-hold 0.4] [--tail-hold 1.5] [--bgm-start 0]
"""
import argparse, json, os, re, struct, subprocess, sys, wave
import numpy as np

ROOT = "/Users/chao/Documents/dailyvideos"
FF = f"{ROOT}/videos/llada-image-turbo/bin/ffmpeg"
FP = FF.replace("ffmpeg", "ffprobe")
AF = "/usr/bin/afconvert"
# 默认 BGM：canonical 文件（2026-09-12 起用用户提供的 NCM 解码件；旧的 paperman 仍可用 --bgm-file 指定）
BGM_MP3 = os.environ.get("CHAI_BGM", f"{ROOT}/assets/bgm/bgm.mp3")
BED_GAIN = 0.07
SR = 44100

def sh(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAIL: {' '.join(str(c) for c in cmd[:3])}…\n{r.stderr[-400:]}")

def read_wav_any(path):
    with open(path, "rb") as f:
        raw = f.read()
    pos, ch = 12, 1
    data = b""
    while pos < len(raw) - 8:
        cid = raw[pos:pos+4]; size = struct.unpack("<I", raw[pos+4:pos+8])[0]
        if cid == b"fmt ":
            ch = struct.unpack("<H", raw[pos+10:pos+12])[0]
        elif cid == b"data":
            data = raw[pos+8:pos+8+size]
        pos += 8 + size + (size & 1)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32768.0
    return x.reshape(-1, ch)

def write_wav(path, pcm, sr=SR):
    out = (np.clip(pcm, -1, 1) * 32767).astype(np.int16)
    w = wave.open(path, "wb")
    w.setnchannels(pcm.shape[1]); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(out.tobytes()); w.close()

def afc_decode(path, out_wav, ch=2, sr=SR):
    sh([AF, "-f", "WAVE", "-d", f"LEI16@{sr}", "-c", str(ch), path, out_wav])
    return read_wav_any(out_wav)

def stream_dur(f, sel):
    r = subprocess.run([FP, "-v", "error", "-select_streams", sel, "-show_entries",
                        "stream=duration", "-of", "csv=p=0", os.path.abspath(f)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("render"); ap.add_argument("cover"); ap.add_argument("out")
    ap.add_argument("--bgm", action="store_true")
    # ⚠️ 2026-09-14 用户指令：「**所有的封面都不要加到视频里面去了**，之后上传视频的时候，
    #    单独选择封面图加进去」。→ 新流程**不加封面头**（--no-cover），封面作为独立图片
    #    在发布时单独上传（`chai_publish_mcp.py` 已按平台传 cover-4x3/3x4/9x16）。
    #    参数保留 `cover`（位置参数，兼容既有调用与历史可复现），但 `--no-cover` 时不读它。
    ap.add_argument("--no-cover", action="store_true",
                    help="不把封面拼进成片（新默认流程）；封面改为发布时单独上传")
    ap.add_argument("--cover-hold", type=float, default=0.4)
    ap.add_argument("--tail-hold", type=float, default=1.5)
    ap.add_argument("--bgm-start", type=float, default=0.0)
    ap.add_argument("--bgm-file", default=None,
                    help="BGM 音频文件（默认 assets/bgm/bgm.mp3；可用 CHAI_BGM 环境变量覆盖）")
    # ⚠️ 2026-09-12 用户反馈「**为什么我没有听到 BGM**」后调整：-21dB 是"垫得很轻"的设定
    #    （实测成品里垫底 active RMS **-42.8 dBFS**，比人声低 21dB；用户这首曲子动态又大，
    #    安静段只有 -54dBFS，手机外放基本听不出来）。**2026-09-12 起定为 -9dB**（= 比人声低 9dB）——用户听过三档样本（-21/-13/-9）后
    #    **选了 -9dB**（样本在 daily-workbench/预览-BGM响度/）。要更轻/更响用 --bgm-bed-db 调。
    ap.add_argument("--bgm-bed-db", type=float, default=-9.0,
                    help="自适应垫底电平：BGM 相对人声的 dB（默认 −21dB；0 表示不自动校正）")
    ap.add_argument("--bgm-gain", type=float, default=None,
                    help=f"BGM 垫底音量（0–1，默认 {BED_GAIN}＝约 −23dB）；调大请同时确认不压过口播")
    a = ap.parse_args()
    render, cover, out = map(os.path.abspath, (a.render, a.cover, a.out))
    if a.no_cover:
        a.cover_hold = 0.0
    # ⚠️ 2026-09-14：临时目录**按成片名隔离**。原来写死 `/tmp/_finalize`，多期并行时
    #    `list.txt` 会被别的 finalize 覆盖 → 成片可能拼进**别人**的渲染件（EP.182 实测踩到，
    #    靠逐帧 md5 对拍才发现）。隔离后各期互不干扰。
    tmp = "/tmp/_finalize_" + re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(out))[:60]
    os.makedirs(tmp, exist_ok=True)

    # ── 视频轨：封面定格（可选） + 正片 + 尾帧定格（三段 concat 拷贝，只用视频流）
    sh([FF, "-y", "-v", "error", "-sseof", "-0.05", "-i", render, "-frames:v", "1",
        f"{tmp}/last.png"])
    segs = []
    if a.cover_hold > 0:
        sh([FF, "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-t", str(a.cover_hold),
            "-i", cover, "-f", "lavfi", "-t", str(a.cover_hold), "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", f"{tmp}/cover.mp4"])
        segs.append(f"{tmp}/cover.mp4")
    segs += [render]
    if a.tail_hold > 0:
        sh([FF, "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-t", str(a.tail_hold),
            "-i", f"{tmp}/last.png", "-f", "lavfi", "-t", str(a.tail_hold), "-i",
            "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", f"{tmp}/tail.mp4"])
        segs.append(f"{tmp}/tail.mp4")
    with open(f"{tmp}/list.txt", "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    sh([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt",
        "-map", "0:v", "-c:v", "copy", f"{tmp}/video_only.mp4"])

    # ── 音频轨：numpy 采样级拼接（封面静音 + 正片原声 + 尾部静音），零拉伸
    render_pcm = afc_decode(render, f"{tmp}/render.wav")
    cover_n = int(a.cover_hold * SR); tail_n = int(a.tail_hold * SR)
    total_n = cover_n + render_pcm.shape[0] + tail_n
    pcm = np.zeros((total_n, 2))
    pcm[cover_n:cover_n + render_pcm.shape[0]] = render_pcm
    if a.bgm:
        bgm_path = os.path.abspath(a.bgm_file) if a.bgm_file else BGM_MP3
        gain = BED_GAIN if a.bgm_gain is None else float(a.bgm_gain)
        if not os.path.isfile(bgm_path):
            sys.exit(f"FAIL: 找不到 BGM 文件 {bgm_path}")
        bg_raw = afc_decode(bgm_path, f"{tmp}/bg.wav") if bgm_path.endswith(".wav") else None
        if bg_raw is None:
            sh([FF, "-y", "-v", "error", "-i", bgm_path, "-ac", "2", "-ar", str(SR),
                "-c:a", "pcm_s16le", f"{tmp}/bg.wav"])
            bg_raw = read_wav_any(f"{tmp}/bg.wav")
        seg = bg_raw[int(a.bgm_start * SR):]
        reps = int(np.ceil(total_n / seg.shape[0]))
        # 曲子短于成片时自动重复铺满（用户要求：时长不够就循环放）。
        # ⚠️ 直接 np.tile 会在拼接点硬切出咔哒声 → 改为**循环点交叉淡化**（0.75s），
        #    首尾仍按既有逻辑做 1.0s 淡入 / 1.4s 淡出。
        seg = np.asarray(seg, dtype=float)
        n_seg = seg.shape[0]
        if n_seg <= 0:
            sys.exit("FAIL: BGM 解码为空")
        xf = int(0.75 * SR)
        xf = max(1, min(xf, n_seg // 4))
        bed = np.zeros((total_n, 2))
        pos, first = 0, True
        while pos < total_n:
            take = min(n_seg, total_n - pos)
            piece = seg[:take].copy()
            if not first:
                # 与已有尾巴做交叉淡化：淡入新片段、淡出旧片段
                k = min(xf, take, pos)
                if k > 1:
                    r = np.linspace(0.0, 1.0, k)[:, None]
                    bed[pos:pos + k] = bed[pos:pos + k] * (1 - r) + piece[:k] * r
                    bed[pos + k:pos + take] += piece[k:]
                else:
                    bed[pos:pos + take] += piece
            else:
                bed[pos:pos + take] += piece
            pos += take
            first = False
        pcm_voice = pcm.copy()   # 混入 BGM 前的人声轨（自适应定标 + 语音终点校验都用它）
        # 自适应垫底：按实测 RMS 把 BGM 压到相对人声的 --bgm-bed-db
        # ⚠️ 固定小系数不可靠：不同曲子响度差 3 倍以上（用户这首 RMS 0.244 vs 人声 0.083，
        #    原固定 0.07 只做到 −13.8dB，会抢人声）。这里按实测自动定标。
        if a.bgm_gain is None:
            def _rms_active(x, thr=0.01):
                w = 1600
                fr = np.array([x[i:i+w].std() for i in range(0, len(x)-w, w)])
                act = fr[fr > thr]
                return float(np.sqrt((act ** 2).mean())) if len(act) else float(np.sqrt((x ** 2).mean()))
            v_rms = _rms_active(pcm_voice.mean(axis=1))
            b_rms = _rms_active(seg.mean(axis=1))
            if v_rms > 1e-6 and b_rms > 1e-6:
                gain = v_rms * (10 ** (a.bgm_bed_db / 20.0)) / b_rms
                print(f"  BGM 自适应垫底：人声RMS={v_rms:.4f} 曲子RMS={b_rms:.4f} "
                      f"→ gain={gain:.4f}（{a.bgm_bed_db:+.1f}dB）")
        bed *= gain
        fi, fo = int(1.0 * SR), int(1.4 * SR)
        bed[:fi] *= np.linspace(0, 1, fi)[:, None]
        bed[-fo:] *= np.linspace(1, 0, fo)[:, None]
        pcm += bed
    write_wav(f"{tmp}/audio.wav", pcm)
    sh([AF, "-f", "m4af", "-d", "aac", "-b", "192000", f"{tmp}/audio.wav", f"{tmp}/audio.m4a"])

    # ── 封装 + 校验
    sh([FF, "-y", "-v", "error", "-i", f"{tmp}/video_only.mp4", "-i", f"{tmp}/audio.m4a",
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
        "-t", f"{total_n/SR:.3f}", "-movflags", "+faststart", out])
    vd, ad = stream_dur(out, "v"), stream_dur(out, "a")
    if abs(vd - ad) > 0.1:
        sys.exit(f"FAIL: 音视频差 {abs(vd-ad):.3f}s（v={vd} a={ad}）")
    check_sr = 16000
    # ⚠️ 有 BGM 时必须在**混入 BGM 之前**测语音终点：BGM 全程有能量，
    #    若在成品上测，检测器会把音乐当人声、余量被算小（实测 1.90s → 0.80s 的假 FAIL）。
    if a.bgm:
        voice_src = f"{tmp}/audio_voice.wav"
        write_wav(voice_src, pcm_voice)
        check_pcm = afc_decode(voice_src, f"{tmp}/check.wav", ch=1, sr=check_sr)
    else:
        check_pcm = afc_decode(out, f"{tmp}/check.wav", ch=1, sr=check_sr)
    mono = check_pcm.mean(axis=1)
    step = int(0.1 * check_sr)
    speech_end = None
    for i in range(mono.shape[0] - step, 0, -step):
        if mono[i:i + step].std() > 0.02:
            speech_end = (i + step) / check_sr
            break
    margin = vd - (speech_end or 0)
    print(f"OK {out}")
    print(f"   v={vd:.3f}s a={ad:.3f}s | 语音终点≈{speech_end:.2f}s | 收尾余量 {margin:.2f}s"
          f"{' ✓' if margin >= 1.0 else ' ✗ 余量不足!'}")
    # 2026-09-12（口径澄清，EP.175 复核轮次 2 遗留项）：
    #   上面这个「收尾余量」是**声学口径**（声学终点→片尾）。声学检测器（16k/0.1s/std>0.02）
    #   会把语音终点**读早约 0.4~0.6s**（末段音节能量低），所以它**比真实尾部留白偏大**。
    #   真实尾部留白 = 成片 −（0.4s 封面头 + Σ配音时长）；装配时给的就是 --tail-hold 秒，
    #   因此下面这行才是可以直接对账的那个数。
    #   ⚠️ 本行不是"漏算了封面头"：pcm_voice 里**已含** 0.4s 封面头静音（见上文 pcm[cover_n:]=render_pcm），
    #      实测把封面头显式补进人声轨测得 143.27s，与本脚本打印值逐位一致；漏算应差 0.4s。
    print(f"   （口径）声学余量偏大属检测器读早；**真实尾部留白 ≈ 尾帧 {a.tail_hold}s**，"
          f"两口径都须 ≥1.0s（`chai_pipeline.py verify` 会同时打印时间轴口径的真实留白并硬判）")
    if margin < 1.0:
        sys.exit("FAIL: 收尾余量不足 1s，语音可能被截")

    # ── 装配口径落盘（2026-09-14）：让下游工具**读事实**，不再各自硬编码 0.4s 封面头。
    #    `chai_pipeline.py verify` / qa_frames / window_check 都按这个文件算偏移；
    #    没有这个文件的旧包回退到历史默认 0.4（保证既有各期可复现）。
    meta = {
        "out": os.path.basename(out),
        "cover_hold": round(a.cover_hold, 3),
        "tail_hold": round(a.tail_hold, 3),
        "cover_baked": a.cover_hold > 0,
        "cover_file": None if a.cover_hold <= 0 else os.path.basename(cover),
        "bgm": bool(a.bgm),
        "bgm_bed_db": None if not a.bgm else a.bgm_bed_db,
        "voice_total": round(pcm_voice.shape[0] / SR, 3) if "pcm_voice" in dir() else None,
        "duration": round(vd, 3),
    }
    try:
        with open(os.path.join(os.path.dirname(out), "finalize-meta.json"), "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        print(f"   已写 finalize-meta.json（cover_hold={meta['cover_hold']}s · "
              f"封面{'已拼进成片' if meta['cover_baked'] else '不进成片，改为发布时单独上传'}）")
    except Exception as e:
        print(f"   ⚠️ finalize-meta.json 写失败（不影响成片）：{e}")

if __name__ == "__main__":
    main()
