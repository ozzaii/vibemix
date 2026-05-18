---
phase: 40-anti-slop-audio-port
plan: 01
subsystem: audio
tags: [audio, mic, gemini-multimodal, anti-slop, ring-buffer, audio-buffer, kaan-spoke]

# Dependency graph
requires:
  - phase: 02-audio-core-port-ring-buffer-fix
    provides: AudioBuffer (zero-alloc pre-allocated ring) — reused verbatim as the 16kHz int16 12s mic_audio_buf instance
  - phase: 03-sensing-state-port
    provides: MusicState.last_kaan_spoke_at — KAAN_SPOKE-recent gate driver
  - phase: 04-livekit-cascade-agent-pivot
    provides: DJCoHostAgent.llm_node multimodal contents list — Part 2 attach point
provides:
  - mic_audio_buf instance (16kHz int16 12s) wired into the sounddevice mic callback
  - AI-talk zero-fill on the mic ring (Pitfall 1 — self-triggered KAAN_SPOKE loop closed)
  - DJCoHostAgent ``mic_audio_buf`` kwarg + 3-gate decision (instance + recency + presence)
  - 2-Part Gemini contract when KAAN_SPOKE-recent and ring has signal; 1-Part backward-compat otherwise
  - MIC_AUDIO_PART_SECONDS / _RECENCY_S / _PRESENCE_RMS constants exposed for Plan 40-03 consumer
  - mic_part_attached / mic_part_skipped recorder events for coach-loop diagnostics
affects:
  - 40-03-PLAN.md (3-Part lookahead consumer — appends Part 3 immediately after Part 2 at dj_cohost.py:417)
  - 40-04-PLAN.md (prompt template enumeration of P1/P2/P3 lands here)
  - tauri Settings → Diagnostics surface (recorder events become a UI consumer in v2.x)

# Tech tracking
tech-stack:
  added: []  # no new dependencies — scipy.signal.resample_poly + numpy already in use
  patterns:
    - "Three-gate multimodal Part attachment (instance + recency + presence) — reusable for Plan 40-03 Part 3 (lookahead) and any future Gemini Part addition"
    - "Sounddevice callback second-buffer tap with try/except Exception: pass — never crash the audio thread (v4:2293-2294 verbatim pattern)"
    - "AI-talk zero-fill at the audio-callback boundary — load-bearing self-loop prevention before the data crosses any async boundary"

key-files:
  created:
    - "tests/audio/test_mic_audio_buf.py (173 LOC) — ring + callback unit tests (T1-T5 + backward compat)"
    - "tests/agent/test_dj_cohost_mic_part.py (318 LOC) — 1/2/3-Part integration tests + mime type + recorder events"
    - ".planning/phases/40-anti-slop-audio-port/deferred-items.md — pre-existing failures logged out-of-scope"
  modified:
    - "src/vibemix/audio/constants.py — three new MIC_AUDIO_PART_* constants (+9 LOC)"
    - "src/vibemix/audio/__init__.py — re-export the three constants (+6 LOC)"
    - "src/vibemix/__main__.py — _mic_callback_factory signature extension + mic_audio_buf instantiation + DJCoHostAgent kwarg wiring (+55 / -4 LOC)"
    - "src/vibemix/agent/dj_cohost.py — mic_audio_buf kwarg + three-gate Part 2 attachment in llm_node + structured recorder events (+101 / -5 LOC)"

key-decisions:
  - "Reuse AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET) directly as the mic_audio_buf — CONTEXT.md's MicAudioRing class would be anti-DRY (RESEARCH 'Alternatives Considered' explicitly recommended verbatim AudioBuffer reuse; v4:2257 uses AudioBuffer for the same purpose)."
  - "Three-gate Part 2 decision (instance + recency + presence) runs ONCE per turn; the snapshot and RMS are reused by both the prompt-suffix wording and the structured log line — avoids double-work on the LLM hot path."
  - "Zero-fill happens at the sounddevice-callback boundary (NOT inside llm_node) so the ring contents are clean before any consumer reads. Filtering in llm_node would still let the AI's own voice land in the ring."
  - "Recorder emits mic_part_attached / mic_part_skipped events at INFO level (no log spam) so coach-loop tails and Settings UI can show the decision per turn without re-deriving from the ``contents`` argument."

