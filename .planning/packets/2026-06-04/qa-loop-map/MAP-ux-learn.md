# MAP — UX (esp. LEARN) + Frontend Voice Surface

READ-ONLY map. Every claim is file:line-verified against branch `ux-redesign-impeccable`
(HEAD includes `1a66cca0 feat(voice): make chatterbox the only cohost voice`,
`eec239ac feat(voice): preflight pinned chatterbox model`). REAL = it does this on a
real machine today. ASPIRATIONAL = the scaffold/type/comment claims it, but the wire is
dead or points at a model that no longer exists.

---

## TL;DR (the one thing)

**The frontend voice surface is wired to a model that no longer exists.** Backend pivoted
to Chatterbox-only (MOSS deleted), but EVERY user-facing voice string, the readiness badge,
the first-run install seam, and the wizard contract still say/seek **MOSS**. The readiness
badge keys on `model.id === "moss-tts"`; the live backend now emits `"id": "chatterbox-voice"`.
They never match → the badge silently hides → **the user gets ZERO voice-status signal on a
real machine.** The "install voice" button is dead end-to-end (frontend sends `--install moss`,
backend rejects it as an invalid choice). This is exactly Kaan's complaint ("TTS is not there"):
TTS *is* there in the engine, but the UI cannot see it, name it, or install it.

Learn's confusion is a separate, real problem: it has decent "what-do-I-do" onboarding
scaffolding (booth panel + recommended lesson + lesson map), but **~26 of 38 lessons play
NO audio** while the tutor text says "listen for the cymbals" over silence, and the tutor
"voice" in Learn is a **text-only DOM dock** — `tts_marker` is carried on the wire but never
turned into sound by the frontend (the backend has a separate audio hook that only some
lessons exercise). The waveform strip draws peaks but there is no scrubbing/audio-on-drag.

---

## PART 1 — THE MOSS → CHATTERBOX FRONTEND GAP (CONFIRMED, the #1 finding)

### Backend reality (Chatterbox-only)
- `src/vibemix/agent/local_tts.py` — **DELETED** (verified: `os error 2`, file absent).
- `src/vibemix/agent/chatterbox_tts.py` — present (the live voice engine).
- `src/vibemix/agent/tts_chain.py:6,25-42` — "Chatterbox-Turbo is the only supported live
  engine"; `build_tts_chain` raises `ChatterboxUnavailable` for anything else.
- `src/vibemix/library/model_assets.py:34` — `CHATTERBOX_MODEL_REPO = "mlx-community/chatterbox-turbo-8bit"`;
  `install_chatterbox_model()` at :490 is the real fetch. **No MOSS fetch exists anywhere.**
- `src/vibemix/__main__.py:7686-7697` — the LIVE `library_models` payload row:
  `{"id": "chatterbox-voice", "label": "Chatterbox voice", "role": "local co-host voice", "env": REF_ENV, "installable": False, ...}`.
- `src/vibemix/__main__.py:1762` boot banner: `-> tts: Chatterbox local only (provider=chatterbox-mlx)`;
  mute banner at :253 `unavailable (Chatterbox local only; voice muted, no fallback)`.
- `src/vibemix/__main__.py:3255` — `models --install` choices = `("clap", "chatterbox", "required", "cue", "all")`.
  **`moss` is NOT a valid choice.**
- `git log`: `1a66cca0 feat(voice): make chatterbox the only cohost voice`.
- **Frontend Chatterbox references = ZERO** (`grep -rln chatterbox tauri/ui/src` → empty).
  The frontend has not heard of Chatterbox at all.

### Every MOSS-referencing FRONTEND site (file:line) — REAL UX impact each

