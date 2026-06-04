# ING02 — START GATE + model lifecycle (adversarial ship-ingest)

**HEAD read at: `d7d5337a175ac90612702c3adda4d17aa3918899`** (branch `ux-redesign-impeccable`, 2026-06-04). The SHIP-MAP-MASTER was synthesized at `7ac35a84`; the tree has advanced ~15 commits since (voice prefetch `0e5590c5`, start-gate idle-cold lock `18dc95cb`, chatterbox preflight `eec239ac`, boot smoke align `02ffb7c0`, device-default isolation `d7d5337a`). Several map claims tagged DARK are now LANDED at HEAD — corrected inline below.

Proof tiers, never conflated: **SRC** (green tests on source) ≠ **PKG** (in a signed DMG at HEAD) ≠ **LIVE** (a real user reaches it). `test-passing-but-dark = 0`. READ-ONLY pass: no product code edited, no sidecar launched.

---

## Headline verdict

The four locked decisions are **all real at HEAD, not just claimed.** Three of four (VOICE source-side, BRAIN, START GATE) are LANDED at the SRC tier with both IPC ends wired and tests green; STREAK is correctly NOT-STARTED. The map's two named #1 blockers are BOTH resolved: the fresh-user crash is gone (SRC), and voice reachability is now wired source-side (mlx-audio extra + ref bundle + first-run fetch + env-seed + gate-swap all landed). The ship gap is no longer "build" — it is **PKG/LIVE only**: the dirty seam files must commit, a fresh signed arm64 DMG must be built at HEAD, and the keystone LIVE capture (a stranger hears a grounded Chatterbox line) has never happened. Plus one real residual: the **README is partner-copy-DARK** — the 4 CI gates pass but the body still leaks `api.altidus.world`, names "Gemini", references the NUKED "MOSS voice path" as if live, points at the old `ozzaii/vibemix` org, uses `security@bravoh.com`, and dumps the internal Phase/ear-pass feature matrix.

---

## DECISION 1 — VOICE = Chatterbox only, MOSS nuked

**Verdict: LANDED (SRC). PKG/LIVE-gated on commit + DMG + keystone.** This contradicts the map's "#1 blocker = voice reachability (`mlx_audio` not an extra)" — that gap has since closed at HEAD.

Sub-claim breakdown:

