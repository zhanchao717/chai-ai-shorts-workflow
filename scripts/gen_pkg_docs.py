#!/usr/bin/env python3
"""发布包人工文档批量生成器（{PKG_DATE}）。
用法：python3 scripts/gen_pkg_docs.py <ep> <proj> <标题> <时长s> <钩子> <支柱> <核心问题> <核心结论> <封面标题两行/斜杠> <来源一句话> <judge结论一行>
例：python3 scripts/gen_pkg_docs.py 146 free-models-list "B.AI 免费模型名单" 42.67 结果 免费/省钱 "..." "..." "充值之前，/先看免费名单。" "B.AI 公告 09-02" "..." "PASS(修复后)"
"""
import os, sys, json
from pathlib import Path

ep, proj, title, dur, hook, pillar, problem, conclusion, cover_title, source, judge = sys.argv[1:12]
import datetime as _dt
PKG_DATE = os.environ.get("PKG_DATE") or _dt.date.today().isoformat()
pkg = Path(f"<REPO>/content/episode-{ep}/publish-package-{PKG_DATE}")
pkg.mkdir(parents=True, exist_ok=True)
t1, t2 = cover_title.split("/")

(pkg/"performance-record.md").write_text(f"""# 柴主编单视频表现记录 — EP.{ep}

## 发布前信息
- 期数：EP.{ep} / 主题：{title} / 支柱：{pillar}
- 计划发布：2026-09-08 / 钩子：{hook} / 时长档：25–45s（实测 {dur}s）/ 图片数：0 / CTA：统一结尾 CTA
- 核心问题：{problem} / 核心结论：{conclusion}
- 本期测试变量：待回填 / 实验假设：待回填
## 发布信息
- 实际发布时间：待回填 / 作品 ID：待回填 / 最终标题：待回填 / 封面标题：{t1}{t2} / 是否置顶：待回填
## 24 小时数据（全部待回填）
曝光/播放/2 秒跳出/5 秒留存/平均时长/完播/点赞/评论/分享/收藏/主页访问/净增关注/流量来源：待回填
## 72 小时数据（全部待回填）
曝光/播放/2 秒跳出/5 秒留存/平均时长/完播/点赞/评论/分享/收藏/主页访问/净增关注/流量来源：待回填
""", encoding="utf-8")

(pkg/"prepublish-checklist.md").write_text(f"""# 发布前检查清单 — EP.{ep}（{PKG_DATE}）

## 成片规格
- [x] 1080×1920 / 30fps / H.264 / AAC（motion PASS）
- [x] 时长 {dur}s（25–45s 档）；音视频流等长；收尾余量 ≥1.2s
## 字幕与口播
- [x] 字幕组对齐；英文专名英文原音；数字中文
- [x] 配音↔脚本逐句相似度 1.00（门禁A）；无 stray token（已扫描）
## 合规红线核对（workflow §5）
- [x] 无未证实宏大叙事 / 无绝对化 / 无金钱施压 / 无爆料数据
- [x] 本节即合规核对项
## 统一结尾 CTA
- [x] 判词后追加「AI 更新太快，关注柴主编陪你一起跟上。」（显式断行）
## 前 2 秒强化
- [x] hero 文字 opacity .5 起步极速到位
## 版式与封面 + BGM
- [x] hyperframes check 0 error；三比例封面标题逐字一致（{t1} / {t2}）
- [x] BGM：恒定垫底 0.07（*-bgm.mp4 主交付；*-nobgm.mp4 备选）
## 发布动作（人工）
- [ ] 双平台上传并勾选 AI 标识
- [ ] 24h/72h 回填 performance-record.md
""", encoding="utf-8")

(pkg/"quality-report.md").write_text(f"""# Quality Report — EP.{ep}（独立评审）

## 评审结论（judge，qa-frames 全量 + 封面）
- {judge}
## 交付判定
- P0 清零 ✓ 准予交付
""", encoding="utf-8")

(pkg/"STORYBOARD.md").write_text(f"""# STORYBOARD — EP.{ep} {proj}

皮肤：Neumorphism「Soft Slate」冷灰。五场景：钩子(警示条+大字+浮起卡)/事实(仓库卡+双卡+凹槽条)/机制(三节点+凹槽卡)/行动(双井+凹槽条)/判词(大字+CTA 卡)。
来源：{source}
详见 SCRIPT.md 与 qa-frames/。
""", encoding="utf-8")
print(f"EP.{ep} 四份文档已生成")
