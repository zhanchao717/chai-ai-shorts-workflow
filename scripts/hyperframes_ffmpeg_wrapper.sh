#!/usr/bin/env bash
set -euo pipefail

compositor_dir="<REPO>/node_modules/@remotion/compositor-darwin-arm64"
real_ffmpeg="$compositor_dir/ffmpeg"
args=("$@")

if (( ${#args[@]} > 0 )); then
  last_index=$(( ${#args[@]} - 1 ))
  last_arg="${args[$last_index]}"
  if [[ "$last_arg" == *.m4a ]]; then
    exec env DYLD_LIBRARY_PATH="$compositor_dir" "$real_ffmpeg" "${args[@]:0:$last_index}" -f mp4 "$last_arg"
  fi
fi

exec env DYLD_LIBRARY_PATH="$compositor_dir" "$real_ffmpeg" "${args[@]}"
