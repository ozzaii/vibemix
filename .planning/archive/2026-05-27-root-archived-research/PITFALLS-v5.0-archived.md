# Pitfalls Research

**Domain:** Adding full-deck awareness + harmonic/transition feedback + actionable-coach persona + floating-pill UI to a mature, grounded local AI DJ co-host (vibemix v5.0 "The Useful Cut")
**Researched:** 2026-05-21
**Confidence:** HIGH on grounding/citation pitfalls (codebase-verified: `EvidenceRegistry`, `derive_audible_deck`, `AICoach`) + deck-source landmines (prior v2/v3 research VERIFIED) + Tauri overlay gotchas (codebase + open GH issues). MEDIUM on key-detection accuracy numbers (multiple secondary sources agree, no single authoritative benchmark). HIGH on persona-regression (in-flight `live-tuning-or-brain` branch diff read directly).

> **Framing.** This milestone adds capabilities to a product whose ENTIRE thesis is "grounded Gemini, never AI slop" enforced by an EvidenceRegistry citation linter (`EVIDENCE_SOURCES = {ev, aud, midi, track, screen, mix, tend}`). The single biggest risk is that the new deck-awareness + harmonic feedback **hallucinates** — claims a clash that isn't there, or names a key/track that isn't audible — which directly trips Kaan's hard release gate. Every pitfall below is scored by **which hallucination class it opens** and **which evidence source would have to back the claim**. Note: there is **no `key` or `harmonic` source in `EVIDENCE_SOURCES` today** — that gap is itself Critical Pitfall 1.

---

## Critical Pitfalls

### Pitfall 1: Harmonic feedback with no evidence source to cite against (uncitable-by-construction)

**What goes wrong:**
The co-host says "those two tracks clash, B is in 7A against A's 9B" but `EVIDENCE_SOURCES` has no `key`/`harmonic` member. The citation linter (Phase 20 / `coach/citation_linter.py`) can only validate `[ev|aud|midi|track|screen|mix|tend]`. So either (a) the harmonic claim ships **uncited** and the anti-slop strip can't catch a false clash, or (b) someone bolts the key into a `track:` citation body, which the linter resolves only against `register_library()` track IDs — not against a *per-deck, per-moment* key assertion. Either way the headline feature is structurally outside the grounding contract.

**Why it happens:**
The grounding stack was designed around audio/MIDI/now-playing/screen — all *single-stream* observations. Harmonic-clash is a **relational, two-deck** claim that the existing 7-source grammar never anticipated. Teams add the feature to the prompt first (easy) and discover the linter can't gate it (hard) only at the release gate.

**How to avoid:**
- Add a new evidence source **`key`** (per-deck Camelot/key with a confidence) to `EVIDENCE_SOURCES` and the EBNF grammar BEFORE writing any harmonic prompt. Body shape e.g. `key:A=9B@conf0.8`.
- The clash claim must cite **both** decks' keys: `[key:A=9B@45.0,key:B=7A@45.0]`. The linter's `has()` lookup confirms each per-deck key was actually registered at that moment.
- Keys come from the **library import** (pyrekordbox XML — VERIFIED: XML export carries `Tonality`/key), NOT from live audio analysis (banned: no CLAP/no DSP key-detect, and Gemini-only). A deck only gets a `key:` observation when (track is resolved to a library entry) AND (audible-deck confidence is high). No library match → no key observation → linter strips any clash claim → fallback ack.
- The "is it actually a clash" math (Camelot adjacency) is **deterministic Python**, not an LLM judgment. The LLM narrates a clash the code already decided is real; it never *discovers* the clash.

**Warning signs:**
Harmonic prompt text exists but `EVIDENCE_SOURCES` is unchanged. Replay-harness shows `[key:...]` citations that `parse_citations()` returns but `has()` always fails (orphan citations). Clash claims surviving with `track=unknown` in the evidence line.

**Phase to address:** Deck-awareness grounding phase (first v5.0 phase, ~Phase 59). The `key` source + linter extension is the gate; harmonic prompting cannot start until it lands.

---

### Pitfall 2: False clash from wrong key detection (the headline hallucination)

**What goes wrong:**
Library-imported key is wrong (~30-43% of tracks carry a wrong or one-off key tag — Rekordbox ~57%, Traktor ~54%, VirtualDJ ~65%, even Mixed In Key ~70% on cross-referenced tests). The co-host confidently announces a clash that doesn't exist, or — worse — tells Kaan a genuinely-good blend is wrong. To a real DJ this is the most credibility-destroying failure possible: it's *wrong about the thing it claims expertise in*.

