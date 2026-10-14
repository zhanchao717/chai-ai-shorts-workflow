#!/usr/bin/env python3
"""把 EP.178 / EP.179 的「旧封面 vs GPT 画面新版」做成一个可直看的预览页。

产物：~/Documents/DSH/daily-workbench/预览-封面GPT/
  index.html          —— 并排对比（点图看原图）
  EP178-旧版/ · EP178-GPT版/ · EP178-画面原图/
  EP179-旧版/ · EP179-GPT版/ · EP179-画面原图/
"""
import pathlib, shutil, html

ROOT = pathlib.Path("<REPO>")
OUT = pathlib.Path("/Users/<you>/Documents/DSH/daily-workbench/预览-封面GPT")
EPS = {
    "EP178": {
        "old": ROOT / "content/episode-178/publish-package-2026-09-13",
        "new": ROOT / "content/episode-178/cover-gpt/out",
        "art": ROOT / "content/episode-178/cover-gpt",
        "title": "EP.178 · ③ 档「今日 GitHub 涨星最快 TOP10」",
    },
    "EP179": {
        "old": ROOT / "content/episode-179/publish-package-2026-09-13",
        "new": ROOT / "content/episode-179/cover-gpt/out",
        "art": ROOT / "content/episode-179/cover-gpt",
        "title": "EP.179 · ① 档「关掉电脑，AI 还在替你干活」",
    },
}
RATIOS = ["cover-4x3.png", "cover-3x4.png", "cover-9x16.png"]
RATIO_CN = {"cover-4x3.png": "4:3（主版 · 中央 3:4 裁切安全窗）",
            "cover-3x4.png": "3:4（小红书）",
            "cover-9x16.png": "9:16（竖版）"}

OUT.mkdir(parents=True, exist_ok=True)
copied = 0
for ep, cfg in EPS.items():
    for kind, src in (("旧版", cfg["old"]), ("GPT版", cfg["new"])):
        d = OUT / f"{ep}-{kind}"
        d.mkdir(exist_ok=True)
        for r in RATIOS:
            if (src / r).is_file():
                shutil.copyfile(src / r, d / r); copied += 1
    d = OUT / f"{ep}-画面原图"
    d.mkdir(exist_ok=True)
    for r in ["cover-art-4x3.png", "cover-art-4x3-v2.png", "cover-art-916.png"]:
        if (cfg["art"] / r).is_file():
            shutil.copyfile(cfg["art"] / r, d / r); copied += 1

rows = []
for ep, cfg in EPS.items():
    rows.append(f'<h2>{html.escape(cfg["title"])}</h2>')
    rows.append('<table><tr><th>比例</th><th>旧版（已发作品用的）</th><th>GPT 画面版（本次重做）</th></tr>')
    for r in RATIOS:
        old_img = (f'{ep}-旧版/{r}')
        new_img = (f'{ep}-GPT版/{r}')
        rows.append(
            f'<tr><th>{RATIO_CN[r]}</th>'
            f'<td><a href="{old_img}" target="_blank"><img src="{old_img}" loading="lazy"></a></td>'
            f'<td><a href="{new_img}" target="_blank"><img src="{new_img}" loading="lazy"></a></td></tr>')
    rows.append('</table>')
    rows.append('<h3>GPT 出的画面原图（尚未压字）</h3><div class="art">')
    for a in ["cover-art-4x3.png", "cover-art-4x3-v2.png", "cover-art-916.png"]:
        if (cfg["art"] / a).is_file():
            rows.append(f'<a href="{ep}-画面原图/{a}" target="_blank">'
                        f'<img src="{ep}-画面原图/{a}" loading="lazy"><span>{a}</span></a>')
    rows.append('</div>')

page = f"""<!DOCTYPE html><html lang="zh-CN"><meta charset="utf-8">
<title>封面预览 · GPT 画面版 vs 旧版</title>
<style>
 body{{background:#0B0E14;color:#E6EAF2;font:15px/1.6 "PingFang SC",system-ui,sans-serif;margin:0;padding:32px 40px}}
 h1{{font-size:26px;margin:0 0 6px}} h2{{font-size:20px;margin:38px 0 12px;color:#D1FF00}}
 h3{{font-size:15px;color:#9FB0CC;margin:22px 0 10px;font-weight:600}}
 .note{{color:#9FB0CC;max-width:1100px;margin-bottom:8px}}
 table{{border-collapse:separate;border-spacing:16px;width:100%}}
 th{{text-align:left;font-size:13px;color:#9FB0CC;font-weight:600;vertical-align:top}}
 td{{vertical-align:top;width:50%}}
 img{{width:100%;max-width:520px;border-radius:10px;border:1px solid #232A38;display:block;background:#05070F}}
 .art{{display:flex;gap:16px;flex-wrap:wrap}}
 .art a{{color:#9FB0CC;font-size:12px;text-decoration:none}}
 .art img{{max-width:290px}}
 code{{background:#161B26;padding:2px 6px;border-radius:5px}}
</style>
<h1>封面预览 · GPT 画面版 vs 旧版</h1>
<p class="note">GPT 只出<b>画面</b>，中文标题/数字仍由 <code>cover.html</code> 模板确定性渲染（中文交给图像模型必糊字，是 P0 事故）。
   scrim 按实测校准到 0.45 权重，六张封面的最差白字对比度 <b>7.4–13.9:1</b>（WCAG AA 大字要求 3.0:1）。
   点任意图可看原图。</p>
{''.join(rows)}
</html>"""
(OUT / "index.html").write_text(page, encoding="utf-8")
print(f"✅ 预览页：{OUT/'index.html'}（复制 {copied} 张图）")
for p in sorted(OUT.rglob("*.png")):
    print("   ", p.relative_to(OUT))
