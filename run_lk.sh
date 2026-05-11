#!/bin/zsh
set -e
cd "$(dirname "$0")"

# Open mascot first so it can connect when the WS server comes up
open "file://$(pwd)/mascot.html"

# Start the LiveKit-backed co-host (foreground; Ctrl-C to stop)
source .venv/bin/activate
exec python3 cohost_lk.py
