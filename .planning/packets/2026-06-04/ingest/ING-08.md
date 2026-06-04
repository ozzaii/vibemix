# ING08 — RUNTIME-IO adversarial ship-ingest (runtime/ audio/ platform/ events/ midi/)

**HEAD read at: `d7d5337a175ac90612702c3adda4d17aa3918899`** (`d7d5337a test(config): isolate device defaults from rig env`), branch `ux-redesign-impeccable`, 2026-06-04. Same HEAD as ING-01..07. The SHIP-MAP-MASTER was synthesized at `7ac35a84`; the tree advanced ~15 commits since (voice prefetch `0e5590c5`, start-gate idle-cold lock `18dc95cb`, chatterbox preflight `eec239ac`, boot smoke align `02ffb7c0`, device-default isolation `d7d5337a`). Several map claims tagged DARK for runtime-io are now LANDED — corrected inline.

Proof tiers, never conflated: **SRC** (green tests on source) != **PKG** (in a signed DMG built at HEAD) != **LIVE** (a real user reaches it). `test-passing-but-dark = 0`. READ-ONLY pass: no product code edited, sidecar not launched.

---

## Headline verdicts (runtime-io)

| Claim | SHIP-MAP said | ING08 verdict @ `d7d5337a` |
|---|---|---|
| START GATE backend handler | DARK (no `_on_session_start`) | **LANDED + committed** (SRC). Full lifecycle wired both ends. CORRECTS the map. |
| Idle = no heavy model resident | claimed by decision #3 | **LANDED** (SRC). Prewarm is import-only; models + capture streams open only inside `_activate_session` on Start. |
| `set_brain` BYO handler (decision #2) | DONE | **LANDED + committed** (SRC). Confirmed. |
| Client default proxy + graceful no-key | DONE | **LANDED** (SRC). No no-key `sys.exit`; idle banner instead. |
| ws_bus single socket (Inv #4) | held | **LANDED** (SRC). Two bind sites, never concurrent. |
| IPC handlers registered | 10 → "12+" | **15 `register_handler` calls** in `session_loop.py`; runtime banner reports `len(ipc_router._handlers)`. |
| Master capture 2ch-first determinism | landed at most sites | **LANDED** at the live capture path + the primary route-doctor ranker. |
| Route-doctor RMS-flip (W5) | partial (4 sites fixed, `:922` not) | **PARTIAL — still DARK in the `top_signal` fallback branch.** `:922` is RMS-only; feeds the 2nd-priority recommend branch. |
| MIDI profile count | 11 (docs undercount 10) | **11 confirmed.** Docs still undercount = CLAIMED-BUT-DARK (doc/copy gap). |
| macOS screen-watch app-agnostic (W15) | DARK (djay-only) | **NOT-STARTED — still djay-only hardcoded.** Confirmed. |
| NI S2-MK3 HID ingest seam (W16) | DARK (0 callers, no `apply_event`) | **NOT-STARTED (post-ship, correct).** Confirmed. |
| R10 recorder→evidence_registry wire | still DARK | **STILL DARK.** `VoiceRecorder(...)` omits `evidence_registry=` at boot. |
| MIDI activity probe honest (idle != active) | honest | **LANDED** (SRC). Confirmed. |

---

## 1. START GATE + model lifecycle (decision #3) — LANDED both ends (SRC), CORRECTS the map

The single most important runtime-io correction. The SHIP-MAP-MASTER (synthesized at `7ac35a84`) and ING-02 flagged the backend handler DARK / in a dirty working tree. **At HEAD `d7d5337a` it is committed and wired end-to-end.**

**Handler side (`runtime/session_loop.py`):**
- `session_start` / `session_stop` / `session_is_active` callbacks accepted in `__init__` (`:189`, stored `:223`).
- `register_handler("ipc.session.start", self._on_session_start)` at `session_loop.py:278`; `ipc.session.stop` at `:279`.
- `_on_session_start` (`:331-354`): no-op if no lifecycle callback wired (`:338`), idempotent on already-active (`:341-342`), `await self._session_start()` (`:344`), emits `IpcError` on failure (`:347-353`). No ack envelope by design (frontend repaints optimistically) — docstring `:334-336`.
- `_on_session_stop` (`:356-374`): symmetric, no-op if not active (`:361`), `await self._session_stop()` (`:364`).

**Lifecycle side (`src/vibemix/__main__.py`):**
- `_activate_session(run_stop_event, started_event)` (`:1704`) — the gated body. Opens capture/voice/passthrough streams + instantiates the Chatterbox TTS model + builds the agent INSIDE this coroutine (`:1751` `ChatterboxLocalTTS()`, `:1864` `open_voice_output`, `:1875` `open_passthrough_output`, `:2058` `open_capture`). None of this runs until Start.
- `_start_live_session` (`:2172-2186`): creates the `_activate_session` task, waits up to 30s for `started_event`, surfaces activation errors (`:2184` `RuntimeError("session.start timed out…")`).
- `_stop_live_session` (`:2188-2198`): sets `active_stop_event`, awaits the task, clears refs — the Stop release.
- `_silent_prewarm_hook` (`:2200-2209`): after a 0.25s delay, calls ONLY `_ensure_live_llm_tts_deps()` + `_ensure_live_session_deps()` (module-global IMPORTS, see §2), prints `start gate prewarm: live imports ready (models still cold)`.
- Wired into `SessionLoop(... session_start=_start_live_session, session_stop=_stop_live_session, session_is_active=_is_live_session_active)` (`:2238-2240`), then `register_handlers()` (`:2242`).
- Boot prints `-> start gate: armed (idle; capture/reactions/model load wait for Start)` (`:2275`), then `await stop_event.wait()` (`:2278`).
- `_is_live_session_active()` (`:1697-1702`): true iff `active_task is not None and not active_task.done()`.

**Verdict: LANDED + committed (SRC).** PKG = unverified (no fresh HEAD DMG; the canonical `dist/vibemix-0.0.1.dmg` is ~190 commits stale and unsigned per ING-07). LIVE = unverified (keystone, Kaan-only).

**Gotcha flagged — dead-after-return legacy body.** `main()` ends the live path at `:2278 await stop_event.wait()` → cleanup → `:2314 return`. Everything from `:2316` (`voice_stream = None`) through `~:4100` is the OLD auto-run body and is now **unreachable dead code after the `return`** (`open_passthrough_output` `:2318`, `open_mic_capture` `:2339`, `open_voice_output` `:2838`, `open_capture` `:4043` all live there). It is dead, not a second active branch — so it does not violate the start-gate (capture does NOT open at idle). But it is ~1800 lines of dead weight that grep hits make line-number reasoning treacherous. The 2ch/native-rate device RESOLUTION (`find_device` `:1503`, `describe_capture_input` `:1518`) DOES run at boot/idle and `sys.exit(3)` fires if BlackHole is absent (`:1517`) — device-missing is a hard fatal at boot, before the gate. That is a fresh-user concern but distinct from "model resident at idle" (the model is not).

---

## 2. Idle = cold (decision #3 second half) — LANDED (SRC)

`_ensure_live_llm_tts_deps` (`__main__.py:197-206`) and `_ensure_live_session_deps` (`:219-234`) are **pure import shims** — they set module globals (`build_llm`, `build_tts_chain`, `AgentSession`, `DJCoHostAgent`, `PlaybackQueueAudioOutput`) by lazy-importing the module, NOT by constructing a model. The prewarm hook calls only these. The actual heavy objects (`ChatterboxLocalTTS()` `:1751`, the agent, the LiveKit `AgentSession`, every `open_*` audio stream) are constructed inside `_activate_session` (`:1704`), gated behind `ipc.session.start`. So at idle: imports warm, models cold, no audio stream open. **Decision #3's "silent pre-warm, no heavy model resident at idle, Stop releases" is honored in source.**

---

## 3. IPC handler count + ws_bus single socket (Inv #4) — LANDED (SRC)

**15 `register_handler` calls** in `session_loop.py:register_handlers` (`:270`): session.start `:278`, session.stop `:279`, session.mute `:280`, session.set_mode `:286`, settings.set `:287`, settings.set_brain `:288`, settings.get `:289`, status.recheck `:290`, recordings.list `:293`, recordings.delete `:294`, recordings.events `:295`, profile.view `:301`, profile.regenerate `:302`, profile.delete `:303`, profile.set_consent `:308`. The runtime banner reads `len(ipc_router._handlers)` and prints `session IPC handlers wired onto mascot bus (N types incl. start/stop)` (`__main__.py:2243-2246`). The SHIP-MAP "10 → 12+" undercounts; the real count of `SessionLoop`-registered handlers is **15**.

**Single socket (Inv #4) — LANDED.** Two `websockets.serve(WS_HOST, WS_PORT)` sites both bind `127.0.0.1:8765`:
- `ws_bus.py:1127` — the mascot/session bus (`ws_broadcast`).
- `ws_bus.py:1527` — `WizardBus.start()`.
The class comment at `ws_bus.py:1473` states they "both bind 127.0.0.1:8765 … they never run at the same time." `IpcRouterBus` (`:912`) does NOT bind its own socket — it rides the mascot server via `bind_emit` (`:943`, wired at `:1055`), comment `:923` "We can't bind a second listener (One Socket invariant)." Invariant #4 holds in source.

---

## 4. Master capture 2ch-first determinism — LANDED at the live path (SRC)

The live capture device selection is deterministic and 2ch-first:
- `audio/device_select.py::select_master_input` (`:133`): ranked, exact `BlackHole 2ch` first (`_BLACKHOLE_EXACT = "blackhole 2ch"` `:75`), then any other BlackHole variant (`:139`), raises `MasterCaptureNotFoundError` (`:125`) rather than grabbing the controller/mic if no BlackHole input exists. Docstring `:12-28` records the founder-hit root cause (naive substring scan grabbed the controller).
- `platform/_audio_macos.py:438` — the macOS auto-master candidate sort uses `exact_2ch = 1 if name == "blackhole 2ch" else 0` as the discriminator with RMS only as the tiebreaker (`:441-447`). Explicit override of `BlackHole 16ch`/`64ch` is honored exactly and not rewritten back to 2ch (`:595-615`).
- Native-rate capture: `_audio_macos.py` reads `sd.query_devices(idx)['default_samplerate']` pre-open (`:61-74`) and wraps the input callback to resample device-native-rate buffers (`:110`). The 44100-vs-48000 BlackHole sanity guard is `:9-13`.
- Self-hear guard intact: `audio/constants.py:43 PASSTHROUGH_GAIN = 0.0` (silent passthrough, stream stays alive but does not mirror BlackHole→speakers).

**Verdict: LANDED (SRC).** The live engine selects a deterministic, 2ch-first master input.

---

## 5. Route-doctor RMS-flip (W5) — PARTIAL, still DARK in the `top_signal` fallback

W5 in BACKEND-WIRING-EXIT-MAP asked for `1 if name=="blackhole 2ch" else 0` as the FIRST sort key at `scripts/learn_live_readiness.py:922` AND the `silent_48k_loopback_fallback` ranker. Current state at HEAD:

- **PRIMARY recommend path = FIXED.** `recommend_auto_master_input` (`:1880`) first tries `_auto_master_candidate_evidence` candidates (`:1892`) and returns the first one that is `signal AND rate_ok AND sampled` (`live_candidates`, `:1898-1915`). Those candidates are scored by `_auto_master_candidate_evidence::score` (`:1825-1838`) which ranks `signal → rate_ok → exact 2ch (:1831) → saved_rekordbox → macos_output → loopback → any-blackhole (:1835) → rms → peak`. This is the strong deterministic 2ch-first ranker; the RMS-flip is gone here.
- **FALLBACK branch = STILL DARK.** When no candidate is fully `signal+rate_ok+sampled`, `recommend_auto_master_input` falls to the `top_signal` branch (`:1917-1932`), and `top_signal` comes from `check_capture_matrix` whose sort at `:922` is **purely `(rms, peak)` with NO 2ch / blackhole discriminator**. On a silent-but-routed rig (the common keystone-prep state: device routed, no deck playing yet), `top_signal` can name whichever device sampled marginally higher RMS noise — the exact run-to-run flip W5 names. The `silent_48k_loopback_fallback` ranker (`:2009-2031`) WAS partially fixed: it now uses `1 if "blackhole" in name else 0` as the first key (`:2019`) — but that is ANY BlackHole, not exact 2ch over 16ch/64ch.
- The pure-display helper `_preferred_loopback_route_name` (`:1341-1355`) HAS the full 2ch-aware sort (exact-2ch `:1347` → any-blackhole `:1348` → 48k `:1349` → rms/peak).

**Verdict: PARTIAL / CLAIMED-BUT-DARK.** The primary path is deterministic and 2ch-first; the `top_signal` fallback at `:922` is the one remaining RMS-flip site and it CAN drive a recommendation when no fully-live 2ch candidate exists. The exact W5 fix (add the 2ch discriminator as the first sort key at `:922`) is NOT landed. Risk: an operator copies a coin-flip device into the keystone capture. Engine-helper lane; one-line fix; do NOT touch the morning `a6625caa` fixes already present.

---

## 6. MIDI profile count — 11 confirmed; docs undercount = CLAIMED-BUT-DARK

11 JSON profiles in `src/vibemix/midi/profiles/`:
`hercules_inpulse_300`, `hercules_inpulse_300_mk2`, `hercules_inpulse_500`, `numark_party_mix_live`, `pioneer_ddj_400`, `pioneer_ddj_1000`, `pioneer_ddj_flx4`, `pioneer_ddj_flx6`, `pioneer_ddj_flx10`, `pioneer_ddj_sx3`, `pioneer_xdj_rx3`. The single-source catalog is `midi/profiles/*.json`. CLAUDE.md, `README.md`, `docs/midi-controllers.md`, `docs/midi-mapping.md` say "10" / "~10" — **doc/copy undercount (W16a), CLAIMED-BUT-DARK** (no product impact; honesty/partner-copy item). MIDI ingest itself: single mido daemon listener (CLAUDE.md threading contract), `midi/state.py::handle_msg` (`:309`) the canonical ingest, `MidiEvent` ring (`:174`) additive.

---

## 7. MIDI activity probe (idle != active) — LANDED (SRC)

`midi/activity.py::classify_controller_midi_activity` (`:7-49`) is honest: an open OS port (`connected=True`) alone is NOT "active". It requires actual frames → mapped events → moves: returns `connected_no_midi_traffic` when `messages==0` (`:41-42`), `midi_traffic_unmapped` when `events==0` (`:43-44`), `midi_events_no_moves` when `moves==0` (`:45-46`), and only `active` when all three are nonzero (`:47-48`). Docstring `:12-16` states "an open port only proves the OS port opened." Idle != fault, idle != active. Confirmed LANDED.

---

## 8. macOS screen-watch (W15) — NOT-STARTED, still djay-only

`platform/_screen_macos.py` is hardcoded to djay:
- `_find_djay_window_bounds(app_name_substring="djay")` (`:121`).
- `ScreenMacOS.find_window_bounds` (`:322`) just delegates to `_find_djay_window_bounds` (`:323`).
- The live capture loop calls `_find_djay_window_bounds("djay")` (`:470`).
- Startup banner `:465`: `screen vision: ScreenCaptureKit @ ~1fps -> screen_buf (djay-only crop)`.
- **No `find_dj_window` method, no `_DJ_HINTS` tuple.**

Windows HAS the full coverage: `_screen_windows.py:64 _DJ_HINTS = ("djay", "serato", "traktor", "rekordbox", "virtualdj")`, `find_dj_window()` (`:191`) iterates them in priority order, banner `:269` "DJ-app crop via 5-app hint list".

**Verdict: NOT-STARTED (W15).** On Mac the vision layer is DARK for Rekordbox/Serato/Traktor/VirtualDJ while README claims app-agnostic. `_find_djay_window_bounds` is already generic on its `app_name_substring` arg, so the fix is to mirror the Windows `_DJ_HINTS` + `find_dj_window` and re-point `:470`/`:465`. Engine lane. SRC/PKG/LIVE all DARK for non-djay Mac vision.

---

## 9. NI S2-MK3 HID ingest seam (W16) — NOT-STARTED (post-ship, correct)

`platform/_hid_macos.py` decodes S2-MK3 HID reports into canonical `MidiEvent` records (`decode_report` `:131`, `_decode_buttons_and_jogs` `:166`, `_decode_scalars` `:212`), `list_s2_mk3_devices` (`:241`), `start_s2_mk3_listener(on_event: Callable[[MidiEvent], None])` daemon loop (`:319-333`). **Zero callers** outside the module (grep `start_s2_mk3_listener|list_s2_mk3_devices` across `src/vibemix/**` excluding `_hid_macos.py` = empty). `midi/state.py::ControllerState` has only `handle_msg(msg)` (`:309`) for raw mido — **no public `apply_event(ev: MidiEvent)` seam** to push a decoded HID event. So decoded S2-MK3 events have nowhere to go.

**Verdict: NOT-STARTED, correct as post-ship (W16).** The decoder is built + import-light + tested but the ingest seam is missing by design until after v1. Confirmed DARK across all tiers.

---

## 10. R10 — recorder → evidence_registry wire — STILL DARK

`audio/recorder.py::VoiceRecorder.__init__` accepts `evidence_registry: object | None = None` (`:198`) and, on close (`:541-561`), snapshots it to `<session_dir>/evidence_registry.json` ONLY if it was passed (`:549 if self._evidence_registry is not None`). At HEAD the live recorder is constructed WITHOUT it:

`__main__.py:1274  recorder = VoiceRecorder(root=recordings_root)`  — **no `evidence_registry=` kwarg.**

This is the SAME recorder object threaded everywhere (`active_recorder=recorder` to `SessionLoop` `:2235`, into `_activate_session` agent build `:1816/:1861`, the playback sink `:2837`). `SessionLoop` receives `evidence_registry=evidence_registry` separately (`:2236`) but that is a different consumer — it does not back-fill the recorder. So `evidence_registry.json` is never written → debrief drills error, all long-session citations resolve `found=false`.

**Verdict: STILL DARK (R10).** Single-kwarg fix: `VoiceRecorder(root=recordings_root, evidence_registry=evidence_registry)` at `:1274` (the `evidence_registry` object exists in scope by then). Trivial, high-value for debrief honesty. SRC dark, PKG/LIVE dark.

---

## 11. set_brain BYO handler (decision #2 client) — LANDED (SRC)

`session_loop.py::_on_settings_set_brain` (`:486-545`): validates mode in `{direct, proxy}` (`:490`, IpcError on bad mode `:491-499`), validates key is a string when present (`:501-512`), persists via `persist_brain_settings(self.config_store, mode=…, gemini_api_key=…, env_path=brain_env_path())` (`:515-520`), acks with `SettingsBrainAck.make(ok, mode, key_set, restart_required=True)` **without echoing the secret** (`:535-544`), error path also strips the key (`:523-532`). `config_store.persist_brain_settings` (`:215`) writes the direct-mode key to `brain_env_path()` (`:169`) only when mode==direct and a key is given (`:224`). Default `llm_mode` is `proxy` for fresh installs (config_store comment `:106-111`), default `tts_engine` is `chatterbox` (`:65`, `_SUPPORTED_TTS_ENGINES` = frozenset of just that, `:66`).

**Verdict: LANDED + committed (SRC).** Decision #2 client side confirmed. Proxy-live + funded is a Kaan/Bravoh-ops flag, unverifiable read-only.

---

## 12. Graceful no-key (decision #2) — LANDED (SRC)

No fresh-user no-key crash. `__main__.py`: invalid `VIBEMIX_LLM_MODE` still `sys.exit`s (`:1143`) — that is a config typo, not a no-key path. The proxy/brain setup failures set `brain_unavailable_reason` and log (`:1155`, `:1175-1179`) rather than exit. On Start, if `brain_unavailable_reason is not None`, the session prints "brain unavailable … remaining idle until Stop" and waits (`session_loop`/`__main__.py:1723-1731`) — no crash, honest idle. `brain_available = brain_unavailable_reason is None` (`:2393`). The only boot `sys.exit(3)` calls (`:1517`, `:1573`) are the **BlackHole audio-device-missing FATAL** with a `brew install blackhole-2ch` hint — a deliberate hard requirement, not the no-key crash. (`:2566` is an OpenRouter-flag guard, dev-only.)

**Verdict: LANDED (SRC).** The fresh-user no-key crash the early maps named is gone; degrades to honest idle.

---

## Ship-relevant runtime-io next moves (verified ordering)

1. **R10 one-kwarg wire** — add `evidence_registry=evidence_registry` to `VoiceRecorder(...)` at `__main__.py:1274`. Trivial; un-darks debrief citations. (engine/backend lane)
2. **W5 route-doctor `top_signal` flip** — add `1 if name=="blackhole 2ch" else 0` as the FIRST sort key at `learn_live_readiness.py:922` (mirror `_preferred_loopback_route_name:1347`). The only remaining RMS-flip that can reach a recommendation. (engine-helper lane; do NOT touch `a6625caa`)
3. **W15 macOS screen-watch app-agnostic** — mirror `_screen_windows.py` `_DJ_HINTS` + `find_dj_window` into `_screen_macos.py`, re-point `:470`/`:465`. README honesty. (engine lane)
4. **Doc copy 10→11 MIDI profiles** — CLAUDE.md/README/docs. (copy)
5. **Dead-after-return body in `__main__.py` (`:2316-~4100`)** — flag for removal; not a bug (unreachable after `:2314 return`) but ~1800 dead lines make every line-number reference treacherous. Owner-call whether to prune now or post-ship. (backend-boot lane, single-owner `__main__.py`)
6. W16 NI HID ingest seam = post-ship, correct to leave.

## Tier recap (runtime-io)

- **SRC:** start-gate, idle-cold, set_brain, proxy-default+graceful, single socket, 2ch live-path determinism, native-rate, MIDI activity honesty = GREEN/LANDED. R10, W5 `:922`, W15, doc-count = dark-but-not-test-failing.
- **PKG:** unverified at HEAD — no fresh signed HEAD arm64 DMG; `dist/vibemix-0.0.1.dmg` is unsigned + ~190 commits stale (per ING-07). Start-gate seam files (`__main__.py`, `session_loop.py`) ARE committed at HEAD now, so the sidecar-freshness gate's `source_dirty` blocker that ING-07 named for them is satisfied AT THE COMMITTED LAYER — but the working tree still shows those files modified (236 dirty status entries), so a build from the dirty tree would still trip `source_dirty` until a clean checkout/commit sweep.
- **LIVE:** the keystone (a real grounded line in the cloned voice over real audio) is untouched — Kaan-only, no autonomous lane.