patterns-established:
  - "Pattern: optional kwargs-only ring-buffer instance on DJCoHostAgent — mirrors the cache / linter / ack_bank / profile pattern; default None preserves byte-identical 1-Part path for the existing Phase 4/18/19 test suite."
  - "Pattern: structured 'attached / skipped' recorder event pair — every conditional multimodal Part attachment in future plans should emit the same pair so coach-loop diagnostics stay uniform."

requirements-completed: [AUDIO-01]

# Metrics
duration: ~10 min
completed: 2026-05-16
---

# Phase 40 Plan 01: Anti-Slop Audio Port — Mic-as-2nd-Gemini-Part Summary

**Mic ring buffer + AI-talk zero-fill + DJCoHostAgent three-gate Part 2 attachment — Kaan's literal voice now lands in front of Gemini whenever KAAN_SPOKE is recent and the mic ring has signal, closing the "AI invents what Kaan said" hallucination class.**

## Performance

- **Duration:** ~10 min (582 seconds wall-clock from RED commit f5d06a4 to GREEN commit 7b6dc02)
- **Started:** 2026-05-16T11:33:18Z
- **Completed:** 2026-05-16T11:43:15Z
- **Tasks:** 2 (each TDD: test → impl)
- **Files modified:** 6 (4 src, 2 tests, +1 created planning doc)
- **LOC delta:** +653 / -9

## Accomplishments

- **Mic as literal Gemini Part 2.** When Kaan speaks (KAAN_SPOKE fires within `MIC_AUDIO_PART_RECENCY_S` = 4.0s) and the mic ring has signal (RMS above `MIC_AUDIO_PART_PRESENCE_RMS` = 0.005 in float-domain ≈ 163 int16), Gemini receives the last 8s of Kaan's mic as a second `audio/wav` Part. Closes the v4-baseline anti-slop primitive that Phase 4/10's port intentionally deferred.
- **Self-loop closed (Pitfall 1).** The mic callback zero-fills the resampled int16 stream whenever `mic._current_gain() == MIC_GAIN_AT_AI_TALK` — the AI's own voice can no longer reach Gemini as "Kaan's voice" through the speaker→mic feedback path. Zero-fill happens at the audio-callback boundary, so every downstream consumer (mic Part 2 included) sees the clean ring.
- **Three-gate attachment preserves byte-identity for 1-Part baseline.** When `mic_audio_buf=None` (test fixtures and any caller not opting in), or KAAN_SPOKE has not fired recently, or the ring is silent, the request shape stays at 2 elements (text + Part 1 mix) — all 99 existing DJCoHostAgent tests pass without modification.
- **Diagnostic surface added.** `mic_part_attached` (with `duration_s`, `rms_int16`, `kaan_spoke_age_s`, `bytes`) and `mic_part_skipped` (with `reason`) events flow through `VoiceRecorder.log_event` to `events.jsonl` — ready for coach-loop tails and the Plan 12 Settings → Diagnostics surface to consume without re-deriving from the `contents` list.

## Task Commits

1. **Task 1 RED: Mic ring + AI-talk zero-fill failing tests** — `f5d06a4` (test)
2. **Task 1 GREEN: Wire mic_audio_buf ring + callback extension** — `74c0b32` (feat)
3. **Task 2 RED: DJCoHostAgent mic Part 2 failing tests** — `288fa38` (test)
4. **Task 2 GREEN: Attach mic Part 2 in DJCoHostAgent.llm_node** — `7b6dc02` (feat)

_TDD RED→GREEN cycle followed for both tasks — every behavior pinned by a failing test before implementation._

## Files Created/Modified

### Created

- **`tests/audio/test_mic_audio_buf.py`** (173 LOC) — Ring + callback unit tests:
  - `test_mic_audio_part_constants_exported` — pins the 3-constant surface and values.
  - `test_t1_push_and_snapshot_16khz_sine` — push/snapshot round-trip at 16kHz.
  - `test_t2_callback_resamples_48k_to_16k` — 48k input becomes 16k in the ring.
  - `test_t3_zero_fill_during_ai_talk` — Pitfall 1 self-loop prevention (load-bearing IP).
  - `test_t4_ring_size_192000` — 12s × 16kHz = 192000 int16 sample reservation.
  - `test_t5_zero_alloc_invariant_across_pushes` — `id(_buf)` stable across 100 pushes.
  - `test_callback_backward_compat_when_mic_audio_buf_none` — v2.1 byte-identical path preserved when not wired.

