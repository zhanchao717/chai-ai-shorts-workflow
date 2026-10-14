#!/usr/bin/env bash
set -euo pipefail

compositor_dir="<REPO>/node_modules/@remotion/compositor-darwin-arm64"
exec env DYLD_LIBRARY_PATH="$compositor_dir" "$compositor_dir/ffprobe" "$@"
