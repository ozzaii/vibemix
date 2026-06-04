# SHIP-WIRE-GOALS — re-rail the sessions onto the real ship blockers (2026-06-04)

W1 (FRONTEND-WIRING-EXIT-MAP) + W2 (BACKEND-WIRING-EXIT-MAP) landed. W3 kept failing, so this doc is the organizer's direct synthesis: the four locked decisions + the two exit-maps + the observed lane state, turned into ONE bounded ship-goal per session. Each goal ends at a concrete by-ear/by-eye DoD so a session stops rabbit-holing and converges.

## ⛔ STOP PROTOCOL — read FIRST (the sessions are in an infinite goal-loop)

ROOT CAUSE: the autonomous goals carry a DoD the agent CANNOT self-satisfy — "sustained driven live set", "by-ear", "human ear-pass". So each loop keeps the goal "active" forever and rabbit-holes into micro-optimizations (e.g. Sven re-tuning prompts at 3.5h). Paste this STOP CONDITION into every looping session; it OVERRIDES any "keep the goal active" text in their spec:

> STOP CONDITION (overrides any "keep goal active" / "final validation gate" text): do exactly ONE bounded piece, commit it surgically when it is green + grounding-review-clean, then **HALT and report — end the loop**. Do NOT keep the goal active waiting for a live / by-ear / driven-set / hardware proof: that gate is KAAN's, not yours. If you finish your one piece, STOP. If a sibling's uncommitted file blocks you, STOP and report the blocker — do not spin or clobber. The live/ear/DMG proof is owned by Kaan and the organizer, never self-certified by a loop.

The by-ear / live-set / DMG gates are EXTERNAL (Kaan + organizer). An autonomous loop must treat them as out-of-scope and exit, not chase them. Bounded code piece → commit → STOP → report. One piece per session, then quiesce.

## Locked decisions (Kaan, do not re-open)
1. **Voice = ONE identity, the zero-shot pranker Chatterbox.** Mac = mlx-audio (built). Windows = a GPU backend BUILD (prefer torch-free ONNX-DirectML, else torch+CUDA, Windows packaging only). **MOSS NUKED** (engine/default/floor gone). No compatible GPU → voiceless + honest banner (transcript still shows). Both platforms ship.
2. **Brain access default = hosted Bravoh proxy** (fresh user pastes nothing). In-GUI Gemini-key field = advanced BYO. Needs the proxy live + credits on `ssh altidus` (organizer owns).
3. **Streak = full Technologic robot voice in v1** — but rebind the streak to a cited EXECUTED transition first (kill the self-applauding suggestion-grade count) before it speaks.
4. **Start gate + model lifecycle = SHIP-CRITICAL** ("when we pre-ship this is the only thing"): no heavy model resident at idle; silent background pre-warm up to start; a "Start/Başlat" button activates capture + reactions; Stop/idle releases the models.

## Lane state (observed)
- **Frontend (Claude, KEYFIELD)**: democratization #1 SHIPPED `8c6a7b6e`. Idle/blocked on MASKLEARN (sibling ws-test uncommitted) + CUETRAY (Lane B CueSet half-built).
- **Library Codex**: cue-landing + Viber-cue→pill + build-set carriers SHIPPED (`426af345`, `2b5034f5`). Dirty `__main__.py`/`codex_curate.py` mid-flight.
- **Learn Codex**: harmonic-cite + proof SHIPPED (`47982741`, `d62378bb`). Fused beatmatch loop progressing well — NOT confused.
- **Sven Codex**: kick-density coach + scaffold leaks SHIPPED (`c15f92a3`, `845d2023`). NOW rabbit-holing citation-lint-parity micro-opt at 3.5h. The prompt axis is plateaued (bench-proven). REDIRECT.
- The AIRA/WhatsApp session is a different project (`~/projects/agentanalytics`) — not part of this ship.

## Re-rail — one bounded goal per session

### SVEN Codex → STOP prompt micro-opt, take the VOICE WIRING (the #1 founder concern, unowned)
```
/goal SHIP-WIRE — VOICE: nuke MOSS, make the zero-shot pranker Chatterbox the only cohost voice,
reachable on a normal/packaged launch. The prompt axis is done (kick-density + scaffold landed +
bench-proven) — do NOT keep tuning prompts. New target:
(1) Rip MOSS out as engine/default/floor across the tree (agent/tts_chain.py, agent/local_tts.py
MossLocalTTS, voice_presets, runtime/config_store, __main__.py, ui_bus, learn/runtime,
llm/_router_config, debrief, library/cost). No MOSS, no cloud TTS, ever.
(2) Make the engine reachable on a packaged launch (launchd strips env, the "always MOSS" root
cause): add config_store.tts_engine + os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg) at
__main__.py:1420 (mirror _apply_deck_audio_config_to_env). Default = chatterbox.
(3) Bundle the production ref: source ~/Downloads/Prank_L4_t20 (1).wav, music-stripped, placed at
~/.cache/vibemix/cohost_voice_ref.wav AND into the app/DMG. Bundle mlx-audio + base
chatterbox-turbo-8bit + clear licensing.
(4) No compatible GPU -> voiceless with an honest banner (transcript still shows), never a MOSS floor.
(Windows GPU backend = a separate BUILD lane, NOT here.)
ISLAND: src/vibemix/agent/** + runtime/config_store.py + __main__.py(env-seed only) + the specs.
PROOF (by-ear, not test-green): on a packaged-style launch reading config.json (NOT env), the cohost
speaks in the pranker voice; grep shows MOSS gone; grounding-review clean.
SHARED LAW: one tree; git add <exact paths> NEVER -A; verify git diff --cached; socket 8765 one
(pkill before probe); commit -s Kaan Özkan <rahipdotaci@gmail.com>; commit each piece green+proven.
```

