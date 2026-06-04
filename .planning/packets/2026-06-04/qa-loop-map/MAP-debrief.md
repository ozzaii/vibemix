# MAP — DEBRIEF engine ("the most overlooked engine")

READ-ONLY map. Branch `ux-redesign-impeccable`. Every claim carries file:line.
Verdict legend: **REAL** = code path verified end-to-end · **PARTIAL** = built but
gapped/untested-live · **ASPIRATIONAL** = comment/doc promises more than the wired code.

---

## TL;DR (the one-paragraph truth)

Debrief is the **most fully-built and most reachable of the secondary engines** — and
genuinely surprising given Kaan calls it "overlooked". The full pipeline EXISTS and is
wired both ends: a recorded `session_dir` → `python -m vibemix --debrief <dir>` →
chapters + 3 cited drills (real Gemini call) + a voiced TLDR MP3 (local Chatterbox) →
WS server on `127.0.0.1:8766` → a dedicated Tauri window UI → it is reachable from **TWO**
live entry points (the Settings → Recordings row's debrief button AND a dedicated Debrief
surface/dock in the DesktopShell). The session→profile loop is CLOSED (`profile_writeback.py`).
The anti-slop citation gate is REAL and aggressive (`stripper.py` drops every uncited
sentence). **The single biggest gap is that the whole thing is GENERATION-GATED on a live
Gemini key + network**: first-time (non-cached) debrief makes blocking `generate_content`
calls for drills and TLDR, and if there's no key the user gets `ipc.debrief.error` and a
blank-ish window. The second gap is that it is **batch/manual only** — nothing auto-launches
a debrief when a live set ends, so for the autonomous QA harness it must be driven by hand.

---

## 1. What is BUILT (the file inventory, all REAL)

`src/vibemix/debrief/` is 10 modules, all substantive (not stubs):

| Module | Role | Verdict |
|---|---|---|
| `session_loader.py` | load events.jsonl + evidence_registry.json + voice.wav meta; enforces 5-min minimum | **REAL** (`session_loader.py:115-166`) |
| `chapters.py` | events.jsonl → `list[ChapterRegion]` (TRACK_CHANGE / PHASE breaks) | **REAL** (`chapters.py:119-189`) |
| `drills.py` | Gemini structured-output → exactly 3 SBI/STAR-AR drills, each citation resolved ±2.0s against the evidence snapshot, retries 2× | **REAL** (`drills.py:225-343`) |
| `tldr.py` | Gemini → 150-220-word cited narration → strip uncited → local Chatterbox TTS → PyAV libmp3lame MP3 | **REAL** (`tldr.py:142-311`) |
| `stripper.py` | DEBRIEF-07 hard gate: sentence-level cited-only filter, reuses Phase-18 `EVIDENCE_CITATION_RE` | **REAL** (`stripper.py:1-40`) |
| `persistence.py` | atomic write/read of `session_debrief.json` + `debrief_tldr.mp3`, SHA-256 cache key | **REAL** (`persistence.py:62-137`) |
| `main.py` | orchestrator: validate → cache-hit fast path → generate → persist → serve WS | **REAL** (`main.py:274-451`) |
| `ws_server.py` | async WS on 8766; progressive frames + citation-tooltip replies | **REAL** (`ws_server.py:39-282`) |
| `profile_writeback.py` | One-Mind S5: feed reviewed session back into long-term DJ profile | **REAL** (`profile_writeback.py:41-90`) |
| `__init__.py` | clean public surface | **REAL** (`__init__.py:25-59`) |

Test coverage is heavy: **32 test files** touch debrief (`tests/debrief/`, `tests/e2e/test_debrief_*`,
`tests/main/test_debrief_*`). Includes path-traversal rejection, no-uncited-critique gate,
profile writeback, cache-hit e2e, open/close cycle e2e. This is NOT a dark module — it's
one of the better-tested subsystems.

---

## 2. What it PRODUCES (per session)

On the **first-time** path (`main.py:345-450`):

