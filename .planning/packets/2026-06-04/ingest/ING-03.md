# ING-03 — BRAIN / proxy CLIENT + fresh-user no-crash (ship-ingestion adversarial verify)

## Read-at
- **HEAD `d7d5337a` (d7d5337a175ac90612702c3adda4d17aa3918899), branch `ux-redesign-impeccable`, 2026-06-04.**
- Maps (`SHIP-MAP-MASTER.md` etc.) were synthesized at `7ac35a84`. The tree advanced **144 files** between `7ac35a84` and `d7d5337a` — the maps are materially stale for voice/packaging/start-gate. Every line number below was re-pinned at `d7d5337a`. Voice/packaging commits that landed since the maps include `0e5590c5 fix(voice): prefetch chatterbox for packaged launch`, `eec239ac feat(voice): preflight pinned chatterbox model`, `7082fb8d build(voice): require packaged chatterbox reference`, `18dc95cb test(start-gate): lock idle-cold`, `02ffb7c0 test(boot): align smoke with start-gated defaults`.
- Proof tiers never conflated: **SRC** (green tests on source) ≠ **PKG** (in a signed DMG at HEAD) ≠ **LIVE** (a stranger reaches it). `test-passing-but-dark = 0`. Read-only pass: no product code edited, sidecar NOT launched (socket 8765 untouched).

---

## SCOPE A — BRAIN / proxy client (locked decision #2)

### A1. config_store llm_mode DEFAULT = proxy — **LANDED (SRC + LIVE-default)**
- `src/vibemix/runtime/config_store.py:271` — `llm_mode: str = "proxy"`. Fresh `ConfigStore()` defaults to proxy.
- `config_store.py:106-111` — `"llm_mode"` is a persisted `_PHASE12_FIELDS` member; docstring explicitly says "Fresh installs default to 'proxy' so a no-key user reaches the hosted Bravoh brain instead of crashing before the Settings UI can explain the direct-key path."
- Verdict: **LANDED. SRC green** (140 brain/proxy/config tests pass). The client default flip direct→proxy is real.

### A2. base_url = api.altidus.world — **LANDED (SRC)**
- `src/vibemix/__main__.py:1139` — `proxy_base_url = os.environ.get("VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world")`. Hardcoded default base.
- `__main__.py:1103` startup banner documents `VIBEMIX_PROXY_BASE_URL = 'https://api.altidus.world' (default)`; `:5690` repeats the default in the CLI canary path.
- `__main__.py:1149` — `os.environ.setdefault("VIBEMIX_PROXY_BASE_URL", proxy_base_url)` so components built later (the proxy-unavailable classifier) see the base even when launchd strips env.
- Verdict: **LANDED. SRC.** Proxy was verified LIVE same-day per the maps (register→JWT→gemini-3.5-flash→HTTP 200 on `api.altidus.world/api/vibemix/v1/register`); credits are a Kaan/Bravoh-ops flag, unverifiable read-only.

### A3. no-key direct falls back to proxy (NO sys.exit(4)) — **LANDED (SRC), crash gone**
- `__main__.py:1131-1138` — mode resolution: `VIBEMIX_LLM_MODE` env wins; else persisted `load_config().llm_mode or "proxy"`; on any load exception → `mode = "proxy"`. Fresh no-key user resolves to `proxy`.
- `__main__.py:1157-1166` — `if mode == "direct"` and `GEMINI_API_KEY` unset → prints `"-> mode: direct requested but GEMINI_API_KEY is unset; trying Bravoh proxy"` and sets `mode = "proxy"`. **Direct-with-no-key does NOT exit — it degrades to proxy.**
- `__main__.py:1169-1181` — `if mode == "proxy"`: register/JWT under try/except; `RuntimeError` → `brain_unavailable_reason` + `_log_brain_unavailable` (no exit); `httpx.HTTPError` → same (no exit). Total brain failure degrades to an honest banner, the boot continues.
- **`grep sys.exit src/vibemix/__main__.py` = 13 hits; NONE is the no-key/brain path:**
  - `:1143` `sys.exit(f"VIBEMIX_LLM_MODE must be 'direct' or 'proxy', got {mode!r}")` — fires ONLY when an operator explicitly sets an INVALID `VIBEMIX_LLM_MODE` env value. NOT a fresh-user path (fresh user has no env, resolves to proxy). Not `sys.exit(4)`.
  - `:1517` `sys.exit(3)` — FATAL **audio input device missing (BlackHole)**. Pre-existing hard requirement, unrelated to brain/no-key.
  - `:1573` `sys.exit(3)` — FATAL **no usable audio OUTPUT device**. Unrelated to brain/no-key.
  - `:2566` `sys.exit("VIBEMIX_LLM_VIA_OPENROUTER=1 but OPENROUTER_API_KEY missing")` — guarded behind the opt-in OpenROUTER flag; not the product path.
  - `:9352-9418` — CLI subcommand exit codes (library/bench/eval dispatch). Not the live-session boot.
