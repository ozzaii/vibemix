---
phase: 62-floating-pill-ui
plan: 04
subsystem: ui
tags: [tauri, vanilla-ts, websocket, floating-pill, citation-strip, waveform, vitest, super-whisper]

# Dependency graph
requires:
  - phase: 62-02
    provides: primary_surface tri-state (pill default) + surface-selection so the pill window is the one that boots
  - phase: 13 (mascot)
    provides: transparent-overlay invariant (mascot.html), direct-WS connectMascotBus, pure state-machine purity discipline, drag handler
  - phase: 43 (meter VIS-03)
    provides: meter.ts data-lit update path + amber warm-zone gradient tokens (reused by the waveform)
  - phase: 44 (citation-strip LAUNCH-02)
    provides: renderCitationStrip (reused verbatim in the expand panel)
provides:
  - "pill.html: transparent-overlay webview entry for the floating pill (mascot.html invariant cloned, never referenced)"
  - "src/pill/state-machine.ts: pure 4-state machine (idle/listening/speaking/expand) with data-driven collapseAt"
  - "src/pill/index.ts: boot — connectMascotBus + reader/writer frame fan-out (defensive flat-or-nested voice) + top-strip drag + rAF loop + waveform + citation wiring"
  - "src/pill/waveform.ts: real voice.rms TTS waveform reusing meter.ts tokens + data-lit update path"
  - "src/pill/ws-client.ts: connectMascotBus copied verbatim (pill decoupled from src/mascot/**)"
affects: [62-05 (deck-context chips + rgba glass surface populate the mounts left here), pill_window.rs, primary_surface]

# Tech tracking
tech-stack:
  added: []  # zero new runtime deps — reuses shipped meter.ts / citation-strip.ts / ws-client.ts + vanilla TS
  patterns:
    - "Pure frame reducer (toPillFrame/reduceFrame) exported for DOM-free unit tests"
    - "Data-driven expand→collapse (collapseAt field, rAF tickCollapse) — no setTimeout"
    - "Per-file @vitest-environment jsdom docblock (DOM tests routed without a vitest.config change)"
    - "ws-client copy-not-import to keep the pill off the mascot-audit fence path"

key-files:
  created:
    - tauri/ui/pill.html
    - tauri/ui/src/pill/state-machine.ts
    - tauri/ui/src/pill/index.ts
    - tauri/ui/src/pill/waveform.ts
    - tauri/ui/src/pill/ws-client.ts
    - tauri/ui/src/pill/state-machine.test.ts
    - tauri/ui/src/pill/index.test.ts
    - tauri/ui/src/pill/waveform.test.ts
  modified: []

key-decisions:
  - "ws-client.ts COPIED into src/pill/ (not imported from src/mascot/) — keeps the pill fully decoupled so a pill PR never path-triggers the mascot-audit CI fence (only the log TAG differs from the original)"
  - "Frame reading split into a pure exported toPillFrame/reduceFrame so the frame→state map is unit-tested with zero DOM/bus — the impure boot() only runs inside a real document"
  - "Per-file @vitest-environment jsdom docblock on the two DOM specs instead of editing vitest.config.ts — respects the strict 7-file plan scope while routing DOM tests correctly"
  - "Silent→baseline floor (WAVE_BASELINE_RMS=0.06) applied in index.ts (not the waveform component) so the waveform stays a pure rms→bars transform; while speaking the bars never flatline to zero between phrases"
  - "Expand label keeps the underlying base-state caption (re-derived in render) so 'expand' never paints a literal 'EXPAND' string"

patterns-established:
  - "Reader/writer frame fan-out: snapshot/flat frames are READERS (update status+voiceRms, no transition), cohost-reaction is the only WRITER (drives expand)"
  - "Defensive flat-or-nested voice read (LIVE-05a): voice flat on the live frame, nested meters.voice.rms on the bridged snapshot"
  - "Reuse-don't-invent UI: renderCitationStrip verbatim, meter.ts tokens + data-lit path for the waveform, mascot.html transparent invariant cloned for pill.html"

requirements-completed: [PILL-03]

# Metrics
duration: 6min
completed: 2026-05-21
---

