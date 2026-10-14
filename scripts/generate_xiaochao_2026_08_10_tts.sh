#!/usr/bin/env bash
set -euo pipefail

project_root="/Users/chao/Documents/dailyvideos"

generate_episode() {
  local episode_dir="$1"
  mkdir -p "$episode_dir/voice"
  for input_path in "$episode_dir"/narration/*.txt; do
    local stem
    stem="$(basename "$input_path" .txt)"
    python3 "$project_root/scripts/minimax_tts.py" \
      "$input_path" \
      "$episode_dir/voice/$stem.mp3" \
      --voice-id "Chinese (Mandarin)_Sincere_Adult" \
      --model speech-2.8-hd \
      --speed 1.02 \
      --vol 1.0 \
      --pitch -1 \
      --emotion happy
  done
}

generate_episode "$project_root/content/2026-08-10/xiaochao-004-oil-motion" &
pid_one=$!
generate_episode "$project_root/content/2026-08-10/xiaochao-005-codex-bridge" &
pid_two=$!
generate_episode "$project_root/content/2026-08-10/xiaochao-006-novel-characters" &
pid_three=$!

wait "$pid_one"
wait "$pid_two"
wait "$pid_three"
