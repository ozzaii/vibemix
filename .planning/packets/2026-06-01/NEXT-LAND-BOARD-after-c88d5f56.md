# NEXT LAND BOARD — after `c88d5f56`

- **Date:** 2026-06-01 · **Author:** Claude (read-only) · **HEAD:** `c88d5f56` (`live-tuning-or-brain`)
- **Source:** workflow `wf_458c5dcb-2ad` board agent + [`CODEX_VERIFICATION-cohost-grounding-tts-tags.md`](CODEX_VERIFICATION-cohost-grounding-tts-tags.md). Raw: [`_verify-cohost-tts-grounding-raw-wf_458c5dcb.json`](_verify-cohost-tts-grounding-raw-wf_458c5dcb.json).
- **Posture:** anything that changes what the co-host SAYS or WHEN it speaks is HOLD until `vibemix-grounding-review` PASS + (where named) a live proof. No board item authorizes a HOLD-lane bleed into a LAND commit.
- **⚠️ Staleness warning:** this HEAD is **~12 commits AHEAD** of the older `NEXT-LAND-BOARD-current-head.md` / `CODEX_READY-next-land-board.md` (authored at `dc4702eb`/`e5c0e34e`). Their L1–L5 queue is now **largely LANDED** — verify before reusing them. This doc supersedes them at `c88d5f56`.

---

## Ranked board (next 5)

### 🟢 SAFE_NOW — land in order

#### L1 — Event-driven library fs-watcher module *(P0 freshness gap)*
- **What:** a dedicated `src/vibemix/library/watcher.py` — best-effort, **off-loop**, debounced — so a mid-session Rekordbox XML re-export or dropped track refreshes freshness without the 10s poll being the only signal. Closes the standout P0 from the Viber correction.
- **Value:** high. **Risk:** med — must stay best-effort/off-loop, **never wedge live audio**, and **augment `staleness.py` (the 10s poll), never rip it out**.
- **Shared file:** `src/vibemix/__main__.py` (the loop wire-up — DIRTY, ~13 lanes → **hunk-stage only**, see register below).
- **Gate:** **none for the source slice + tests** — the old "must declare `watchfiles`" blocker is CLEARED (`pyproject.toml:101` + both PyInstaller specs already carry it). Packaged proof (frozen bundle loads the native ext) is a later, separate step.
- **Evidence:** `NEXT-LAND-BOARD-current-head.md#5` (L5) + checklist `:2610-2658` acceptance sketch.

#### L2 — Real-audio auto-cue eval gate *(extend the landed harness)*
- **What:** extend the cue-detect eval scaffold already landed as `89447433` (`scripts/eval/cue_detect.py`, `tests/library/fixtures/cue_real_corpus/manifest.json`, `tests/library/test_cue_detect_eval.py`) with a small license-clean audio/anchor fixture + the regression assertion.
- **Value:** med-high. **Risk:** low-med — **offline regression gate only**; keep ONNX out of CI (load committed embeddings/anchors, mirror `scripts/eval/clap_retrieval.py`).
- **Shared files:** none — pure additive eval lane, no speech path, no contention.
- **Gate:** none. **Do NOT modify the runtime `detect_cues_auto` producer** (eval only).
- **Evidence:** `89447433` landed the scaffold; `NEXT-LAND-BOARD #4` / `CODEX_READY L4`.

#### L3 — Rebuild + re-sign + notarize the macOS DMG from current HEAD
- **What:** every packaged/signed/boots-clean claim is currently **UNPROVEN** — the newest `dist/fresh-20260601-latest/vibemix-0.0.1.dmg` predates all the MOSS/voice-tag/co-host fixes that define current behavior (DMG mtime ≈ 08:32; the verified commits run to 14:56).
- **Value:** high — turns "verified in source" into "verified in the artifact a stranger runs." **Risk:** med — build/release op, not a code change. The MOSS-model-absent boot path is now guarded (`7e496239` boots muted) and `sentencepiece` is in both specs (`07bf2f34`), so the old fresh-machine crash is mitigated.
- **Gate (build hygiene — critical):** build from a **clean `c88d5f56` tree**. The dirty DROP block in `runtime/coach.py` and the dirty `__main__.py`/perception files **MUST NOT be in the build tree**, or **ungated DROP speech ships in the signed binary**. Stash/worktree-isolate before building.
- **Evidence:** `DRIFT-current-head.md` blocker #2 (stale DMG) — now wider at `c88d5f56`.

### 🔴 HOLD — do NOT land without the named gate

