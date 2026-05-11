#!/bin/zsh
set -e
cd "$(dirname "$0")"

open "file://$(pwd)/mascot.html"

source .venv/bin/activate
exec python3 cohost_v2.py
