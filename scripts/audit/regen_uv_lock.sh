#!/usr/bin/env bash
# Phase 46 / DEPS-01 — Hermetic uv.lock regenerator.
#
# Why: Pitfall 1 (.planning/research/PITFALLS.md) — `pip freeze` from
# Kaan's .venv poisons the lockfile with macOS-arm64-only wheels +
# dev-only packages. This script runs `uv lock` inside a Linux container
# so the resulting lockfile is portable across Mac arm64+x86_64 + Win64
# + Linux and reproducible bit-for-bit on any developer machine + CI.
#
# Usage: bash scripts/audit/regen_uv_lock.sh
# (No arguments — re-runs are idempotent.)

set -euo pipefail

IMAGE="python:3.12-slim-bookworm"
UV_VERSION="0.11.14"

command -v docker >/dev/null 2>&1 || { echo "docker not found; install Docker Desktop"; exit 2; }
[ -f pyproject.toml ] || { echo "pyproject.toml not found — run from repo root"; exit 2; }

docker run --rm \
  -v "$PWD":/work \
  -w /work \
  "$IMAGE" \
  bash -lc "pip install --no-cache-dir uv==${UV_VERSION} && uv lock --no-progress"

echo "uv.lock regenerated hermetically against $IMAGE + uv==$UV_VERSION"