### FRONTEND Claude (KEYFIELD) → while MASKLEARN/CUETRAY blocked, take the START GATE (ship-critical #4)
```
/goal SHIP-WIRE — START GATE + model lifecycle (Kaan: "when we pre-ship this is the only thing").
Today the session auto-runs and heavy models sit resident at idle (strains the machine). Wire:
(1) A "Start / Başlat" control in the session UI that activates capture + reactions (idle before it).
(2) A Stop/idle path that releases the heavy models.
(3) The IPC for start/stop (you own the schema): ipc.session.start / ipc.session.stop (+ the Python
handler name for the backend lane). Optimistic repaint per the frontend convention.
The silent pre-warm hook (load models in the background up to Start) is the backend's half — name the
handler; backend implements.
ISLAND: tauri/ui/src/** + the IPC schema + ui_bus. NOT other src/vibemix python.
PROOF (by-eye, real app ?dev=session-mock): app idle = no Start pressed = no reactions; pressing Start
flips to active; the control renders on-brand, no slop.
SHARED LAW: one tree; git add <exact paths> NEVER -A; IPC = Frontend-only; socket 8765 one; commit -s
Kaan Özkan <rahipdotaci@gmail.com>; prove by-eye, test-passing-but-dark = 0.
```

### LIBRARY Codex → unblock CUETRAY (so the Frontend can land the Cue Tray)
```
/goal SHIP-WIRE — unblock CUETRAY. The Frontend Cue Tray is blocked because cue_landing.CueSet does
not carry the fields the UI needs and there is no Rust land command. Add, in the library/intel island:
(1) summary / detected_target / policy-floor fields to cue_landing.CueSet (confidence banded to the
policy floors, provenance AUTO vs DJ preserved).
(2) the library_land_cues Tauri command in tauri/src-tauri/src/library_cmds.rs (+ register in main.rs)
that calls cue_landing.land() — non-destructive, VM-prefixed, one-consent.
(3) a CLI verb if missing, so it is driveable headless.
Then continue the build-set carrier work you have mid-flight (commit the dirty __main__/codex_curate
surgically first).
ISLAND: src/vibemix/library/** + intel/** + tauri/src-tauri/src/library_cmds.rs + main.rs. NOT the IPC
schema (Frontend owns it), NOT tauri/ui.
PROOF: pyrekordbox re-parse biconditional + a CueSet fixture the Frontend can render; zero DB writes.
SHARED LAW: one tree; git add <exact paths> NEVER -A; socket 8765 one; commit -s Kaan Özkan
<rahipdotaci@gmail.com>; commit each piece green+proven.
```

### LEARN Codex → finish the fused beatmatch loop to its kill-criterion (NOT confused, just bound it)
```
/goal SHIP-WIRE — close the fused beatmatch loop to the kill-criterion and stop. A beginner on L2.01
hears the kicks drift+lock, Sven SAYS it, the lock-meter needle centers, [ev:BEATMATCH_GRADED@t]
resolves on the ws bus. You already cite harmonic practice; finish audible-decks -> grade -> IPC ->
HUD + tutor voice, honoring A1 (practice audio NEVER over a live set). When the kill-criterion is
proven by-bus, STOP (do not keep adding lessons).
ISLAND: src/vibemix/learn/** (+ audio/miniplayer). PROOF: by-bus L2.01 kill-criterion on the live
sidecar. SHARED LAW as above.
```

### ORGANIZER (me) → the hosted-proxy keystone on `ssh altidus` (Kaan opened it for ANYTHING)
Verify read-first: is `/register` live, is a valid Gemini key + credits configured on the Bravoh
proxy (`/var/www/bravoh-clean-backend`, PM2 `bravoh-clean-api-0/1`)? Then make democratization-default
real: a fresh app with no key reaches the brain through the proxy. Report state, propose/apply the fix.
Plus coordinate keystone/packaging (route-doctor determinism + a fresh signed DMG at HEAD) — unowned.

## What ends the confusion
Every session now has ONE bounded target that ends at a by-ear/by-eye DoD. Sven stops prompt-tuning and
takes the voice (the actual #1 concern). Frontend takes the ship-critical Start gate instead of idling.
Library unblocks CUETRAY. Learn converges on the kill-criterion. Organizer takes the proxy keystone.
