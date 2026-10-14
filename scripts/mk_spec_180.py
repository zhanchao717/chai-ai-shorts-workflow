"""生成 EP.180 的 spec（GitHub 本周涨星榜 · EP 01 · ≤60s 清单型）。

数据全部来自一手源：
  本周涨星 = github.com/trending?since=weekly（2026-09-13 抓取，页面自带 "stars this week"）
  总星/创建日/语言 = GitHub API（gh api repos/<owner>/<repo>）
核验：i-have-adhd 的 README 原文有 "## The rules — 10 rules"，第 1 条 = Lead with the next action
      diagram-design 官方描述 38 editorial diagram types；markitdown = 微软官方仓库；
      hyperframes「写 HTML 出视频」= 官方描述 "Write HTML. Render video."
"""
import json, pathlib

ROWS = [
    # rank, repo, 本周涨星, 总星, 热度%
    (8, "microsoft/markitdown",                4823, "18.3 万", 30, "文件转 Markdown"),
    (7, "heygen-com/hyperframes",              5124, "4.9 万",  32, "写网页出视频"),
    (6, "cathrynlavery/diagram-design",        7409, "3.9 万",  47, "图表模板"),
    (5, "affaan-m/ECC",                        8086, "25.8 万", 51, "智能体性能优化"),
    (4, "DietrichGebert/ponytail",             9272, "13.7 万", 58, "最懒的资深工程师"),
    (3, "tt-a1i/archify",                     10442, "6.0 万",  66, "画架构图"),
    (2, "bilawalsidhu/gods-eye-view",         10510, "3.1 万",  66, "实时地球"),
    (1, "ayghri/i-have-adhd",                 15924, "4.4 万", 100, "治 AI 说废话"),
]

# 口播（A 方案句式：第 N 名 + 你能拿它干什么 + 口语化数字）
NARR = {
    "01-hook":   "一周涨星最快的八个，逐个核了官方说明，从第八名往回数。",
    "02-facts":   "第八名，微软的，十八万星，能把文件转成 AI 好读的。",
    "03-facts":   "第七名，快五万星，写网页就能出视频。",
    "04-facts":   "第六名，图表模板三十八种，出图不用自己调。",
    "05-facts":   "第五名，二十五万星，给智能体做性能优化。",
    "06-facts":   "第四名，十三万星，让 AI 少写代码，能省就省。",
    "07-facts":   "第三名，六万星，让 AI 自己画架构图和流程图。",
    "08-facts":   "第二名，三万星，把飞机轮船卫星装进一个地球。",
    "09-facts":   "第一名，十条规则，让它先把下一步说清楚。",
    "10-verdict":   "八个都开源，先挑一个用一周。想每周看，关注柴主编。",
}

HOOK = {
    "warn_a": "GitHub 本周涨星榜 · 09-13 抓取",
    "warn_b": "八个狠货 · 逐个核过官方说明",
    "hero_l1": "一周涨了 1.6 万星",
    "hero_l2": "第一名不是大模型",
    "card_big": "8 条",
    "card_t": "周榜里涨星最快的八个",
    "card_s": "GitHub Trending 周榜 + GitHub API",
    "note": "SOURCE · github.com/trending（09-13 抓取）",
    "hero_fs": 78,
}

VERDICT = {
    "hero_l1": "八个都开源",
    "hero_l2_pre": "先挑",
    "hero_l2_em": "一个用一周",
    "hero_l2_tail": "",
    "card_tt": "想每周看这个榜{em}",
    "card_tt_em": "关注柴主编",
    "card_ss": "本期观点",
    "note": "SOURCE · GitHub 周榜 + API（09-13）",
    "hero_fs": 74,
}

COVER = {
    "kicker": "GitHub 本周涨星榜 · EP 01",
    "hero_l1": "一周涨了 1.6 万星",
    "hero_pre": "",
    "hero_em": "八个狠货全开源",
    "hero_tail": "",
    "act": "八个狠货 · 先挑一个用一周",
    "cap43": "本周涨星 = GitHub Trending 周榜（最近 7 天）· 09-13 抓取",
    "font": 56,
}

scenes = {"01-hook": HOOK}
for rank, repo, wk, tot, heat, tag in ROWS:
    fid = f"{9 - rank + 2:02d}-facts"          # #8 → 02, #1 → 09
    scenes[fid] = {
        "repo_big": f"+{wk:,}",
        "repo_t": "本周涨星",
        "repo_s": "",
        "st1_num": tot,
        "st1_t": "总星",
        "st1_s": "",
        "st2_num": f"{heat}%",
        "st2_t": "热度",
        "st2_s": "",
        "tag_a": repo,
        "tag_b": f"第 {rank} 名 · {tag}",
        "note": "",
    }
scenes["10-verdict"] = VERDICT

spec = {
    "ep": 180,
    "proj": "videos/gh-weekly-rank-01",
    "scenes": scenes,
    "cover": COVER,
    "line_breaks": [],
}
out = pathlib.Path("specs/180.json")
out.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")

# 口播稿 + TTS 输入
ep = pathlib.Path("content/episode-180")
(ep / "audio").mkdir(parents=True, exist_ok=True)
for fid, text in NARR.items():
    n = fid.split("-")[0]
    (ep / "audio" / f"{n}.txt").write_text(text + "\n", encoding="utf-8")

print(f"✅ specs/180.json 写出（{len(scenes)} 场）")
print(f"✅ content/episode-180/audio/01..10.txt 写出")
chars = sum(len(t) for t in NARR.values())
print(f"  口播 {chars} 非空白字符 ≈ {chars*0.20:.1f}–{chars*0.21:.1f}s（+1.9s 封面头/尾帧）")
onscreen = sum(len(str(v)) for sc in scenes.values() for v in sc.values() if isinstance(v, str))
print(f"  屏上字 ≈ {onscreen} 字 → 按 55s 算 {onscreen/55:.2f} 字/秒（门禁 ≤13）")
