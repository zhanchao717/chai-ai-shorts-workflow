#!/usr/bin/env bash
# 每天一条命令出「今日选题」：
#   ① 浏览器侧：把**没有 API 的榜单页**读回来（HN / GitHub Trending / Product Hunt / 知乎热榜）
#      —— 用本机已有的 ego-browser（一个能被 Agent 驱动的 Chromium），一次跑一个站、跑完就落盘；
#   ② API 侧：GitHub 新建仓库搜索 + HuggingFace trending；
#   ③ 合并打分排序（规则来自自己 356 条作品的流量归因），输出 top 榜 + 可组「三件套」的类目；
#   ④ 落一份当日报告到工作台。
#
# 为什么要分两半（2026-09-22 定）：**采集可以自动化，判断不能外包**。
#   · jev / browser-use 那一类是"浏览器智能体"（挑操作和元素），擅长干"没有 API 的页面"，
#     所以我们用同类能力的 ego-browser 做采集，不额外接一套计费 API；
#   · 打分是可解释的脚本（能回答"为什么选它"），拍板仍然留给人。
#
# 用法：
#   bash scripts/daily_topics.sh              # 浏览器采集 + API 雷达 + 报告
#   bash scripts/daily_topics.sh --no-browser # 只跑 API 侧（快，不弹浏览器）
set -uo pipefail
cd "$(dirname "$0")/.."

BROWSER=1
[ "${1:-}" = "--no-browser" ] && BROWSER=0

HOT=/tmp/hot-candidates.json
TARGETS=/tmp/hot_targets.txt
DAY=$(date +%F)
WB="$HOME/Documents/DSH/daily-workbench"
REPORT="$WB/选题雷达-$DAY.md"
EGO="$HOME/.local/bin/ego-browser"

if [ "$BROWSER" = 1 ]; then
  # 每个站单独一次调用（ego CLI 只接受一个 source 参数）：某站弹权限框只影响那一站
  # Product Hunt 不在浏览器名单里（首页弹通知权限框 → 空间被收回），它走 curl 的 Atom feed，
  # 由 chai_topic_radar.py 的 ph_feed() 直接拉，见该函数注释。
  # 2026-09-28 起加两站**中文 AI 媒体**（雷达原来是纯开发者雷达，看不见大厂发布/芯片/事故）：
  #   新智元·搜狐号（官网不可达，用它的搜狐号当镜像）· 机器之心（首页是付费墙壳，暂 0 条，留着探路）
  for site in HackerNews GitHubTrending 知乎热榜 新智元·搜狐号 机器之心; do
    printf '%s\n' "$site" > "$TARGETS"
    echo "── 采集 $site"
    "$EGO" nodejs < scripts/collect_hot_topics.mjs 2>&1 | tail -5
  done
fi

# ①b 静态站的中文 AI 媒体（curl 直连，不占浏览器）：量子位 / 智东西 / IT之家·AI
echo "── 采集 中文 AI 媒体（静态）"
python3 scripts/collect_ai_media.py --json /tmp/ai-media.json 2>&1 | tail -6
python3 - <<'PYEOF'
import json, pathlib
# 把媒体线索并进 /tmp/hot-candidates.json，让 chai_topic_radar.py 一起打分
hot = pathlib.Path('/tmp/hot-candidates.json')
try:
    cur = json.loads(hot.read_text(encoding='utf-8'))
except Exception:
    cur = []
try:
    media = json.loads(pathlib.Path('/tmp/ai-media.json').read_text(encoding='utf-8'))
except Exception:
    media = []
names = {m['source'] for m in media}
cur = [r for r in cur if r.get('source') not in names] + media
hot.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'  合并后候选总数 {len(cur)}（其中媒体线索 {len(media)}）')
PYEOF

echo
python3 scripts/chai_topic_radar.py --top 15 --json /tmp/radar.json --with-web "$HOT" | tee /tmp/radar-report.txt

{
  echo "# 选题雷达 · $DAY"
  echo
  echo '```'
  cat /tmp/radar-report.txt
  echo '```'
  echo
  echo "> 生成方式：\`bash scripts/daily_topics.sh\`（浏览器采集脚本 \`scripts/collect_hot_topics.mjs\` + 打分脚本 \`scripts/chai_topic_radar.py\`）"
  echo "> 明细 JSON：\`/tmp/radar.json\`、\`/tmp/hot-candidates.json\`"
} > "$REPORT"
echo
echo "📝 当日报告：$REPORT"