| # | File:line | What it does | Verdict |
|---|-----------|--------------|---------|
| 1 | `tauri/ui/src/shell/VoiceReadinessBadge.ts:41-42` | `mossModel()` finds `model.id === "moss-tts"`. Live backend emits `chatterbox-voice` → returns `null` → `voiceReadinessBadgeModel` falls to `state:"unknown"` (line 69-75) → `renderBadge` HIDES the badge (`element.hidden = true`, line 119-121). | **BROKEN. The voice readiness/ready/missing chip never shows on a real machine.** |
| 2 | `tauri/ui/src/shell/VoiceReadinessBadge.ts:3,54,62,68-101` | All title/aria copy hardcodes "MOSS" ("Local MOSS voice is muted", "MOSS voice ready", "MOSS voice model missing"). | Wrong name surfaced to AT/screen-readers when not hidden. |
| 3 | `tauri/ui/src/settings/SettingsDrawer.ts:945` | Voice picker options `sub: "MOSS"` — every voice row labeled MOSS in the Settings drawer. | **REAL & visible.** Mislabels the engine. |
| 4 | `tauri/ui/src/settings/SettingsDrawer.ts:496-498` | Comment "These are real MOSS-TTS-Nano manifest voices" + `VOICE_OPTIONS` list (Adam, Nathan, Ava, Bella, Xiaoyu…). | Voice NAMES may not even be Chatterbox's voice set — needs check vs `voice_presets.py`. Picker may offer voices the Chatterbox path cannot honor. |
| 5 | `tauri/ui/src/wizard/step0-intro.ts:522` | First-run contract grid: `["Voice", "local MOSS"]`. | **REAL & visible on the VERY FIRST screen.** New user's first impression names a deleted model. |
| 6 | `tauri/ui/src/library/api.ts:2524-2531` | `DEV_MODELS` mock row `id:"moss-tts", label:"MOSS TTS ONNX", env:"VIBEMIX_MOSS_TTS_DIR", path:".../MOSS-TTS-Nano-100M-ONNX"`. Used as the no-Tauri (vite/jsdom) fallback. | Dev/test only, but it sets the type contract the badge keys on. |
| 7 | `tauri/ui/src/library/api.ts:119,124,162` | The `LibraryModelInstallTarget` union includes `"moss"`; `LibraryModelAsset.id` typed `"clap"\|"moss-tts"\|"cue-detr"`. | Type contract still says moss-tts; chatterbox-voice falls through to the `\| string` escape, untyped. |
| 8 | `tauri/ui/src/library/api.ts:2234-2237, 2821` | `normalizeInstallTarget` accepts `"moss"`; `libraryModels("moss")` filters `model.id === "moss-tts"`. | The whole install seam is keyed on the dead id. |
| 9 | `tauri/ui/src/library/api.ts:2806-2808` | Doc comment: first-run downloads "CLAP + MOSS voice". | Stale. |
| 10 | `tauri/ui/src/shell/dj-vocab.ts:25` | Comment "The MOSS speech model, by what it does." (the VALUE is `"Voice"` — user-safe). | Comment-only; user sees "Voice", fine. Low priority. |
| 11 | `tauri/ui/src/shell/DesktopShell.ts:90` | Cmd+K search alias array includes `"moss"`. | Search keyword; harmless but stale. |
| 12 | `tauri/ui/src/library/model-setup.test.ts` (entire file) | Pins the first-run contract: "CLAP + MOSS are required"; `env: "VIBEMIX_MOSS_TTS_DIR"`, `rel_path: "MOSS-TTS-Nano-100M-ONNX/encoder_model.onnx"`. | **Test LOCKS the dead contract** — any fix to id/label must update this or CI blocks it. |
| 13 | `tauri/ui/src/library/api.test.ts:106,124,128-132,148` | Asserts model ids `["clap","moss-tts","cue-detr"]` + `install "moss"` shape. | Same: test pins the gap. |
| 14 | `tauri/ui/src/library/build.test.ts:155-268` | More MOSS fixtures (`sha256:"sha-moss"`, urls). | Test fixtures pin the gap. |

### The Rust ↔ Python install MISMATCH (dead button, end-to-end)
- `tauri/src-tauri/src/library_cmds.rs:331` — `normalize_model_install_target` accepts
  `"required" | "clap" | "moss" | "cue" | "all"` and at :190 pushes `--install <target>`.