| Wire | file:line | SRC verdict | flag |
|------|-----------|-------------|------|
| MOSS nuked — `local_tts.py` deleted | `src/vibemix/agent/local_tts.py` absent | gone | LANDED |
| `tts_chain` Chatterbox-only, no MOSS/cloud fallback | `agent/tts_chain.py` (Chatterbox-only build) | — | LANDED |
| `DEFAULT_TTS_ENGINE="chatterbox"`, only supported engine | `runtime/config_store.py:65-66` (`_SUPPORTED_TTS_ENGINES = frozenset({DEFAULT_TTS_ENGINE})`) | — | LANDED |
| `engine_selected()` defaults chatterbox | `agent/chatterbox_tts.py:119-121` (env default `"chatterbox"`) | — | LANDED |
| **mlx-audio as a pyproject extra (Apple-only)** | `pyproject.toml:162,167` (`"mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'"`) | — | **LANDED** (was the map's #1 blocker) |
| ref clip bundled as PyInstaller `datas` | `vibemix-core.macos.spec:36,307` (`collect_chatterbox_ref_datas()`); helper `scripts/dist/chatterbox_bundle.py:30-43` | — | LANDED |
| `resolve_ref_path()` prefers bundled, falls back to dev-cache | `agent/chatterbox_tts.py:106-116` (env override → bundled `models/chatterbox/cohost_voice_ref.wav` → `_DEV_REF`) | — | LANDED |
| first-run model fetch via `install_chatterbox_model()` | `library/model_assets.py:490`; registered in `--install chatterbox|all` at `:857,859`; pinned repo `mlx-community/chatterbox-turbo-8bit` rev `2f2e21a0…` at `:34-35` | — | LANDED |
| wizard pre-fetch trigger (download before first set, never mid-set) | `runtime/wizard.py:436` → `_prefetch_chatterbox_model()` `:499-535` (offline → voiceless banner, not a stall) | — | LANDED |
| env-seed `VIBEMIX_TTS_ENGINE` from config (launchd strips env) | `__main__.py:1063` and `:1434` (`os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine)`) | — | LANDED |
| release gate swap `--require-moss-source` → `--require-chatterbox-source` | `scripts/dist/pretag_check.sh:109,111,113`; `.github/workflows/release.yml:355,399,426,541` (all sites `--require-chatterbox-ref --require-chatterbox-source`) | — | LANDED |
| gate body actually validates Chatterbox HF source (not a stub) | `scripts/dist/check_sidecar_bundle_ready.py:180-224` `chatterbox_release_source_ready()` (verifies pinned revision SHA + required sibling files at HF API) | — | LANDED |
| voiceless-honest-banner on no-GPU | `chatterbox_tts.py:124-143` `chatterbox_available()`/`chatterbox_unavailable_reason()` return False + actionable reason (no `mlx_audio`, no ref, or model not cached); `__main__.py:1446` prints `-> tts engine: chatterbox armed (loads on Start)` else the unavailable reason to stderr | — | LANDED |

**Adversarial gaps found (real, but not SRC-build gaps):**
- **`collect_chatterbox_ref_datas()` returns `[]` (not an error) if the ref clip is absent at build time** (`chatterbox_bundle.py:32-43`). On its own that would silently ship a voiceless DMG. **MITIGATED:** the release path passes `--require-chatterbox-ref`, and `chatterbox_release_ref_ready()` (`check_sidecar_bundle_ready.py:168-177`) hard-fails the pretag gate if the bundled ref is missing/zero-length. So a HEAD DMG built off the release path CANNOT silently ship voiceless. A hand-rolled `pyinstaller` invocation that skips the gate could. Flag: PKG-discipline, not a code gap.
- **The 675MB model is NOT in the DMG** (Kaan-decided): it is first-run fetched from the public HF repo by the wizard. `chatterbox_available()` is False until that fetch completes (`:130` `chatterbox_model_cached(...)`). On a real fresh launch the voice is voiceless until the wizard download succeeds — by design, but it means LIVE voice depends on a successful first-run network fetch, not the DMG alone.
- **Tests pass by mocking `mlx_audio`** — 73 chatterbox/sidecar/start-gate tests green, but none prove real `mlx_audio.load_model` synthesis (the engine seam `ChatterboxEngine` exists precisely to test without mlx-audio, `chatterbox_tts.py:146-201`). The voice has SRC + PKG-gate coverage but **zero LIVE coverage** — no run with nonzero `voice_rms`. This is the keystone, Kaan's hand on the rig.

**Tier verdict: SRC = GREEN. PKG = blocked on committing dirty `__main__.py` (source_dirty fails the freshness gate) + a fresh signed arm64 DMG at HEAD. LIVE = 0 (never spoken).**

---

## DECISION 2 — BRAIN = hosted Bravoh proxy DEFAULT, client flips direct→proxy, set_brain BYO, no-key graceful

**Verdict: LANDED (SRC). Proxy credits = Kaan/Bravoh-ops, unverifiable read-only.**

| Wire | file:line | verdict |
|------|-----------|---------|
| client default `llm_mode="proxy"` | `runtime/config_store.py:271` (`llm_mode: str = "proxy"`); boot reads `(load_config().llm_mode or "proxy")` at `__main__.py:1136`, fresh-install fallback `"proxy"` at `:1138` | LANDED |
| no-key direct → proxy fallback (NO `sys.exit`) | `__main__.py:1147-1166` — `mode=="direct"` + unset `GEMINI_API_KEY` flips `mode="proxy"`, prints honest stderr line, never exits | LANDED |
| total brain failure degrades to honest banner | `__main__.py:1169-1181` proxy setup/network error → `brain_unavailable_reason` set + `_log_brain_unavailable`; `_activate_session` (`:1723-1731`) then runs idle until Stop, no crash; the only `sys.exit` near brain (`:1142`) is on an INVALID mode literal, not on a missing key | LANDED |
| register → JWT | `agent/jwt_cache.py` `get_or_refresh_jwt`, base `https://api.altidus.world` (`__main__.py:1139`) | LANDED |
| proxy genai client build | `__main__.py:1740-1742` `build_proxy_genai_client(jwt, proxy_base_url)` + `build_llm(mode="proxy", ...)` | LANDED |
| `ipc.settings.set_brain` BYO handler | `runtime/session_loop.py:288` `register_handler` → `_on_settings_set_brain` `:486-535` (validates mode ∈ {direct,proxy}, persists via `persist_brain_settings`, writes `GEMINI_API_KEY` to `brain_env_path()` `:208-225`, acks without echoing the secret) | LANDED |

**Adversarial note:** the in-GUI Gemini key field shipped under this decision collides head-on with the Phase-33 "never ship a key surface" CI gate (`tests/security/test_no_api_key_surface.py`). The map flagged this RED. **At HEAD this test is GREEN** (it ran clean in the 57-test README+security pass) — so either the gate was scope-narrowed/retired (Kaan D2) or the BYO field's surface no longer trips it. Either way it no longer blocks `full-test-matrix`. 26 brain/set_brain/proxy/no-key tests pass.

**Tier verdict: SRC = GREEN. LIVE = the proxy register→JWT→gemini-3.5-flash→200 was verified same-day per the maps (cannot re-verify read-only without launching). Credits top-up + per-client rate cap = Kaan/Bravoh-ops flag, not a code wire.**

---

## DECISION 3 — START GATE + model lifecycle (SHIP-CRITICAL)

**Verdict: LANDED end-to-end (SRC), BOTH IPC ends wired.** This is the headline correction to the maps, which had the backend handler DARK. It is no longer dark.

### Backend (the half the maps said was absent)
- `register_handler("ipc.session.start", self._on_session_start)` — `runtime/session_loop.py:278`
- `register_handler("ipc.session.stop", self._on_session_stop)` — `:279`
- `_on_session_start` — `:331-354`: idempotent (returns if already active `:341`), calls the wired `_session_start` callback, emits `IpcError` on failure (no ack by design — schema is ack-less, shell repaints optimistically).
- `_on_session_stop` — `:356-374`: no-op if not active `:361`, calls `_session_stop`, error-guarded.
- Callbacks injected from `main()`: `session_start=_start_live_session, session_stop=_stop_live_session, session_is_active=_is_live_session_active` — `__main__.py:2238-2240`.

### main() idle/activate split (the lifecycle)
- **Idle = cold.** `main()` boots ARMED: `print("-> start gate: armed (idle; capture/reactions/model load wait for Start)")` — `__main__.py:2275`. At idle only the ws bus + parent-watch + prewarm task run; the heavy graph (LiveKit session, TTS instance, agent, audio/MIDI streams) is built ONLY inside `_activate_session` — `:1704-…`, allocated lazily at `:1709-1719`, brain/TTS deps via `_ensure_live_llm_tts_deps()` `:1722`, Chatterbox TTS instantiated `:1751-1755`.
- **Start activates.** `_start_live_session` — `:2172-2186`: creates the `_activate_session` task, waits up to 30s for `started_event`, re-raises activation errors.
- **Stop releases.** `_stop_live_session` — `:2188-2198`: sets the run-stop event, awaits the task, clears it. The activate body's `finally` parks the graph (`-> session parked; live graph released` near `:2170`).
- **Cold bus view at idle.** `_RunGatedMusicState` / `session_state_view` — `:2248`: the broadcaster reads cold values while armed; `brain_available=_DynamicBool(_is_live_session_active)` `:2265` so a paused/armed deck does NOT falsely flip to a fault (Invariant #5 honored).
- **Silent pre-warm hook.** `_silent_prewarm_hook` — `:2200-2209`: after 0.25s, if not active, runs `_ensure_live_llm_tts_deps()` + `_ensure_live_session_deps()` (IMPORTS only) and prints `-> start gate prewarm: live imports ready (models still cold)`. Models stay cold; only Python imports warm. Scheduled at `:2272-2274`.

### Frontend (both ends)
- Default state boots ARMED: `session/state.ts:267` `runState: "armed"` (with comment: "the app boots ARMED … pressing Start flips to running"). The `?? "running"` fallback at `render-loop.ts:436` only applies when a bridge snapshot omits runState; the default singleton is armed.
- Start button: `SessionLayout.ts:1046-1062` (`data-action="start"`, `aria-label="start co-host"`), click handler `:1055-1058` flips `data-runstate="running"` optimistically (CLAUDE.md repaint rule) then calls `onStart`.
- Stop affordance: `SessionLayout.ts:972-982` flips `data-runstate="armed"` then `onStop`. CSS gates the armed/running surfaces `:428-433`.
- `onStart`/`onStop` bound in the render-loop: `render-loop.ts:437-438` → `sessionStartHandler` `:73-80` (`emitIpc("ipc.session.start", {})`) / `sessionStopHandler` `:86-93` (`emitIpc("ipc.session.stop", {})`), both optimistic-then-emit, fire-and-forget.
- Schema both-ends-typed: `messages.schema.json:1430-1463` (the `$comment` even names `register_handler('ipc.session.start', _on_session_start)` as the backend contract); codegen-synced in `messages.ts:31-32,324-330` (`SessionStart`/`SessionStop`).

**ipc-wiring lens result: BOTH ends present.** Sender = `render-loop.ts` `emitIpc`; handler = `session_loop.py` `register_handler` → real `_on_session_start`/`_stop` → real `_start_live_session`/`_stop_live_session` → `_activate_session`. Not a one-ended dead type.

**Adversarial gap:** the start handler has NO ack envelope (by schema design); the shell repaints optimistically and the backend reflects authoritative run-state on the next `ipc.session.snapshot`. I did NOT find an explicit snapshot emit that carries `runState` back — so if the backend activation FAILS after the optimistic flip, the deck stays visually "running" while the backend is idle (the `_on_session_start` failure path emits `IpcError`, not a run-state correction). This is a UX-honesty edge, not a ship-blocker: the maps note "no ack" is intentional. 73 start-gate/idle-cold tests green (`18dc95cb` locks idle-cold). 

**Tier verdict: SRC = GREEN (both ends, idle-cold test-locked). PKG = blocked on committing dirty `__main__.py` + `session_loop.py`. LIVE = unproven (needs a real Start→activate→Stop→release run on the rig).**

---

## DECISION 4 — STREAK robot voice (Daft-Punk Technologic), SEQUENCED behind re-grounding

**Verdict: NOT-STARTED (correct).** No `technologic`/robot-voice/vocoder code anywhere in `src/vibemix/` (the "Daft Punk" hits are unrelated genre-profile tuning comments in `audio/constants.py:2,68`). The streak signal is STILL the self-applause path: `_attach_grade_progress` (`runtime/suggestion.py:1365-1426`) grades and increments `streak` on the co-host's OWN un-played suggestion (`:1391-1404`, `streak +1`). Per decision #4 this MUST be rebound onto a cited EXECUTED transition BEFORE any robot voice fires — that rebind has not happened, so leaving the voice unbuilt is the correct sequencing. Invariant #3 risk (self-applause) persists but is dark (no voice consumes it). NOT v1-launch-critical.

---

## Residual ship gaps found this pass (precise)

1. **DIRTY TREE blocks PKG.** Modified-not-committed at HEAD: `src/vibemix/__main__.py`, `src/vibemix/runtime/session_loop.py`, `CLAUDE.md`, `tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts`, plus 2 `.planning` files; 229 untracked. The start-gate + brain edits live in these files; `check_sidecar_bundle_ready` fails on `source_dirty` until they commit. **The single owner of `__main__.py` must commit before any DMG.** Flag: PKG-blocker, not a code gap. SRC verdict: green.

2. **README is partner-copy-DARK (CI-green but policy-violating).** All 4 pinning gates PASS at HEAD (`test_readme_shape.py` + `test_readme_feature_matrix_sync.py` + grids-a11y + hero-hash; 57 tests green) — the map's "RED README gates" are now GREEN. But the gates do NOT check body prose, and the README still violates the public partner-copy policy:
   - leaks `api.altidus.world` — README.md:39, 61, 241, 259
   - names "Gemini" — :39, 61, 149, 241, 259, 269, 271, 283, 287 (policy: say "AI model")
   - references the NUKED **"MOSS voice path"** as if live — :229, 241, 271 (now factually WRONG; voice is Chatterbox/on-device)
   - `security@bravoh.com` — :63 (policy domain is bravoh.ai)
   - old org `ozzaii/vibemix` — :330 (policy org is Bravoh-ai; the badges at :42-54,94 already correctly use `bravoh-ai`)
   - internal feature-matrix dump: Phase numbers (:134,135,140-142,148-149,279), "Kaan ear-passes daily" (:69), KAAN-ACTION (:11,30,86,134,148,198,142)
   Flag: CLAIMED-BUT-DARK (the README "looks shipped" and tests pass, but it is not partner-ready). Fix is copy + a new gate, not product code. SRC verdict: gates green, content dark.

3. **Voice LIVE depends on a successful first-run HF fetch**, not the DMG alone (model is not bundled). No `voice_rms`-nonzero run exists. Keystone, Kaan-only.

4. **Start-gate has no run-state correction on activation failure** (optimistic flip can desync from a failed backend). UX-honesty edge, non-blocking.

---

## 3-tier roll-up

- **SRC:** GREEN for all four decisions. 73 start-gate/chatterbox/sidecar + 26 brain/proxy + 57 README/security tests pass at HEAD. The map's RED gates (README, no-api-key-surface) are now GREEN. MOSS fully purged from product + release path (only the stale dev util `scripts/local_tts_speak.py` remains, off-path).
- **PKG:** BLOCKED on (a) committing the dirty seam files (`__main__.py`, `session_loop.py`) — `source_dirty` fails the freshness gate; (b) a fresh signed arm64 DMG built at HEAD (`dist/*.dmg` are ~190+ commits stale, the canonical one unsigned per the maps); (c) `VIBEMIX_PRETAG_MAC_ONLY=1` to skip Windows/SignPath (D3 locked macOS-arm64-only). The MOSS→chatterbox gate-swap is DONE, so the gate no longer fails on a missing MOSS bundle.
- **LIVE:** UNCROSSED. The co-host has never spoken in the cloned voice over real audio. Voice reachability is now wired SRC-side; the remaining LIVE dependencies are the first-run model fetch + Kaan's hand on the rig for the keystone capture. The fresh-user crash is gone; proxy-default carries a no-key stranger to the brain.

**Bottom line: the build is done; the gap is commit → sign → capture.** Three of four locked decisions LANDED (SRC), STREAK correctly deferred, the two map-named #1 blockers both resolved. The honest next moves are PKG/LIVE/copy, not engineering: commit the dirty seam files, fix the partner-copy-DARK README (and gate it), build+sign a fresh arm64 DMG at HEAD, then Kaan crosses the keystone.
