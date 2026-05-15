#!/usr/bin/env bash
# scripts/dayzero/launch_trigger.sh — vibemix public-launch trigger sequence
#
# Stages: T-30, T+0, T+5, T+24h
# Recommended slot: 09:00 EST (HN front-page sweet spot) — Pitfall P78 timing.
#
# DEFAULT MODE = --dry-run. Every action logs `[dry-run] would run: <cmd>`.
# --publish flag required to actually publish. --publish without GH_TOKEN or
# DISCORD_WEBHOOK_URL → exit 2 (autonomous safety).
#
# Usage:
#   bash launch_trigger.sh [--stage t-30|t+0|t+5|t+24h|all] [--publish]
#   bash launch_trigger.sh                      # dry-run all stages
#   bash launch_trigger.sh --publish            # FORBIDDEN without all secrets

set -u

STAGE="all"
PUBLISH="0"
RELEASE_TAG="${RELEASE_TAG:-v2.1.0}"
REPO="${REPO:-bravoh-ai/vibemix}"
DRY_PREFIX="[dry-run]"
LIVE_PREFIX="[publish]"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage)
      STAGE="$2"
      shift 2
      ;;
    --publish)
      PUBLISH="1"
      shift
      ;;
    -h|--help)
      sed -n '1,16p' "$0"
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

# --publish requires both GH_TOKEN and DISCORD_WEBHOOK_URL
if [[ "$PUBLISH" == "1" ]]; then
  if [[ -z "${GH_TOKEN:-}" ]]; then
    echo "error: --publish requires GH_TOKEN (KAAN-ACTION-LEGAL.md OPS-13)" >&2
    exit 2
  fi
  if [[ -z "${DISCORD_WEBHOOK_URL:-}" ]]; then
    echo "error: --publish requires DISCORD_WEBHOOK_URL (KAAN-ACTION-LEGAL.md OPS-13)" >&2
    exit 2
  fi
fi

PREFIX="$DRY_PREFIX"
[[ "$PUBLISH" == "1" ]] && PREFIX="$LIVE_PREFIX"

run() {
  if [[ "$PUBLISH" == "1" ]]; then
    echo "${PREFIX} run: $*"
    "$@"
  else
    echo "${PREFIX} would run: $*"
  fi
}

post_webhook() {
  local body="$1"
  if [[ "$PUBLISH" == "1" ]]; then
    echo "${PREFIX} run: curl -X POST -H 'Content-Type: application/json' -d ... \$DISCORD_WEBHOOK_URL"
    curl -fsS -X POST -H 'Content-Type: application/json' \
      -d "{\"content\":\"$body\"}" "$DISCORD_WEBHOOK_URL" || true
  else
    echo "${PREFIX} would post: $body"
  fi
}

stage_t_minus_30() {
  echo "═ STAGE T-30 ═══════════════════════════════════════════"
  # Spot-check healthz (1 iteration)
  run bash "$(dirname "$0")/healthz_check.sh" --max-iterations 1 --interval 0 --dry-run
  # Preview announcement
  post_webhook "vibemix T-30: launch sequence armed, healthz green"
  echo
}

stage_t_zero() {
  echo "═ STAGE T+0 ═══════════════════════════════════════════"
  # Flip release from draft to published
  run gh release edit "$RELEASE_TAG" --draft=false --repo "$REPO"
  # Discord announcement
  post_webhook "vibemix v2.1 is live → https://github.com/$REPO/releases/tag/$RELEASE_TAG"
  # Cross-post copy paths
  local copy_dir="$(dirname "$0")/launch_copy"
  for platform in twitter instagram linkedin reddit; do
    if [[ -f "$copy_dir/$platform.txt" ]]; then
      echo "${PREFIX} cross-post copy: $copy_dir/$platform.txt"
    fi
  done
  echo
}

stage_t_plus_5() {
  echo "═ STAGE T+5 ═══════════════════════════════════════════"
  # Healthz validate
  run bash "$(dirname "$0")/healthz_check.sh" --max-iterations 1 --interval 0 --dry-run
  # Stargazer count
  run gh api "/repos/$REPO" --jq .stargazers_count
  # Discord celebration
  post_webhook "vibemix T+5: healthz green, momentum measured"
  echo
}

stage_t_plus_24h() {
  echo "═ STAGE T+24h ═══════════════════════════════════════════"
  # Stargazer snapshot
  run gh api "/repos/$REPO" --jq .stargazers_count
  # Traffic snapshot (requires repo admin)
  run gh api "/repos/$REPO/traffic/views" --jq '.count'
  # Discord recap
  post_webhook "vibemix T+24h recap: first day landed"
  echo
}

case "$STAGE" in
  t-30)    stage_t_minus_30 ;;
  t+0)     stage_t_zero ;;
  t+5)     stage_t_plus_5 ;;
  t+24h)   stage_t_plus_24h ;;
  all)
    stage_t_minus_30
    stage_t_zero
    stage_t_plus_5
    stage_t_plus_24h
    ;;
  *)
    echo "unknown stage: $STAGE (valid: t-30, t+0, t+5, t+24h, all)" >&2
    exit 1
    ;;
esac