1. **Chapters** — derived purely from `events.jsonl` event types (`derive_chapters`,
   `chapters.py:119`). Breaks on `TRACK_CHANGE` (always) and `PHASE/LAYER_ARRIVAL/MIX_MOVE/
   KAAN_SPOKE` (≥30s gap). Each chapter carries a `citation_event_id` of the form
   `ev:<TYPE>@<t>`. Degenerate sessions get one synthesized chapter (`chapters.py:159-171`).
   → **REAL, deterministic, no LLM, no key needed.**

2. **3 drills** — Gemini structured output (pydantic `Drills`, exactly 3, `drills.py:61-64`).
   Each drill's `citation` MUST resolve against the `evidence_snapshot` at ±2.0s
   (`drills.py:120-144`, tolerance bound to `coach/constants.DEBRIEF_TOLERANCE_S` at
   `drills.py:48`). Each behavior/impact/action field must carry ≥1 citation
   (`drills.py:301-309`). Retries 2× then raises `DrillsGenerationError`. → **REAL but
   key-gated** (blocking `client.models.generate_content`, `drills.py:247`).

3. **Voiced TLDR MP3** — Gemini narration (`tldr.py:142`) → `strip_uncited_sentences`
   (`tldr.py:189`) → if everything stripped, raises (`tldr.py:200`) → local Chatterbox TTS
   (`tldr.py:222-301`) → PyAV libmp3lame MP3 bytes (`tldr.py:366-400`). → **REAL but
   key-gated for the text leg; the voice leg is local/keyless.**

4. **Profile write-back** — after review, rebuilds the long-term DJ profile from the
   session's STRUCTURED events + evidence snapshot (NOT from drill prose — deliberate
   anti-slop choice, `profile_writeback.py:14-30`). Consent-gated, best-effort
   (`main.py:453-461` → `profile_writeback.py:41`). → **REAL — the session→profile loop
   IS closed.** This directly answers Kaan's "close the session→lesson→profile loop" — the
   profile half is done.

Persisted artifacts: `session_debrief.json` (chapters+drills+sha) + `debrief_tldr.mp3`
(`persistence.py:35-36`). Cache key = SHA-256 of the MP3 (`persistence.py:80`). On a
cache hit the whole thing replays in <1s with **zero Gemini calls** (`main.py:316-343`) —
this is the key-free, network-free, deterministic replay path.

---

## 3. Is it REACHABLE from the live UI? — YES, two ways (both wired)

**Entry point A — Settings → Recordings row "Open Debrief" button:**
- `recording-row.ts:471-501` renders a debrief button, disabled when session
  `< 300s` OR `< 5 events` (`recording-row.ts:475-478`), click → `invoke("open_debrief_window", { sessionDir })` (`recording-row.ts:494`).
- The recording browser IS mounted in the live settings drawer:
  `SettingsDrawer.ts:1155 renderRecordingBrowser(...)`, populated from `ipc.recordings.list_result`
  (`SettingsDrawer.ts:1442-1444`). The browser renders rows via `renderRecordingRow`
  (`recording-browser.ts:365`). → **REAL chain, both ends present.**

**Entry point B — dedicated Debrief surface in the DesktopShell (the "dock"):**
- A `debrief` surface is registered in the shell (`surfaces.ts:92`, wire `shell.surface.debrief`).
- `app.ts:80-82` provides `mountDebrief` → dynamic-imports + mounts `DebriefDock`
  (`DebriefDock.ts:426 mountDebriefDock`). `surface-mounts.ts:127-128` calls it during shell wire-up.
- The dock fetches `ipc.recordings.list` (`DebriefDock.ts:487-491`), renders a session
  list + a "readiness" panel, and each session's open button → `invokeTauri("open_debrief_window", { sessionDir })`
  (`DebriefDock.ts:624-628`). → **REAL chain, both ends present.**

**The Rust command exists and is registered:**
- `tauri/src-tauri/src/debrief_window.rs:145 open_debrief_window` — resolves+path-validates
  the session dir (`debrief_window.rs:81 resolve_debrief_session`), spawns the
  `--debrief <dir>` sidecar (`debrief_window.rs:169 build_debrief_sidecar_command`), opens a
  webview at `debrief.html?session=...` (`debrief_window.rs:195-199`), watches for crash
  and emits `sidecar-debrief-crashed` (`debrief_window.rs:234`).