**Why it happens:**
Teams treat the library key field as ground truth. It isn't — it's a third-party estimate with a known error rate, and the error is *silent* (no confidence shipped in the XML). Tracks with key changes, ambiguous tonality, or heavy percussion (i.e. a lot of techno/psytrance — vibemix's actual genres) are exactly where detectors fail most.

**How to avoid:**
- **Conservative-by-default clash gate.** Only fire a clash callout when (both keys present) AND (both from a library match, not a guess) AND (Camelot distance is in the *unambiguous* clash band — e.g. a semitone/tritone collision, not a "one-off-on-the-wheel" case which is often still fine and may just be a detector error). One step off the Camelot wheel = SUPPRESS, because that's indistinguishable from a key-detection error and pros mix fifths/relatives freely.
- **Frame as observation, not verdict.** Harmonic notes should be flag-rare and hedged toward the audible: prefer "those leads are fighting in the mids" (an `aud:` band-overlap claim the system can actually hear) over "7A vs 9B clash" (a `key:` claim resting on a maybe-wrong tag). The audible evidence is the stronger ground.
- **Suppress during breakdown / acapella / atmospheric sections** — key relationships don't matter when there's no tonal harmonic content overlapping (see Pitfall 3).
- Carry a per-key **confidence** even though the XML doesn't give one: derive it from (genre — percussion-heavy → lower) and (whether two independent sources agree, if available). Below threshold → no clash claim.

**Warning signs:**
Replay harness flags clash callouts on Kaan's real sets that he disagrees with. Clash fires on tracks the DJ knows mix fine. Any clash claim where one deck's key came from a non-library guess.

**Phase to address:** Harmonic-feedback confidence-gate phase (the phase that OWNS the conservatism gate — must be its own phase, not folded into deck-awareness). This is the hard hallucination gate for the milestone; it gets a Kaan-ear veto like Phase 42's regime.

---

### Pitfall 3: Flagging clashes / transitions where the call doesn't apply (context-blind feedback)

**What goes wrong:**
The co-host calls a harmonic clash during a breakdown (no overlapping tonal elements), or gives "you overstayed the blend" feedback during a long intentional ambient bridge, or critiques a transition that already finished 12 seconds ago (latency — the blend is long done by the time the voice lands). It's technically "grounded" on a real key/track but contextually nonsense.

**Why it happens:**
The grounding stack proves a key *exists*; it doesn't prove the key is *currently sounding against another key*. The evidence line carries `phase=` was deliberately REMOVED (load-bearing invariant in `coach.py`: RMS phase-label primed invented drops) — so the model has weaker section-context than it appears. And the 5-10s LLM+TTS latency means transition advice is structurally late (the codebase already enforces past-tense framing for this exact reason).

**How to avoid:**
- Harmonic-clash logic must require **both decks audibly contributing tonal content** — gate on `derive_audible_deck() == "mix"` (two decks live) AND both decks above a low-band+mid energy floor. A breakdown (sub/low dropped out) suppresses the clash check.
- Transition-execution feedback is **retrospective only**: "that blend ran ~16 bars, a touch long" framed in past tense, never "bring the fader down now" (the moment is gone before the voice arrives). Lean on the existing past-tense anti-latency guard in `prompts/matrix.py`.
- Never give unsolicited *prescriptive* transition advice mid-blend; the actionable note lands AFTER, as a "next time" only when feedback mode is explicitly on and the move clearly under/over-shot.

**Warning signs:**
Clash callouts during `deck=A` or `deck=none` (single deck / silence) states. Transition critiques firing on `MIX_MOVE` events where only one deck is up. Present-tense imperative verbs ("bring", "pull", "drop it now") in feedback-mode output.

**Phase to address:** Harmonic-feedback confidence-gate phase (shares the gate with Pitfall 2) + the actionable-feedback persona phase (owns the past-tense / no-mid-blend-imperative rule).

---

### Pitfall 4: Audible-deck ambiguity silently poisons the whole deck-awareness feature

**What goes wrong:**
`derive_audible_deck()` returns `"none"` or `"mix"` far more often than expected because the Pioneer DDJ-FLX4 doesn't write play-state back to the controller when djay Pro is the controlling app (documented KNOWN ISSUE in `track_resolver.py`). When the system can't tell which deck is audible, it can't attribute a key/track to "the thing you're hearing" — so either it stays silent (feature feels dead) or it guesses (hallucination). The whole "full deck awareness" promise rests on a heuristic that's already shaky on the flagship target controller.

**Why it happens:**
"Full deck awareness" assumes the system knows the *state of every deck*. But vibemix's only deck-state signals are MIDI (fader/xfader/vol — play-LED desync'd) + one now-playing title (whichever deck the app decided to publish, "often wrong when mid-mix" per prior research). There is **no per-deck track telemetry** that survives the one-click-install constraint for Rekordbox/Serato/djay/Traktor (VERIFIED: prior B-industry-integrations research — all closed apps refuse usable real-time per-deck APIs). Reading more decks doesn't mean *knowing* more decks.

