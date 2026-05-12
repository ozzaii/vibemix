# Phase 13 — Manual Smoke Checklist (Plan 13-08)

**Phase:** 13 — 3D Mascot Screen Overlay
**Plan:** 13-08 — Verification suite + manual smoke
**Generated:** 2026-05-12
**Owner:** Kaan (macOS rig: DDJ-FLX4 + djay Pro + BlackHole 2ch + nowplaying-cli)
**Estimated time:** 30-45 minutes (one rig session)

---

## How to use this checklist

1. Build + run the app:
   ```bash
   cd tauri/ui && npm run build
   cd ../src-tauri && cargo run
   ```
   (Or use a signed dev binary if Phase 18 has shipped one.)

2. Open this file in a side window. For each numbered item:
   - **Tick** `[x]` if pass
   - **Cross** `[F]` if fail, append a one-line observation
   - **Skip** `[S]` if not applicable on this run (e.g., MIDI not plugged), with a reason

3. For any failure (`[F]`): file an item in
   `.planning/phases/13-3d-mascot-overlay/deferred-items.md` under
   "From Plan 13-08 manual smoke" so Phase 14 polish loop can pick it up.

4. After completing all 30: update `13-VERIFICATION.md` Aggregate Status with the
   final pass count (X/30 manual items, Y/6 ROADMAP criteria fully done) and
   flip `status: human_needed` → `status: done` in the frontmatter once each
   ROADMAP criterion has both auto-PASS + manual-PASS.

5. Resume the orchestrator with: `approved — X/30 manual items, Y/6 criteria done. Deferred: <list or "none">.`

---

## A. Window + Overlay (criterion #1) — items 1-6

- [ ] **1.** Launch app → mascot window visible on primary monitor (default position top-right; 300×400 default size).
- [ ] **2.** Drag mascot window to bottom-left. Close + relaunch → window reopens at the new bottom-left position (geometry persists via `write_mascot_window_state` debounce + `config.json`).
- [ ] **3.** Switch to a different macOS Space (Ctrl+Right Arrow or Mission Control) → mascot remains visible on the new Space (`visible_on_all_workspaces: true` honoured).
- [ ] **4.** In the Phase 12 Settings drawer, toggle "click-through" ON → click on the mascot — the click passes through to the app underneath (e.g., Finder window receives the click). Toggle OFF → mascot becomes draggable again.
- [ ] **5.** Close the main session window with Cmd+W → the app keeps running (mascot still visible, tray icon still present). The CloseRequested override in 13-02 is doing its job. Only the tray-menu **Quit** kills the process.
- [ ] **6.** Click the tray icon menu → "Quit vibemix" → both windows close cleanly, no stale tray icon.

---

## B. Animation Library (criterion #2) — items 7-16

- [ ] **7.** Boot mascot → `idle_breathe` plays continuously, **no T-pose flash** on the first frame (Plan 13-04 boot state contract).
- [ ] **8.** Manual fire via tray menu's "Manual fire" item (or the Cmd+Shift+M-equivalent hotkey if wired) → `react_yes` plays cleanly, then returns to idle.
- [ ] **9.** Start a real drop in djay Pro (load a track with a known build → drop) → mascot enters `dance_hard` on the drop (within 1 bar at conf ≥ 0.6, or immediately if conf < 0.6).
- [ ] **10.** When the drop ends and `phase` transitions to "groove" → mascot returns to `idle_bop_to_beat_energetic` smoothly (no T-pose between dance and idle).
- [ ] **11.** Trigger an AI reaction (manual fire, or wait for an organic event) → mascot enters `talk_loop` cleanly; no T-pose between previous state and talk_loop.
- [ ] **12.** AI reply ends → mascot plays `react_yes` then returns to prior idle/dance state.
- [ ] **13.** Switch decks in djay Pro (TRACK_CHANGE event) → mascot plays `react_surprised` then settles into `idle_bop_to_beat_energetic`.
- [ ] **14.** Leave the mascot idle for 5+ minutes (no AI events, no controller moves) → mascot transitions to `sleep` clip per `tickIdleTimeout` 5-min default (CONTEXT Open Q 5).
- [ ] **15.** Wake the mascot with any controller move or AI event → mascot smoothly exits sleep back to `idle_breathe` (no T-pose).
- [ ] **16.** Simulate a sidecar restart (kill the Python process, wait 5s for the WS reconnect-backoff, restart) → mascot freezes during disconnect, resumes on reconnect; if a glitch event fires, `react_glitch` plays.

