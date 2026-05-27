# Project Research Summary

**Project:** vibemix — AI DJ Co-Host (v5.0 "The Useful Cut")
**Domain:** Local AI DJ co-host — adding full-deck awareness, harmonic/transition feedback, actionable-coach persona, floating-pill live UI
**Researched:** 2026-05-21
**Confidence:** HIGH

> Detailed research: [STACK.md](./STACK.md) · [FEATURES.md](./FEATURES.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [PITFALLS.md](./PITFALLS.md)

## Executive Summary

v5.0 adds three capabilities to a mature, grounded local AI DJ co-host: (A) full deck-state awareness that powers (B) transition + harmonic key-clash feedback, (C) an actionable-not-hype coaching persona, and a floating Super-Whisper-style pill that becomes the primary live surface (the 3D mascot demotes to opt-in/secondary, kept not retired). All four research streams **converged independently** on the same architecture: this is an *integration* milestone on an existing single-writer/citation-linter system, not a greenfield build. Every new capability is anchored to a real file on the in-flight `live-tuning-or-brain` branch, and every recommendation passes the project's central test — "what hallucination class does it close?"

The recommended approach for deck data is a **layered grounding ladder, not a single source**: pyrekordbox **XML export** (unencrypted, carries `Tonality`/key/BPM/cues) as the primary metadata oracle, **Gemini-vision deck read** of the already-captured screenshot as the universal cross-app fallback, and the existing numpy/scipy audio + nowplaying-cli/MIDI audible-deck heuristic as the acoustic cross-check ("trust the audio" wins ties). Two stale-stack corrections are load-bearing: **Essentia and librosa are NOT installed** (the audio path is pure numpy/scipy FFT — any "reuse" is actually a new heavy dependency), and **pyrekordbox is installed XML-only** with the SQLCipher path deliberately banned by a grep-gate. Musical key prefers pre-computed tags; the fallback is an in-house ~80-line numpy Krumhansl/Temperley estimator (no new dep). Camelot logic is a deterministic 24-entry Python table — the LLM *narrates* a clash the code already confirmed, it never computes intervals.

The dominant risk is **hallucination tripping Kaan's hard release gate**: a false key clash, or naming a deck/key that isn't audible, is the most credibility-destroying failure possible for a tool claiming harmonic expertise. The mitigation chain is non-negotiable and must land in order: a new citable evidence source for keys → deterministic Camelot verdict → a percussive/melodic suppression gate → a conservative confidence gate (library key tags are only ~57-70% accurate, with silent errors) → a Kaan-ear veto. The persona refactor *extends* the in-flight branch (it does NOT add a new mode) and must regression-fence the Phase-54-validated hype goldens. The pill's load-bearing spike is the drag-on-unfocused-window bug — "draggable" and "non-focus-stealing" are in direct tension and that tension is exactly where the pill will look done but feel broken.

## Key Findings

### Recommended Stack

No new PyPI package is required for deck-state + key. The recommended path is config + code on already-pinned deps: activate pyrekordbox's XML import (already shipped), add an in-house numpy key estimator + a Camelot lookup table (both zero-dep new source files), and extend the existing Gemini-vision screenshot prompt to read both deck panels. Two new Rust crates serve the pill. **Critical correction:** the briefing's "reuse Essentia/librosa" assumption is false — they are not in the stack; the entire MIR path is hand-rolled numpy/scipy, so any MIR library is a *new* heavy install, not a reuse.

**Core technologies:**
- **pyrekordbox XML export** — deck metadata oracle (key/BPM/cues) — unencrypted, stdlib-parseable, no live-DB lock or post-6.6.5 encryption wall. (Live SQLCipher `master.db` = best-effort-only, read-only-on-temp, NEVER write.)
- **Gemini-vision deck read** — universal cross-app deck-state fallback — reuses the screenshot already sent every turn; works for Serato/djay/Traktor/Engine without per-app parsers; zero new dependency.
- **In-house numpy KS/Temperley key estimator + Camelot table** — key fallback + clash math — same DSP family as the shipped BPM autocorrelation; deterministic verdict the LLM narrates. (Essentia = RED install-impact, librosa = YELLOW — both rejected; key detection is fallback-only and doesn't justify a heavy binary.)
- **tauri-nspanel v2.1** (macOS, git branch) — non-activating NSPanel so the pill doesn't steal focus from the DJ app.
- **window-vibrancy 0.7.x** (crates.io) — cross-platform frosted glass (HudWindow on mac; acrylic/mica on Windows).

### Expected Features

Every feature maps to a hallucination class it closes. The harmonic feature is the most defensible anti-slop claim in the whole product because a key clash is *math-checkable* — the AI can be proven right or wrong.

**Must have (table stakes):**
- Deterministic Camelot clash detection (lookup table, cited verdict) — a harmonic tool that gets key math wrong is instantly discredited.
- Percussive/atonal suppression gate — flagging a clash on two drum loops is the canonical slop; this is a *hard precondition* before any clash note fires.
- Phrase-alignment note ("you came in off-phrase") — #1 amateur error, every coach leads with it.
- Bass-clash note ("two basslines running — swap the lows") — most audible mistake.
- Actionable coach register (observed→prescriptive, DJ verbs: kill/swap/cut/filter/wait/ride/tighten) — the whole v5.0 premise.
- Draggable floating pill with idle/active/speaking states, collapse-by-default/expand-on-event, TTS-synced waveform.

**Should have (competitive):**
- Full-deck awareness powering *prescriptive* transition notes ("real DJ friend who sees both decks") — the flagship.
- Provably-correct harmonic verdict — marketing-grade: "the AI can be *proven* right about key."
- Deliberately *withholding* wrong advice (no key nag on percussive content) — sophistication a generic LLM tool never shows.
- Key chips + deck-context micro-display in the expanded pill.
- Blend-length judgment tied to content; prescriptive timing ("breakdown now — bring B in").

**Defer (v2+):**
- Per-deck DSP (true dual-stream audio analysis) — only if metadata grounding proves insufficient; heavy.
- Per-app library parsers (Serato/Traktor/Engine) — vision-read covers them universally for v5.0.
- ProDJ Link / prolink-connect — hardware-gated, explicitly deferred.

**Anti-features (LOCK these out):**
- No next-track recommendation (kills DJ agency; out of scope).
- No 1-10 transition scoring (turns a friend into a nagging judge; most "errors" are creative choices).
- No headphone-cue analysis (Gemini conflates cue with master → wrong reactions).
- No live audio key-*detection* as primary (unreliable, invites false-confident clash claims).
- No full chat history in the pill; no notch-locked Dynamic Island; no 3D character in the pill.

### Architecture Approach

Pure integration on the existing system, respecting four cardinal invariants: **single-writer** (`state_refresh_loop._tick_once` is the only `MusicState` writer), **citation grounding** (new evidence must be written to the registry before the LLM can cite it; `CitationLinter` does a binary response-level strip), **"trust the audio"** (no fabricated phase/key claims), and **one socket** (everything on `ws://127.0.0.1:8765`). Deck-state is a new `DeckState` dataclass *embedded* in `MusicState` (additive, golden-equivalence preserved); a read-only poller writes its own holder and `_tick_once` copies it under the lock — the *third* such external source alongside controller/track polling. The pill is a near-clone of `mascot_window.rs` consuming the same `ipc.session.*` frames on the same socket.

**Major components:**
1. **`DeckState`/`DeckTrack` model + deck poller** (`state/deck_state.py`, `state/deck_poller.py` — NEW) — session-wide per-deck track facts; read-only producer feeding `_tick_once` only.
2. **`harmonics.py`** (NEW) — pure Camelot/key/clash functions, no I/O, fully unit-testable.
3. **`KEY_CLASH` + `TRANSITION_OPPORTUNITY` events** (`event.py`, `event_detector.py` — MODIFIED) — diff-based, read-only, onset-gated with long cooldowns; reuse `mix:`/`track:` evidence sources (no new `deck:` source).
4. **`AICoach` + persona cells** (`state/coach.py`, `prompts/matrix.py` — MODIFIED) — extend COACH_* cells + add per-event task arms; do NOT add a new mode.
5. **`pill_window.rs` + pill UI + `primary_surface` tri-state** (NEW) — transparent/on-top/draggable window; `"pill"|"mascot"|"none"` config; mascot kept as secondary.

> **One architectural divergence to flag:** ARCHITECTURE.md recommends reusing the existing `mix:` evidence source for deck keys (existence-only, no grammar change), while PITFALLS.md (Pitfall 1) argues for a dedicated **`key:` source with confidence** (`key:A=9B@conf0.8`) so the linter can validate per-deck per-moment key assertions. **The roadmapper must resolve this in the deck-grounding phase.** PITFALLS' position is stronger for the headline anti-slop guarantee (per-moment, per-deck, confidence-carrying) — recommend the `key:` source unless the deck-grounding spike proves `mix:` reuse is sufficient.

### Critical Pitfalls

1. **Uncitable harmonic feedback (no evidence source)** — there is no `key`/`harmonic` member in `EVIDENCE_SOURCES` today. Add the citable key source + linter rule **FIRST**, before any harmonic prompt text. The clash must cite *both* decks' keys; the linter strips a fabricated clash.
2. **False clash from wrong key (the headline hallucination)** — library key tags are ~57-70% accurate with *silent* errors, worst on percussion-heavy techno/psytrance (vibemix's actual genres). Conservative gate: clash only when both keys present, both from a library match, and Camelot distance is in the unambiguous clash band. **One-step-off-wheel = SUPPRESS** (indistinguishable from a detection error; pros mix fifths/relatives freely). Carry derived confidence; Kaan-ear veto.
3. **Context-blind feedback** — clash called during a breakdown (no overlapping tonal content), or transition critique landing 12s late. Gate on `audible_deck == "mix"` + both decks above an energy floor; transition feedback is **retrospective/past-tense only**, never mid-blend imperatives.
4. **Audible-deck ambiguity poisons the feature** — the DDJ-FLX4 doesn't write play-state when djay Pro controls it; `derive_audible_deck()` returns `none`/`mix` often. Trust fader+xfader (the v4 fix), suppress cross-deck claims when the 2nd deck is unresolved — degrade to single-deck feedback, never guess.
5. **Reading live `master.db`** — file locks during live sessions, post-6.6.5 encryption wall, and **any write corrupts the user's collection**. Read the unencrypted XML export; SQLCipher best-effort-only on a temp copy; NEVER write. Repo test asserts no DJ-DB write-mode open.
6. **No graceful degradation when no source exists** — Serato/Traktor/encrypted-RB users get a broken or *fabricating* feature. Tiered capability (T0 audio+MIDI only / T1 +library); harmonic prompt fragments are conditionally injected — absent → not in the prompt → model can't be tempted.
7. **Persona over-correction (cold/nag)** — "actionable" overshoots into a fault-finding QC bot. Keep the in-flight BALANCED rule (~half turns specific positive callouts, never reuse a praise line). Actionability is in *specificity + peer register*, not frequency of critique.
8. **Shared-prompt refactor breaks hype mode** — `matrix.py`/`coach.py` are shared. Regression-fence the Phase-54-validated hype goldens; any hype-golden change is a deliberate, reviewed decision.
9. **Pill steals focus / blocks DJ input** — interactive draggable pill re-opens every focus/drag bug the click-through overlay sidestepped (tauri#10767/#14102/#6568). `focused(false)` + NSPanel + verify keystrokes still reach the DJ app after clicking the pill.
10-11. **Multi-monitor positioning + mac/win transparency** — clamp-to-visible on display-change; explicit `--glass-*` background (not pure OS-vibrancy → opaque white box on Windows); `--blur-glass-light` (16px) for integrated-GPU perf; keep `mascot-audit` CI green.

## Implications for Roadmap

The dependency chain is firm: **harmonic + transition feedback both gate on deck-state existing first; the pill parallelizes.** Within the deck/harmonic spine, the citable key source must precede any harmonic prompt. PITFALLS, ARCHITECTURE, and FEATURES independently produced the same four-phase shape. (v4.0 ended at Phase 58; v5.0 begins at 59. Names are recommendations, not locked titles.)

### Phase 59: Deck-Awareness Data Source + Grounding
**Rationale:** The gate for everything. No flagship feature can ground until "all loaded tracks" has a resolved source + the keys are *citable*. Three research streams flag this as the critical-path item.
**Delivers:** `harmonics.py` (pure Camelot/key/clash); `DeckState`/`DeckTrack` embedded in `MusicState` (additive); deck poller (XML-primary + Gemini-vision fallback + audio cross-check, single-writer compliant); the citable key evidence source + linter rule; XML-primary read-only decision with a repo test asserting no DJ-DB write; tiered capability model (T0 audio-only / T1 +library).
**Addresses:** Full-deck awareness (table stakes); deck data-source resolution (P1).
**Avoids:** Pitfalls 1 (uncitable harmonic), 4 (audible-deck ambiguity), 5 (master.db landmine), 6 (graceful degradation).
**Uses:** pyrekordbox XML, Gemini-vision deck read, in-house numpy key estimator.

### Phase 60: Harmonic-Feedback Confidence Gate
**Rationale:** The hard hallucination gate. Owns the conservatism that keeps a wrong-key tag from announcing a false clash. Must be its own phase, not folded into deck-awareness — it gets a Kaan-ear veto.
**Delivers:** `KEY_CLASH` + `TRANSITION_OPPORTUNITY` detectors (onset-gated, long cooldowns); the percussive/melodic suppression gate (runs BEFORE any clash note); one-step-off-wheel suppression; derived per-key confidence; breakdown/single-deck suppression; deterministic Camelot verdict the LLM only narrates.
**Addresses:** Deterministic Camelot clash, percussive-suppression gate, provably-correct verdict.
**Avoids:** Pitfalls 2 (false clash — headline), 3 (context-blind).
**Implements:** Event detectors + `harmonics.is_clash`.

### Phase 61: Actionable-Not-Hype Coach Persona
**Rationale:** Consumes the deck-state from 59-60. Extends the in-flight `live-tuning-or-brain` work — sharpens the *coach* register and wires prescriptive deck instructions, without adding a new mode.
**Delivers:** COACH_* cell deck-feedback paragraphs (transition mechanics + harmonic vocabulary); `task_for_event` arms for the two new events; observed→prescriptive (SBI/AID) phrasing on the existing citation contract; the hardened BALANCED rule; conditional prompt-fragment injection by tier; hype-golden regression fence + cross-mode verification gate.
**Addresses:** Actionable coach register (table stakes); deliberately-withholding-wrong-advice (differentiator).
**Avoids:** Pitfalls 3 (no present-tense imperatives), 6 (conditional injection), 7 (over-correction), 8 (hype regression).
**Implements:** `prompts/matrix.py` + `state/coach.py` (extend, don't duplicate).

### Phase 62: Floating Pill UI (parallel — soft-depends only on snapshot deck fields)
**Rationale:** Independent of deck-state; can run in parallel with 59-61. Only its final polish (deck chips) waits on Phase 59's snapshot fields. The drag-on-unfocused spike is load-bearing and should be de-risked first.
**Delivers:** `pill_window.rs` (clone of `mascot_window.rs`) + `PillWindowState`; pill.html + shared `src/ipc/session-frames.ts` parser (Vite 5th entry); `primary_surface` tri-state + `set_primary_surface` command + tray/Settings toggle; NSPanel non-activating focus behavior; window-vibrancy frosted glass with explicit `--glass-*` fallback; clamp-to-visible multi-monitor handling; capability allowlist `"pill"` (closes the v0.1.0-rc1 drag-capability debt); deck chips after 59.
**Addresses:** Draggable pill + idle/active/speaking states; TTS-synced waveform; deck-context chips.
**Avoids:** Pitfalls 9 (focus steal), 10 (multi-monitor), 11 (transparency mac/win + mascot regression).
**Uses:** tauri-nspanel v2.1, window-vibrancy 0.7.x.

### Phase Ordering Rationale
- **59 -> 60 -> 61 is a hard critical path:** feedback cannot cite deck-state that doesn't exist; conservatism cannot gate clashes that aren't detected; persona cannot narrate keys the registry never saw.
- **62 parallelizes** with the spine — the pill's core (reaction text + meters) needs nothing from deck-state; only its deck-chip polish waits on 59 step 4.
- **The citable key source lands in 59 before any harmonic prompt** — Pitfall 1's "uncitable-by-construction" trap is a HIGH-cost retrofit if discovered at the release gate.
- Grouping mirrors the four research files' independent convergence and the existing single-writer/citation/one-socket invariants.

### Research Flags

Phases likely needing deeper research / a spike during planning (`/gsd:plan-phase --research-phase N`):
- **Phase 59:** pyrekordbox **live-DB read safety** post-6.6.5 (encryption wall, `download-key` fragility on a distributed binary) — confirm XML-primary is sufficient and SQLCipher stays opportunistic. Also the `mix:`-reuse vs dedicated-`key:`-source decision (ARCHITECTURE <-> PITFALLS divergence).
- **Phase 59:** **Gemini-vision deck-badge reliability eval** — how reliably can Gemini read the loaded track + key/BPM badge off each deck panel across djay/Serato/Traktor UIs? This is the universal fallback; needs a real-screenshot accuracy pass.
- **Phase 62:** **Pill drag-on-unfocused-window spike** (tauri#11605/#10767/#14102) — the single most likely "looks done but feels broken" failure; resolve `startDragging` vs `data-tauri-drag-region` vs NSPanel `isMovableByWindowBackground` before building the UI. Plus the DMG-build transparency regression (tauri#13415).

Phases with standard patterns (lighter research):
- **Phase 60:** Camelot theory is HIGH-confidence and fully sourced; the math is a deterministic table. Effort is in the gate tuning + Kaan-ear veto, not research.
- **Phase 61:** extends well-mapped in-flight branch code on the existing citation contract; SBI/AID coaching structure is established.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH (MEDIUM on non-RB deck sources) | Tauri pill, key detection, Rekordbox path verified against `pyproject.toml`/`uv.lock` + official docs. Non-Rekordbox deck sources web-verified but no live-hardware confirmation. |
| Features | HIGH | Camelot theory + transition mechanics cross-verified across MixedInKey/DJ.Studio/Pioneer/NI. Pill UX MEDIUM (reference-app behavior inferred from product pages, not source). |
| Architecture | HIGH | Read directly against real files on branch `live-tuning-or-brain`; every recommendation anchored to a file/line. |
| Pitfalls | HIGH (MEDIUM on key-accuracy numbers) | Grounding/citation + deck-source + Tauri gotchas codebase- and GH-issue-verified. Key-detection accuracy from multiple agreeing secondary sources, no single authoritative benchmark. |

**Overall confidence:** HIGH

### Gaps to Address
- **Deck data-source live confirmation:** XML-primary + vision-fallback is the recommended ladder, but no live FLX4+djay drive has confirmed two-deck resolution rates. Resolve via a real-hardware live test in Phase 59 (KAAN-ACTION).
- **`mix:` reuse vs dedicated `key:` evidence source:** ARCHITECTURE recommends `mix:` reuse (no grammar change), PITFALLS recommends a confidence-carrying `key:` source. Decide in Phase 59 planning — lean `key:` for the strongest anti-slop guarantee unless the spike proves reuse sufficient.
- **Gemini-vision deck-badge accuracy:** the universal fallback's reliability across DJ-app UIs is unmeasured. Eval in Phase 59.
- **Pill drag/focus resolution:** which drag mechanism survives the non-activating-window constraint on both mac + win. Spike in Phase 62.
- **Key-detection accuracy band:** the ~57-70% library-tag accuracy drives the conservatism gate; validate the suppression thresholds against Kaan's real disagreed-pairs corpus in Phase 60.

## Sources

### Primary (HIGH confidence)
- Live codebase on branch `live-tuning-or-brain` — `state/{music_state,event,event_detector,refresh,coach,track_resolver,evidence_registry}.py`, `coach/citation_linter.py`, `prompts/matrix.py`, `agent/dj_cohost.py`, `runtime/ws_bus.py`, `audio/features.py`, `library/rekordbox.py`, `pyproject.toml`/`uv.lock`, `tauri/src-tauri/src/{mascot_window,config,overlay}.rs`, `tauri.conf.json5`.
- [pyrekordbox PyPI/docs](https://pyrekordbox.readthedocs.io/en/stable/quickstart.html) — v0.4.4, `Rekordbox6Database`, `download-key`, db6 SQLCipher 6.6.5 obfuscation.
- [tauri-nspanel](https://github.com/ahkohd/tauri-nspanel) (v2.1) · [window-vibrancy](https://github.com/tauri-apps/window-vibrancy) (0.7.x) · [Tauri window customization](https://v2.tauri.app/learn/window-customization/).
- [Tauri #11605](https://github.com/tauri-apps/tauri/issues/11605) (drag-region broken unfocused), [#10767](https://github.com/tauri-apps/tauri/issues/10767), [#14102](https://github.com/tauri-apps/tauri/issues/14102), [#6568](https://github.com/tauri-apps/tauri/issues/6568), [#13415](https://github.com/tauri-apps/tauri/issues/13415).
- [Mixed In Key — Harmonic Mixing Guide](https://mixedinkey.com/harmonic-mixing-guide/), [DJ.Studio Camelot Wheel](https://dj.studio/blog/camelot-wheel) + [Transitions Playbook](https://dj.studio/blog/the-dj-transitions-playbook), [Pioneer DJ harmonic mixing](https://blog.pioneerdj.com/djtips/how-do-djs-approach-harmonic-mixing/), [Native Instruments transitions](https://blog.native-instruments.com/dj-transitions/).
- PROJECT.md, REQUIREMENTS.md, CLAUDE.md anti-slop thesis; prior VERIFIED research `.planning/research/v2-buckets/{B-industry-integrations,C-ui-overlay}.md`, `v3-buckets/v3.x-pyrekordbox-depth.md`.

### Secondary (MEDIUM confidence)
- Key-detection accuracy: [Crossfader MIK 11](https://wearecrossfader.co.uk/blog/mixed-in-key-11/), [Dubspot MIK vs Beatport](https://blog.dubspot.com/dubspot-lab-report-mixed-in-key-vs-beatport), [Engine DJ key thread](https://community.enginedj.com/t/engine-dj-badly-analyses-track-key/52099), [VirtualDJ key issues](https://virtualdj.com/forums/228037/) — RB ~57% / Traktor ~54% / VirtualDJ ~65% / MIK ~70%.
- Pill UX: [Superwhisper](https://superwhisper.com/), [MacStories NotchNook/MediaMate](https://www.macstories.net/reviews/notchnook-and-mediamate-two-apps-to-add-a-dynamic-island-to-the-mac/), [Alcove](https://tryalcove.com/).
- Coaching structure: [HR Acuity constructive feedback](https://www.hracuity.com/blog/constructive-feedback-examples/), [ICCS AID/SBI](https://iccs.co/feedback-in-coaching-supervision/).

### Tertiary (LOW confidence)
- [Essentia KeyExtractor](https://essentia.upf.edu/reference/std_KeyExtractor.html) — accuracy context only; NOT adopted (RED install-impact).
- [prolink-connect](https://github.com/evanpurkhiser/prolink-connect) / [python-prodj-link](https://github.com/flesniak/python-prodj-link) — PRO DJ Link, hardware-gated, DEFERRED.
- Non-RB library parsers (traktor-nml-utils, python-serato-crates, Engine Library Format) — v.next, vision-read covers them for v5.0.

---
*Research completed: 2026-05-21*
*Ready for roadmap: yes*
