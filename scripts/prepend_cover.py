#!/usr/bin/env python3
"""前置封面首帧：把 cover-9x16.png 作为视频前 N 秒，抖音自动抓首帧当封面。

用法：python3 scripts/prepend_cover.py <video.mp4> <cover.png> <output.mp4> [hold_sec]
默认 hold=1.5 秒；日更默认用 0.4 秒（用户 2026-09-07 反馈封面别太长）。
wrapper ffmpeg 无 zoompan → 用 scale+crop 静态首帧（0.4s 低于 0.8s 静帧阈值）。
"""
import subprocess, sys, os

FF = os.path.join(os.path.dirname(__file__), "..", "videos", "qwen38-max-explained", "bin", "ffmpeg")
FF = os.path.abspath(FF)

def prepend(video, cover, out, hold=1.5):
    video = os.path.abspath(video); cover = os.path.abspath(cover); out = os.path.abspath(out)
    tmp_hold = "/tmp/_coverhold.mp4"
    # 封面已是 1080x1920（covers 管线产出），无需 scale；wrapper 的 scale 不认 force_original_aspect_ratio
    subprocess.run([FF, "-y", "-v", "error",
                    "-loop", "1", "-framerate", "30", "-t", str(hold), "-i", cover,
                    "-f", "lavfi", "-t", str(hold), "-i", "anullsrc=r=44100:cl=stereo",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k",
                    "-shortest", tmp_hold], check=True)
    with open("/tmp/_cover_list.txt", "w") as f:
        f.write(f"file '{tmp_hold}'\nfile '{video}'\n")
    tmp_out = out + ".tmp.mp4"
    # concat -c copy 时 AAC 时间戳伪影会把音频轨拉长，用 -t 裁齐到视频总长
    probe = subprocess.run([FF.replace("ffmpeg", "ffprobe"), "-v", "error",
                            "-select_streams", "v", "-show_entries", "stream=duration",
                            "-of", "csv=p=0", video], capture_output=True, text=True)
    vdur = float(probe.stdout.strip())
    subprocess.run([FF, "-y", "-v", "error",
                    "-f", "concat", "-safe", "0", "-i", "/tmp/_cover_list.txt",
                    "-t", str(round(hold + vdur, 3)),
                    "-c", "copy",
                    "-movflags", "+faststart", tmp_out], check=True)
    os.rename(tmp_out, out)
    print(f"OK {out} ({hold}s cover + {vdur:.2f}s original)")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    hold = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
    prepend(sys.argv[1], sys.argv[2], sys.argv[3], hold)