- `src/vibemix/__main__.py:3255` — Python `--install` choices = `("clap", "chatterbox", "required", "cue", "all")`.
- **`moss` is accepted by Rust, passed to Python, and rejected by argparse** → the CLI exits
  non-zero. The frontend "install voice"/repair path is **dead on a real machine**: it can
  only ever fetch via `chatterbox` (which no UI surface ever requests).

### Voice status that DOES survive (the one half-working path)
- `src/vibemix/runtime/ws_bus.py:1444` emits `voice="muted" if voice_muted else "ok"` on
  `ipc.status.tick`.
- `tauri/ui/src/shell/VoiceReadinessBadge.ts:194-198` subscribes to `ipc.status.tick` and
  calls `setVoiceStatus(msg.payload.voice)`. **The MUTE-during-session signal works** (badge
  flips to warn "voice muted"). But READINESS (model present / missing / installable),
  which comes from `libraryModels()`, is dead because of the id mismatch. Net: the user can
  *sometimes* see "voice muted" mid-session, but **never** sees "voice ready" or "voice
  missing — install it" because that path resolves to `null`/hidden.

**REAL-vs-ASPIRATIONAL verdict (voice surface):** ASPIRATIONAL. The engine ships Chatterbox;
the whole UI voice surface (badge, settings label, wizard contract, install seam) is wired to
MOSS and is either hidden, mislabeled, or dead. This is a one-bug class — rename + reroute.

---

## PART 2 — WHY LEARN IS CONFUSING ("you cannot tell what to do")

### What IS there (REAL — give credit, don't rebuild)
- `tauri/ui/src/learn/learn-window.ts:324-343` — a **booth panel** with kicker "ready to
  practice", a recommended lesson title, a "your move" command line ("do one clean move and
  I'll confirm it."), a "start practice" primary button, and a "choose lesson" map button.
- `tauri/ui/src/learn/lesson/curriculum-meta.ts:100-157` — a real recommendation engine
  (`firstRecommendedLessonId` / `buildProgressEntries`) that picks the next lesson (in-progress
  → first-unlocked → L1.01) and marks it `is_recommended`.
- `tauri/ui/src/learn/learn-window.ts:381-393` — first paint renders an on-screen practice
  deck (DDJ-FLX4) so you are not staring at a void with no controller.
- `tauri/ui/src/learn/components/status-bar.ts:69-88` — controller/mirror status rail.
- So the "no onboarding / what do I do now" complaint is **partly stale**: the booth panel +
  recommended lesson + "your move" line is a legible CTA. The confusion is downstream.

### Why it STILL feels confusing / dead (REAL gaps)
1. **Silent lessons over "listen" instructions.** Practice/exemplar audio is gated to a tiny
   subset: `runtime.py:196-207` `_PRACTICE_AUDIO_DEMO_LESSONS = {L1.09, L1.10, L1.11, L1.12,
   L1.13, L1.15, L2.11, L2.13}` (8), plus L1.14 exemplar (`__main__.py:2515-2522`) and
   beatmatch L2.01/L2.02 (`runtime.py:166`, `two_deck_player.py`). That is ~12 of **38**
   lessons (`curriculum-meta.ts` has 38 rows incl. course headers). The other ~26 lessons run
   tutor text like "spot the breakdown by ear" / "listen for the cymbals" **over silence.**
   This is the single most disorienting thing: the app tells you to listen and there is
   nothing to hear.
2. **The tutor "voice" in Learn is TEXT-ONLY in the frontend.** `tauri/ui/src/learn/lesson/
   tutor-dock.ts:134-173` writes `payload.text` to DOM ghosts + an aria-live region; it
   carries `tts_marker` (line 38) but **never plays audio.** No `new Audio`, `AudioContext`,
   or `.play()` exists anywhere under `tauri/ui/src/learn/` (grep confirmed empty).
   - The backend DOES have a tutor-voice hook: `learn/runtime.py:2416-2439` (`_emit_tutor_speak`
     → `_tutor_speak_audio`) wired from `__main__.py:281-321` (`_build_learn_tutor_speak_audio`
     → `voice_tts.synthesize_pcm` → headphone playback) and passed at `__main__.py:2380`.
     So if Chatterbox is installed AND not muted, the tutor *can* speak on the audio bus — but
     (a) the UI shows no indication it's speaking or muted, and (b) on a fresh machine
     Chatterbox is absent → silent, with no on-screen "voice off" cue inside Learn.