# Phase 62 Plan 04: Floating Pill UI Core Summary

**The pill consumes the existing ws:8765 bus (direct-WS, no new port) and renders idle/listening/speaking/expand from real wire data — a pure 4-state machine, a real voice.rms TTS waveform (meter.ts tokens), and a verbatim citation strip — all decoupled from src/mascot/ so the mascot-audit fence stays green.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-21T21:49:33Z
- **Completed:** 2026-05-21T21:54:56Z
- **Tasks:** 3 automated (Task 4 = human-verify checkpoint, auto-approved overnight → KAAN-ACTION)
- **Files created:** 8 (1 html + 4 ts + 3 test)

## Accomplishments

- **Pure 4-state pill machine** — `baseState`/`applyFrame`/`tickCollapse` map `cohost_status` → idle/listening/speaking and `cohost-reaction` → expand with a data-driven `collapseAt` (EXPAND_MS ~6s). No wall-clock, no timers (grep-verified) — 18 deterministic now-param vitest cases.
- **Pill boot consuming the EXISTING bus** — a pill-local `connectMascotBus` (copied verbatim) subscribes to ws:8765; the reader/writer `toPillFrame`/`reduceFrame` derive the four states with a defensive flat-or-nested voice read (LIVE-05a); the drag handler is scoped to the top 28px strip (`startDragging`, left-only, `[data-no-drag]` exempt).
- **Real voice.rms TTS waveform** — a horizontal 14-bar strip reusing meter.ts's amber warm-zone gradient tokens + the byte-identical `data-lit-count` single-attribute update path (no canvas/SVG), driven by the real voice.rms signal and floored to a low baseline between phrases.
- **Verbatim citation strip in expand** — `renderCitationStrip` reused verbatim (null-on-empty), reaction text rendered as a text node (never innerHTML, T-62-11), chips tagged `data-no-drag`.
- **Transparent-overlay invariant cloned** — `pill.html` mirrors the mascot.html `html,body transparent !important` + `body::before display:none` invariant + boots `/src/pill/index.ts`, without ever referencing `mascot.html`.
- **Fence stays green** — all pill code is path-scoped under `tauri/ui/src/pill/`; `grep -c "../mascot/" index.ts == 0`; full UI suite 761/761 green (no regressions); `tsc --noEmit` clean.

## Task Commits

Each task was committed atomically (per-file staged):

1. **Task 1: Pure pill state machine + transparent pill.html scaffold** — `8b25859` (feat)
2. **Task 2: Pill boot — copied ws-client + connectMascotBus + reader/writer + drag** — `993cf17` (feat)
3. **Task 3: Real voice.rms waveform (meter.ts reuse) + citation strip in expand** — `650bbca` (feat)
4. **Task 4: Pill UI checkpoint** — no code change; human-verify, auto-approved overnight → KAAN-ACTION

**Plan metadata:** (this commit) `docs(62-04): complete floating-pill-ui core plan`

## Files Created/Modified