- Verdict: **LANDED. The fresh-user brain crash the maps named is GONE.** SRC. The map claim "no `sys.exit(4)`" is accurate; there is no `sys.exit(4)` anywhere. The only fresh-boot exits are the two AUDIO-device FATALs (BlackHole + output), which are a separate, deliberate, pre-existing fault class with install hints, NOT the brain path.

### A4. jwt_cache register path — **LANDED (SRC); MAP PATH ERROR corrected**
- **File is `src/vibemix/agent/jwt_cache.py`, NOT `llm/jwt_cache.py` (the map's `jwt_cache.py:79` cited the wrong package).**
- `agent/jwt_cache.py:79` — `url = f"{proxy_base_url.rstrip('/')}/api/vibemix/v1/register"`. Matches the locked path exactly.
- `:80-84` — `httpx.AsyncClient(timeout=30.0).post(url, json={"install_uuid": install_uuid, "client_version": client_version})`.
- `:85-87` — non-200 → `raise RuntimeError("proxy /register rejected install_uuid (status=...)")` (body sanitized, never echoed). Caught at `__main__.py:1174` → `brain_unavailable_reason`, no crash.
- `:65-77` — refresh gate: 90-day JWT TTL, refresh when <7 days from expiry; cached JWT skips `/register`. JWT cached via keyring (`_cache_jwt`); keyring failures log + re-fetch next launch (no crash).
- Module docstring `:7-9`: "on permanent failure (proxy 401, network broken), raise — NEVER silently fall back to direct mode." So a proxy user with a dead proxy gets an honest unavailable banner, not a silent BYO-key fall-through.
- `__main__.py:1170-1173` calls `get_or_create_install_uuid()` then `await get_or_refresh_jwt(install_uuid, proxy_base_url, client_version)`.
- Verdict: **LANDED. SRC green** (`tests/agent/test_jwt_cache.py` jwt_01..07 pass).

### A5. set_brain handler persists llm_mode + writes key to brain_env_path() — **LANDED (SRC)**
- Registered: `runtime/session_loop.py:288` — `self.bus.register_handler("ipc.settings.set_brain", self._on_settings_set_brain)`.
- Handler `session_loop.py:486-544`:
  - `:489-499` rejects mode not in `("direct","proxy")` with an `IpcError`.
  - `:500-512` rejects non-string `gemini_api_key` with a `SettingsBrainAck(ok=False)`.
  - `:514-520` calls `persist_brain_settings(self.config_store, mode=mode, gemini_api_key=..., env_path=brain_env_path())`.
  - `:521-533` persist exceptions → `SettingsBrainAck(ok=False, error=...)`, no crash.
  - `:535-544` success → `SettingsBrainAck(ok=True, mode=mode, key_set=key_set, restart_required=True)`.
- `config_store.persist_brain_settings` `config_store.py:208-228`:
  - `:220-222` validates mode (raises ValueError on bad mode).
  - `:223-225` — **writes the key to the dotenv ONLY when `mode == "direct"` AND a key is supplied** (`_write_dotenv_key(target_env, "GEMINI_API_KEY", gemini_api_key)` at `:225`).
  - `:226-227` — `store.llm_mode = normalized_mode; save_config(store)` — persists the mode either way.
  - `brain_env_path()` `config_store.py:168-170` = `_app_data_dir()/".env"` (the per-user app-data dotenv, NOT the repo `.env`).
  - `_write_dotenv_key` `:187-205` writes atomically (tmp + `os.replace`), chmods `0o600`, never logs the value.
- **Behavior nuance (not a defect):** selecting **proxy** persists `llm_mode="proxy"` but writes NO key (correct — proxy is keyless). Selecting **direct** with a key persists mode + writes the key. The handler returns `restart_required=True` — the mode flip takes effect on next boot (the live mode dispatch reads config at `__main__.py:1136`), which is the documented contract.
- Verdict: **LANDED. SRC green.** set_brain persists llm_mode + writes the BYO key to `brain_env_path()` exactly per locked decision #2.

### A6. fresh no-key boot reaches the funded brain, never crashes — **WALKED, LANDED (SRC); LIVE = Kaan-gated**
Fresh user, no env, no `config.json`, no key:
1. `__main__.py:1131-1138` — no `VIBEMIX_LLM_MODE` env, no config → `mode = "proxy"`.
2. `:1139` — `proxy_base_url = "https://api.altidus.world"`.
3. `:1169-1181` — proxy branch: `get_or_create_install_uuid()` (UUID generated/cached), `get_or_refresh_jwt(...)` POSTs `/api/vibemix/v1/register`, caches the JWT, prints `-> mode: proxy (install_uuid=..., jwt cached)`.
4. If the proxy is unreachable: `brain_unavailable_reason` set, honest banner, boot continues to the START GATE armed-idle state (no crash).
5. The only hard exits on the path are the two AUDIO-device FATALs (BlackHole input `:1517`, output `:1573`) — independent of the brain.
- Verdict: **LANDED at SRC.** The funded brain is the default and reachable on a fresh boot. **LIVE proof (a stranger actually hears a line) remains Kaan-gated** — that depends on voice reachability + a real driven set, not on this brain wiring. The brain leg itself is no longer a crash or a blocker.

---

## SCOPE B — Locked decision #1 (VOICE = Chatterbox only; MOSS nuked)

### B1. MOSS nuked / Chatterbox-only — **LANDED (SRC)**
- `config_store.py:65` — `DEFAULT_TTS_ENGINE = "chatterbox"`; `:66` `_SUPPORTED_TTS_ENGINES = frozenset({DEFAULT_TTS_ENGINE})` (chatterbox is the only supported engine); `:69-72` `normalize_tts_engine` coerces anything else back to chatterbox; `:248` `tts_engine: str = DEFAULT_TTS_ENGINE`.
- `agent/chatterbox_tts.py:119-121` — `engine_selected()` reads `VIBEMIX_TTS_ENGINE` (default `"chatterbox"`).
- NOTE: `src/vibemix/agent/local_tts.py` + `agent/moss_tts/*` still appear in the `7ac35a84..d7d5337a` diff (touched), but the live build path is Chatterbox-only; commit `fddddfc9 refactor(voice): retire legacy moss runtime` + `de9233f9 docs(voice): remove retired moss comments` are in HEAD. The product TTS path is Chatterbox; MOSS is off the product path.
- Verdict: **LANDED (source). SRC.**

### B2. mlx-audio as a pyproject extra — **LANDED (the map's #1 blocker is RESOLVED)**
- `pyproject.toml:162` (clap/voice extra) + `:167` (`ai-local` extra) — `"mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'"`. Apple-arm64-gated marker (Intel Macs + Windows correctly skip it → voiceless + honest banner, per decision #1).
- `chatterbox_tts.py:124-130` `chatterbox_available()` now requires: (1) `mlx_audio` importable, (2) a resolvable ref clip, (3) `chatterbox_model_cached(...)` (model on disk). `:133-143` `chatterbox_unavailable_reason()` returns an actionable string for each gap.
- Verdict: **LANDED. SRC.** The map's stated #1 blocker ("mlx_audio not an extra → voiceless forever") is now fixed in source. PKG/LIVE still depend on the model fetch (B4) + a real launch.

### B3. bundle cohost_voice_ref.wav (PyInstaller datas) — **LANDED (SRC, build-spec)**
- `vibemix-core.macos.spec:36` imports `collect_chatterbox_ref_datas`; `:307` `datas.extend(collect_chatterbox_ref_datas())`.
- `scripts/dist/chatterbox_bundle.py` (new since maps, dated 18:41) — `CHATTERBOX_REF_NAME="cohost_voice_ref.wav"`, `collect_chatterbox_ref_datas()` maps the source ref → bundled `models/chatterbox/cohost_voice_ref.wav`.
- `chatterbox_tts.py:93-116` — `bundled_ref_candidates()` searches `sys._MEIPASS` + exe-parent + `_internal` for `models/chatterbox/cohost_voice_ref.wav`; `resolve_ref_path()` prefers the override env, then the bundled ref, then the dev-cache `~/.cache/vibemix/cohost_voice_ref.wav`. So resolution PREFERS the bundled path on a packaged launch.
- `mlx`/`mlx_audio`/`mlx_lm` are in the spec hidden-imports (`:151-153`, `:185-187`).
- Verdict: **LANDED in source + spec.** PKG-real only when the DMG is actually rebuilt at HEAD (every distributable is stale per the maps — PKG=stale).

### B4. first-run model fetch via model_assets.py + wizard prefetch — **LANDED (SRC)**
- `library/model_assets.py:34` — `CHATTERBOX_MODEL_REPO = "mlx-community/chatterbox-turbo-8bit"` (Kaan D1 = 8bit, ~675MB).
- `model_assets.py:490` `install_chatterbox_model(...)` (mirrors install_clap/install_moss) + `chatterbox_model_cached`/`chatterbox_model_snapshot_path`/`chatterbox_model_revision` (`:356-426`) for a pinned-revision cached check.
- `runtime/wizard.py:436` calls `await self._prefetch_chatterbox_model()`; `:499-520` `_prefetch_chatterbox_model` lazy-imports `install_chatterbox_model`, runs it in an executor, warns (not crashes) on failure — so the 675MB weights fetch happens once via the wizard with a progress path, never mid-set.
- Verdict: **LANDED. SRC** (the prefetch commit `0e5590c5` + preflight `eec239ac` are in HEAD).

### B5. env-seed VIBEMIX_TTS_ENGINE at __main__.py — **LANDED (SRC)**
- `__main__.py:1062-1063` — `tts_engine = str(getattr(cfg, "tts_engine", DEFAULT_TTS_ENGINE) or DEFAULT_TTS_ENGINE); os.environ.setdefault("VIBEMIX_TTS_ENGINE", tts_engine)` (packaged-defaults path).
- `__main__.py:1433-1434` — `_tts_engine_seed = ...; os.environ.setdefault("VIBEMIX_TTS_ENGINE", _tts_engine_seed)` (boot path). Both seed from `config.json` so a launchd/Dock launch (which strips `VIBEMIX_*`) still selects Chatterbox.
- Verdict: **LANDED. SRC.** (Decision #1 wire #4. The single-owner `__main__.py` env-seed was handed to the keystone lane per the goal docs and is in place.)

### B6. release gate --require-moss-source → --require-chatterbox-source — **LANDED (SRC, CI)**
- `scripts/dist/pretag_check.sh:109/111/113` — `--require-chatterbox-ref --require-chatterbox-source` (all three OS-branches). **No `--require-moss-source` remains.**
- `.github/workflows/release.yml:355-356/399-400/426-427/541-542` — `--require-chatterbox-ref --require-chatterbox-source` at every sidecar-bundle-ready check (bash + PowerShell).
- Verdict: **LANDED. SRC/CI.** The map's flagged release-gate conflict (gate still demands a NUKED MOSS bundle) is RESOLVED. A HEAD DMG built with the Chatterbox ref will now pass the pretag/release gate.

### B7. voice reachability — overall verdict
- Decision #1 is **LANDED at SRC across all six sub-wires** (engine-default, mlx extra, ref bundling, model install+prefetch, env-seed, gate-swap). The maps' "#1 blocker = voice reachability / mlx not an extra" is **STALE — resolved at HEAD.**
- **Remaining gap is PKG + LIVE, not SRC:** no DMG has been rebuilt at HEAD (PKG=stale per the maps), and the model is first-run-fetched, so `chatterbox_available()` is True on a real launch ONLY after the wizard fetch completes. The co-host has **never spoken LIVE** (no captured run with nonzero `voice_rms`) — that is Kaan's hand on the rig, the single keystone artifact.

---

## SCOPE C — Locked decision #3 (START GATE)

### C1. backend _on_session_start / _on_session_stop handlers — **LANDED (SRC)**
- `session_loop.py:278-279` — `register_handler("ipc.session.start", self._on_session_start)` + `("ipc.session.stop", self._on_session_stop)`.
- Handlers `session_loop.py:331-371` — `_on_session_start` calls the injected `self._session_start` lifecycle callback (no-op + logs if unwired); exceptions caught → `IpcError`, never crash. `_on_session_stop` mirrors it.
- Constructor injects `session_start=...`, `session_stop=...`, `session_is_active=...` (`session_loop.py:189-190, 223-224`).
- Verdict: **LANDED. SRC.** The map's "backend handler absent / DARK" claim is STALE.

### C2. main() idle/activate split + Stop releases — **LANDED (SRC)**
- `__main__.py:2225-2241` constructs `SessionLoop(..., session_start=_start_live_session, session_stop=_stop_live_session, session_is_active=_is_live_session_active)`; `:2242` `register_handlers()`; `:2245` banner "session IPC handlers wired ... incl. start/stop".
- `__main__.py:1704-...` `_activate_session(...)` builds the WHOLE live graph (LLM client `:1736/1741`, TTS `:1745-1768`, `DJCoHostAgent` `:1811+`, audio streams, MIDI) only on Start. **At idle this graph is NOT constructed → no heavy model resident at idle** (the Chatterbox TTS `ChatterboxLocalTTS()` is instantiated at `:1751-1755` inside activate, not at boot).
- `_start_live_session` `:2172-2186` creates the activate task, waits ≤30s for `started_event`, raises a clean RuntimeError on timeout. `_stop_live_session` `:2188-2198` sets `active_stop_event` and awaits the task; the teardown block (`:2150-2170`) closes streams, clears playback, `recorder.log_event("session_lifecycle", state="stopped")`, prints "session parked; live graph released". Stop releases.
- `_silent_prewarm_hook` `:2200-2209` — after 0.25s, runs `_ensure_live_llm_tts_deps()` + `_ensure_live_session_deps()` (imports only, "models still cold"), skipping if already active. Silent background pre-warm = LANDED.
- `:2275` banner "start gate: armed (idle; capture/reactions/model load wait for Start)".
- If the brain is unavailable, `_activate_session:1723-1731` prints the unavailable banner, sets `started_event`, and waits on stop without building the graph — Start does not crash on a dead brain.
- Verdict: **LANDED. SRC green** (`18dc95cb test(start-gate): lock idle-cold`, `02ffb7c0 test(boot): align smoke with start-gated defaults`). v1 scope (Start + Stop-releases + silent pre-warm) is met.

### C3. frontend Start button + IPC both ends — **LANDED (SRC)**
- Schema: `messages.schema.json:1429 SessionStart` (`const "ipc.session.start"` `:1440`) + `:1453 SessionStop` (`const "ipc.session.stop"` `:1463`). Both types present; the `$comment` documents the optimistic-repaint contract.
- State: `session/state.ts:201 runState?: "armed" | "running"`; `:267 makeDefault()` sets `runState: "armed"` (real boot starts idle).
- Render: `session/SessionLayout.ts:1037-1057` renders the armed Start affordance; click flips `data-runstate="running"` locally (optimistic repaint per CLAUDE.md) then calls `onStart`. `:971-982` Stop control (running-only via CSS) flips to "armed" + calls `onStop`. `:155-162` declares `runState` + `onStart`/`onStop`.
- Emit: `session/render-loop.ts:74-79` `onStart` → `setSessionState({runState:"running"})` + `emitIpc("ipc.session.start", {})` (failure logs only, deck stays running). `:87-92` `onStop` → `emitIpc("ipc.session.stop", {})`.
- CSS gating `SessionLayout.ts:424-477` hides reactions/voice/live surface while `data-runstate="armed"`, shows Stop only while running.
- Verdict: **LANDED end-to-end (SRC).** Frontend Start/Stop button + optimistic repaint + emit, backend handler + lifecycle, both ends wired. `tsc --noEmit` + vitest were green per the maps; the IPC schema/codegen triplet is among the in-flight dirty files but the types are present at HEAD.

### C4. START GATE overall — **LANDED at SRC.** The map's "backend handler DARK" + "no UI button" claims are both STALE. LIVE proof (idle=cold confirmed on a running app, Start flips active, Stop releases) is a by-eye/by-bus check owned by the organizer/Kaan, not self-certifiable read-only.

---

## SCOPE D — Locked decision #4 (STREAK robot voice)
- Per the maps + goal docs, STREAK = full Daft-Punk "Technologic" robot voice in v1, but **SEQUENCED behind re-grounding the streak to a cited EXECUTED transition first** (the present `_attach_grade_progress` self-applauds an un-played suggestion — `runtime/suggestion.py:1365/1391/1450` per the map, Invariant #3 risk). The recipe is `CODEX_READY-PILL-STREAK-ROBOT-VOICE.md`.
- Verdict: **NOT-STARTED (correct).** This is deliberately deferred and not v1-launch-critical. Did not deep-verify the suggestion.py line numbers (out of my brain/proxy scope); flagging it as the map states.

---

## SCOPE E — README partner-copy policy (public-facing) — **CLAIMED-BUT-DARK (policy violations persist; FACTUALLY STALE for voice)**
The README still violates the partner-copy policy AND now carries factually-wrong voice copy:
- **Leaks `api.altidus.world`** (should be "Bravoh's hosted service"): `README.md:39, 61, 241, 259`.
- **Names "Gemini"** (should be "AI model"): `README.md:39, 61, 241, 259, 269, 271`.
- **Still says "MOSS voice path" / "local MOSS voice"** — now FACTUALLY WRONG (MOSS is nuked, the voice is Chatterbox): `README.md:241, 271`.
- **`security@bravoh.com`** — domain is `bravoh.ai` not `.com`: `README.md:63`.
- **Internal dev slop leaked**: KAAN-ACTION / "Kaan ear-passes daily" / Phase numbers + SHIPPED dates in the feature matrix: `README.md:69, 86, 134-149, 198, 279` (and the Phase-numbered grid rows).
- **CI status:** the 4 README CI gates **PASS at HEAD** — `tests/repo/test_readme_shape.py` + `test_readme_feature_matrix_sync.py` + (grids/hero a11y) = 57 passed. These gates enforce shape/grid-counts/hero-hash, **NOT** partner-copy policy, so the leaks ship green. The map's claim that these 2 gates were RED (asserting `altidus.world/vibemix`) is **STALE — they were re-pinned to bravoh.ai** (`aaa330ad test(repo): re-pin README funnel to bravoh.ai`) and are green.
- Verdict: **CLAIMED-BUT-DARK.** The README is test-green but partner-copy-dirty + voice-stale. This is a launch-copy fix (not a code wire); it does not block a tag (gates green) but it IS public slop that must be scrubbed before public launch.

---

## SCOPE F — GA-TAG LANDMINE — **CONFIRMED LIVE**
- `release.yml:57-60` — workflow fires on `push` of a tag matching `v*`. `:11-12` matrix = `macos-14 (Apple Silicon)` **AND `windows-latest`**; `:20, :136-154` Windows SignPath signing stage. So a `v*` tag push fires the FULL matrix incl. Windows + SignPath.
- The release gate is now `--require-chatterbox-source` (B6) — so the previously-broken MOSS gate no longer fails the build. BUT Windows is STILL in the matrix; v1 = macOS-arm64-only (Kaan-locked), Windows = v1.1. Pushing `v0.1.0` today would fire the Windows leg against a `.placeholder`-only Windows binary + need SignPath secrets in the `Bravoh-ai` org.
- **Tags present:** `v0.1.0-rc1` already exists. The LOCAL `v0.1.0-rc1` points at an OLD commit `905b24b5` (2026-05-13, pre-everything). The **`origin` (ozzaii) remote has a DIFFERENT `v0.1.0-rc1`** annotated tag at `654f8737`. Two remotes exist: `bravoh https://github.com/Bravoh-ai/vibemix.git` and `origin https://github.com/ozzaii/vibemix.git`. The prompt says `main` was pushed to `Bravoh-ai`.
- **`v0.1.0` (the GA, non-rc) is NOT yet pushed** anywhere (no `v0.1.0` exact tag found). The interim `0.1.0` source-snapshot was a non-`v` tag (fires only the benign SBOM job).
- Verdict: **LANDMINE LIVE.** Do NOT push `v0.1.0` until: (a) Windows is excluded from the v1 matrix (or `VIBEMIX_PRETAG_MAC_ONLY=1` path is the only one used), (b) the `Bravoh-ai` org has the signing secrets, (c) the keystone voice capture is signed off. The moss→chatterbox gate-swap is DONE (one of the named preconditions is cleared). Apple-only `VIBEMIX_PRETAG_MAC_ONLY=1` exists per the maps.

---

## ROLL-UP — verdicts table

| Item | Flag | Tier | Evidence |
|------|------|------|----------|
| llm_mode default = proxy | LANDED | SRC + LIVE-default | config_store.py:271 |
| base_url = api.altidus.world | LANDED | SRC (LIVE-verified per maps) | __main__.py:1139 |
| no-key direct → proxy, no crash | LANDED | SRC | __main__.py:1131-1181; no sys.exit(4) anywhere |
| jwt register POST /api/vibemix/v1/register | LANDED | SRC | agent/jwt_cache.py:79-91 (map mis-pathed to llm/) |
| set_brain persists mode + writes key to brain_env_path() | LANDED | SRC | session_loop.py:486-544 → config_store.py:208-228 |
| fresh no-key boot reaches funded brain | LANDED | SRC (LIVE Kaan-gated) | walked __main__.py boot |
| MOSS nuked / Chatterbox-only | LANDED | SRC | config_store.py:65-72; chatterbox_tts.py:119-121 |
| mlx-audio pyproject extra (Apple-arm64) | LANDED | SRC | pyproject.toml:162/167 |
| ref clip bundled (PyInstaller datas) | LANDED | SRC/spec (PKG=stale) | macos.spec:36/307; chatterbox_bundle.py |
| chatterbox model install + wizard prefetch | LANDED | SRC | model_assets.py:490; wizard.py:436/499 |
| env-seed VIBEMIX_TTS_ENGINE | LANDED | SRC | __main__.py:1063/1434 |
| release gate moss→chatterbox swap | LANDED | SRC/CI | pretag_check.sh:109-113; release.yml:355-542 |
| voice REACHABLE on packaged launch | LANDED@SRC, PKG/LIVE pending | — | needs HEAD DMG rebuild + first-run model fetch + Kaan ear |
| START GATE backend handler | LANDED | SRC | session_loop.py:278-279/331-371 |
| START GATE main() idle/activate/Stop | LANDED | SRC | __main__.py:1704+/2172-2275 |
| START GATE frontend button + emit | LANDED | SRC | state.ts:267; SessionLayout.ts:1037-1057; render-loop.ts:74-92 |
| STREAK robot voice | NOT-STARTED (correct) | — | deferred, sequenced behind re-grounding |
| README partner-copy (no Gemini/altidus/MOSS) | CLAIMED-BUT-DARK | SRC-green/policy-dirty | README.md:39,61,63,241,259,269,271 leak; gates green |
| GA-tag landmine (Windows in v* matrix) | LIVE | CI | release.yml:11-12/57-60; v0.1.0 not yet pushed |

## Bottom line for the organizer
The brain/proxy/fresh-user-no-crash leg (my scope) is **fully LANDED at SRC and graceful** — the fresh-user crash the maps named #1 is gone, proxy is the funded default, set_brain + register are correctly wired, and there is no `sys.exit(4)`. All four locked decisions have moved hard since the `7ac35a84` maps: **#1 VOICE and #3 START GATE are now LANDED at SRC** (the maps' "voice voiceless / start-gate backend DARK" are both STALE). The real residual risk is no longer code — it is the three things a read-only lane cannot produce: (1) a **fresh signed arm64 DMG rebuilt at HEAD** (every PKG is stale), (2) the **keystone LIVE capture** (no run with nonzero voice_rms; Kaan's hand on the rig), and (3) two non-blocking-but-dirty items — **README partner-copy scrub** (leaks Gemini/altidus + factually-stale MOSS copy, green only because the gates don't check policy) and the **GA-tag landmine** (Windows still in the `v*` matrix; do not push `v0.1.0` until Windows is excluded + secrets land).
