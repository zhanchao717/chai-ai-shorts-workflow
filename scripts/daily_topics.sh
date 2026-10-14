#!/usr/bin/env bash
# 柴主编 V2.2 新闻雷达：公开官方消息 + 中文媒体线索，按时间列出，不自动选题或发布。
# --no-browser 为兼容旗标；默认不启动浏览器。旧入口存档于 scripts/legacy/。
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/chai_news_radar.py "$@"