- Registered in the invoke handler: `main.rs:99 debrief_window::open_debrief_window`. → **REAL.**

**The window UI exists** (`tauri/ui/src/debrief/`):
- `debrief-window.ts` connects `new DebriefWsClient(8766)` (`debrief-window.ts:62`), listens
  for `session-loaded / chapter-list / drills / tldr-audio / citation-tooltip / error`
  (`debrief-window.ts:67-161`), mounts chapter list, drills panel, TLDR player (with amber
  playhead sweep), timeline, citation tooltips, and a verdict headline built from REAL
  session structure (`debrief-window.ts:115-124 renderVerdictLine`). Components:
  `chapter-list.ts`, `drills-panel.ts`, `tldr-player.ts`, `timeline.ts`, `citation-tooltip.ts`,
  `error-banner.ts`, `ear-test-toggle.ts` (dev-only gate). → **REAL.**

**Verdict: NOT orphaned.** Debrief is the best-wired of the "secondary" engines. The
"overlooked" framing is about attention/polish, not about it being dark — the wires are live.

---

## 4. Does the live session actually FEED debrief? — YES, the event kinds are emitted

The debrief's input is `events.jsonl` + `evidence_registry.json`, both written by the live
recorder. Verified the consumed event kinds are actually produced live:

- **`ai_text`** (the live co-host's spoken, already-cited replies — the primary critique
  source, consumed at `main.py:157-165`): emitted by `dj_cohost.py:3834, 3889, 3992` via
  `recorder.log_event("ai_text", ...)`. → **REAL.**
- **`event`** kinds (TRACK_CHANGE/PHASE/etc. — chapter breaks): EventDetector emits → fanned
  to the recorder; `__main__.py:1284` confirms `"event"` is recorded (skipped only from the
  *trace* mirror, not from events.jsonl). → **REAL.**
- **`transition_judged`** (Judge verdicts → drill critique lines, consumed `main.py:174,217`):
  `transition_judge.py:32 TRANSITION_JUDGED_KIND`; written live via
  `state/transition_judge_runtime.py:77 recorder.log_event(TRANSITION_JUDGED_KIND, ...)` and
  registered as evidence at `runtime/coach.py:423-431`. → **REAL.**
- **`learn_action_observed` / `learn_tutor_speak`** (Learn-mode critique, consumed
  `main.py:166-173`): emitted by `learn/runtime.py:2824` and `learn/runtime.py:2399`. → **REAL.**
- **`evidence_registry.json`** (the snapshot drills cite against): persisted on recorder close
  at `audio/recorder.py:560-561`. → **REAL** (optional — legacy sessions without it get an
  empty snapshot, `session_loader.py:152-156`, which means drills generation will fail the
  citation-resolve and ERROR. See gap §6.2).

`--debrief` correctly short-circuits all audio/livekit/mido init before `main()`
(`tests/main/test_debrief_short_circuits_audio_init.py:4-6`, dispatch at `__main__.py:7867-7870`),
so it runs headless without BlackHole — **good news for the QA harness.**

---

## 5. The model route + cost truth

- `debrief` resolves to `("gemini-3.5-flash", "FLEX")` (`_router_config.py:66`) — the cost
  lane, no hardcoded literal (resolved at `tldr.py:54` and `drills.py:42`).
- TTS is **local Chatterbox** (`DEBRIEF_TTS_PROVIDER = "chatterbox-local"`, `tldr.py:55`) — NOT
  Gemini, keyless, but needs the Chatterbox model present or `synthesize_chatterbox_mp3` raises
  `ChatterboxUnavailable` → `DebriefGenerationError` (`tldr.py:259-267`). Note CLAUDE.md/memory
  say the live voice path moved to **chatterbox-turbo via mlx-audio** (ear-locked 2026-06-04);
  debrief's `build_default_line_adapter` (`tldr.py:33`) is the integration seam to confirm it
  uses the same voice as Sven — worth a 1-line check during wiring.
