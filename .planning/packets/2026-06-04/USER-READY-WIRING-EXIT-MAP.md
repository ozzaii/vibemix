# USER-READY WIRING EXIT-MAP — the integration JOIN (2026-06-04)

The master integration exit-path that lands vibemix at a fully-wired, user-ready state. This is the JOIN of
`FRONTEND-WIRING-EXIT-MAP.md` (W1) + `BACKEND-WIRING-EXIT-MAP.md` (W2) + the ship packets
(`SHIP-DRIVE.md`, `SHIP-FINISH-PLAN.md`, `SHIP-READINESS-2026-06-04.md`, `HANDOFF-SESSION3-KEYFIELD-DONE.md`)
+ the four Kaan-locked decisions in `SHIP-WIRE-GOALS-RERAIL.md`. It does NOT re-list the FE/BE wires — it owns
the SEAMS between them: the cross-engine handshakes, the conflicts the two single-lane maps each saw from one
side, and the fresh-user path neither map traces end-to-end.

Pinned at HEAD `16a547dd` (read-only pass; sidecar not launched). Tier language is load-bearing and never
conflated: **SRC** (green tests on current source) != **PKG** (in the signed DMG built at HEAD) != **LIVE**
(a real user runs the app and HEARS/SEES a grounded result). `test-passing-but-dark = 0`. The tree is hot;
confirm every line anchor before editing.

The four locked decisions that re-aim both maps (verbatim from `SHIP-WIRE-GOALS-RERAIL.md`):
1. **Voice = ONE identity, the zero-shot pranker Chatterbox.** MOSS NUKED (engine/default/floor gone). No
   compatible GPU -> voiceless + honest banner (transcript still shows). Both platforms ship.
2. **Brain default = hosted Bravoh proxy** (fresh user pastes nothing). In-GUI key field = advanced BYO.
3. **Streak = full Technologic robot voice in v1** — but rebind to a cited EXECUTED transition first.
4. **Start gate + model lifecycle = SHIP-CRITICAL** ("when we pre-ship this is the only thing").

---

## Are we one wire away or many?

Many — but they are a small, named set of JOINS, not a sprawl. The engine is real (~80% SRC), and within each
lane the maps are clean: zero emitted-but-unread server->client IPC types, the citation-grounded read path is
healthy, the fused-beatmatch learn loop closes end-to-end. The dark is concentrated at the SEAMS the two
single-lane maps handed to each other and at the four locked decisions that postdate both maps.

The blunt state of the end-to-end chain: **a stranger who installs the DMG falls into every gap between the two
halves.** The brain-key field is 16 green frontend files (`8c6a7b6e`) firing into a Python handler that does not
exist (`set_brain` is absent from `session_loop.py` / `settings.py`, confirmed at HEAD). The locked voice is
unreachable on a packaged launch (no `tts_engine` config field, MOSS still the floor the decision nukes). The
locked proxy default contradicts `llm_mode = "direct"` still live at `config_store.py:194`. And the Start gate —
Kaan's only named pre-ship gate — is a whole lifecycle that exists in NEITHER map and has zero code (no
`ipc.session.start`/`stop` anywhere).

Counting the real JOINS: **five integration seams** (brain handler, voice-engine reachability + MOSS-nuke,
Start gate, citation-receipt ts-carry, proxy default + credits), plus **one external dependency** (proxy
credits at 429), plus **one structural risk** (the Start-gate refactor and three other edits all touch
`__main__.py main()`, so that file needs ONE owner). Close those five seams together and the fresh-user path
holds; close any one alone and the stranger lands in the next gap. So: not one wire, but a countable five — and
the hardest (Start gate) is the one neither map planned for.

---

## The fresh-user path — step ladder

Each step is LIVE / DARK / MISSING with the owning wire. This is the spine: the journey a fresh non-dev walks
from DMG to a grounded co-host line, which neither single-lane map traces as ONE continuous flow.

Process model (load-bearing for every seam): the Tauri Rust shell spawns the Python sidecar TWICE in sequence
as one supervised slot — first `vibemix --wizard` (`__main__.py` wizard process), then on clean exit the watchdog
flips `wizard_mode=false` (`sidecar.rs:549-555`) and respawns the FLAG-LESS `main()` (the live co-host). Both
share `app_data_dir()/.env` + `config.json`. So a choice the wizard persists to `.env`/config DOES reach the
respawned session — but only if a handler writes it.

