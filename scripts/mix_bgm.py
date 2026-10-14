#!/usr/bin/env python3
"""柴主编 BGM 混音器（自研，2026-09-04 固化）。

原理：wrapper ffmpeg 无 AAC 编码器且缺 afade/sidechaincompress，故
  ffmpeg 解码(voice/bgm → wav) → numpy 恒定垫底混音（2026-09-06 用户反馈：
  音乐要平稳，不要时大时小——已弃用侧链闪避，只保留首尾淡入淡出）
  → afconvert 编码 AAC 192k → ffmpeg -c copy 封装进 MP4（视频流不重渲）。
  BED_GAIN=0.07 为恒定垫底增益（约低于口播 12dB），想更响/更弱改这一个值。

用法：
  单视频：python3 scripts/mix_bgm.py <video.mp4> <out.mp4> <duration_s> [bgm_start_s]
  批量：  python3 scripts/mix_bgm.py --batch <ep:proj:duration:bgm_start:pkgdate> [...]
  例：python3 scripts/mix_bgm.py --batch 126:doubao-agent-phone:36.936:12.0:2026-09-04

BGM 文件固定为 assets/bgm/paperman-the-king.mp3（网易云版权曲库——发布前
建议核对平台音乐授权，被静音则改发无 BGM 原版）。
"""

import subprocess, sys, wave, os
import numpy as np

ROOT = "/Users/chao/Documents/dailyvideos"
BGM_MP3 = f"{ROOT}/assets/bgm/paperman-the-king.mp3"
AF = "/usr/bin/afconvert"

FF = f"{ROOT}/videos/qwen38-max-explained/bin/ffmpeg"
def to_wav(src, dst, ch=2):
    subprocess.run([FF, "-y", "-v", "error", "-i", src, "-vn", "-ac", str(ch),
                    "-ar", "44100", "-c:a", "pcm_s16le", dst],
                   check=True, capture_output=True)

def read_wav(path):
    w = wave.open(path, "rb")
    n = w.getnframes(); ch = w.getnchannels(); sr = w.getframerate()
    data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    data = data.reshape(-1, ch)
    w.close()
    return data, sr

def write_wav(path, data, sr):
    out = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    w = wave.open(path, "wb")
    w.setnchannels(data.shape[1]); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(out.tobytes()); w.close()

def smooth(x, win):
    k = np.ones(win) / win
    return np.convolve(x, k, mode="same")

def mix(video, out_mp4, dur, bg_start=0.0):
    video = os.path.abspath(video); out_mp4 = os.path.abspath(out_mp4)
    v_wav, b_wav = "/tmp/_voice.wav", "/tmp/_bg.wav"
    to_wav(video, v_wav)
    to_wav(BGM_MP3, b_wav)
    voice, sr = read_wav(v_wav)
    bg, bsr = read_wav(b_wav)
    assert sr == bsr == 44100, (sr, bsr)
    n = int(dur * sr)
    voice = voice[:n]
    if voice.shape[0] < n:
        voice = np.pad(voice, ((0, n - voice.shape[0]), (0, 0)))
    # BGM：从 bg_start 秒取 dur 长度，不够则循环
    seg = bg[int(bg_start*sr):]
    need = n
    reps = int(np.ceil(need / seg.shape[0])) if seg.shape[0] else 1
    seg = np.tile(seg, (reps, 1))[:n]
    # 恒定垫底（平稳，无闪避）——用户 2026-09-06 偏好
    BED_GAIN = 0.07
    bed = BED_GAIN * seg
    # 首尾淡入淡出
    fi = int(1.0*sr); fo = int(1.4*sr)
    bed[:fi] *= np.linspace(0, 1, fi)[:, None]
    bed[-fo:] *= np.linspace(1, 0, fo)[:, None]
    mixed = voice + bed
    write_wav("/tmp/_mixed.wav", mixed, sr)
    m4a = "/tmp/_mixed.m4a"
    subprocess.run([AF, "/tmp/_mixed.wav", m4a, "-f", "m4af", "-d", "aac", "-b", "192000"],
                   check=True, capture_output=True)
    ff = "/Users/chao/Documents/dailyvideos/videos/qwen38-max-explained/bin/ffmpeg"
    subprocess.run([ff, "-y", "-v", "error", "-i", video, "-i", m4a,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
                    "-movflags", "+faststart", out_mp4], check=True)
    print("OK", out_mp4)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        base = f"{ROOT}/content"
        for spec in sys.argv[2:]:
            ep, proj, dur, off, pkg = spec.split(":")
            src = f"{base}/episode-{ep}/publish-package-{pkg}/czbvideo-{ep}-{proj}.mp4"
            out = f"{base}/episode-{ep}/publish-package-{pkg}/czbvideo-{ep}-{proj}-bgm.mp4"
            mix(src, out, float(dur), float(off))
    else:
        if len(sys.argv) < 4:
            raise SystemExit(__doc__)
        mix(sys.argv[1], sys.argv[2], float(sys.argv[3]),
            float(sys.argv[4]) if len(sys.argv) > 4 else 0.0)
