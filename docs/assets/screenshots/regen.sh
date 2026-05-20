#!/usr/bin/env bash
# Regenerate the 5 README UI screenshots from _studio.html.
# The studio renders all 5 surfaces at app fidelity using the real v5
# CDJ Whisper tokens (tauri/ui/src/tokens.css). It lives here (not in
# tauri/ui/public/) so it never ships inside the app bundle; the script
# copies it into public/ only while shooting, then removes it.
#
# Prereq: vite dev server serving tauri/ui on http://localhost:1420
#   (cd tauri/ui && npm run dev)   — needed so /fonts/*.woff2 resolve.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
PUBLIC="$REPO/tauri/ui/public"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

cp "$HERE/_studio.html" "$PUBLIC/_studio.html"
trap 'rm -f "$PUBLIC/_studio.html"' EXIT

for shot in wizard mode-picker voice-picker session recordings; do
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --window-size=1100,720 \
    --screenshot="$HERE/$shot.png" \
    "http://localhost:1420/_studio.html?shot=$shot" >/dev/null 2>&1
  echo "shot $shot -> $HERE/$shot.png"
done