| # | Step (fresh non-dev, clean Mac) | State | Owning wire (lane) |
|---|---|---|---|
| 0 | Download DMG, open, Gatekeeper | **DARK (PKG=0)** | Canonical DMG is ~104-158 commits stale + predates the voice-lock + Start gate + organism. Rebuild + sign at HEAD. Keystone+packaging lane; external SignPath/Apple clock. NOT a code wire. |
| 1 | First-run wizard launches | **LIVE** | `main.rs:138 is_first_run` -> `--wizard` -> `runtime/wizard.py`. Steps intro->permissions->audio->controller->skill->profile->telemetry->smoke-test->done (`router.ts:168`). |
| 2 | Wizard telemetry-consent persists | **DARK (phantom emit)** | FE#9: `step-telemetry-consent.ts` fires `ipc.telemetry.set_consent` into NO schema + NO handler. FE adds schema + codegen; BE registers handler in `wizard.py:142` (mirror `_on_profile_set_consent:446`). Owner: assign `wizard.py` (unowned in the lane table — see Inter-lane). |
| 3 | Audio routing (BlackHole install + route DJ app) | **PARTIAL** | `wizard.py` detects BlackHole, deep-links install; no in-app installer. Master capture FATALs without it. Assist gap, not a wire. SHIP-READINESS democratization #5. |
| 4 | **Reach the brain (proxy default, no paste)** | **DARK — half-wired, the JOIN gap** | Seam A below. |
| 5 | Voice model reachable + fetched | **DARK (the locked voice cannot play)** | Seam B below. |
| 6 | Wizard `done` -> Start the session | **MISSING — zero wiring** | Seam C below. |
| 7 | Hear a grounded line in the cloned voice | **DARK (LIVE=0)** | Depends on 4+5+6. No captured run has nonzero `voice_rms`. Never crossed. |
| 8 | The deck line underlines its own citation | **DARK (silently mis-keyed live)** | Seam D below. |

### The first dead step IS the ship blocker

A fresh non-dev completes the whole wizard, the session respawns flag-less, boots `mode="direct"` (the still-live
default), finds no key, and `sys.exit(4)`s with `api-key-missing`. **The wizard's happy path terminates in a
crash today.** Step 4 (brain) is the first dead step; Step 5 (voice) and Step 6 (Start gate) are the next two.
These three are the cross-engine JOINS the FE and BE maps each saw only half of.

**Verdict on the step ladder:** the on-ramp is dead at Step 4 and stays dark through Step 8. The user-ready
landing is crossed only when Seams A+B+C+D close together AND the DMG is rebuilt at HEAD AND the proxy credits
top up — not when each lane is independently test-green.

---

## Integration exit-map

