# Phase 53: Controller Live + Graceful Fallback - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded — live-source findings injected directly (autonomous `fully`). Planning works against the live `src/vibemix/midi/` tree at HEAD, not guesses. Independent of Phase 52 (depends only on Phase 51's running app).

<domain>
## Phase Boundary

Prove the **DDJ-FLX4 MIDI path is live** during a real session — controller moves (jogs, faders, knobs, pads) are ingested and reach `ControllerState` in real time — AND the app **degrades cleanly when the controller is unplugged** (and rebinds on replug), with no crash, no stale moves, no hang. Covers **BRINGUP-03**.

**Out of this phase:** audio path / features / genre (Phase 52), the reaction modes that consume controller moves (hype 54 / feedback 55), perf/mascot-reacts-to-MIDI (56). This phase makes the **controller input seam** trustworthy + resilient.
</domain>

<decisions>
## Implementation Decisions (Claude's discretion, autonomous `fully`)

- **Graceful fallback is the engineering core (the part that's automatable).** `midi/watcher.py::port_watcher_task` already polls ports and emits `('connected', port)` / `('disconnected', port)`. Harden + TEST the disconnect path: on unplug mid-session, `ControllerState` must degrade cleanly — no stale "recent moves" leaking into reactions, no exception on the daemon thread, the session keeps running on audio alone. On replug, the watcher must rebind via `registry.find_mapping` (FLX4 re-recognized). Add deterministic tests that simulate disconnect→reconnect mid-session and assert: no crash, state cleared/degraded, rebind works.
- **FLX4 live decode, proven deterministically.** The FLX4 profile + listener thread + `controller_state` wiring already exist (see code context). Engineering proves the decode end-to-end with a **synthetic FLX4 MIDI stream** (feed real CC/note messages matching the FLX4 profile → assert `ControllerState` reflects the right deck/knob/fader/pad). The real hardware plug-in + play-a-set confirmation is **Kaan-action**.
- **Resolve the two-mapping-dir question (flag for planner, confirm before asserting).** There are TWO map dirs: `src/vibemix/midi/profiles/*.json` (port-name `ControllerProfile`s read by `registry.py` via `profile.load_profile`/`list_profiles`) AND `src/vibemix/midi/controllers/*.json` (separate map files, likely read by `map_loader.py`). FLX4 appears in BOTH (`pioneer_ddj_flx4.json` + `controllers/ddj-flx4.json`). The planner must confirm which is canonical for **live binding** vs which is the **MIDI-CC map**, and ensure the live path uses the right one — do NOT assume; verify against `registry.py` + `map_loader.py` + `__main__` wiring.
- **Unknown-controller path stays graceful.** `registry.find_mapping_or_generic` binds unknown ports to a generic Coach mapping — confirm an unknown/unmapped controller doesn't crash and gets the generic profile (this is part of "graceful fallback").
</decisions>

<code_context>
## Existing Code Insights (verified live this session)

- **Curated controller library (~10+):** `midi/profiles/` has pioneer_ddj_flx4, flx6, flx10, ddj_1000, ddj_400, sx3, xdj_rx3, numark_party_mix_live, hercules_inpulse_300/500. `midi/controllers/` has ddj-flx4, ddj-400, ddj-200, kontrol-s2/s4, mc-6000/7000, mixtrack-pro-fx, mixtrack-platinum-fx. (CLAUDE.md's "~10 popular controllers mapped out of box" = this set.)
- **Registry:** `midi/registry.py::find_mapping(port_name)` — case-insensitive substring match against each profile's `port_name_hints`; `find_mapping_or_generic` falls back to a generic profile for unknown ports.
- **Hotplug/fallback:** `midi/watcher.py::port_watcher_task(on_change, stop_event, ...)` — polling sweep diffing seen ports; emits `('connected'|'disconnected', port)`. First sweep emits `connected` for everything present. This is the unplug-detection seam.
- **Live wiring (`__main__.py`):** `MidiMacOS()` (line ~517); MIDI daemon thread started AFTER `session.start` (~845-847, mirrors v4:2039-2043); `midi_macos.controller_state` passed to coach + event detector (~857-867); `midi_stop.set()` on shutdown (~916). Windows path: `platform/_midi_windows.py`.
- **State:** `midi/state.py` (`ControllerState` — live decode + recent-moves ring), `midi/generic.py` (generic profile), `midi/map_loader.py` (map loading), `midi/profile.py` (`ControllerProfile` dataclass + loader), `midi/schema.json` (profile schema).
- **Existing tests:** `tests/midi/test_profiles_all_controllers.py` (every curated profile loads/validates), `tests/midi/test_sniff_controller.py`, `tests/wizard/test_step3_controller.py`, `tests/test_midi_macos.py` / `_common.py` / `_windows.py`. Plenty of test surface to extend — find the watcher/disconnect coverage gap rather than re-testing profile loading.
</code_context>

<specifics>
## Specific Ideas

- **Disconnect/reconnect test:** drive `port_watcher_task` with a fake port-list provider that returns [FLX4] then [] then [FLX4]; assert the `on_change` callback fires `disconnected` then `connected`, and that the bound `ControllerState` clears its recent-moves ring on disconnect and rebinds on reconnect — all without raising.
- **Synthetic FLX4 decode test:** feed a sequence of FLX4 CC/note messages (from the FLX4 profile's map) into the decode path; assert `ControllerState` reflects deck select, crossfader, tempo, jog, pad hits correctly.
- **Live-drive recipe (Kaan-action):** plug the FLX4, start a session, move jog/crossfader/knobs → confirm moves register on the bus/UI; mid-set, unplug the FLX4 → confirm the app keeps running on audio alone with no crash; replug → confirm it rebinds.
</specifics>

<deferred>
## Deferred Ideas (Kaan-action — real hardware, autonomous carveout)

- The real **FLX4 plug-in + live set + mid-set unplug/replug on Kaan's Mac** is the true BRINGUP-03 sign-off (his hands on the controller). Engineering ships: hardened watcher disconnect path + deterministic disconnect/reconnect tests + synthetic-FLX4 decode tests + the live-drive recipe. The physical-hardware confirmation rides the live-drive / Kaan-hands surface (per [[project_phase_16_kaan_dj_testing]]).
- Validating all ~10 curated controllers on real hardware is out of scope — FLX4 (Kaan's) is the one real-hardware target; the rest are covered by profile-load/validate tests only.
</deferred>