**How to avoid:**
- Be honest that "all loaded tracks" = "all tracks vibemix could resolve," which on closed apps is **0-1 reliable + the rest inferred**. Scope the feature to what's actually knowable: library-import gives all *potentially-loadable* tracks; live state gives at best the audible-deck title + xfader-derived which-side. The harmonic clash can only fire when BOTH sides are independently resolved — which is the rare high-confidence case, by design.
- Lean on the v4 fix already in the code: `deck_weight` dropped the hard play-gate and trusts **fader+xfader** as the reliable grounded signal (2026-05-21 Kaan fix). Keep that. Don't reintroduce play-state gating for deck attribution.
- Where a second deck's track can't be resolved, emit `deck_b_track=unknown` and **suppress** any cross-deck (harmonic/transition) claim — degrade to single-deck audio feedback, never guess the second track.

**Warning signs:**
Harmonic feature works in dev (where you manually set both deck states) but never fires on Kaan's real FLX4+djay session. `audible_deck` distribution heavily weighted to `none`/`mix`. Second-deck track resolved by "most recent now-playing title" rather than independent confirmation.

**Phase to address:** Deck-awareness data-source + state-resolution phase (the phase that picks the source and builds two-deck resolution). Confidence/degradation rules verified against a real FLX4+djay live drive (KAAN-ACTION live test).

---

### Pitfall 5: Reading a live DJ-app database (master.db) — file locks, version drift, the write-unsafe landmine

**What goes wrong:**
To get "all loaded tracks" someone reaches for the live Rekordbox `master.db`. Three failures: (1) Rekordbox holds the SQLCipher file open with **locks during a live session** — concurrent read is unreliable (VERIFIED: prior research). (2) **Post-Rekordbox-6.6.5 the encryption key extraction is broken** (Pioneer obfuscated `app.asar`) — most users today simply can't be read at all. (3) Any *write* to `master.db` is **UNSAFE** (confirmed prior spike, memory `project_vibe_mix_bravoh_prep_module`) — corrupts the user's collection, the worst possible outcome for a tool asking for trust. Schema also drifts across Rekordbox 6 vs 7 and across Serato/Engine/djay (each a separate undocumented binary/DB format).

**Why it happens:**
The live DB *looks* like the richest source (per-deck, full metadata). Teams underestimate the encryption wall, the locking, and the per-version fragility, and over-estimate how stable the schema is.

**How to avoid:**
- **NEVER write to any DJ-app DB.** XML round-trip is the only safe write path (locked decision). For v5.0 we don't need writes at all — deck awareness is read-only.
- **Read the unencrypted XML export, not the live DB.** Rekordbox → Preferences → Advanced → Export Collection as XML is unencrypted, parses with stdlib, and carries title+BPM+**key**+cue points (VERIFIED). This is the recommended primary source. Treat live `master.db`/SQLCipher as **opportunistic best-effort** for the minority of users on a readable version, never the default, and **read-only with a copy-to-temp** to avoid the live lock.
- Pin the source recommendation in research BEFORE requirements lock (PROJECT.md flags this as the open feasibility question). Recommended: **pyrekordbox XML import as primary; nowplaying-cli + MIDI audible-deck for live "which is playing"; no live DB writes ever; SQLCipher best-effort only.**
- Version-drift defense: parse defensively (missing fields → degrade, never crash), and treat an unparseable/locked DB as "no library" → graceful degradation (Pitfall 6), not an error.

**Warning signs:**
Any code path opening `master.db` in read-write mode. Library import that crashes (rather than degrades) on Rekordbox 7 / 6.6.5 / a Serato `.crate`. Tests that only cover one DJ-app version.

**Phase to address:** Deck-awareness data-source phase (owns source selection + read-only guarantee + XML-primary decision). A repo-scrub-style test asserting no write-mode open of any DJ DB.

---

### Pitfall 6: No graceful degradation when no deck data source is available

**What goes wrong:**
A user on Serato, or Traktor, or Rekordbox-7-encrypted, or who never exported an XML, gets a deck-awareness feature that either errors, goes silent, or — worst — *fabricates* a library/clash because the code assumed a source exists. The feature must be additive: present when grounded, absent (not broken, not invented) when not.

**Why it happens:**
Dev/test happens on the one machine that has a clean Rekordbox XML and an FLX4. The "no source" path is the untested majority case across the cross-platform install base (Serato users, Traktor users, encrypted-Rekordbox users — none get a library).

