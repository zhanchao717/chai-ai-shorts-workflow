#!/usr/bin/env bash
set -euo pipefail

project_root="<REPO>"
ffmpeg_bin="$project_root/node_modules/@remotion/compositor-darwin-arm64/ffmpeg"
music="$project_root/assets/music/look-beyond.mp3"
output_dir="$project_root/output/xiaochao/2026-08-10/videos-with-bgm"
mkdir -p "$output_dir"

mix_video() {
  local input_video="$1"
  local output_video="$2"
  local duration="$3"
  local fade_out_start="$4"

  "$ffmpeg_bin" -hide_banner -loglevel error -y \
    -i "$input_video" \
    -i "$music" \
    -filter_complex "[1:a]atrim=start=0:end=${duration},volume='0.10*if(lt(t,1),t,if(gt(t,${fade_out_start}),${duration}-t,1))':eval=frame[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix];[mix]loudnorm=I=-16:LRA=7:TP=-1.5[master]" \
    -map 0:v:0 -map "[master]" \
    -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest \
    "$output_video"
}

mix_video \
  "$project_root/output/xiaochao/2026-08-10/videos/04-oil-motion.mp4" \
  "$output_dir/04-oil-motion-bgm.mp4" \
  "56.866667" "55.866667"

mix_video \
  "$project_root/output/xiaochao/2026-08-10/videos/05-codex-bridge.mp4" \
  "$output_dir/05-codex-bridge-bgm.mp4" \
  "55.566667" "54.566667"

mix_video \
  "$project_root/output/xiaochao/2026-08-10/videos/06-novel-characters.mp4" \
  "$output_dir/06-novel-characters-bgm.mp4" \
  "60.300000" "59.300000"
