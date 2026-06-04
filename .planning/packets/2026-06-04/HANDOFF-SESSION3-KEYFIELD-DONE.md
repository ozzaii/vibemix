# Session-3 Handoff — KEYFIELD shipped; MASKLEARN + CUETRAY cross-session-blocked (2026-06-04)

Branch: `ux-redesign-impeccable` (ONE shared tree, 3+ concurrent sessions — VERY hot;
HEAD moved 4× during this lane). Continues `HANDOFF-SESSION2-FONTS-NEXTLANES.md` +
`NEXT-LANE-BLUEPRINTS.md`. Read those for the lane specs.

## ✅ DONE — KEYFIELD (DEMOCRATIZATION #1) — `8c6a7b6e`
In-GUI Gemini-key field + DIRECT/PROXY brain toggle. Kaan's named #1 deliverable.
Built, fully green, committed, **proven by-eye live** (`?dev=session-mock` → gear →
SETTINGS → BRAIN group under PERSONA: DIRECT lit rose, masked `AIza…` field, recessive
disabled SAVE, Geist type, zero gold). 16 files, atomic.

- **IPC DEF (Lane-A owned, frozen):** `ipc.settings.set_brain {mode, gemini_api_key?}` +
  `ipc.settings.brain_ack {ok, mode, key_set, restart_required, error}` (no secret in ack).
  Schema + Python wrapper mirror (`ui_bus/messages.py`) + codegen (`messages.ts` /
  `validator.generated.mjs`) + `check_ipc_schema` example all landed together → count
  parity green (79 oneOf == 79 wrappers). 5 hardcoded count-ledger tests bumped 77→79
  (test_messages_schema ×2, test_recordings_messages, test_mood_change_envelope; +definitions 80→82).
- **Never-log guard:** `client.ts::redactForLog()` — the request-log copy of `set_brain`
  shows `gemini_api_key:"<redacted>"`; wire payload carries the real key. Pinned by
  `tests/ipc/client-redaction.spec.ts`.
- **UI:** `src/settings/components/brain-group.ts` (mirrors PerformanceGroup) — optimistic
  rocker, write-only masked input (never seeded, cleared on good ack), Save, one-line state
  readout + "Restart now" affordance. Mode held module-local (§3.4 fallback; no `llm_mode`
  field added — cold drawer shows DIRECT until first toggle).
- **Gates:** tsc + 1510 vitest + vite build green; check_ipc_schema parity green; 204 ui_bus
  pytest green.
- **PENDING Lane B (no test reddens for it):** the Python persist handler
  `register_handler("ipc.settings.set_brain", _on_settings_set_brain)` in
  `runtime/session_loop.py` → `SettingsApplier.apply_brain(mode, gemini_api_key)` writes
  `GEMINI_API_KEY` → `app_data_dir()/.env` (chmod 600) OR keychain + `ConfigStore.llm_mode`,
  emits the ack (NO secret). End-to-end "paste key → restart → co-host speaks" (SHIP DoD #4)
  is the joint A+B proof. **The key is never logged/echoed/committed — fake `AIza-test-fake`
  in all tests.**

## ⛔ BLOCKED — MASKLEARN (unblock = ONE sibling commit)
Everything is ready EXCEPT the contested file. The Python emit side
(`learn/runtime.py:2213/2686`) is **committed/stable** now. The blocker:
`tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts` is **uncommitted** (a sibling is
mid-flight, has across 4 HEAD moves) and rewrites the test to assert the EXACT Tauri
subscription set. MASKLEARN's **mandatory Wire #3** (`LEARN_INBOUND_TYPES += "ipc.learn.teaching_focus"`
in `learn/ws-client.ts`) makes the bridge subscribe to one more type → that exact-set test
fails → I'd have to edit the sibling's dirty file = clobber. `ws-client.ts` itself is clean,
but editing it alone breaks both the committed (`toHaveBeenCalledTimes(12)`) and the dirty
(exact-set) test.
- **UNBLOCK:** the moment that spec commits, add `teaching_focus` to BOTH `LEARN_INBOUND_TYPES`
  and the committed `EXPECTED_TAURI_SUBSCRIPTIONS`, then build the rest (all my island, no
  collision): `learn/organism-stage.ts` (slim renderer reusing ParticleOrganism/FocusLayer),
  the canvas mount + local `setControlRect` feed + `teaching_focus` window-event subscribe in
  `learn-window.ts`, `.learn-stage__organism` CSS, the 4 TDD tests. Spec:
  `NEXT-LANE-BLUEPRINT-masklearn.md`. Mask stays VISUALLY AS-IS (Kaan-locked).

## ⛔ BLOCKED — CUETRAY (unblock = Lane B exposes the cue command + DTO passthrough)
The frontend is buildable, but it can't ship **green + honest** solo:
- Lane B's `library/cue_landing.py` EXISTS but its `CueSet` carries **no** `summary` /
  `policy` floors / `detected_target` — exactly the fields the ConfidenceMeter band + the
  honesty line need (blueprint §6.1 says B must pass `SmartCueProposalSummary` floors + summary
  + `detected_target` through the command JSON).
- **No `library_land_cues` Rust command** in `main.rs::generate_handler!`. Writing the real
  `invoke("library_land_cues")` in `api.ts` forces a `library.outbound` entry → reddens the
  `keeps contracted Tauri commands registered in Rust` vitest, which I **cannot green solo**
  (`library_cmds.rs`/`main.rs` is Lane B's island; a stub would be fake/dark).
- **UNBLOCK:** Lane B (a) adds `library_propose_cues` (or folds into `library_cue_folder`)
  returning a `CueSet[]` whose JSON includes the summary floors + `detected_target`, and
  (b) registers `library_land_cues` in `main.rs`. Then build per `NEXT-LANE-BLUEPRINT-cuetray.md`
  (DTO is a 1:1 projection of `cue_landing.LandedCue`/`SmartCue` — snake_case, keep casing).

## SHARED-TREE LAW (unchanged, load-bearing — tree is HOT)
`git add <exact paths>` → review `git diff --cached --name-only` SEPARATELY → scoped
`git commit -s -F - -- <paths>`. NEVER `-A`. Commit the instant green+proven. Re-read any
shared file (contract.ts, ws-client.ts) right before editing — HEAD moves under you.
Git `Kaan Özkan <rahipdotaci@gmail.com>`; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