**How to avoid:**
- Tiered capability, explicit at session start: **(T0)** audio + MIDI only (always available — today's grounding) → single-deck audible feedback, **no** harmonic/transition claims. **(T1)** + library XML resolved → key-aware, but clash only on confirmed two-deck resolution. The co-host's *behavior* degrades cleanly; it never announces a capability it lacks.
- The harmonic/transition prompt fragments are **conditionally injected** — only present in the system instruction when a library is loaded AND the source tier supports it. No library → those instructions aren't even in the prompt → model can't be tempted to use them.
- Surface tier honestly in the UI (a small "library connected" / "audio-only" indicator), not as an error.

**Warning signs:**
Harmonic prompt fragments present in the system instruction on an audio-only session. Any "library not found" code path that raises rather than sets tier=T0. Clash/transition claims appearing for a user who never imported a library.

**Phase to address:** Deck-awareness data-source phase (tier model) + actionable-feedback persona phase (conditional prompt-fragment injection).

---

### Pitfall 7: Persona over-correction — actionable becomes cold/robotic, loses "friend in your ear"

**What goes wrong:**
Sharpening hype→prescriptive coach overshoots into a clipped, fault-finding QC bot. The core value is *"real DJ friend in your ear,"* not "voice assistant reading a spectral analyzer." A coach that only ever flags problems reads as a nag and a downer — exactly the "AI slop" failure in a different costume. The in-flight `live-tuning-or-brain` branch already started addressing this (added a BALANCED rule: "roughly half your turns should be a quick 'that worked' callout… say it in your OWN words EVERY time… NEVER reuse the same praise line twice"), which shows the risk is real and live.

**Why it happens:**
"Actionable, not hype" gets read as "remove warmth, add critique." The pendulum swings from cheerleader to critic, skipping the actual target: a *peer who hypes the good moves AND calls the bad ones, in fresh specific language*.

**How to avoid:**
- Keep the BALANCED rule from the in-flight branch and harden it: ~half of turns are specific positive callouts, problems flagged only when real, **never a stock praise line twice** (the branch already bans "the energy held"/"that was clean" reuse — extend with a runtime repeat-detector if needed).
- "Actionable" ≠ "constant critique." The actionability is in the *specificity* ("blend overstayed by 16," "high-mid pileup at 0:42") and the *peer register*, not in the frequency of fault-finding. Don't manufacture a problem every turn (explicit rule already added).
- Preserve warmth via voice + brevity + genuine reaction to good moves — the friend who *also* tells you the truth, not a truth-machine.

**Warning signs:**
Replay/ear-test: every turn is a criticism. Repeated praise phrasings. Output reads like a checklist. Kaan's gut: "this feels like a tool, not a friend."

**Phase to address:** Actionable-feedback persona phase (owns the COACH_PRO/COACH_* prompt evolution + the balance rule + repeat-detector).

---

### Pitfall 8: Refactoring shared persona/prompt code breaks hype mode

**What goes wrong:**
Sharpening the feedback persona means touching `prompts/matrix.py` and `state/coach.py` — both **shared** across hype and coach modes (the `task_for_event` tasks, the evidence-line builder, the silence/citation rules). A change meant for coach mode regresses hype mode (which Kaan validated live in Phase 54). The in-flight branch already diverged `HYPE_INTERMEDIATE` from its "byte-identical to v4, DO NOT EDIT" lock (relaxed the silence bias) — so the load-bearing IP is now mutable and a further refactor can silently break it.

**Why it happens:**
The prompt matrix is one file with mode-specific blocks but shared scaffolding (evidence packet format, citation grammar, latency/past-tense rules, MIX_MOVE task). Coach-targeted edits leak into shared scaffolding.

**How to avoid:**
- Treat hype-mode prompts + golden tests as a **regression fence**: the existing `test_coach_prompt_grounding.py` / `test_persona.py` / hype golden tests must stay green through every coach-persona change. Any hype-golden change is a deliberate, reviewed decision (as the in-flight silence-bias divergence was), never incidental.
- Keep mode-specific instruction blocks textually separated; shared scaffolding (evidence packet, citation grammar, latency guard) edited only with both modes' goldens re-checked.
- The MIX_MOVE `task_for_event` is shared and was just rewritten on the branch ("give your take on the MIX AS A WHOLE… do NOT do play-by-play") — verify that change reads well in BOTH hype and coach voices before locking.

**Warning signs:**
Hype golden tests need updating "just to make them pass." Hype mode output shifts tone after a coach-only PR. `HYPE_INTERMEDIATE` edited without an explicit decision note.

**Phase to address:** Actionable-feedback persona phase (regression-fence the hype goldens) + a cross-mode verification gate before milestone close.

---

### Pitfall 9: Floating pill steals focus / blocks input to the DJ software

**What goes wrong:**
The always-on-top draggable pill grabs keyboard/mouse focus when clicked or dragged, pulling focus away from Rekordbox/Serato/djay mid-set — a catastrophic UX failure when the DJ needs every keystroke. Tauri has **live, open bugs** here: clicking a `data-tauri-drag-region` toggles window focus and can eat mouse-up events, occasionally sticking the window in a drag-follow state (tauri#10767); `focusable:false` steals focus from the previously-focused window on click on macOS (tauri#14102); always-on-top + accept-first-mouse + a normal window shifts position (tauri#6568).

**Why it happens:**
The prior overlay research (C-ui-overlay) solved a **draw-only, fully click-through** highlight overlay (`set_ignore_cursor_events(true)`, `focused(false)`). The v5 pill is the OPPOSITE: it's **interactive and draggable**, so it *must* accept cursor events — which re-opens every focus/drag bug the click-through overlay sidestepped. The existing mascot recipe doesn't transfer.

**How to avoid:**
- The pill must **never take keyboard focus**: build with `focused(false)` and verify with the DJ app focused that typing/cue keys still reach it after clicking the pill. Test the tauri#14102 macOS focus-steal directly.
- Drag via `data-tauri-drag-region` on a dedicated grip zone only — keep interactive controls (buttons) out of the drag region to avoid the mouse-up-eating drag-stick bug (tauri#10767). Consider OS-native drag (`startDragging`) over the drag-region attribute if the bug bites.
- Pill is `skip_taskbar` + `always_on_top` but **small and movable** so the DJ parks it off the critical deck area; never fullscreen, never modal.
- Known carryover: "Tauri capability missing for drag" is already an open v0.1.0-rc1 bug (memory `project_v0_1_0_rc1_open_bugs`) — fix the capability/permission for `startDragging`/drag-region as part of this work, don't inherit it.

**Warning signs:**
Cue/hotkey presses get swallowed after touching the pill. Pill follows the mouse after a drag without a second click. DJ app loses focus when pill is clicked. Drag works in dev but the built app lacks the capability.

**Phase to address:** Floating-pill UI phase (focus + drag behavior is the core of it). Verified with the DJ app as the focused app on both mac + win.

---

### Pitfall 10: Pill obscures critical deck info / multi-monitor + display-change positioning bugs

**What goes wrong:**
The pill sits over the waveform, cue points, or BPM readout the DJ actually needs; or it lands off-screen / on the wrong monitor after a display change (DJ plugs into the club projector, unplugs a monitor, or the laptop wakes with a different display arrangement). Multi-monitor coordinate bugs are well-documented for this stack: macOS global coords have origin at primary top-left with **negative Y on secondary displays** (mixing Quartz vs NSScreen flips puts it a screen off — prior research, Swindler#62); Windows `GetWindowRect` auto-rescales across **per-monitor DPI** (a 100%+150% setup silently mis-positions — prior research).

**Why it happens:**
The pill position is user-set (draggable) but display geometry changes underneath it. Dev happens on a single monitor at one DPI; the multi-monitor + hot-plug + mixed-DPI matrix is the untested real-DJ case (club setups are almost always multi-display).

**How to avoid:**
- **Clamp-to-visible on every display change.** Subscribe to display-config change events; if the pill's saved position is now off any visible monitor, snap it back to a safe default corner. Never let it vanish.
- macOS: stay in Quartz coords (top-left origin, Y down) consistently; multiply by `scale_factor()` for Retina (prior research recipe). Windows: mark `PROCESS_PER_MONITOR_DPI_AWARE_V2`, compute per-monitor scale via `MonitorFromWindow`+`GetDpiForMonitor`.
- Pill is small + user-parkable by design so the DJ owns the "don't cover my waveform" decision — but ship a sane default position that's out of the typical deck/waveform zone.
- Persist position per-display-arrangement, not globally, so reconnecting a known setup restores the user's chosen spot.

**Warning signs:**
Pill invisible after sleep/wake or monitor hot-plug. Pill on the projector instead of the laptop. Half-position on Retina. Wrong position when an external display at a different scale is attached.

**Phase to address:** Floating-pill UI phase (positioning + display-change handling). Tested on a real two-monitor mixed-DPI setup (KAAN-ACTION or VM matrix).

---

### Pitfall 11: Transparency / vibrancy renders differently mac vs win + breaks the existing mascot overlay

**What goes wrong:**
The Super-Whisper-style frosted pill looks right on macOS (vibrancy/`macOSPrivateApi`) but renders as an opaque white box or a hard-edged rectangle on Windows (no native vibrancy; `WS_EX_LAYERED` transparency is different). Or: making the pill the primary surface accidentally regresses the shipped 3D mascot overlay (`mascot.html` / Three.js GLB rig, wired into `ws_bus` + the `mascot-audit` CI) which PROJECT.md says is **kept, not retired** (opt-in/secondary).

**Why it happens:**
Tauri abstracts window flags but NOT the visual fidelity of vibrancy/blur — mac has native material, win approximates. And the transparent-window gotcha (HTML/body must be transparent or the engine fills white — VERIFIED tauri docs) bites the new window. The mascot regresses because the two windows share the ws_bus and the "primary surface" reshuffle touches shared wiring.

**How to avoid:**
- Design the pill to look intentional on BOTH platforms: a real (semi-opaque) glass background, not pure transparency relying on OS vibrancy. Set HTML/body transparent + an explicit `--glass-*` background (the CDJ-Whisper tokens already define `--glass-1..3` with rgba alphas — reuse them; backdrop-filter blur as enhancement, not as the only thing making it readable).
- Backdrop-filter perf caveat (prior HANDOFF watchout): `blur(32px)` on an always-on-top window over a busy DJ waveform can hammer integrated GPUs — use the lighter `--blur-glass-light` (16px) for the pill, test on a non-dev machine.
- **Mascot regression fence:** the `mascot-audit` CI + the 6-file `mascot.html` allowlist grep-gate already exist — keep them green. The pill is a NEW window; do not refactor the mascot window's ws_bus subscription. Verify both windows can run simultaneously (pill primary, mascot opt-in) without ws_bus contention.

**Warning signs:**
Pill is a white/opaque box on Windows. Pill unreadable over bright waveforms. FPS drop / fan spin on integrated GPU when pill is up. `mascot-audit` CI red. Mascot stops reacting after the pill lands.

**Phase to address:** Floating-pill UI phase (cross-platform rendering + mascot coexistence). Visual smoke on both OSes; mascot-audit stays green.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use library key field as ground truth (no confidence) | Ships harmonic feature fast | False clash calls trip the hallucination gate; ~30-43% wrong-key rate corrupts the headline feature | **Never** — must carry derived confidence + conservative gate |
| Stuff harmonic claim into a `track:` citation body | Avoids touching `EVIDENCE_SOURCES` | Linter can't actually validate per-moment per-deck key; uncitable-by-construction | **Never** — add the `key` source first |
| Read live `master.db` directly for "all loaded tracks" | Richest per-deck data | File locks, post-6.6.5 encryption wall, version drift, corruption risk on any write | Best-effort read-only on a copy, never default, never write |
| Reuse the click-through overlay recipe for the interactive pill | Existing `mascot_window.rs` builder | Re-opens focus-steal/drag bugs the click-through path avoided | Never — interactive pill needs its own focus/drag handling |
| Pure-transparency pill relying on OS vibrancy | Looks great on mac in dev | Opaque white box on Windows, unreadable over waveforms | Never — ship explicit glass background both OSes |
| Edit shared prompt scaffolding for a coach-only change | One file, fast | Silently regresses Kaan-validated hype mode | Only with both modes' goldens re-checked + decision note |
| Skip the "no library source" tier path | Dev machine has Rekordbox XML | Majority cross-platform users (Serato/Traktor/encrypted-RB) get a broken or fabricating feature | Never — tiered degradation is required |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Rekordbox library | Read live SQLCipher `master.db` | Read unencrypted XML export (title+BPM+**key**+cues); SQLCipher best-effort only; post-6.6.5 key extraction broken |
| Any DJ-app DB | Open read-write / write back | NEVER write (corruption); read-only on a temp copy to dodge live locks |
| Serato / Traktor / djay per-deck state | Assume a real-time per-deck API exists | None survives one-click install (VERIFIED prior research) — fall back to audio + MIDI + nowplaying; suppress cross-deck claims |
| nowplaying-cli "current track" | Treat as authoritative per-deck | It's ONE title, the deck the app *chose* to publish — "often wrong mid-mix"; cross-ref with MIDI audible-deck, cap confidence |
| Gemini key/harmonic reasoning | Let the LLM *decide* if keys clash | Camelot adjacency is deterministic Python; LLM only narrates a clash the code confirmed |
| EvidenceRegistry | Ship harmonic claims under existing 7 sources | Add `key` source + EBNF + linter rule before any harmonic prompt |
| Tauri drag region | Put buttons inside `data-tauri-drag-region` | Separate grip zone; keep interactive controls out of drag region (tauri#10767 mouse-up-eating) |
| Tauri transparent window | Rely on default backgrounds | HTML/body MUST be transparent + explicit glass bg, or engine fills white |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `backdrop-filter: blur(32px)` on always-on-top pill over live waveform | Fan spin, FPS drop, dropped audio callbacks on integrated GPU | Use `--blur-glass-light` (16px); test on non-dev machine | Integrated-GPU laptops (the bedroom-DJ majority) |
| Harmonic Camelot computation per audio tick | CPU spike, contends with audio thread | Compute clash only on track-change / two-deck-resolve events, not per 10Hz state tick | Sustained two-deck mixing |
| Library XML parse on every session start, full collection | Slow startup; large collections (10k+ tracks) lag the boot | Parse once, cache locally (existing pattern); incremental on change | 5k+ track libraries |
| EvidenceRegistry `key` observations unbounded | Memory growth over long sets | Same cooldown/append-only discipline as existing sources (~500 obs/hr cap) | Multi-hour sets |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Writing to user's `master.db` / collection DB | Corrupts the DJ's library — total trust loss, the worst outcome | Read-only always; XML round-trip is the only safe write path (locked) |
| Bundling SQLCipher key-extraction workaround | Legal/EULA grey zone (Pioneer obfuscated the key deliberately) | Use XML export path; treat SQLCipher as user-provided best-effort, don't ship extraction tooling |
| Pill window reading other apps' content beyond public APIs | Reverse-engineering EULA breach | Stay on public window APIs / audio / MIDI / user-exported library — same posture as v3.0 overlay (overlay-only = clean) |
| Harmonic feature exfiltrating library data | Privacy — user's collection is personal | Library stays local; only embeddings/derived state, never raw collection, leaves the machine (matches Gemini-only + Bravoh-proxy model) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Pill covers waveform / cue / BPM | DJ can't see critical deck info mid-set | Small, parkable, sane default off the deck zone; user owns placement |
| Pill steals focus on click | Cue/hotkeys swallowed mid-set — set-ruining | `focused(false)`, verify keystrokes reach DJ app after pill interaction |
| Constant harmonic/transition nagging | Feels like a backseat driver; DJ mutes it | Flag-rare, conservative, balanced with positive callouts; cooldown-gated |
| Coach mode = pure criticism | Reads as a downer, not a friend — "AI slop" in disguise | ~half positive, fresh language every time, problems only when real |
| Clash callout the DJ disagrees with | Destroys credibility (wrong about its expertise) | Suppress one-step-off-wheel + breakdown + low-confidence-key cases |
| Pill vanishes after monitor change | DJ thinks app crashed mid-set | Clamp-to-visible on every display-config change |
| No accessibility on pill | Low-vision DJs / club-dark conditions | WCAG-AA contrast (existing wizard precedent), readable amber-on-glass, keyboard-dismissable |
| Mascot silently disappears when pill ships | Users who liked the mascot feel features were removed | Mascot kept opt-in/secondary; both windows coexist; toggle in settings |

## "Looks Done But Isn't" Checklist

- [ ] **Harmonic clash:** Often missing the `key` evidence source + linter rule — verify a fabricated clash gets STRIPPED by the linter in replay, not just absent in the demo.
- [ ] **Deck awareness:** Often missing the "second deck unresolved" path — verify it suppresses cross-deck claims rather than guessing on a real FLX4+djay session.
- [ ] **Library import:** Often only tested on one Rekordbox version — verify graceful degrade on Rekordbox 7 / 6.6.5-encrypted / Serato / no-library (tier T0).
- [ ] **Key confidence:** Often missing — verify clash suppressed on percussion-heavy / ambiguous-key tracks and on one-step-off-wheel pairs.
- [ ] **Coach persona:** Often ships as pure-critique — verify ~half turns are fresh positive callouts and no praise phrase repeats across a 30-min replay.
- [ ] **Hype mode:** Often regressed by shared-prompt edits — verify hype goldens still green after every coach change.
- [ ] **Pill focus:** Often missing the focus-steal test — verify DJ-app keystrokes survive pill clicks on BOTH mac + win (tauri#14102/#10767).
- [ ] **Pill multi-monitor:** Often single-monitor only — verify clamp-to-visible on hot-plug/sleep-wake and correct mixed-DPI positioning.
- [ ] **Pill transparency:** Often mac-only — verify it's not an opaque white box on Windows and is readable over a bright waveform.
- [ ] **Mascot coexistence:** Often regressed — verify `mascot-audit` CI green and mascot still reacts with pill running.
- [ ] **No-DB-write guarantee:** Verify a repo test asserts no DJ-app DB is ever opened in write mode.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| False clash shipped (wrong key) | MEDIUM | Tighten conservatism gate (suppress one-off-wheel + low-conf); add the disagreed pair to replay corpus; re-run Kaan-ear veto |
| Harmonic claims uncitable (no `key` source) | HIGH | Retrofit `key` source + EBNF + linter; re-thread all harmonic prompts through it — touches grammar + linter + prompt + tests |
| Hype mode regressed by shared edit | LOW | Hype goldens catch it at CI; revert the shared-scaffold change, re-route as mode-specific |
| Pill steals focus | MEDIUM | Rebuild with `focused(false)` + native drag; may need to drop drag-region attribute for `startDragging` |
| Pill off-screen after display change | LOW | Add display-change listener + clamp-to-visible; persist per-arrangement |
| Pill opaque on Windows | LOW-MEDIUM | Add explicit glass background; stop relying on OS vibrancy |
| master.db corrupted by a write | HIGH | Restore from Rekordbox backup; reaffirm read-only invariant + repo guard — but trust damage with that user is largely irreversible |
| Coach reads as a nag | LOW-MEDIUM | Re-tune balance rule / cooldowns; Kaan-ear pass |

## Pitfall-to-Phase Mapping

> v4.0 ended at Phase 58; v5.0 phases begin at 59. Names below are research recommendations for the roadmap, not locked phase titles.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Uncitable harmonic (no `key` source) | Deck-awareness grounding (P59) | Linter strips a fabricated `[key:...]` clash in replay; `EVIDENCE_SOURCES` includes `key` |
| 2. False clash from wrong key (headline) | Harmonic confidence-gate (P60) | Replay corpus of Kaan-disagreed pairs all suppressed; Kaan-ear veto on harmonic turns |
| 3. Context-blind clash/transition | Harmonic confidence-gate (P60) + persona (P61) | No clash on single-deck/breakdown states; no present-tense imperatives |
| 4. Audible-deck ambiguity poisons feature | Deck data-source + state-resolution (P59) | Cross-deck claims suppressed when 2nd deck unresolved on a real FLX4+djay drive |
| 5. master.db locks/version/write landmine | Deck data-source (P59) | Repo test: no DJ-DB write-mode open; degrades on RB7/6.6.5/Serato |
| 6. No-source graceful degradation | Deck data-source (P59) + persona (P61) | Audio-only session has zero harmonic prompt fragments; tier surfaced honestly |
| 7. Persona over-correction (cold/nag) | Actionable-feedback persona (P61) | 30-min replay: ~half positive, no repeated praise, problems only when real |
| 8. Shared-prompt refactor breaks hype | Actionable-feedback persona (P61) + cross-mode gate | Hype goldens green after every coach change |
| 9. Pill steals focus / blocks input | Floating-pill UI (P62) | DJ-app keystrokes survive pill clicks, mac + win (tauri#14102/#10767) |
| 10. Pill obscures info / multi-monitor | Floating-pill UI (P62) | Clamp-to-visible on hot-plug/sleep; correct mixed-DPI position |
| 11. Transparency mac/win + mascot regress | Floating-pill UI (P62) | Not white box on Win; readable over waveform; `mascot-audit` green |

## Sources

- **Codebase (HIGH, read directly):** `src/vibemix/state/evidence_registry.py` (`EVIDENCE_SOURCES`, grammar, linter contract); `src/vibemix/state/track_resolver.py` (`derive_audible_deck`/`derive_audible_track`, FLX4 play-state KNOWN ISSUE, confidence thresholds); `src/vibemix/state/coach.py` (`AICoach`, removed-`phase=` invariant, MIX_MOVE task); `src/vibemix/prompts/matrix.py` (persona blocks); `git diff main...live-tuning-or-brain` (in-flight persona/silence/BALANCED changes).
- **Prior research (VERIFIED, multi-source):** `.planning/research/v2-buckets/B-industry-integrations.md` (master.db SQLCipher post-6.6.5 wall, live-lock, no per-deck APIs for closed apps, XML-export fallback, ProDJ-Link laptop-only NO); `.planning/research/v2-buckets/C-ui-overlay.md` (Tauri transparent/always-on-top recipe, multi-monitor Quartz vs NSScreen, Windows DPI, sidecar AX bug, fullscreen-Space gap); `.planning/research/v3-buckets/v3.x-pyrekordbox-depth.md` (SQLCipher install-fragility).
- **PROJECT.md / CLAUDE.md / memory (HIGH):** anti-slop grounded-Gemini thesis; no-CLAP Gemini-only; master.db-write-unsafe / XML-round-trip; one-click-install hard req; v0.1.0-rc1 Tauri-drag-capability open bug; Gemini Embedding 2 for library.
- **Web (MEDIUM, secondary sources agree):** Key-detection accuracy — [Mixed In Key 11 review (We Are Crossfader)](https://wearecrossfader.co.uk/blog/mixed-in-key-11/), [Dubspot Lab Report MIK vs Beatport](https://blog.dubspot.com/dubspot-lab-report-mixed-in-key-vs-beatport), [Engine DJ key mis-analysis thread](https://community.enginedj.com/t/engine-dj-badly-analyses-track-key/52099), [VirtualDJ key detection issues](https://virtualdj.com/forums/228037/VirtualDJ_Technical_Support/Key_Detection_Issues.html) (RB ~57% / Traktor ~54% / VirtualDJ ~65% / MIK ~70%; fails on key changes, ambiguous tonality, heavy percussion). Tauri window bugs — [tauri#10767 drag focus-toggle/mouse-eat](https://github.com/tauri-apps/tauri/issues/10767), [tauri#14102 focusable:false focus-steal macOS](https://github.com/tauri-apps/tauri/issues/14102), [tauri#6568 always-on-top position shift](https://github.com/tauri-apps/tauri/issues/6568), [Tauri window customization docs](https://v2.tauri.app/learn/window-customization/).

---
*Pitfalls research for: full-deck awareness + harmonic/transition feedback + actionable-coach persona + floating-pill UI on a grounded local AI DJ co-host (vibemix v5.0)*
*Researched: 2026-05-21*