3. **No voice/TTS status anywhere in Learn.** `status-bar.ts` and `lesson/hud.ts` have ZERO
   voice/tts/muted strings (grep confirmed). The `VoiceReadinessBadge` lives in the shell
   footer, not the Learn window — and it's hidden anyway (Part 1). So inside Learn you cannot
   tell whether the tutor is supposed to be talking, is muted, or the model is missing.
4. **No audio-on-drag / no scrubbing.** `learn/drag-control.ts` emits MIDI position frames
   (`AnalogDragFrame`) for the on-screen deck but produces **no audio feedback** on drag.
   `learn/waveform-display.ts` draws static peaks + cue regions + a playhead tick
   (`updatePlayhead`) but there is **no audio coupled to the waveform** — you cannot scrub it,
   and the playhead only moves when the backend two-deck player is running (the 12 audio
   lessons). For the other lessons the waveform host stays hidden (`waveform-display.ts:118`
   "Start hidden: with no audio loaded the strips are empty boxes").
5. **Empty-state is a dead end on no-controller.** `learn/components/empty-state.ts` ("no
   controller detected / plug one in to begin.") — but the booth panel already provides a
   screen-deck fallback, so which surface wins can read as inconsistent ("it says plug one in,
   but there's also a deck and a start button"). The empty-state copy doesn't mention the
   on-screen deck path.

**REAL-vs-ASPIRATIONAL verdict (Learn):** MIXED. Onboarding scaffold = REAL and decent. The
teaching *experience* = ASPIRATIONAL for the majority of lessons: the loop closes (text →
expected MIDI action → confirm) but the **sensory half (hear the music, hear the tutor, feel
the move) is dark for ~26/38 lessons**, which is precisely why it "feels like you can't tell
what to do" — you're told to listen and grade by ear with nothing playing.

---

## PART 3 — WHAT MUST BE BUILT / WIRED, AND WHERE (the UX lane queue)

Ordered by legibility-jump-per-effort.

### A. KILL THE MOSS→CHATTERBOX GAP (biggest single win, mostly rename+reroute)
1. **Rename the model id + label across the frontend** so the badge resolves.
   - `tauri/ui/src/shell/VoiceReadinessBadge.ts:42` — match `model.id === "chatterbox-voice"`
     (and accept the legacy `moss-tts` for back-compat, or just switch). Replace all "MOSS"
     copy (lines 3,54,62,68-101) with "Voice" (use `DJ_VOCAB.voiceModel` from `dj-vocab.ts`).
   - `tauri/ui/src/settings/SettingsDrawer.ts:945` — drop `sub:"MOSS"` (use "Voice" or nothing).
   - `tauri/ui/src/wizard/step0-intro.ts:522` — `["Voice", "on-device"]` (no model name; the
     CLAUDE.md partner-copy rule and `dj-vocab.ts` say no model filenames in user copy).
   - `tauri/ui/src/library/api.ts:124,162,2524-2531,2806-2808` — retype id to
     `"chatterbox-voice"`, update DEV_MODELS row + doc comment.
   - `tauri/ui/src/shell/dj-vocab.ts:25` + `DesktopShell.ts:90` — update comment/alias.
2. **Fix the install target end-to-end** so the "install/repair voice" button works.
   - Either add `"moss"`→`"chatterbox"` remap in `library_cmds.rs:331`/`:190`, OR change the
     frontend target token to `"chatterbox"` and add it to `library_cmds.rs` accept-list +
     `api.ts` union. Python already supports `--install chatterbox` (`__main__.py:3255`).
   - Backend row is `installable: False` (`__main__.py:7693`) — decide: flip to installable so
     the UI can fetch (Chatterbox is a HF snapshot, `install_chatterbox_model()` exists), or
     keep manual and have the UI say "voice download in app setup" not a dead repair button.
3. **Update the test pins** (they currently LOCK the dead contract):
   `model-setup.test.ts`, `api.test.ts:106-148`, `build.test.ts:155-268`. Re-key to
   `chatterbox-voice` so a correct fix passes CI instead of being blocked by it.

### B. MAKE VOICE STATUS VISIBLE INSIDE LEARN (small, high legibility)
4. Surface a voice chip in the Learn window (the tutor's mouth). The signal already arrives:
   `ipc.status.tick.voice` (`ws_bus.py:1444`). Add a tiny readout in `learn/components/
   status-bar.ts` (or the tutor-dock header) that shows "voice on / muted / installing" so a
   learner knows whether the tutor is supposed to be heard. Reuse `VoiceReadinessBadge`'s
   `RuntimeVoiceStatus` type. (Today Learn has zero voice status — confirmed.)

### C. CLOSE THE SILENT-LESSON GAP (the real teaching fix — larger)
5. Extend practice/exemplar audio beyond the 12 wired lessons, OR make the silent lessons
   honest: when a lesson's tutor copy says "listen" but no audio is wired for that lesson_id
   (`runtime.py:196` set), the tutor-dock should NOT pretend. Either (a) play a short exemplar
   for every "listen/spot/ear" lesson, or (b) the frontend shows a "no audio for this drill"
   affordance instead of an instruction to listen to silence. The frontend wire exists
   (`ipc.learn.exemplar_play` → `showExemplarPlay`, `learn-window.ts:477-491`) — it's the
   backend lesson coverage that's thin.
6. Couple the waveform to audio: when an exemplar/practice player is active, the playhead +
   peaks already update (`waveform-display.ts:updatePlayhead`). Add audio-on-drag for the
   on-screen deck (`drag-control.ts` emits frames; a small local scrub-sample on drag would
   make the deck feel alive). Lower priority than A/B.

### D. ONBOARDING POLISH (cheap)
7. Make the empty-state and booth panel agree: `empty-state.ts` should mention "or use the
   on-screen deck" so the no-controller path doesn't read as a dead end.

---

## RELEVANCE TO THE AUTONOMOUS QA LOOP (tonight)

- The MOSS/Chatterbox UI gap is a **product/UX bug**, not a QA-harness blocker per se — the
  harness can still launch the app and capture Sven's live-set utterances regardless of Learn.
- BUT two things matter for the harness's UX-legibility judge:
  - The harness should **assert the voice readiness badge is visible and correctly named** —
    right now it would (correctly) screenshot a *hidden* badge, which the judge should flag as
    a UX failure (no voice status shown). That's a useful signal, not a harness blocker.
  - Learn is **out of scope for a 3-hour recorded-DJ-set replay** (Learn is controller/MIDI +
    practice-deck driven, not master-audio driven). The QA loop's set replay exercises Sven +
    Debrief, not the Learn teaching loop. So Learn does NOT block tonight's loop.

---

## FILE INVENTORY (read for this map)
- `tauri/ui/src/learn/learn-window.ts`, `lesson/tutor-dock.ts`, `lesson/curriculum-meta.ts`,
  `components/status-bar.ts`, `components/empty-state.ts`, `drag-control.ts`,
  `waveform-display.ts`
- `tauri/ui/src/shell/VoiceReadinessBadge.ts`, `shell/dj-vocab.ts`, `shell/DesktopShell.ts`
- `tauri/ui/src/settings/SettingsDrawer.ts`, `tauri/ui/src/wizard/step0-intro.ts`
- `tauri/ui/src/library/api.ts` (+ `model-setup.test.ts`, `api.test.ts`, `build.test.ts`)
- `tauri/ui/src/ipc/messages.ts`, `messages.schema.json`
- `src/vibemix/learn/runtime.py`, `two_deck_player.py`, `__main__.py` (281-321, 2329-2540, 7670-7709, 3244-3262)
- `src/vibemix/agent/tts_chain.py`, `chatterbox_tts.py` (present), `local_tts.py` (DELETED)
- `src/vibemix/library/model_assets.py`, `runtime/ws_bus.py:1444`
- `tauri/src-tauri/src/library_cmds.rs` (183-333, 1265-1287)