- **`tests/agent/test_dj_cohost_mic_part.py`** (318 LOC) — 1/2/3-Part integration tests:
  - `test_part_count_2_when_no_mic_audio_buf` — Phase 4/18/19 backward compat.
  - `test_part_count_2_when_kaan_spoke_not_recent` — recency gate.
  - `test_part_count_2_when_mic_silent` — presence-floor gate.
  - `test_part_count_3_when_recent_kaan_with_signal` — all-three-gates happy path.
  - `test_mic_part_mime_is_audio_wav` — Part 2 mime + RIFF envelope.
  - `test_mic_part_attached_logs_event` — `mic_part_attached` recorder event surface.

- **`.planning/phases/40-anti-slop-audio-port/deferred-items.md`** — pre-existing failures logged out-of-scope per executor SCOPE BOUNDARY rule.

### Modified

- **`src/vibemix/audio/constants.py`** (+9 LOC) — Three new module-level constants in a clearly-marked "Plan 40-01 — mic-as-2nd-Part wiring" block:
  - `MIC_AUDIO_PART_SECONDS: float = 8.0`
  - `MIC_AUDIO_PART_RECENCY_S: float = 4.0`
  - `MIC_AUDIO_PART_PRESENCE_RMS: float = 0.005`

- **`src/vibemix/audio/__init__.py`** (+6 LOC) — Re-export the three new constants in both the `from vibemix.audio.constants import (...)` block and the `__all__` list.

- **`src/vibemix/__main__.py`** (+55 / -4 LOC):
  - Import `MIC_GAIN_AT_AI_TALK` from `vibemix.audio`.
  - Extend `_mic_callback_factory(mic, mic_audio_buf=None)`. When `mic_audio_buf` is provided, the inner callback ALSO: (a) `resample_poly` 48k→16k, (b) zero-fill if `mic._current_gain() == MIC_GAIN_AT_AI_TALK`, (c) clip to int16, (d) `mic_audio_buf.push(pcm16)`. All wrapped in `try/except Exception: pass` (v4:2293-2294 pattern).
  - Instantiate `mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)` next to the existing `clean_audio_buf` allocation.
  - Pass `mic_audio_buf` to `_mic_callback_factory(mic, mic_audio_buf)` at the mic-stream open site.
  - Pass `mic_audio_buf=mic_audio_buf` into the `DJCoHostAgent(...)` constructor.

- **`src/vibemix/agent/dj_cohost.py`** (+101 / -5 LOC):
  - Import `MIC_AUDIO_PART_SECONDS`, `MIC_AUDIO_PART_RECENCY_S`, `MIC_AUDIO_PART_PRESENCE_RMS` from `vibemix.audio`.
  - Add kwargs-only `mic_audio_buf: AudioBuffer | None = None` to `DJCoHostAgent.__init__`; store as `self._mic_audio_buf`. Default `None` preserves Phase 4/18/19 backward compat.
  - In `llm_node`, immediately BEFORE the `contents = [...]` assembly, compute the three-gate mic Part decision (instance check → recency check → presence-RMS check). When all three pass, `snapshot_wav(self._mic_audio_buf, MIC_AUDIO_PART_SECONDS)` → `mic_wav` bytes.
  - Replace the f-string prompt suffix with a Part-aware branch: when no mic Part, emit the original 1-Part wording; when Part 2 attached, emit `"Attached: P1 = last Ns of live mix (BlackHole), P2 = your mic (last 8s, your voice as Kaan)."`.
  - When `mic_wav` is non-None, `contents.append(types.Part.from_bytes(data=mic_wav, mime_type="audio/wav"))` immediately after Part 1 and BEFORE the screen append block — Plan 40-03 will append Part 3 (lookahead) at this same insertion point.
  - Emit `mic_part_attached` (with `duration_s`, `rms_int16`, `kaan_spoke_age_s`, `bytes`) or `mic_part_skipped` (with `reason`, `kaan_spoke_age_s`, `rms_int16`) recorder event per turn.

## Decisions Made

1. **Reuse `AudioBuffer` instead of subclassing as `MicAudioRing`.** CONTEXT.md mentioned a `MicAudioRing` class name; the PLAN's `<interfaces>` section AND RESEARCH "Alternatives Considered" explicitly recommended verbatim `AudioBuffer(12.0, 16000)` reuse — v4 does the same at `cohost_v4.py:2257`. A new identical class would be anti-DRY. Decision propagated cleanly.