| Seam | Both endpoints (file:line) | The join wire | Owning lane | Proof (by-ear/by-eye E2E) |
|---|---|---|---|---|
| **A — Brain handler** (Step 4; flagship test-passing-but-dark) | FE: `brain-group.ts` fires `ipc.settings.set_brain` (committed `8c6a7b6e`); schema + DTO already exist (`ui_bus/messages.py:381/1022`). BE: NO `_on_settings_set_brain` in `session_loop.py`, no `apply_brain` in `settings.py` (confirmed absent at HEAD). | **FE/BE maps each owned half; neither closed the JOIN: the FE map says "author the schema" but it ALREADY exists — re-authoring clobbers `messages.schema.json`.** The schema + DTO are DONE; do NOT re-create. The one missing piece: register `ipc.settings.set_brain` -> `_on_settings_set_brain` at `session_loop.py:~270` -> write `GEMINI_API_KEY` to `app_data_dir()/.env` chmod 600 (or keychain, mirror `install_uuid.py`) + persist `ConfigStore.llm_mode` via `save_config` -> emit `SettingsBrainAck.make(restart_required=True)` (NO secret). Must ALSO register on the WIZARD loop (`wizard.py`), not only `session_loop`, or the wizard step has no responder. **JOIN correction: "next reaction uses it" resolves to SIDECAR-RESTART, not a hot brain swap** (the brain is built once at boot, `__main__.py:1605`; do NOT fight the in-flight coach gate). If Seam C lands, a key pasted at idle applies at next Start with no restart (see Inter-lane R6). | keystone+packaging (Python handler); FE owns schema (frozen, do not re-author) | by-bus: paste key in running app -> `.env` written (key absent from `ui.log` + ack) -> by-ear: restart -> co-host SPEAKS. Joint A+B proof = SHIP DoD #4. No green test substitutes. |
| **B — Voice-engine reachable + MOSS-nuke** (Step 5; locked decision 1) | FE: voice-engine rocker (W1 #3, `SettingsDrawer.ts:938-950`) + `VoiceReadinessBadge.ts` (moss-keyed). BE: `build_tts_chain` reads `os.environ.get("VIBEMIX_TTS_ENGINE","moss")` (`tts_chain.py:53`); NO `ConfigStore.tts_engine` (confirmed absent); MOSS floor at `tts_chain.py:56-67`; ref clip `~/.cache/vibemix/cohost_voice_ref.wav` is dev-cache only; `mlx-audio` not a `pyproject.toml` extra; spec bundles MOSS not Chatterbox. | **Both maps assume MOSS survives as a floor — decision 1 nukes it; this is a contradiction the lanes hit on contact, not a new wire.** (1) BE: add `tts_engine="chatterbox"` (NOT `"moss"`) to `config_store.py` dataclass + `_PHASE12_FIELDS:68` + `from_dict` coerce; add `os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine)` at `__main__.py:1420` (mirror `_apply_deck_audio_config_to_env:1060`). (2) BE: rip MOSS across the tree (`tts_chain.py`, `local_tts.py`, `voice_presets`, `config_store`, `__main__.py:1044`, `ui_bus`, `learn/runtime`, `_router_config`, `debrief`, `library/cost`); replace the MOSS-fallback branch with VOICELESS + honest banner. (3) FE: the MOSS/CHATTERBOX rocker (W1 #3) is **DELETED, not built** (one voice = nothing to pick); replace with a read-only voice-status indicator; rewire `VoiceReadinessBadge.ts` off `moss-tts` to the Chatterbox asset / voiceless state. (4) packaging: bundle `cohost_voice_ref.wav` as a PyInstaller `datas` asset + add `mlx-audio` extra; the ~675MB `chatterbox-turbo-8bit` auto-downloads on first `load()`. (5) learn tutor sink (`__main__.py:294 _build_learn_tutor_speak_audio`) is hard-bound to `MossLocalTTS` — re-point to `ChatterboxLocalTTS` (API-compatible mirror: same `synthesize_pcm` + `sample_rate`), or the tutor goes voiceless while the co-host speaks (Inter-lane R3). **Ordering hazard: bundle ref + mlx-audio + land reachability BEFORE ripping MOSS, or `chatterbox_available()=False` ships voiceless with no floor and the keystone capture is impossible.** | sven/keystone+packaging (Python + specs); FE deletes the rocker + rewires the badge | by-ear on a PACKAGED launch reading config.json (NOT env): co-host speaks in the pranker clone; `grep` shows MOSS gone; no-GPU shows the honest banner with transcript still rendering. |
| **C — Start gate + model lifecycle** (Step 6; locked decision 4, SHIP-CRITICAL, in NEITHER map) | FE: no Start control anywhere; `shell/activation-bridge.ts:25` derives activation from audio RMS (passive mirror, not a user action). BE: `main()` is fully EAGER — builds TTS (`:1607`) + LLM/cache (`:1669`), opens capture (`:3262`), spawns `coach_loop`/`refresh_loop`/learn loops (`:3117-3215`) all unconditionally; `ipc.session.mute` (`session_loop.py:304`) only drains the PlaybackQueue, does NOT unload models or stop capture. Heavy models (~675MB Chatterbox + Gemini pipeline) sit resident at idle (the strain Kaan felt). | **The largest JOIN miss; both maps predate the decision.** NEW IPC pair `ipc.session.start`/`ipc.session.stop` (FE owns schema) + `ipc.session.lifecycle {state:idle|prewarming|active}` echo. FE: a Start/Başlat control + `sessionPhase` in `shell-store.ts` (a real user-driven state, not the RMS-derived mirror); re-gate the Receipts panel auto-open (W1 #4) on `lifecycle==="active"` not on boot. BE: split `main()` into a light idle boot (ws bus + handlers + device probe, NO model load) and a `_activate_session()` that builds TTS + LLM/cache + opens capture + arms `coach_loop`; `start` calls it, `stop` releases the TTS model + lets the Gemini cache lapse + clears an `active_event` gating `coach_loop`'s publish (keep loops cold-running, gate the expensive Gemini/TTS legs). **Silent pre-warm hook:** `prewarm()` (already exists, `chatterbox_tts.py:189`) + prime the ref conditional in the background during wizard/setup, WITHOUT opening capture or reacting. Capture stays open only at active (the keystone "BlackHole is heard" precondition); `watch_parent` + `stop_event` already exist as cooperative plumbing — Stop drives them WITHOUT killing the process. | keystone+packaging owns `main()` restructure (it also owns Seam A handler + Seam B env-seed in the same file); FE owns button + schema + state | by-feel on the real app: idle = no resident Chatterbox model, capture closed, CPU/RAM low; Start -> capture opens, first audio fast (prewarm paid the encode); Stop -> model unloads. NOT a unit test. |
| **D — Citation-receipt ts-carry** (Step 8; the signature anti-slop gesture, orphan JOIN) | BE: `SessionCohostReaction.make()` mints `ts=_now_iso()` (`messages.py:1540`); `_push_transcript` -> `ws_bus.py:783` mints a SEPARATE `_now_iso()`. FE: `SessionLayout.ts:1171` joins chips by `reactions.get(nowLine.ts)`. | **The orphan: FE map assigns it to "backend lane (ui_bus-adjacent)" but the BE map never enumerated it — it falls through the crack between lanes.** The two `_now_iso()` calls never byte-match -> `.get()` returns undefined -> the "sentence underlines its own claim" gesture is silently dark live (works in unit tests only because mocks hand-author matching ts). BE captures ONE `reaction_ts = _now_iso()` near `dj_cohost.py:4011`, threads it to BOTH `make(ts=...)` and `_push_transcript(text, ts=...)`; `ws_bus.py:781-784` drains the carried ts. FE adds a regression vitest asserting a MISMATCHED ts fails to fire (so a future coincidental ts-equality can't false-fire a receipt on the wrong line). **Explicitly assign to the sven lane** (it owns `dj_cohost.py`); name it in the BE backlog or it ships dark. | sven (owns `dj_cohost.py`); FE owns the regression vitest | by-bus on a captured voice-ON set: the `transcript_delta` line and its `cohost-reaction` envelope carry the SAME ts; the deck hero ignites its citation chip in real time. |
| **E — Proxy default + credits** (Step 4 second half; locked decision 2) | BE: proxy chain LIVE end-to-end (`__main__.py:1155-1167`); packaged default `llm_mode="direct"` (`config_store.py:194`, confirmed). External: Bravoh proxy at 429 (out of credits) + needs per-client rate limit. | **The fresh-user path's gating external dependency, resolved by decision 2 but not yet wired.** FE wizard takes the proxy-default shape (W1 #10 Option B), NOT a key prompt; persists `llm_mode="proxy"` via `ipc.wizard.set_llm` (mirror `_on_wizard_set_skill:470`). BE flips the packaged default `direct`->`proxy` at `__main__.py:1108-1117`. The in-GUI key field (Seam A) becomes the advanced BYO path. **External (flag, not a code wire): proxy credits top-up + per-client rate limit on `ssh altidus` (`/var/www/bravoh-clean-backend`, PM2 `bravoh-clean-api-0/1`) — organizer/Bravoh-ops.** Until topped up, the proxy-default ships a brain that 429s for every stranger; the boot must surface an honest "brain temporarily unavailable" banner, never a raw `sys.exit(4)`. | keystone+packaging (default flip) + FE (wizard step) + organizer/Bravoh-ops (credits) | by-ear E2E: fresh wizard with no key paste -> session boots proxy -> register->JWT->Gemini -> co-host speaks. Gated on credits. |

### Confirmed-sound seams (do NOT "fix")

- Wizard->session cross-process handoff (`.env`/config shared, respawn flag-less) is sound — the brain seam fails on the missing handler, not the handoff.
- Cue Tray / `library_land_cues` (W1 #2) is a moat surface, not on the fresh-user critical path to a first grounded line. It IS a real 3-party seam (see Inter-lane R5) but ships behind the keystone, not before it.
- Organism is the rare fully-wired grounded-to-render chain (Kaan-LOCKED visual). Its only gap is the stale DMG (Step 0), not a wire.
- taste->suggestion, key/camelot->next-suggestion, intel-scorer->pill, debrief->profile, memory/recall are all LIVE end-to-end (behind default-off opt-in flags = owner ear-pass, not wires).

---

## Inter-lane resolutions

Single-owner calls for every conflict found vs the FE/BE maps. Hot files, IPC handshakes, and the contradictions
the two single-lane maps would hit on contact.

- **R1 — `__main__.py main()` has ONE owner = keystone+packaging.** Seam A (brain handler boot read), Seam B
  (`tts_engine` env-seed at `:1420`), Seam C (the eager->lazy lifecycle restructure), and Seam E (the
  `direct`->`proxy` default flip at `:1108-1117`) ALL touch `main()`. The Start-gate refactor (C) is the most
  load-bearing edit and risks the keystone capture. Sequence the other three behind it; no other lane edits
  `main()`.

- **R2 — `config_store.py` has ONE owner = keystone+packaging.** Three new/changed fields land in the same
  dataclass + `_PHASE12_FIELDS` tuple: `tts_engine` (Seam B, default `"chatterbox"` NOT `"moss"`), `llm_mode`
  default flip `direct`->`proxy` (Seam E), and the `voice: str = DEFAULT_MOSS_VOICE` literal (`:171`) to rip
  with the MOSS-nuke. `config.rs` Rust writers already `reload()` before save (no clobber); the secret
  (`GEMINI_API_KEY`) goes to `.env`/keychain, NEVER `config.json`.

- **R3 — `tts_chain.py` MOSS-nuke must land BEFORE the FE rocker is built, OR the FE builds a dead control.**
  Decision 1 deletes the MOSS floor; W1 #3 (MOSS/CHATTERBOX rocker) and W2 V1/W1 (`tts_engine` default `"moss"`,
  never-mute floor) all assume MOSS survives. **Resolution: the FE rocker is DELETED, not built; `tts_engine`
  defaults to `"chatterbox"`; the fallback is voiceless + honest banner (not MOSS).** Sven/keystone lane rips
  MOSS + repoints the learn tutor sink (`__main__.py:294`) to Chatterbox in the SAME ship window FE rewires
  `VoiceReadinessBadge.ts`. Out-of-sync = MOSS UI over a Chatterbox backend.

- **R4 — `ipc.settings.set_brain` schema is DONE; neither lane re-creates it.** It already exists
  (`messages.schema.json` + `ui_bus/messages.py:381/1022`, confirmed at HEAD). FE#1's "author the schema"
  instruction is downgraded to "build the UI + redact the key" (already shipped `8c6a7b6e`). BE owns ONLY the
  missing handler. Re-running `codegen:ipc` on the existing type would clobber the shared schema file.

- **R5 — `library_land_cues` is a 3-party seam; ONE owner of the Rust+CLI middle = library lane.** FE owns the
  Cue Tray UI + the `invoke()` call (behind a `DEV_LAND` fixture); BE library lane owns the `CueSet` DTO
  extension (`summary`/`policy` floors/`detected_target`) + the `library_land_cues` Rust command in
  `library_cmds.rs` + `main.rs::generate_handler!` + a headless CLI verb. The FE cannot ship green+honest until
  both land (HANDOFF-SESSION3 confirms CUETRAY blocked on exactly this). Not on the fresh-user critical path.

- **R6 — Start-gate vs brain-ack `restart_required` is one handshake, not a conflict.** If Seam C lands, a brain
  key pasted at idle applies at next Start with NO restart -> the `restart_required` value should be lifecycle-
  aware (`False` when idle, `True` only when a live session is active). BE owns the ack value, FE owns the copy;
  coordinate so the readout matches reality (telling a fresh user to restart when it is unnecessary is UX slop).

- **R7 — Streak robot voice (decision 3) is a SEQUENCED single-owner chain, not parallel work.** FE#7 ("strip,
  don't render") is right for the LIVE pill; W2 V2/V3 ("defer until grounded") is right that the current signal
  is self-applause (`suggestion.py:1375` grades its own un-played suggestion). **Resolution: (1) sven lane lands
  the grounded `[ev:BEATMATCH_GRADED]`/`[judge:]` executed-transition signal (W2 #8 master-only Judge + #12 live
  beatmatch credit); (2) rebind the streak increment off `suggestion.py` onto `coach.py:_credit_judged_transition:313`;
  (3) ONLY THEN the robot voice (new `streak_vocal.py` mirroring `mastered_vocal.py`) on the debrief/progress
  surface, NEVER the live eyes-off pill.** Landing the robot voice on the present signal = Invariant #3
  violation that SOUNDS earned. Owner-gate: confirm v1 scope vs defer (the grounded event barely fires on a
  master-only rig).

- **R8 — `learn/runtime.py` is a hot shared file; single owner = learn Codex.** The organism `teaching_focus`
  emit (FE), the harmonic-seed wire, the learn cue-grade, and the MOSS-nuke tutor repoint all touch it. FE/sven
  request; the learn lane edits. (Confirmed in SHIP-DRIVE.md hot-file note.)

- **R9 — `wizard.py` is UNOWNED in the lane table but carries three live seams** (telemetry-consent handler
  R2/Step 2, the `set_brain` responder for Seam A, the proxy-default `llm_mode="proxy"` persist for Seam E).
  Assign it to keystone+packaging (it lives in `runtime/`) before the fresh-user path can be wired.

- **R10 — debrief `evidence_registry.json` never written** (FE map "Confirmed CLEAR" note; BE map omits it).
  `__main__.py:1260` -> `recorder.py:208/549` never hands the live `EvidenceRegistry` to the recorder ->
  debrief drills + citation tooltips show `found=false`. Assign to the engine/keystone lane (the runner-up
  reveal surface depends on it). Not on the fresh-user critical path.

---

## Ship-wire goals to hand to the AIs

The final per-session paste-ready /goal blocks. Each is disjoint by island. Each carries the SHARED LAW. These
are what we ship to the sessions.

> **SHARED LAW (every lane obeys, verbatim):** ONE shared tree (`ux-redesign-impeccable`), 2+ concurrent
> sessions — commits survive, uncommitted work gets WIPED by a sibling git op. `git add <exact paths>` NEVER
> `-A`; review `git diff --cached --name-only` in a SEPARATE step before every commit; before staging a SHARED
> file (`contract.ts`, `tokens.css`, `messages.schema.json`, `__main__.py`, `config_store.py`,
> `learn/runtime.py`) re-check `git diff` for foreign hunks and stage only yours. The IPC schema
> (`tauri/ui/src/ipc/messages.schema.json`) is FRONTEND-lane-owned — backend lanes implement the named Python
> handler, never edit the schema. ONE socket `127.0.0.1:8765`, one listener; `pkill -f "python -m vibemix"`
> before any probe. Do NOT rush to exit at test-green — `test-passing-but-dark = 0`: prove the E2E BY EAR /
> BY EYE in the real app (`drive-vibemix` / `VIBEMIX_DEV_SIDECAR=1` / `?dev=` on the Vite server), run
> `vibemix-grounding-review` on every new co-host line. Commit each piece the instant it is green + proven,
> not in a batch. `commit -s`, identity `Kaan Özkan <rahipdotaci@gmail.com>`, trailer
> `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

### Frontend (cclaude)

```
/goal USER-READY FRONTEND — close the frontend half of the integration seams, from
.planning/packets/2026-06-04/USER-READY-WIRING-EXIT-MAP.md. Pin a SHA first (~16a547dd, tree is hot). In order:
(C) START GATE (SHIP-CRITICAL, Kaan's only pre-ship gate) — a "Start/Başlat" control in the session shell +
    a real sessionPhase (idle|prewarming|active) in shell-store.ts that DRIVES activation (replace the RMS-derived
    mirror in activation-bridge.ts). NEW ipc.session.start / ipc.session.stop (you OWN the schema; codegen:ipc) +
    an ipc.session.lifecycle {state} echo so the button self-corrects. Re-gate the Receipts-panel auto-open on
    lifecycle==="active", NOT on boot. Optimistic repaint. The model load/unload + silent pre-warm is the
    backend's half — name the handler, do not implement it.
(B-FE) MOSS-NUKE frontend half — the MOSS/CHATTERBOX voice rocker is DELETED, not built (decision 1: one voice,
    nothing to pick). Replace it with a read-only voice-status indicator; rewire VoiceReadinessBadge.ts off the
    moss-tts asset id to the Chatterbox/voiceless state + honest "no compatible GPU - transcript only" banner.
    Fix the wizard step0-intro "Voice: local MOSS" copy. Coordinate the sync window with the backend MOSS rip
    (R3) so MOSS UI never ships over a Chatterbox backend.
(D-FE) Citation-receipt regression — ADD a vitest that exercises the live ts-mismatch (reaction ts != transcript
    ts) and asserts the receipt FAILS to fire (the sven lane carries the matching ts; you guard the regression).
(2) Wizard telemetry-consent — NEW ipc.telemetry.set_consent {consent} (schema + codegen); backend persists.
(E-FE) Wizard proxy-default step — persist llm_mode="proxy" (decision 2, NO key prompt on the happy path) via
    ipc.wizard.set_llm; the in-GUI key field stays the advanced BYO path (already shipped 8c6a7b6e).
(4) Shell Receipts panel — render real citation_strip chips from reactions[last] + next_suggestion; honest-null
    when empty. (5) Cue Tray — ship behind getInvoke()===null -> DEV_LAND fixture until the library lane lands
    the Rust command (R5); do NOT codegen:ipc for library_land_cues (it is a Tauri invoke).
HANDSHAKE: you OWN every IPC schema type; backend lanes implement the named handlers. The ipc-wiring-checker will
show backend handlers RED until they land — note as a known cross-lane dep, do NOT fake the Python side. R4: the
ipc.settings.set_brain schema ALREADY EXISTS — do NOT re-author it.
PROOF (by-eye, real app): idle = no Start = no reactions, models cold; Start flips to active; voice-status shows
honest state; the receipt fires only on a matching-ts reaction. test-passing-but-dark = 0.
SHARED LAW applies (see header).
```

### library (Viber / cue / embeddings)

```
/goal USER-READY LIBRARY — unblock CUETRAY (R5) + close the cue-landing consolidation, from
USER-READY-WIRING-EXIT-MAP.md + BACKEND-WIRING-EXIT-MAP.md. Pin a SHA first. The Viber auto-cue path is LIVE
end-to-end — do NOT rebuild it. ISLAND: src/vibemix/library/**, intel/**, tauri/src-tauri/src/library_cmds.rs,
main.rs. NOT the IPC schema (Frontend owns it), NOT tauri/ui.
(R5) Unblock the Frontend Cue Tray: add summary / detected_target / policy-floor fields to cue_landing.CueSet
    (confidence banded to policy floors, provenance AUTO vs DJ preserved); add the library_land_cues Tauri command
    in library_cmds.rs (mirror library_cue_folder:866) + register in main.rs::generate_handler!; add a headless
    CLI verb that emits the proposed CueSet JSON + calls cue_landing.land(cueset, target, granted=True). This is
    the 3-party seam middle the FE cannot build solo.
(13) Route toolset.export_set auto-cue through cue_landing.land() (replace the hand-rolled propose->marks in
    _auto_cue_marks_for_export:2124 with cue_set_from_proposal; call land() at the carrier seam :1044). ONE
    permissioned landing verb. Owner-gate: confirm consolidate vs leave tested-but-unused.
(14) Re-point learn/mastered_marker_writer at cue_landing.land() so the mastered marker inherits the consent/receipt.
PROOF: library build-set "..." --cue --export rekordbox -> re-parse XML: VM-named marks fill empty slots, DJ cues
byte-preserved, zero DB writes; a CueSet fixture the Frontend can render. test-passing-but-dark = 0.
SHARED LAW applies (see header).
```

### learn

```
/goal USER-READY LEARN — close the fused beatmatch loop to its kill-criterion and the MOSS-nuke tutor repoint,
from USER-READY-WIRING-EXIT-MAP.md + BACKEND-WIRING-EXIT-MAP.md. The loop is WIRED at HEAD (06-03 diagnosis is
STALE) — do NOT re-wire it. ISLAND: src/vibemix/learn/** (+ audio/miniplayer.py). learn/runtime.py is the hot
shared file (R8) — you are its single owner; FE/sven request, never edit it.
(B-LEARN) MOSS-nuke tutor sink: when the keystone lane rips MOSS, the learn tutor (_build_learn_tutor_speak_audio,
    __main__.py:294, today hard-bound to MossLocalTTS) goes voiceless unless repointed to ChatterboxLocalTTS
    (API-compatible mirror: same synthesize_pcm + sample_rate). Coordinate with the keystone lane so the tutor
    speaks the SAME cloned voice as the live co-host (decision 1), gated on chatterbox_available() not
    local_tts_enabled(); voiceless + banner on no-GPU. The grade line stays the grounded fixed text, never ad-lib.
- Widen the audible-practice lesson gate (_PRACTICE_LESSONS) to Course-1/2 control lessons that touch a deck,
  keeping TwoDeckPlayer.can_play() + the A1 guard (practice audio NEVER over a live set).
- Fix passive-skip crediting: on_enter_completed credits full WEIGHT_FIRST_TRY even on a 45s skip
  (runtime.py:1224 + skill_tree.py:254) — persist a demonstrated flag, record skip at floor weight.
PROOF (by-bus + by-ear): L2.01 kill-criterion on the live sidecar — a beginner HEARS the kicks drift+lock in the
Chatterbox tutor voice, the lock-meter needle centers, [ev:BEATMATCH_GRADED@t] resolves on the ws bus; a skip does
not credit mastery. When the kill-criterion is proven, STOP. test-passing-but-dark = 0.
SHARED LAW applies (see header).
```

### sven (the live Gemini reaction brain + the locked voice)

```
/goal USER-READY SVEN — the locked VOICE (decision 1) + the citation-receipt carry + grounded-coaching, from
USER-READY-WIRING-EXIT-MAP.md + GOAL-sven.md. The prompt axis is DONE (bench-proven) — do NOT keep tuning prompts.
ISLAND: src/vibemix/agent/** (tts_chain.py, local_tts.py, chatterbox_tts.py, dj_cohost.py), prompts/**,
state/coach.py, runtime/{suggestion_voice,set_plan_voice,speak_gate}.py, intel/{judge_voice,transition_scorer,
move_grade}.py, scripts/eval/respan_*. NOT __main__.py main() lifecycle (keystone owns it, R1) — request env-seeds.
(B-SVEN) VOICE the #1 founder concern: rip MOSS as engine/default/floor (decision 1, no MOSS no cloud TTS ever);
    replace the tts_chain.py:56-67 MOSS fallback with VOICELESS + honest banner. The pranker Chatterbox is the
    one voice. Coordinate the config_store.tts_engine field + the __main__.py:1420 env-seed with the keystone lane
    (R1/R2 — they own those files); you own agent/**. Ordering hazard (R3): the ref clip + mlx-audio + reachability
    must land BEFORE the rip, or chatterbox_available()=False ships voiceless.
(D) Citation-receipt ts-carry (the orphan JOIN, signature anti-slop gesture): capture ONE reaction_ts near
    dj_cohost.py:4011, thread it to BOTH SessionCohostReaction.make(ts=) AND _push_transcript(text, ts=); ws_bus.py
    :781-784 drains the carried ts. (FE owns the regression vitest.)
(3) HEARTBEAT grounded receipt; (4) fix the TRACK_CHANGE Option-A/B malformed line; (6) make
    HYPE_INTERMEDIATE=SVEN_COACH_IDENTITY live + re-pin the 5 RED agent tests; (7) LAYER_ARRIVAL band-jump narrate;
    (8) FINISH the master-only Judge branch; (9) feed score_transition_slate into the spoken line; (11) Judge
    risk_flags; (12) WIRE+BUILD the live beatmatch credit (coordinate the grid feed with the engine lane).
(R7) Streak robot voice is SEQUENCED, NOT parallel: land the grounded executed-transition signal (#8 + #12) FIRST,
    rebind the streak off suggestion.py onto coach.py:_credit_judged_transition:313, THEN the robot voice on the
    debrief surface — NEVER on the present self-applauding signal (Invariant #3).
PROOF: run scripts/eval/respan_sven_sim.py + respan_sven_heartbeat_judge.py, show the dim numbers moved;
vibemix-grounding-review on EVERY change to what/when the co-host speaks; drive-vibemix by-ear on a real set in
the Chatterbox voice. test-passing-but-dark = 0. SHARED LAW applies (see header).
```

### keystone + packaging (the engine-reachability, brain-persist, Start-gate, ship gates)

```
/goal USER-READY KEYSTONE+PACKAGING — own the cross-engine boot seams + the ship gates, from
USER-READY-WIRING-EXIT-MAP.md + SHIP-READINESS-2026-06-04.md + SHIP-DRIVE.md. Pin a SHA first. ISLAND:
src/vibemix/runtime/{config_store.py, session_loop.py, settings.py, wizard.py}, src/vibemix/__main__.py,
src/vibemix/audio/**, platform/_audio_*.py, scripts/** (release/build), the PyInstaller specs. You are the SINGLE
owner of __main__.py main() (R1) and config_store.py (R2) — three other seams touch them; sequence behind you.
(A) Brain persist handler (SHIP DoD #4): register ipc.settings.set_brain at session_loop.py:~270 AND on the wizard
    loop (wizard.py, R9) -> NEW _on_settings_set_brain: write GEMINI_API_KEY to app_data_dir()/.env chmod 600 (or
    keychain) NEVER log, persist ConfigStore.llm_mode via save_config, emit SettingsBrainAck.make(restart_required
    lifecycle-aware, R6). R4: the schema ALREADY EXISTS — implement the Python handler ONLY.
(C) START GATE main() restructure (SHIP-CRITICAL): split main() into a light idle boot (ws bus + handlers + device
    probe, NO model load) and a _activate_session() (TTS + LLM/cache + capture + coach_loop). ipc.session.start
    handler calls it; ipc.session.stop releases the TTS model + lets the Gemini cache lapse + clears an active_event
    gating coach_loop's expensive legs (loops run cold, capture stays open only at active). Silent pre-warm hook:
    prewarm() (exists, chatterbox_tts.py:189) + prime the ref conditional in the background during setup. Drive
    stop_event WITHOUT killing the process. The FE owns the schema + button.
(B-KEY) tts_engine reachable: add tts_engine="chatterbox" (decision 1, NOT "moss") to config_store.py +
    _PHASE12_FIELDS + from_dict coerce; add os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine) at
    __main__.py:1420; bundle cohost_voice_ref.wav as a spec datas asset + add the mlx-audio extra; resolve_ref_path
    falls back to the bundled location. Repoint the learn tutor sink direction is the learn lane's (coordinate).
(E) Default flip: llm_mode default direct->proxy at __main__.py:1108-1117 (decision 2); the boot must surface an
    honest "brain unavailable" banner on a 429, never sys.exit(4). EXTERNAL: proxy credits + per-client rate limit
    on ssh altidus = organizer/Bravoh-ops, flag it.
(5) Route-doctor determinism: `1 if name=="blackhole 2ch" else 0` as the FIRST sort key at
    learn_live_readiness.py:922 AND :2018-2022. (17) voice-model literal gate. (10/R10) hand the recorder the live
    EvidenceRegistry (__main__.py:1260 -> recorder.py:208/549).
PACKAGING: with SRC green at HEAD, rebuild the sidecar AND the DMG at HEAD (stale), run the release gates, report
which pass vs wait on the external SignPath/Apple clock, confirm boot-clean.
PROOF: by-ear on the real app for (A)+(B)+(C); idle = models cold + low RAM, Start = first audio fast, Stop =
unload; by-bus 3 repeated route-doctor runs all name BlackHole 2ch. test-passing-but-dark = 0.
SHARED LAW applies (see header).
```

---

## NEEDS-CLARIFICATION

1. **Start-gate scope (Seam C / decision 4):** is the full eager->lazy `main()` refactor in the v1 ship, or is
   the minimum a "Stop releases models" without a full lazy boot? The full refactor touches the most load-bearing
   file and risks the keystone capture — confirm appetite before the keystone lane restructures boot. Also: does
   pre-warm begin the moment the shell mounts (eager, fast first-audio, brief idle warmth) or only on an explicit
   "getting ready" signal (coldest idle)?

2. **MOSS-nuke ship sequence (Seam B / decision 1):** decision 1 nukes MOSS, but MOSS is the current bundled
   never-mute floor and the only voice that works on a fresh Mac today (Chatterbox needs mlx-audio + a bundled
   ref, neither shipped). Confirm: does v1 ship voiceless-until-Chatterbox-bundled (honest banner), or does MOSS
   stay as the floor for ONE release while the Chatterbox bundle lands? The two exit-maps assume MOSS-floor;
   decision 1 contradicts them — one-line ruling needed before the keystone lane rips MOSS out.

3. **Proxy-default + credits (Seam E / decision 2):** confirm the packaged default flip `direct`->`proxy` AND
   that proxy credits + per-client rate limit are funded before ship. The whole fresh-user path is gated on the
   external credit top-up; without it the proxy-default ships a 429 brain. Ship proxy-default GATED on credits,
   or ship direct+key-field as the interim default until Bravoh-ops tops up?

4. **Streak robot voice v1 scope (R7 / decision 3):** the grounded `[ev:BEATMATCH_GRADED]`/`[judge:]` event
   barely fires on a master-only rig. Confirm the robot voice ships in v1 behind the full 3-step re-bind
   plumbing (real build), or defers to a deck-routed-judge milestone. Do NOT ship it on the present
   self-applauding signal regardless.
