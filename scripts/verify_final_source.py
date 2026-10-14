"""验证「成片」的视频轨确实出自本期的渲染件（防 /tmp/_finalize 并发污染）。

原理：finalize 只是把 [渲染件] + [1.5s 尾帧定格] concat 起来（本期 cover_hold=0），
所以**成片 t 秒处的帧应当与渲染件 t 秒处的帧逐像素/逐字节一致**。
做法：两个文件各抽同样的时间点 → 比较抽帧图的 md5；再核对时长关系（成片 = 渲染件 + tail_hold）。
"""
import hashlib
import os
import pathlib
import subprocess
import sys

FF = '/Users/chao/Documents/dailyvideos/node_modules/@remotion/compositor-darwin-arm64'


def frame_md5(video: str, t: float) -> str:
    video = os.path.abspath(video)
    out = f'/tmp/_verifyframe_{pathlib.Path(video).stem}_{t}.png'
    subprocess.run(['./ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(video),
                    '-frames:v', '1', '-y', out], cwd=FF, check=True)
    return hashlib.md5(pathlib.Path(out).read_bytes()).hexdigest()


def dur(video: str) -> float:
    video = os.path.abspath(video)
    r = subprocess.run(['./ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', str(video)], cwd=FF, capture_output=True, text=True)
    return float(r.stdout.strip())


def check(label: str, final: str, render: str, times=(8.0, 20.0, 35.0)) -> bool:
    df, dr = dur(final), dur(render)
    print(f'── {label}')
    print(f'   成片 {df:.3f}s · 渲染件 {dr:.3f}s · 差 {df - dr:.3f}s（应 ≈ 1.5s 尾帧）')
    ok = True
    for t in times:
        a, b = frame_md5(final, t), frame_md5(render, t)
        same = a == b
        ok &= same
        print(f'   t={t:5.1f}s  成片帧 {a[:10]} vs 渲染件帧 {b[:10]}  {"✅ 一致" if same else "❌ 不一致"}')
    print(f'   → {"✅ 成片视频轨出自本期渲染件" if ok else "❌ 疑似被他期渲染件污染，必须重做"}')
    return ok


def newest_render(proj):
    """取该工程 renders/ 里**最新**的渲染件。

    ⚠️ 2026-09-14（EP.182 评审）：原来这里**硬编码渲染件文件名**，一旦重渲就比对上旧文件，
    结论会变成假的「一致」。改成自动取最新，并把选中的文件名打出来，便于人工核对。
    """
    d = pathlib.Path(proj) / 'renders'
    if not d.is_dir():
        return None
    cands = sorted(d.glob('*.mp4'), key=lambda p: p.stat().st_mtime)
    return str(cands[-1]) if cands else None


if __name__ == '__main__':
    eps = [
        ('EP.190', 'content/episode-190/publish-package-2026-09-17', 'videos/photo-tools-three'),
        ('EP.191', 'content/episode-191/publish-package-2026-09-17', 'videos/speech-to-text-three'),
        ('EP.192', 'content/episode-192/publish-package-2026-09-17', 'videos/pdf-offline-three'),
    ]
    allok = True
    for label, pkg, proj in eps:
        finals = sorted(pathlib.Path(pkg).glob('czbvideo-*.mp4'), key=lambda p: p.stat().st_mtime)
        render = newest_render(proj)
        if not finals or not render:
            print(f'── {label}: 缺文件（final={bool(finals)} render={render}）')
            allok = False
            continue
        print(f'   （本期渲染件：{pathlib.Path(render).name}）')
        allok &= check(label, str(finals[-1]), render)
    print('\n总结论：' + ('✅ 各期成片都干净' if allok else '❌ 有污染，需重做'))
    sys.exit(0 if allok else 1)