- `tauri/ui/pill.html` — transparent-overlay webview entry; --glass-3 lozenge, top 28px drag strip w/ silk-22 grab-bar, collapsed row (state dot + label + waveform mount), expand panel (reaction + citation + deferred deck mount); boots /src/pill/index.ts
- `tauri/ui/src/pill/state-machine.ts` — pure 4-state machine; baseState/applyFrame/tickCollapse; EXPAND_MS; READER/WRITER discipline
- `tauri/ui/src/pill/index.ts` — boot + bus + drag + rAF loop; pure toPillFrame/reduceFrame (DOM-free, exported for tests); waveform + citation wiring; consume-only (no message-send path)
- `tauri/ui/src/pill/waveform.ts` — horizontal 14-bar waveform; meter.ts amber gradient tokens + data-lit update path; _CSS_FOR_TEST
- `tauri/ui/src/pill/ws-client.ts` — connectMascotBus copied verbatim (1→2→4→8s backoff, silent-drop of malformed frames); decouples the pill from src/mascot/**
- `tauri/ui/src/pill/state-machine.test.ts` — 18 cases (mapping, expand+collapseAt, re-extend, READER-holds-expand, purity grep)
- `tauri/ui/src/pill/index.test.ts` — 13 cases (frame→state map, flat vs nested voice, cohost-reaction → verbatim expand) [jsdom docblock]
- `tauri/ui/src/pill/waveform.test.ts` — 9 cases (14 bars, rms→lit-count, idempotent, silent→baseline, clamp, no-hex + amber 20/80) [jsdom docblock]

## Deviations from Plan

**None for Rules 1-3** — the plan executed as written. Two structural choices worth noting (both within plan intent, not deviations):

- **Per-file `@vitest-environment jsdom` docblock** instead of adding a `src/pill/*.test.ts` jsdom glob to `vitest.config.ts`. The two DOM specs (index/waveform) import components whose `registerStyle()` touches `document.head` at module load, so they require jsdom; the default env for `src/**/*.test.ts` is node. The docblock routes them correctly while honouring the strict 7-file plan scope (vitest.config.ts is not in `files_modified`). The plan's interfaces note already said "NO config change needed" for collection — this keeps that true for env routing too.
- **`waveform.ts` accepts `peak` for meter.ts API parity but does not render a separate peak needle** — the compact 14-bar pill strip carries the level in the lit-bar count; the peak param is plumbed through `setWaveform` so the session-meter signature is preserved.

## Threat Surface

No new threat flags. The pill is a pure CONSUMER of the existing localhost bus:
- **T-62-11 (XSS)** mitigated — reaction text set via `textContent` (never `innerHTML`); chips via the contract-tested `renderCitationStrip`.
- **T-62-12 (info disclosure)** mitigated — chips rendered exactly as the backend emits (`citation_strip ?? []`); the pill fabricates/adds nothing, reaction text verbatim (no pill-side framing).
- **T-62-13 (DoS)** mitigated — the copied `connectMascotBus` silently drops non-JSON/malformed frames + self-heals (1→2→4→8s backoff).
- **T-62-14 (spoofing / scope creep)** mitigated — the pill registers NO message-send path (consume-only); no new socket/port (`grep` proves the only URL is the existing 8765 client).
- **T-62-SC** — zero new runtime npm deps (reuses shipped meter.ts / citation-strip.ts / ws-client.ts); slopcheck N/A.

## Known Stubs

One **intentional, deferred** mount — NOT a PILL-03 blocker (the core states + waveform + citation strip are fully wired):

- `pill.html` `#pill-decks` (`.pill__decks`, `display:none`) + the `index.ts` insert-before anchor — the **deck-context chips mount left for Plan 62-05** to populate (62-05 owns deck chips + the explicit rgba glass surface). Documented in the plan's `<success_criteria>` ("this plan's expand panel leaves a deck-chips mount for 62-05 to populate"). The expand panel renders the reaction text + citation strip today; the deck-chips row stays hidden until 62-05 wires the per-deck `deck_state` source (the wire-source gap flagged in 62-PATTERNS "No Analog Found").

## KAAN-ACTION (live-confirm)

These are FELT-rendering items that can only be confirmed on the running app (per `gsd-autonomous fully` they are RECORDED, not blockers — engineering shipped at the green-test bar: 40 pill tests + 761 full-suite green, tsc clean). Auto-approved overnight; confirm at the deck when convenient:

1. **IDLE:** with no session, the pill renders as a compact dark-glass lozenge — dim dot + `IDLE` label, no waveform, no filler chatter (silence is the honest empty state).
2. **LISTENING/SPEAKING:** start a session — the state dot pulses (slow 1.4s listening / fast 0.9s speaking) and the waveform animates on REAL AI speech (tracks voice.rms, not a loop).
3. **EXPAND:** on a co-host reaction the pill grows DOWN to show the reaction text (verbatim, no "AI:" prefix) + citation chips, then collapses back after ~6s.
4. **Transparency on the built `.dmg`:** the --glass-3 rgba surface composites over the desktop with no vignette / no white-box (tauri#13415 is only confirmable on the built dmg).
5. **Drag + non-focus-steal:** dragging from the top strip moves the pill; clicking a chip does NOT start a drag; (focus-non-steal is owned by the pill_window.rs native block from 62-01/02, confirm keystrokes still land in the DJ app).

## Self-Check: PASSED

(see appended verification below)