- Every Gemini + TTS call is mirrored to global AI observability (`tldr.py:111-139`,
  `drills.py:196-222`) — so the QA harness can read debrief generations from the obs log.

---

## 6. GAPS — what blocks "shine" and what blocks the QA loop

### 6.1 Generation is hard-gated on a live Gemini key + network (THE biggest gap)
First-time debrief makes **blocking** `generate_content` for drills (`drills.py:247`) and TLDR
(`tldr.py:158`). No key / no network → `tldr_generation_failed` / `drills_generation_failed`
→ `ipc.debrief.error` (`main.py:378-391`) → the window shows an error banner
(`debrief-window.ts:149-161`). There is NO offline/deterministic debrief fallback (e.g.
chapters-only, or a template TLDR from the cited critique). The cache-hit path is fully
offline (`main.py:316-343`) but only AFTER a successful first generation.
→ **Impact on QA loop:** the harness MUST have a working `GEMINI_API_KEY` to exercise the
full debrief, OR pre-seed `session_debrief.json`+`.mp3` to hit the cache path.

### 6.2 Empty evidence snapshot → drills always fail (silent-ish)
If `evidence_registry.json` is missing/empty (legacy sessions, or a recorded set where the
registry didn't persist), `_citation_resolves` returns False for every drill
(`drills.py:138-141`), all 3 are invalid every retry, → `DrillsGenerationError`
(`drills.py:340`). The whole debrief then errors out even though chapters + a TLDR could
still be useful. The drills are an all-or-nothing dependency on a populated snapshot.
→ **Highest-leverage fix:** decouple — emit chapters + TLDR even when drills can't resolve
(degrade gracefully instead of erroring the whole window).

### 6.3 No auto-launch on set end — manual/batch only
Nothing in `session_loop.py` or the Rust shell auto-spawns a debrief when a live set ends.
`session_loop.py` only treats `debrief` as a *mode picker* value (`session_loop.py:410`), not
an end-of-set trigger. The DJ must go to Settings/Recordings (or the dock) and click.
→ **Impact on QA loop:** the harness must explicitly call `--debrief <dir>` after feeding
the 3-hour set; it won't happen by itself. (For UX shine: an end-of-set "your debrief is
ready" CTA would close the loop.)

### 6.4 The session→lesson loop is the missing third of the triad
Profile write-back is done (`profile_writeback.py`). But there is **no debrief→lesson
hand-off**: drills are SBI/STAR-AR review prose, not wired to the Learn skill-tree /
`curriculum.py` to *schedule* a practice lesson. Kaan's "session→lesson→profile loop" is
2/3 closed (session→profile yes; session→lesson NO). The drill `action_recommended` is the
natural seam to mint a Learn lesson, but no code consumes it that way.
→ This matches MEMORY's "debrief→lesson" gold-vein note.

### 6.5 UX legibility (Kaan's #1 weak-layer concern) — partially mitigated
The window has a real verdict headline + chapters before the slow TLDR finishes
(`debrief-window.ts:115-124`), and the dock has a readiness/"fastest payback" panel
(`DebriefDock.ts:450-465`). But TTFB is poor on first run: drills (~5s) + TLDR (~30s) per
the header doc (`ws_server.py:6-9`) of dead-ish air after chapters land. The error path
copy is generic reason-code mapping. No "generating… (30s)" progress affordance for the
slow TLDR leg beyond the placeholder. For a 3-hour set the chapter list could be huge with
no virtualization mentioned.

### 6.6 Two competing entry surfaces (mild)
Both the Settings recording-row AND the shell DebriefDock list sessions and open debriefs.
They share `ipc.recordings.list` + `open_debrief_window` so neither is broken, but the
product story is split (which is the canonical "review" home?). Not a blocker; a polish call.

---

## 7. CONCRETE: what to build / wire, and where

Ordered by leverage. All paths absolute-able under repo root.

1. **Graceful degradation when drills/TLDR fail** (fixes 6.1 + 6.2; biggest QA + UX win).
   In `src/vibemix/debrief/main.py:345-450`, make drills and TLDR failures **non-fatal**:
   emit chapters always; on `DrillsGenerationError` emit chapters + a "drills unavailable"
   marker frame instead of `_emit_error_and_exit`; on `DebriefGenerationError` emit a
   text-only cited recap built from `cited_critique` (already computed at `main.py:356`)
   without TTS. This turns "no key / empty snapshot" from a blank error window into a useful
   offline debrief — and lets the autonomous QA loop run without a Gemini key.

2. **Pre-seeded cache fixture for the QA harness** (unblocks QA tonight, no product change).
   The cache-hit path (`main.py:316-343`) is fully offline + deterministic. The harness can
   write a `session_debrief.json` + `debrief_tldr.mp3` (matching SHA per `persistence.py:80`)
   into the recorded session dir, then `--debrief <dir>` replays it with zero Gemini calls
   and the QA judge scores the WS frames. This is the fastest path to exercising the debrief
   UI/telemetry without a key. (Alternatively run the harness WITH a real key once to
   populate the cache, then assert determinism on replay.)

3. **Decouple drills from the empty-snapshot all-or-nothing** (fixes 6.2 root cause).
   `src/vibemix/debrief/drills.py:300-310`: when the snapshot is empty, short-circuit to a
   typed "no_evidence" outcome the orchestrator can render as "not enough graded moments to
   drill" rather than burning 3 Gemini retries that are guaranteed to fail.

4. **Close session→lesson** (fixes 6.4; the named missing loop third).
   New seam: consume each `Drill.action_recommended` (`drills.py:57`) → mint a Learn
   practice item via `src/vibemix/learn/curriculum.py` / skill-tree. Mirror the existing
   `profile_writeback.py` pattern (consent-gated, best-effort, structured-not-prose). Wire it
   in `main.py` next to `_write_back_profile_best_effort` (`main.py:453`).

5. **Auto-launch CTA on set end** (fixes 6.3; UX shine).
   In the Rust shell or `session_loop.py` end-of-session path, when the just-ended session
   passes the `>=300s & >=5 events` gate (same as `recording-row.ts:475-478`), emit an
   "open your debrief" CTA → `open_debrief_window`. Don't auto-open the window (intrusive);
   surface a one-click prompt.

6. **First-run progress affordance for the 30s TLDR leg** (fixes 6.5).
   `tauri/ui/src/debrief/debrief-window.ts:132` (tldr-audio handler) — show an explicit
   "voiced recap rendering (~30s)" state between chapter-list arrival and tldr-audio, instead
   of relying on the verdict headline alone to fill the gap.

7. **Confirm the voice matches Sven's** (1-line check; consistency).
   `src/vibemix/debrief/tldr.py:33 build_default_line_adapter` — verify it resolves to the
   same chatterbox-turbo/mlx path now locked for the live co-host (MEMORY 2026-06-04), so the
   debrief narrator and Sven sound like the same friend.

---

## 8. QA-harness-specific notes (for the AI/engines lane)

- **Headless-safe:** `--debrief` short-circuits all audio I/O (`__main__.py:7867`,
  proven `tests/main/test_debrief_short_circuits_audio_init.py`). It does NOT need BlackHole.
- **Observable:** every generation is logged to global AI obs (`tldr.py:111`, `drills.py:196`)
  — the judge can read debrief outputs there, plus the WS frames on `8766`.
- **Citation-grounded by construction:** the stripper (`stripper.py`) + per-field citation
  check (`drills.py:301-309`) + ±2.0s snapshot resolution (`drills.py:120`) mean a passing
  debrief is *guaranteed* every sentence cites real evidence — the harness can assert
  "0 uncited sentences" as a hard anti-slop gate, mirroring `tests/debrief/test_no_uncited_critique_in_debrief.py`.
- **Determinism handle:** SHA-256 cache (`persistence.py:80`) gives the harness a stable
  replay; same input session → byte-identical MP3 + JSON on the cache path.