#### H1 — DROP-call live hype line *(net-new fixed-text speech on the 2s drop-arm window)*
- **State:** DIRTY-ONLY (uncommitted) across 4 files: `runtime/coach.py:693-718` (WHAT it says — one hunk: `mastered_speak(reaction_line(drop_cue))` then `continue`, skipping the LLM), `state/event_detector.py` (ceiling-priority DROP event — WHEN), `state/drop_predict.py` (`DROP_ARM_WINDOW_S` — WHEN), `__main__.py` (wire-up).
- **Value:** high IF it lands ON beat and grounded — a deterministic on-beat hype line via the fixed-text `say()` path (no LLM, so no tag/English leak). **Catastrophic slop if it fires on a phantom predicted drop.** This is exactly the "real DJ friend, no AI slop" release gate.
- **Gate before any land:** (1) `vibemix-grounding-review` (5 cardinal invariants) **PASS**; (2) live-rig proof the 2s window + TTS latency lands the line **ON** the drop, not late; (3) measure `predicted_drop` **false-positive rate** on real sets.
- **Note:** the old on-by-default aggravator (`VIBEMIX_DROP_CALL=1` setdefault) is **GONE** — the flag is now dormant/opt-in. HOLD-bleed at this HEAD is CLEAN.

#### H2 — `BEATMATCH_GRADED` production producer *(owned-deck practice loop)*
- **State:** consumer-only today — `learn/beatmatch_judge.py:146-153` documents the payload ("A future owned-deck practice loop must fire…"); `skill_recognizer` consumes it. No real-time producer exists.
- **Value:** high — completes the Learn/Earned "Mastered" moat for the headline competency (beatmatching). **Risk:** high — needs **live owned-deck grading hardware** + a Mastered vocal (if the vocal changes → grounding-review).
- **Gate:** `NEEDS_LIVE_PROOF_FIRST` — build the real-time owned-deck producer + live owned-deck proof **BEFORE** unmasking stored Beatmatch mastery. Do NOT unmask without the producer; the honesty boundary (masked + reality-pinned) must hold.

---

## Shared-file risk register (verified live at `c88d5f56`)

| File | Exists | Dirty now | Contention | Caution |
|---|---|---|---|---|
| `src/vibemix/__main__.py` | yes | **DIRTY** | **~13 lanes** (1A observability, 5C/5E/5F freshness, cost, TTS-shutdown, 16ch, deck-audio, + the DROP wire) | **HIGHEST contention.** A whole-file `git add` sweeps an unknown mix — possibly the DROP-call boot-wire — into one LAND commit. **Hunk-stage only**; `git add -p` is unavailable here → write a filtered patch + `git apply --cached --recount`, verify `git diff --cached` before commit. |
| `src/vibemix/runtime/coach.py` | yes | **DIRTY** | Package 8B (Judge voice) + Package 9 (Earned wall) | **CRITICAL bleed risk.** The only dirty content is the **30-line net-new DROP-call SPEECH block** (ungated by grounding-review). A whole-file `git add` ships ungated drop-call speech into a LAND commit. Stage by hunk; keep the DROP block OUT until H1's gate clears. |
| `src/vibemix/state/coach.py` | yes | clean | none active | **CLEAN** (== committed). The brain / prompt builder. **Two `coach.py` files exist — do not conflate** with `runtime/coach.py`. |
| `src/vibemix/agent/dj_cohost.py` | yes | clean | none active | **CLEAN.** LiveKit session + Gemini reaction path. Any future edit is a SPEECH-surface change → `vibemix-grounding-review`. No current staging hazard. |
| `src/vibemix/prompts/matrix.py` | yes | clean | none active | **CLEAN.** Prompt-composition surface → any edit changes WHAT the co-host says (grounding-review + `PROMPT-COMPOSITION.md`). No current staging hazard. |

---

## Cross-cutting follow-ups from the verification (not yet packaged)

- **English-only runtime backstop (MEDIUM)** — the spoken path enforces English by prompt instruction only; no language filter. A non-English (esp. Turkish, given the persona) emission would reach TTS + transcript unfiltered. Candidate next package: a lightweight spoken-path English guard. **Touches the speech surface → ships HOLD (grounding-review).**
- **Citation-in-TTS open question (MEDIUM)** — `[aud:rms@…]`/`[ev:…]` atoms are preserved into `spoken_text` (correct for the visible receipt) but appear to reach MOSS as literal bracket characters. Verify whether the TTS input needs a citation-strip the visible transcript keeps. **Diagnostic first, not a code change.**

---

## Land-queue summary for Codex

```
L1  library/watcher.py (P0 freshness)          SAFE_NOW   hunk-stage __main__.py only
L2  real-audio auto-cue eval gate              SAFE_NOW   pure-additive, no shared files
L3  rebuild+sign+notarize DMG from c88d5f56    SAFE_NOW   build from CLEAN tree (no dirty DROP/main)
H1  DROP-call live hype line                   HOLD       grounding-review PASS + on-beat live proof + FP rate
H2  BEATMATCH_GRADED producer                  HOLD       live owned-deck producer + proof before unmask
```
**Hunk-staging rule (shared files):** `git add -p` is unavailable here → write a filtered patch with only your hunks and `git apply --cached --recount`; verify `git diff --cached` shows only your hunks before committing. Never whole-file `git add` `__main__.py` or `runtime/coach.py`.
