# CODEX_READY — Cohost/Viber Runtime Canaries Wrapper

Date: 2026-06-01
Package: Package 1G - Cohost/Viber Runtime Canaries Wrapper
Classification: LAND, source-side release/proof automation

## Summary

This package adds a narrow release helper that runs the exact source-side tests
pinning cohost/Viber anti-hallucination invariants. It is intentionally smaller
than the full cohost/Viber matrix: it answers "are the dangerous speech guards
still exercised and green?" before a broader model/session proof is trusted.

## Files

- `scripts/release/check_cohost_viber_runtime_canaries.sh`
- `tests/eval/test_check_cohost_viber_runtime_canaries_sh.py`

## Canary Set

- `manual_no_evidence_skips_llm`
- `manual_audio_signal_reaches_model`
- `audio_causal_guard_strips_before_tts`
- `audio_source_detail_guard_strips_before_tts`
- `audio_listener_read_survives_before_tts`
- `guard_fallback_stays_silent`
- `uncertain_ack_loop_becomes_silence`
- `manual_silence_report_is_not_repair`

## Verification

- `bash -n scripts/release/check_cohost_viber_runtime_canaries.sh`
  passed.
- `uv run pytest -q tests/eval/test_check_cohost_viber_runtime_canaries_sh.py`
  passed: 2 tests.
- `uv run ruff check tests/eval/test_check_cohost_viber_runtime_canaries_sh.py`
  passed.
- `COHOST_VIBER_RUNTIME_CANARY_OUT_DIR=/tmp/vibemix-runtime-canaries-current-codex PYTHON="$PWD/.venv/bin/python" PYTHONPATH="$PWD/src" bash scripts/release/check_cohost_viber_runtime_canaries.sh`
  passed with:
  `ok=True canaries=8 exercised=8 passed=8 failed=0 missing=0 out_dir=/tmp/vibemix-runtime-canaries-current-codex`.

## Boundaries

- This is source-side automation, not a live DDJ/BlackHole proof and not a
  signed/package release claim.
- The generated `/tmp/vibemix-runtime-canaries-current` artifacts are scratch
  evidence; durable package evidence is this packet plus the package checklist.
- No staging, commit, or product-release claim was made.
