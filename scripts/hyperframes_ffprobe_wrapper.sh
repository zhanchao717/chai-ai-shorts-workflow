#!/usr/bin/env bash
set -euo pipefail

compositor_dir="<原制作工作区>/node_modules/@remotion/compositor-darwin-arm64"
exec env DYLD_LIBRARY_PATH="$compositor_dir" "$compositor_dir/ffprobe" "$@"
