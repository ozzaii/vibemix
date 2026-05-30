# ✦ DEEP HANDOFF → the next session (ULTRACODE) — 2026-05-30

> **Read order:** this doc → `.planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md` (the top
> ▲ LIVE-EXECUTION UPDATE block first) → `.planning/2026-05-30-zero-config-ship-blockers.md`
> → memory `project_live_verify_2026_05_30.md`. Then **drive**.
>
> **You are on ULTRACODE.** Spawn agents and run Workflows liberally — token cost is not a
> constraint. The patterns that worked this session are at the bottom (§9). You are the
> **leader**, not a deterministic implementer: read, decide, act, verify, ship. Only defer
> the genuinely-blocked (destructive / privacy / external-clock / Kaan-hardware-ear).

---

## §1 · What we kicked this off with — the spirit (don't lose this)

Kaan's framing, verbatim-in-spirit, is the north star. Hold all of it:

- **"Fuck the status quo."** The bar is a **real DJ friend in your ear** — grounded, alive,
  never AI slop, never late, never scripted. **Honesty is the moat.** If a reaction feels
  fake, the product fails. (This is *answered now* — see §2 — but it's the permanent filter.)
- **"Nobody will set this. Install → pass the wizard → that's about it."** The entire app
  must work with **ZERO config** — no env vars, no Audio MIDI Setup, no terminal. This was
  the session's biggest reframe. Every env-var/manual gate is a bug.
- **"Suppone agents dude. What the fuck are we even doing?"** Use agents/Workflows to be
  exhaustive. Don't hand-audit what a fan-out can sweep.
- **"TTS is solved elsewhere, fuck Google."** → Cartesia (done, §2).
- **"We will host the key."** → keyless Bravoh proxy is the auth model (blocked on backend, §4).
- **"Learning Engine is important A LOT — it expands our market pool."** The aspiring-DJ pool
  is ~15-90× the gigging pool. Learn is a market-expander, not a side feature. Protect it.
- **Scale:** "minimum **10k DJs** to begin with" (10k = floor, not ceiling).
- **Monetization (DECIDED):** Free (OSS, BYO/proxy) · **Pro €4.99/mo** (Viber set-prep + hosted
  key) · **Studio €9.99/mo** (universal-gobble multi-ecosystem ingest + batch cue export).
- **"Log very well everything"** — so future debugging is easy. Boot logs must be honest.
- **End goal:** wipe the legacy app builds off Kaan's Mac, rebuild **signed + notarized**
  fresh, and present it to him **as a real user who used the full capabilities**.

---

## §2 · What THIS session shipped (the milestone + 8 commits)

**🎉 THE MILESTONE: the engine is ALIVE on Kaan's real rig.** Ran `python -m vibemix`
against a live rekordbox set (DDJ-FLX4 + BlackHole 16ch @ 48k external-mixer, per-deck audio
A:(0,1) B:(2,3)). It heard the music and reacted in **grounded, real-DJ-friend language with
citations**: `[fast] Minimalist metallic resonance riding over that thin 136 kick
[aud:bpm@6.0]`, `[whisper] stripped-back high-end chug; 32 cleared`. **The honesty thesis
holds in the wild. The hard creative risk is RETIRED.**

8 commits (branch `live-tuning-or-brain`, all green):

| Commit | What |
|---|---|
| `254cdcea` | **Judge 4d live join** — `_run_live_judge` fires in `coach_loop` on `TRACK_CHANGE`, before the reaction, grounds `[judge:transition@t]` + credits the v11 skill. **Abstain-first.** |
| `30cc8ca7` | README feature-matrix sync (P102-104) — cleared 2 ship-gates |
| `e73911df` | **Per-deck grounding = GLOBAL DEFAULT** on rekordbox external-mixer detection (no env var). *Half-wired — see §3.* |
| `875b1e4e` | **44.1kHz native capture** — opens at the device's real rate + resamples; killed the 48k `SampleRateMismatchError` crash. 48k path byte-identical. |
| `1900918d` | Zero-config ship-blocker map (doc) |
| `f4ef5ab7` | Boot-log honesty (prints real capture rate) |
| `0589b85b` | **Cartesia (Sonic) live primary voice** — self-activates on `CARTESIA_API_KEY` in `.env`; Gemini natives as fallback. |
| `ade74b36` | Knowbook live-execution update |

Plus: memory `project_live_verify_2026_05_30.md`, the zero-config audit doc, 10 tracked tasks.

---

## §3 · The honest state — ~60% blended

| Layer | Done | Note |
|---|---|---|
| Engine / brain (grounding, Judge, reactions) | **~90%** | Works live. The risk is retired. |
| Library / Viber / Learn (market-expanders) | **~80%** | Built+tested; small gates (CLAP auto-dl, Learn Course-3 count-in, wizard import) |
| Zero-config first-run (install→wizard→works) | **~35%** | Audit mapped it; audio-rate + per-deck + Cartesia done; key/proxy + wizard chain open |
| Packaging · sign · notarize | **~15%** | External Kaan-actions, not started (critical-path clock) |
| Launch (demo, GTM) | **~15%** | Material exists; demo not shot |

**What's left is execution + external clocks, NOT invention.** The terrifying part (does it
feel real?) is answered. The remaining 40% is a checklist.