2. **Zero-fill at the callback boundary, not in `llm_node`.** Pitfall 1 is a real observed self-loop failure mode (the AI's voice plays through speakers → mic → ring → Gemini hears the AI saying what it just said and fires KAAN_SPOKE on its own output). Filtering in `llm_node` would still let the AI's voice contaminate the ring; filtering at the callback boundary keeps the ring contents clean for every consumer. This is the v4 verbatim pattern from `cohost_v4.py:2278-2296`.

3. **Three-gate decision computed once per turn.** The snapshot + RMS calculation runs ONCE; the result feeds both the prompt-suffix wording ("P1 + P2" vs 1-Part baseline) AND the structured log line. Avoids double-work on the LLM hot path and keeps the wiring legible.

4. **Structured `mic_part_attached` / `mic_part_skipped` events.** Both branches log to `events.jsonl` with a consistent field schema (`duration_s` / `rms_int16` / `kaan_spoke_age_s` / `bytes` on attach; `reason` / `kaan_spoke_age_s` / `rms_int16` on skip). The Settings → Diagnostics surface (Phase 12) and coach-loop tails can consume these without re-deriving from the `contents` list — a v2.x UX hook is now pre-wired.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree dev environment had no Python venv + POC files**

- **Found during:** Task 1 verify suite execution (post-RED commit).
- **Issue:** The worktree at `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a1f1006e8be7ee50b/` does not carry a `.venv/` (Python venv lives in the main project tree only), and the POC files `cohost_v4.py` / `cohost_v4_tr.py` are untracked at the main project root and absent from the worktree (the test suite needs `cohost_v4.py` for the `v4_persona_string()` AST extract).
- **Fix:** Used the main project's `.venv/bin/python` with `PYTHONPATH=<worktree>/src` to resolve `vibemix.*` from the worktree (verified `vibemix.__file__` resolves correctly). Symlinked `cohost_v4.py` and `cohost_v4_tr.py` from the main project root into the worktree (untracked, dev-only). Both are local-dev fixups — not part of the plan deliverable, not committed.
- **Files modified:** None tracked. Symlinks at worktree root: `cohost_v4.py → /Users/ozai/projects/dj-set-ai/cohost_v4.py`, `cohost_v4_tr.py → /Users/ozai/projects/dj-set-ai/cohost_v4_tr.py`.
- **Verification:** `from vibemix.audio import MIC_AUDIO_PART_SECONDS; print(MIC_AUDIO_PART_SECONDS)` → `8.0` from worktree path. Full test suite ran cleanly.

**2. [Rule 2 - Missing Critical] Plan suffix wording would have leaked "mic" into the 1-Part baseline**

- **Found during:** Task 2 (GREEN implementation).
- **Issue:** The existing prompt suffix said `"Attached: last Ns of audio (mix + mic)"` even in the 1-Part baseline. Plan 40-01 PLAN specified switching to a Part-aware wording but did NOT call out that the 1-Part baseline phrase mentions a mic that isn't there. Left as-is, Gemini would expect mic content in the single mix Part — a confused-by-prompt hallucination class.
- **Fix:** Split the suffix into two branches. When no mic Part: keep the existing v4-byte-identical `"mix + mic"` wording (test pins this — the existing `test_dj_cohost.py` tests passing 99/99 confirms byte-identity). When Part 2 attached: explicit `"P1 = last Ns of live mix (BlackHole), P2 = your mic (last 8s, your voice as Kaan)"`. Both branches now match Gemini's mental model of the attached Parts.
- **Files modified:** `src/vibemix/agent/dj_cohost.py` (llm_node prompt suffix block).
- **Verification:** All 99 existing DJCoHostAgent tests pass (no regression in 1-Part baseline wording); new 2-Part path test passes with the explicit P1/P2 wording.

---

**Total deviations:** 2 auto-fixed (1 blocking environment fix, 1 missing-critical prompt-wording fix).
**Impact on plan:** No scope creep. The environment fix is local-dev infrastructure (no committed code). The prompt-wording fix is required for correctness — without it, the 1-Part baseline wording would mismatch reality. Both are local to Task 1/2 surface and documented inline.

## Issues Encountered

- **Stale `origin/main` vs local `main`:** The worktree was spawned from a base that did NOT contain Phase 40 plans (origin/main at `d7accba`); local `main` was 458 commits ahead and contained the expected sentinel `00e7b6c`. Merged local `main` into the worktree per the runbook's fallback (`git merge origin/main --no-edit 2>/dev/null || git merge main --no-edit`). Verified merge brought in `.planning/phases/40-anti-slop-audio-port/` and the expected HEAD shape (`dj_cohost.py` with `cache`, `linter`, `profile` kwargs — Phase 33+ shape, not the Phase-10-era stub).
- **Pre-existing test failures on main:** `test_main_smoke 03/04/05` (mock fixture chain drift), `test_event_gap_dict_shape_and_values` (Phase 30 SENSE-17/18 keys missing from snapshot), `test_persona_02_byte_identical_to_v4` (post-Phase-18 persona drift). All confirmed pre-existing on `/Users/ozai/projects/dj-set-ai/` without any Plan 40-01 changes. Logged to `.planning/phases/40-anti-slop-audio-port/deferred-items.md` per SCOPE BOUNDARY rule; none are caused by this plan.
- **Stale LFS pointers in `tauri/ui/assets/mascot/*.glb` (21 files):** Worktree LFS resolution mismatch — the merge from local `main` brought down pointer text instead of binary blobs. Pre-existing infrastructure issue (the merge message explicitly flagged 2 files in `tests/library/fixtures/`). Documented in `deferred-items.md`. Not relevant to audio code; will surface when Phase 13 mascot render rebuilds.

## User Setup Required

None — no external service configuration. All wiring is in-process (`AudioBuffer` ring + `_mic_callback_factory` + `DJCoHostAgent.__init__`).

## Plan 40-03 Continuation Note

**Part 2 attach point is at `src/vibemix/agent/dj_cohost.py:417`** — the line
`contents.append(types.Part.from_bytes(data=mic_wav, mime_type="audio/wav"))`.
Plan 40-03 (3s file-based lookahead Part 3) appends immediately after Part 2,
inside the same conditional block (or as a sibling block — both Part 2 and
Part 3 should share the `mic_part_attached` / `lookahead_part_attached`
recorder-event pattern established here). The prompt-suffix wording branch
extends from the current 1-Part / 2-Part split to a 3-way 1-Part / 2-Part /
3-Part dispatch — keep the f-string composition open for that.

The three new constants (`MIC_AUDIO_PART_SECONDS / _RECENCY_S / _PRESENCE_RMS`)
are re-exported from `vibemix.audio` so any Plan 40-03 / 40-04 consumer can
import them without a downstream patch.

## POC Immutability Gate (Phase 37-06)

`git status` on tracked POC files (`cohost.py`, `cohost_v2.py`, `cohost_lk.py`)
shows no modifications. `cohost_v4.py` and `cohost_v4_tr.py` are untracked in
the repo at the main project root; the worktree symlinks them locally for
test access only and they are NOT committed. **POC immutability gate: PASS.**

## Self-Check: PASSED

- All four task commits exist in `git log`: `f5d06a4` (RED 1), `74c0b32` (GREEN 1), `288fa38` (RED 2), `7b6dc02` (GREEN 2).
- All 4 created/modified files exist at the expected paths.
- Plan 40-01 verify suite green: `tests/audio/test_mic_audio_buf.py` (7 passed) + `tests/agent/test_dj_cohost_mic_part.py` (6 passed) + `tests/audio/test_buffers.py` (21 passed, no regression) + `tests/agent/test_dj_cohost.py` (31 passed, no regression) = 65/65 in the verify-suite.
- `grep -n "MIC_AUDIO_PART_SECONDS\|MIC_AUDIO_PART_RECENCY_S\|MIC_AUDIO_PART_PRESENCE_RMS" src/vibemix/audio/constants.py | wc -l` = 3 ✓
- `grep -c "mic_audio_buf" src/vibemix/__main__.py` = 9 (≥3) ✓
- `grep -c "self._mic_audio_buf" src/vibemix/agent/dj_cohost.py` = 6 (≥3) ✓
- `mic_audio_buf._size == 192000` confirmed by `test_t4_ring_size_192000` ✓

---
*Phase: 40-anti-slop-audio-port*
*Completed: 2026-05-16*
