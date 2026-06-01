# CODEX_READY: No Spoken Fallbacks Live Guard

Date: 2026-06-01
Author: Codex
Status: LAND packet, spoken safety slice
Package: Package 8D - No Spoken Fallbacks Live Guard

## Decision

LAND this slice as `fix(cohost): strip unsafe live-claim fallbacks`.

The product rule is simple: when the live co-host guard catches unsupported
deck, EQ, transition, or source-detail causality, Sven must not speak a canned
replacement. A guard hit means the turn was unsafe; the spoken path should stay
silent while raw/corrected text remains available in logs and repair artifacts.

## Files

- `.planning/handoffs/2026-05-31-no-spoken-fallbacks-invariant.md`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/eval/session_report.py`
- `src/vibemix/state/deck_context.py`
- `tests/agent/test_dj_cohost.py`
- `tests/agent/test_dj_cohost_linter.py`
- `tests/eval/test_cohost_viber_session_report.py`
- `tests/state/test_deck_context.py`
- `tests/library/test_codex_curate.py`
- `tests/library/test_live_context_cli.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-no-spoken-fallbacks-live-guard.md`

## What Changed

- The invariant doc records the no-spoken-fallback product rule: guard hits are
  strip/silence events, not user-facing replacement copy.
- `DJCoHostAgent.llm_node` treats `live_claim_guard.corrected` like a strip on
  the spoken path: it logs `live_claim_guard` with `action="strip"`, records the
  raw and corrected text, clears buffered chunks, clears spoken text, and avoids
  transcript/cohost-reaction publication from the corrected fallback.
- `apply_live_claim_guard()` still returns short held replies for artifacts and
  repair/eval, but the live co-host audio path no longer voices those held
  replies when the guard corrected the model output.
- `session_report.py` now detects the bad regression shape: if a live-coach
  `ai_message` emits or bypasses text that matches a `live_claim_guard`
  corrected/fallback row, it raises `live_claim_guard_spoken_fallback` as a
  blocker.
- Viber/library verification keeps honest text results separate from spoken
  co-host behavior. Explicit library/chat turns can return text; unsafe live
  causality does not become Sven speech.

## Evidence

Live co-host strip behavior:

```text
uv run pytest -q tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py -k 'live_claim_guard or deck_audio_parts_not_attached or event_audio_capture_context'
8 passed, 62 deselected in 1.00s
```

Live-claim policy:

```text
uv run pytest -q tests/state/test_deck_context.py -k 'live_claim_guard or live_claim_policy'
37 passed, 69 deselected in 0.05s
```

Viber/live-context verifier:

```text
uv run pytest -q tests/library/test_codex_curate.py -k 'library_request or live_context or chat_with_codex' tests/library/test_live_context_cli.py -k 'verify_live_reply'
9 passed, 119 deselected in 0.33s
```

Release report blocker:

```text
uv run pytest -q tests/eval/test_cohost_viber_session_report.py -k 'live_claim_guard or spoken_live_claim_guard'
1 passed, 24 deselected in 0.03s
```

Current-source manual no-evidence live proof:

```text
VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix
ws trigger: {"action":"trigger"}
runtime: [event MANUAL] audible=False deck=none track=None(0.0) phase=silent
runtime: [ai_text] <manual silence: no live evidence>
```

Observed session:

```text
~/Library/Application Support/vibemix/recordings/20260601-085534/
events.jsonl: manual_silence_short_circuit reason=manual_no_live_evidence
events.jsonl: ai_message engine=live_coach event=MANUAL message="" response_chars=0
events.jsonl: suppression=manual_no_evidence citation.action=skip
events.jsonl: extra.pre_llm_short_circuit=true extra.audio_tokens_est=0
events.jsonl: extra.avoided_audio_tokens_est=1920
invocations/0001_085547_MANUAL/response.txt: 0 bytes
ai_messages/artifacts/0001_085547/response.txt: 0 bytes
ws ipc.session.snapshot observation: transcript_delta stayed []
```

This proves the current source does not voice, publish, or synthesize a canned
fallback when a manual request has no grounded live evidence. It complements the
guard-corrected-output tests above: unsafe turns are logged for observability and
repair, while the spoken path stays silent.

Lint:

```text
uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py src/vibemix/eval/session_report.py tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/eval/test_cohost_viber_session_report.py
All checks passed!
```

Whitespace:

```text
git diff --check -- src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py src/vibemix/eval/session_report.py tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/eval/test_cohost_viber_session_report.py .planning/handoffs/2026-05-31-no-spoken-fallbacks-invariant.md
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This does not prove the packaged app or a final live DJ recording set.
- The current-source manual silence proof had no controller move context; it
  proves the no-evidence speech path only, not a full two-deck judged set.
- It does not remove the guard-held text from artifacts; keeping that text is
  useful for repair, eval, and prompt hardening.
- This does not claim a direct Viber-to-Sven TTS bridge exists. Current source
  review shows the bug class was shared held-reply behavior and live-cohost
  emission, not a direct Viber speech bridge.

## Next Required Proof

Before release, run `vibemix eval latest-session` or the cohost/Viber matrix
against the final recording set and fail the release if any guard-corrected live
co-host turn produced spoken audio, transcript text, or
`ipc.session.cohost-reaction`.