---

## C. Crossfade Quality (criterion #3) — items 17-21

- [ ] **17.** Every transition in items #7-16 uses a visible crossfade — **no hard pose-snap** between clips. Confirm by eye on at least 5 random transitions.
- [ ] **18.** Mood swap (hype-man → teacher in Settings) — `puff_particle` is visible masking the rig pose change; mood swap is NOT a hard cut.
- [ ] **19.** AnimationMixer blend duration feels right — not too snappy (< 200ms blends look like cuts), not too laggy (> 400ms blends feel mushy). Target = 300ms per CONTEXT Area 3.
- [ ] **20.** No visible foot-sliding during locomotion-style clips (`idle_bop_to_beat`, `dance_hard`).
- [ ] **21.** No rigging artifacts: no elbow flips, no weight-popping at the shoulders, no neck rotation snaps on any transition.

---

## D. Beat-Lock (criterion #4) — items 22-25

- [ ] **22.** Load a clean 128 BPM track with strong downbeats; trigger a drop → `dance_hard` enters **on the bar boundary** (count "1 2 3 4" by ear; clip change lands on the "1"). Plan 13-08 fixture `beat_locked_entry_at_high_confidence` already pins the math; this is the audible check.
- [ ] **23.** Force `bpm_confidence < 0.6` (low-confidence track — e.g., ambient intro, drum-machine-only loop) → `dance_hard` enters **immediately** when the PHASE→drop event fires (no beat-lock wait). Plan 13-08 fixture `low_confidence_immediate_switch` pins the math.
- [ ] **24.** Half-tempo track (~70 BPM source that the BPM detector half-corrects to ~140) → clip change lands on the **corrected** bar boundary (Phase 6 half-correction wires into the dispatcher via the snapshot's bpm field).
- [ ] **25.** Track without strong downbeats (disco intro, no clear "1") → clip changes immediately on PHASE event; mascot doesn't stall waiting for a downbeat that never lands.

---

## E. Event Mapping (criterion #5) — items 26-28

- [ ] **26.** Open the mascot window with `?dev=mascot-mock` URL param (DEV-only — Plan 13-06 ships a 10-event cycling harness). Observe each of the 10 events fire in sequence (every 3s); each produces the documented state from the dispatcher's taxonomy table.
- [ ] **27.** During a real session, when the AI starts talking mid-drop → mascot **interrupts** the dance clip and switches to `talk_loop` (priority 80 > dance 40). When AI finishes → mascot plays `react_yes` then returns to dance/idle.
- [ ] **28.** Trigger a mood swap (Settings drawer → mood pill) **mid-drop** → `puff_particle` fires; dance pool draws from the new mood's clip selection after the puff (cross-reference `MOOD_PROFILES[<new>].dance_pool`).

---

## F. Mood Swap (criterion #6) — items 29-30

- [ ] **29.** Open Settings drawer → switch mood: `hype-man` → `teacher` → `coach` (three successive swaps).
  - For each swap: particle puff visible (~500ms lifetime), rig pose change masked by puff.
  - Idle pool clearly differs between moods: hype-man uses `idle_bop_to_beat_energetic`; teacher uses `idle_bop_to_beat_mellow`; coach uses `idle_breathe`.
  - Mood-driven lighting shifts (warmer / cooler ambient + key).
- [ ] **30.** After each mood swap, trigger an AI reaction:
  - Voice (Gemini TTS speaker) changes within 1-2 reactions of the mood swap (sidecar's `MusicState.mood` is the canonical writer).
  - Prompt vocabulary visibly different in the transcript window: hype-man hyped, teacher explanatory, coach reflective.

---

## Aggregate

After completing, update this section in-place:

- **Pass count:** ___ / 30 items
- **Criteria fully done (auto + manual):** ___ / 6
- **Items deferred to Phase 14 polish:** ___ (list IDs)
- **Items still failing:** ___ (list IDs + observations)
- **Date completed:** YYYY-MM-DD

---

## Resume signal to orchestrator

After completing the checklist, resume the GSD orchestrator with:

```
approved — X/30 manual items, Y/6 criteria done. Deferred: [list or "none"].
```

The orchestrator will then close Phase 13 in STATE.md + ROADMAP.md and advance to Phase 14.