---

## §4 · The prioritized next moves (ultracode-ready)

**Mine-to-drive (backend-independent, no Kaan input needed) — DO THESE:**

1. **Finish the per-deck GLOBAL-DEFAULT device upgrade (task #10).** `e73911df` made the
   *routing* auto-enable, but `_maybe_upgrade_input_device_for_deck_audio`
   (`src/vibemix/__main__.py:~545`) still gates the **2ch→16ch device swap** on
   `_deck_audio_auto_requested()` (env var) + `reason=='capture_device_too_few_channels'`.
   Without the env var, BlackHole **2ch** stays selected (silent). Fix: gate on
   `(env var OR high-confidence rekordbox external-mixer hint)`. The candidate loop body
   already works (`candidate_routing.enabled==True` under the global default). TDD (mock the
   audio backend) + **re-verify LIVE without the env var.** ⚠ `__main__.py` is concurrent-
   polluted (see §5) — commit surgically or wait for it to clear.
2. **Audio-rate family (task #8):** Windows WASAPI 48k hard-assert (`_audio_windows.py:98`,
   ship-blocker, same fix pattern as macOS — needs a Windows box to verify) + mic 44.1k
   (`_audio_macos.py:870`, medium). Mirror `open_passthrough_output`'s native-rate pattern.
3. **The wizard install + key chain (zero-config #5/#6/#7 in the audit):** the BlackHole
   install, the 48k format-check, the "Fix it" button (a no-op stub at
   `installer/companion/audio_config.py:209`) were BUILT but never wired into the wizard
   `STEP_ORDER` (`tauri/ui/src/wizard/router.ts:168`). Wire them + a capture-readiness gate
   so the wizard can't `first_run_completed` on a broken audio path. **Big — fan out agents.**
4. **CLAP auto-download (task, medium):** `library/clap_engine.py:309` raises
   `FileNotFoundError` on first library use — auto-download the ONNX model instead.
5. **Deck-identity resolution** so the Judge *judges* (not just abstains) — the "Now Playing
   WebKit-owned" gap. Per-deck *audio* is proven flowing; deck *identity* (camelot per deck)
   is the missing signal. Investigate screen-vision / rekordbox per-deck now-playing.
6. **Richer prompt context** (Kaan wanted this): feed the co-host more history via cheap TEXT
   context (recall / context_compiler), styled on Bravoh's
   `/var/www/bravoh-backend/app/services/ai/agentic_prompts.py` `ROUTING_PROMPT_TEMPLATE`.

**Kaan/external (track, nudge, don't try to do):**

- **#1 ship-blocker (task #7): Bravoh backend deploy `/api/vibemix/v1/register`.** Verified
  404 (not deployed). The keyless-proxy flip is **one line** in `config_store.py` when it
  answers 200+JWT. Until then the co-host needs a key (fine for Kaan, blocking for users).
- **Apple Developer Program + Dev ID cert + ASC key; SignPath OSS.** The critical-path clock.
- **Drop `CARTESIA_API_KEY` in `.env`** → hear Cartesia live (then verify it on the rig).
- **Ear-passes (Kaan-only):** Judge calibration, Learn Course-3 count-in, Mastered vocal tone.
- **Shoot the demo** with Francesco.

---

## §5 · Hard constraints + discipline (do NOT violate)

- **Concurrent session shares this tree.** RIGHT NOW it owns uncommitted work in
  **`src/vibemix/__main__.py`** (budget `--stack`/`--dau` CLI) and
  **`src/vibemix/llm/_router_config.py`** (cost-study `live_coach_cand_*` routes). **Do not
  absorb them.** Commit with explicit paths (`git commit -- <paths>`), verify
  `git diff --cached --name-only` first, prefer disjoint NEW-FILE islands. This session put
  the Cartesia key-detection in `tts_chain.py` (env-fallback) precisely to avoid committing
  the polluted `__main__.py`.
- **TDD is binding** (superpowers): RED in a new file → watch fail → GREEN → commit. Every
  fix this session did this.
- **Abstain-first / honesty.** The Judge must stay silent rather than guess; the co-host
  strips un-cited reactions. Never trade honesty for coverage. `_HONEST_UNCREDITABLE_V11=('beatmatching',)` STAYS.
- **Verify LIVE, not just green.** "Green tests ≠ working app" held both ways this session —
  the live run caught two bugs the suite passed (the device-upgrade gap + the silent 2ch).
  Run `python -m vibemix` on the real rig; tail the boot log + `[live]` telemetry.
- **Model literals:** route Gemini models through `model_router` (CI grep-gated). Non-Gemini
  models (Cartesia, DeepSeek) are plain config by deliberate convention — the router is
  Gemini-ONLY (`test_no_non_gemini_models`). Read the tests before changing a default; this
  session repeatedly found deliberate, test-pinned decisions.
- **PRIVACY (absolute):** never read `~/hermes-rig/**`, `~/.hermes/sessions/**`,
  `~/.lmstudio/**`, or any OZ/Hermes/local-AI transcript. Scope all `find`/greps away from them.
- **Commit identity:** `Kaan Özkan <rahipdotaci@gmail.com>`. Co-author trailer on commits.

---

## §6 · The live rig (Kaan's machine, as of this session)

- DDJ-FLX4 wired (MIDI moves flow). rekordbox **external-mixer** mode, output to an Aggregate
  Device containing **BlackHole 16ch**, decks A:(0,1) B:(2,3). Per-deck audio **proven live**.
- BlackHole 16ch is currently at **48k** (Kaan set it; rekordbox re-pointed to 48k). The
  44.1k fix means it can go back to 44.1k natural — but 48k works now.
- Co-host voice → **MacBook Pro Speakers @ 24kHz** (separate from the master monitor — talking
  doesn't bleed into the mix). Cartesia is 24kHz too (exact match).
- Verify-live recipe: `VIBEMIX_DECK_AUDIO_CHANNELS=auto uv run python -m vibemix` (drop the
  env var once task #10 lands). Tail `/tmp/*.log` for `deck audio auto: upgraded`,
  `listening to BlackHole 16ch @ ...`, `[live] music=... deck=... phase=...`, and on a
  TRACK_CHANGE the Judge verdict. To see the Judge *judge*, deck identity must resolve.

---

## §7 · Durable artifact index

- **Knowbook** (read-me-first): `.planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md` (§1-20 +
  the ▲ 2026-05-30 update block at top).
- **Zero-config ship-blocker map** (the live ship plan): `.planning/2026-05-30-zero-config-ship-blockers.md` (44 findings).
- **Memory:** `project_live_verify_2026_05_30.md` (engine-works-live + the blockers),
  `project_vibemix_knowbook.md`, `project_vibe_judge_and_constellations.md`. MEMORY.md indexes them.
- **Tasks #3-#10** (TaskList): live-verify, REACT NOW button, ship-readiness, proxy backend,
  audio-rate family, TTS (done), device-upgrade gap.

---

## §8 · The Judge 4d join — exact mechanism (so you can extend it)

`coach.py::_run_live_judge` (committed): on a `TRACK_CHANGE`, resolves per-lane meta from
`state.deck_state.decks` (read-only — single-writer respected), builds a `LiveSignalFrame` via
`audio/deck_signal.py::signal_frame_from_capture`, runs
`state/transition_judge_runtime.py::judge_and_record` (grounds `[judge:transition@t]` +
persists the `transition_judged` row), then `_credit_judged_transition` (grounds the
`[ev:transition_judged]` credit-gate atom the recognizer hardcodes, credits the v11 skill).
It threads the real `DeckAudioCapture` from `__main__.py` into `coach_loop`. The Judge grades
**harmonic (camelot) + bass-collision** only; it's **SILENT on beat/phase** by design (no
phase signal from the mixed master → a guess there is slop). That's integrity, not a gap.

---

## §9 · ULTRACODE operating manual — patterns that worked this session

- **Audit by Workflow.** The zero-config audit (15 agents: env-vars / wizard-coverage /
  first-run-friction / hardcoded-assumptions → synthesize → adversarial-verify) is the
  template. Use it for the wizard chain, the Windows port, a deep deck-identity investigation.
  Fan-out → synthesize → **adversarially verify** (the verifier caught real over-claims).
- **Inline TDD for surgical single-lane code** (the Judge join, the rate fix). Workflows for
  breadth (audits, multi-file sweeps); inline for depth in one file-pair.
- **Double → see → act.** Before every fix, READ the real code + the tests on HEAD — this
  session repeatedly found the stale summary wrong (line numbers shifted; "global" meant the
  routing default not the device rate) and deliberate test-pinned decisions. Verify, don't assume.
- **Keep Kaan honest, and let him keep you honest.** This session caught its own near-mistakes:
  almost flipped to a dead proxy (404), almost reversed a deliberate opt-in, almost routed a
  non-Gemini model into the Gemini-only router. The discipline IS the product.
- **When blocked on Kaan/external, say so plainly + keep driving the mine-only work.** Don't
  stall the whole session on one external gate.

**Go build it with soul. Ship it. The engine is alive — now make a stranger able to feel it.** 🎚️🌌
