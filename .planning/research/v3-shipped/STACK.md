# Stack Research

**Domain:** Cross-platform real-time AI desktop app (audio + screen + MIDI + LLM/TTS streaming) — extending the v0.1.0 shipping stack with the v2.0 Research-Driven Ship feature set

**Researched:** 2026-05-11 (baseline, Phases 1-14 shipped) + 2026-05-14 (v2.0 additions from `.planning/research/v2-buckets/`)

**Confidence:**
- HIGH on the v0.1.0 baseline — Phases 1-14 shipped this stack to a working `.onedir` Tauri sidecar on Kaan's rig.
- HIGH on v2.0 additions for python-osc, pyrekordbox, sqlite-vec, watchdog, mutagen, pydub, three.js — all verified at PyPI/npm at time of research.
- MEDIUM on the AX-bridge + overlay path — proven via `kyleawayan/djay-pro-bridge` for djay Pro but pointer-rectangle extraction has not been tested by anyone (we'd be the first to lift positions from the AX tree).
- MEDIUM on sqlite-vec Windows wheels — PyPI currently lists Mac + Linux only; Windows currently needs source-build via `loadable_path()` JSON config (see installation footprint section).

---

## TL;DR — what changes for v2.0

The shipping v0.1.0 stack stays put. v2.0 adds **8 capability buckets** on top of it, each rated for one-click-install impact:

| Bucket | New deps (size on wheel) | Install rating | Why |
|---|---|---|---|
| 1. **Latency** | NONE — all in existing `livekit-agents` + `google-genai` | 🟢 GREEN | `SpeechHandle.interrupt(force=True)` already shipped in `livekit-agents==1.5.8`. `cached_content` is a config field on `google-genai==2.0.1`. Ack bank = 40 bundled WAV files (~5MB total). |
| 2. **Citation linter** | NONE — stdlib `re` + new in-memory `Evidence` registry | 🟢 GREEN | Bucket E's hard requirement: zero third-party deps. |
| 3. **djay Pro overlay** | `pyobjc-framework-ApplicationServices` (~5MB, darwin only, already transitive of pyobjc-core) | 🟢 GREEN | Calls AX from the Rust parent (per Tauri issue #8329). Adds 1 Rust crate (already-present `tauri::webview::WebviewWindowBuilder` covers it). |
| 4. **Pyrekordbox XML import** | `pyrekordbox==0.4.4` (~250KB pure-Python, MIT, 395★) | 🟢 GREEN | XML-only path; never touches SQLCipher. Pure Python, no native deps. |
| 5. **Library intelligence** | `sqlite-vec==0.1.9` (~500KB ext, 7.6k★) + `pydub==0.25.1` (~50KB pure Python) + `mutagen==1.47.0` (~250KB pure Python) + `watchdog==6.0.0` (~150KB) + `ffmpeg` binary (bundled, ~20MB Win, native on Mac via afconvert fallback) | 🟡 YELLOW | sqlite-vec Windows wheel currently absent — must ship the `.dll` ourselves or use the `loadable_path` workaround. ffmpeg bundling on Windows is the install-size hit. |
| 6. **Mascot 4-layer additive** | `three.js@0.184.0` (npm, already-vendored in `tauri/ui/`) + 8 new GLB asset files (~6MB) | 🟢 GREEN | Existing renderer; AnimationMixer extension is pure Three.js code. No new npm dep version bump required for `AdditiveAnimationBlendMode` (in r150+). |
| 7. **Post-session debrief** | NONE — single Gemini call via existing `google-genai==2.0.1` cascade | 🟢 GREEN | Memory file `project_phase_16_kaan_dj_testing.md` killed the mem0/vector DB path. ~2KB structured JSON DJ profile = local SQLite row. |
| 8. **10-SKU MIDI library** | NONE — 10 JSON files + new `MidiMapLoader` Python class | 🟢 GREEN | Already-present `mido==1.3.3` + `python-rtmidi==1.5.8` decode. JSONs ship inside the wheel as package-data (precedent: Phase 6 genre profiles). |

**Net impact on the wheel:** +~7MB Python deps (sqlite-vec, pyrekordbox, pydub, mutagen, watchdog) + ~6MB mascot GLBs + ~20MB ffmpeg on Windows = total bundle grows from 242 MB (Phase 11 W1 closed at) → **~270-290 MB on Mac, ~290-310 MB on Windows**. Still under the 350 MB hard cap. No dep rated RED.

**Net impact on Tauri/Rust:** zero new crates. AX bridge uses `core-foundation` + `core-graphics` (already transitive via `tauri` on darwin). Highlight overlay is a second `WebviewWindow` in the same Tauri shell.

**Net impact on npm:** zero new packages (three.js already vendored at the version we need).

---

## I. What Stays Exactly the Same (DO NOT change)

This is the validated baseline from Phases 1-14. Every entry below is shipping today in the Phase 11 W1 sidecar. Re-doing any of this in v2.0 is regression risk:

| Layer | Component | Locked Version | Why locked |
|---|---|---|---|
| Runtime | Python | **3.12.x** | PyInstaller, PyAudioWPatch, scipy, pyobjc all have mature 3.12 wheels. POC's 3.14 was dropped in Phase 1. |
| Brain | `livekit-agents` + `livekit-plugins-google` | **1.5.8 / 1.5.8** | AgentSession cascade `stt=None, vad=None, llm=google.LLM, tts=google.beta.gemini_tts.TTS`. Phase 4 shipped. |
| Brain | `google-genai` | **2.0.1** | Direct SDK (used by the cascade LLM, the citation grounding probes, and the new context-cache call). Phase 4 shipped. |
| Audio in (mac) | `sounddevice` | **0.5.5** | BlackHole 48kHz int16 stereo — Phase 2 ring buffer locked the format. |
| Audio in (Windows) | `PyAudioWPatch` | **0.2.12.8** | WASAPI loopback. Phase 7 shipped. |
| Audio math | `numpy` + `scipy` | **2.4.4 / 1.17.1** | RMS, FFT, BPM autocorr, `signal.resample_poly`. Phase 2 + 6. |
| MIDI | `mido` + `python-rtmidi` | **1.3.3 / 1.5.8** | CoreMIDI on Mac, WinMM on Windows. Phase 3 + 9. |
| Screen (Mac) | `pyobjc-framework-ScreenCaptureKit` + `pyobjc-framework-Quartz` | **12.1 / 12.1** | Phase 8 migration shipped; SCStream + delegate-on-dispatch-queue. Window enum stays on Quartz. |
| Screen (Win) | `mss` + `winsdk` + `pywin32` | **10.2.0 / 1.0.0b10 / 308** | Phase 7 shipped. |
| Permissions (Mac) | `pyobjc-framework-AVFoundation` | **12.1** | AVCaptureDevice + CGPreflightScreenCaptureAccess. Phase 11 W4. |
| Image | `pillow` | **12.2.0** | JPEG encode pre-Gemini. Phase 4. |
| WS bus | `websockets` | **16.0** | 127.0.0.1:8765 IPC. Phase 11 W0. |
| IPC | hand-written `@dataclass(frozen=True, slots=True)` + `jsonschema` Draft-07 | (stdlib + jsonschema 4.x) | **NO pydantic** — D-Area-4.4 / Phase 6 constraint. 27 IPC messages × 1 schema file. |
| Tauri shell | `tauri` Rust + Vite + TS | **tauri 2.x / vite ^6 / vitest ^2** | Phase 11 W0+W2 scaffold + Phase 14 v5 design tokens. |
| Tauri plugins | `tauri-plugin-shell` + `tauri-plugin-store` | **2.3 / 2.4** | Already vendored. |
| Packaging | PyInstaller sidecar `--onedir` | **6.20.0** | Phase 11 W1 shipped. `--onefile` explicitly forbidden (AV false positives). |
| Backend | FastAPI + slowapi + Redis 7+ + PyJWT | **0.115.x / 0.1.9+ / 7.x / 2.12.1+** | Phase 5 shipped to `proxy/`. Per-install-UUID JWT HS256. |
| Design | CDJ Whisper v5 tokens.css + Saira/JetBrains Mono | (vendored) | Phase 14 migration complete; legacy fonts deleted. |

**If a v2.0 plan proposes changing any row above, kick it back to research.** The whole v2.0 plan is additive on this baseline.

---

## II. v2.0 Stack Additions — Capability by Capability

### A. Latency Stack (Bucket A + A-followup-1)

**Goal:** Sub-2s actual voice-to-voice + <300ms perceived first reaction via prompt-diet + Gemini context caching + pre-canned ack bank + predictive firing + cancel-and-refire.

**New Python deps:** NONE. Everything lives on the validated `livekit-agents==1.5.8` + `google-genai==2.0.1` baseline.

**Verified APIs (empirically from A-followup-1):**

1. **`SpeechHandle.interrupt(force=True)`** — at `.venv/.../livekit/agents/voice/speech_handle.py:141-154`. With `force=True`, bypasses `allow_interruptions=False` gate and calls `self._cancel()` → `cancel_and_wait(*tasks)` kills both LLM stream + TTS task in flight. **No new method names; no API surface change since 1.5.x.**

2. **Gemini context caching** — `client.caches.create()` (sync) + `client.aio.caches.create()` (async) at `.venv/.../google/genai/caches.py:1053-1144`. `cached_content` field on `types.GenerateContentConfig` (`google/genai/types.py:5983`). **`gemini-3-flash-preview` is in the supported-models matrix** (verified at https://ai.google.dev/gemini-api/docs/caching, 2026-05-14). 1024-token floor for the cached block — pad with deterministic per-session context (controller MIDI map, event taxonomy, voice persona) to stay above the floor when prompt-dieting.

3. **`extra_kwargs={"cached_content": ...}` plumbing** — `livekit-plugins-google/llm.py:256-261, 441-448` forwards `extra_kwargs` to `google-genai`'s `GenerateContentConfig`. The `prompt_cached_tokens` field surfaces at `llm.py:475` for telemetry verification.

**Ack bank shipping format:**
- **40 OPUS samples** (drop_hit/, track_change/, mix_move/, silence_break/, generic_filler/) × ~200-800ms each
- Total disk: **~5MB at 24kHz mono OPUS** (negligible — well under the 350MB cap)
- Decoded with Python's stdlib `wave` module if we ship as WAV instead (~12MB) — slightly larger but **zero new deps**. Recommendation: WAV for v2.0 unless install-size shows pressure.

**Asset bundling pattern:** package-data inclusion (same precedent as Phase 6 genre profile JSONs + Phase 11 W3 audio test WAV). Bundled into the PyInstaller `.onedir` via `datas=` in the `.spec` file.

**Install rating: 🟢 GREEN.** Zero new pip deps. ~5-12 MB bundle growth (ack bank).

---

### B. Citation Linter (Bucket E + E-followup-1)

**Goal:** Grammar `[ev:KICK_SWAP@<t>]` / `[aud:peak_rms@<t>]` / `[midi:filter_open@<t>]` / `[track:Camelot_8A→9A]` enforcement, in-memory Evidence registry, response-level strip (live) + sentence-level strip (debrief), zero hallucinations.

**New Python deps: NONE.** Stdlib `re` is sufficient. The Evidence registry is a `dict[(source, key)] → list[(t_session, value)]` held inside the existing MusicState lifecycle (no new persistence layer).

**Module shape:**
- `vibemix/citation/grammar.py` — regex catalog + EBNF docstring
- `vibemix/citation/evidence.py` — in-memory registry, write from EventDetector, read from linter
- `vibemix/citation/linter.py` — `validate_response(text) → (clean_text, stripped_spans, telemetry)`

**Integration:** wraps the existing `llm_node` cascade in `vibemix/agent/dj_cohost.py` (Phase 10). Citation validation runs AFTER the negative-dict filter, BEFORE TTS dispatch. On total-strip the existing `<silence/>` short-circuit fires; on partial-strip the cleaned text proceeds to TTS.

**Install rating: 🟢 GREEN.** Zero new dependencies. ~600 LOC + tests. Hard scope discipline (no nltk, no spacy, no parser library — stdlib `re` is enough).

---

### C. djay Pro Mac Overlay Highlight (Bucket C)

**Goal:** Transparent always-on-top Tauri webview drawing soft amber rings on 12 hand-mapped djay Pro UI elements when Gemini emits a `point` field. Mac-only for v2.0. Windows + Rekordbox/Serato explicitly deferred.

**New Python deps:** None directly (the AX call lives in the Rust parent per Tauri issue #8329 — sidecar AX permission inheritance is broken on installed Mac apps). If we ever lift the AX call into Python for development/debugging, the canonical module is:

- `pyobjc-framework-ApplicationServices` — bundled `AXUIElement*` definitions (`HIServices` module). **No version bump needed**: it's already an transitive dep of the existing `pyobjc-framework-Quartz==12.1` install. [VERIFIED: https://pyobjc.readthedocs.io/en/latest/apinotes/ApplicationServices.html]

**New Rust crates: NONE.** `tauri::webview::WebviewWindowBuilder` already covers the second-window pattern. `transparent + always_on_top + decorations:false + set_ignore_cursor_events(true)` flags all exist in `tauri==2.x`. AX from the Rust parent uses `core-foundation` + `core-graphics` crates which are already transitive via `tauri`'s `macos-private-api` feature flag.

**New npm packages: NONE.** The overlay HTML is vanilla Canvas 2D in a new `highlight.html` asset (~200 LOC vanilla JS, no framework). Single CSS keyframe for the ring animation. Follows the `mascot.html` pattern.

**Element coord map:** `assets/element_maps/djay_pro_5.json` (hand-mapped percentage-of-window-rect coords for 12 elements × 2 decks = 24 instances). Bundled in PyInstaller `--datas`. AX label refinement at runtime when AX position attributes are available; falls back to percentage map.

**Install rating: 🟢 GREEN.** Zero new pip/npm/cargo deps. The AX permission TCC prompt is the only friction — onboarded via the existing Phase 11 W4 permissions card. Drop-in to existing Tauri shell + Phase 11 capability allowlist (add `"highlight"` window to `capabilities/default.json`).

**Mac-only constraint:** the entire C bucket is `target_os = "macos"` gated. Windows users see a "highlight feature: macOS only in v2.0" notice in the Settings panel. **Windows overlay parity deferred to v2.1** per `B-followup-1` open question Q4.

---

### D. Pyrekordbox XML Import (Bucket B-followup-1)

**Goal:** Read user's exported Rekordbox `collection.xml` once, store enriched per-track metadata (title, artist, BPM, Camelot key, energy, hot cues, beat grid) in a local SQLite cache. Fuzzy-match live now-playing-title against the cache for prompt grounding. Skips SQLCipher entirely (broken post-Rekordbox 6.6.5).

**New Python dep:**

| Library | Version | License | Wheels | Pure Python? | Install footprint |
|---|---|---|---|---|---|
| **`pyrekordbox`** | **0.4.4** | MIT | pure Python (no platform-specific wheels needed) | ✅ Yes | ~250 KB |

[VERIFIED at https://pypi.org/project/pyrekordbox/ as 0.4.4, 395★, last release 2025-08-17 — 2026-05-14]

**Why pyrekordbox over manual XML parsing:**
- `RekordboxXml(path).get_tracks()` is a 1-line parser that handles the format quirks (TEMPO + POSITION_MARK nested elements, Rekordbox 5/6/7 schema variations)
- Apache 2.0-compatible (MIT)
- Pure Python — wheel-trivial on Mac/Win
- Active maintainer (last release 2025-08-17, contributors writing fixes)
- Bravoh-style "import the SDK, ignore the SQLCipher path" pattern

**What we DON'T use from pyrekordbox:** the `sqlcipher3-wheels` dependency tree (its `Rekordbox6Database()` class). The Rekordbox 6.6.5+ key-obfuscation wall makes SQLCipher access unreliable for >80% of users. We pin `pyrekordbox==0.4.4` with `--no-extras` or similar to skip the SQLCipher chain. [Verify in plan: confirm `pyrekordbox` doesn't hard-require `sqlcipher3-wheels` at import — if so, `pip install pyrekordbox --no-deps` + explicit re-add of just the XML deps may be needed.]

**Storage shape:**
- One SQLite file at `~/Library/Application Support/vibemix/library/rekordbox.db` (Mac) / `%APPDATA%\vibemix\library\rekordbox.db` (Win)
- 3 tables: `tracks` + `cues` + `beat_grid` per B-followup-1 §2 schema
- ~2.5 MB for 5k tracks, ~8 MB for 15k tracks — negligible

**Install rating: 🟢 GREEN.** Pure Python, MIT, 250KB, active maintainer. Bundles cleanly into PyInstaller — no hidden imports, no native dylib chains.

---

### E. Library Intelligence (Bucket F)

**Goal:** Gemini Embedding 2 over user's audio library; sqlite-vec embedded vector store; live "what's playing now?" grounding via embedding-distance lookup; post-session "your library had a better neighbor" suggestions.

**New Python deps (the largest cluster in v2.0):**

| Library | Version | License | Platform Wheels | Pure Python? | Install footprint | Why |
|---|---|---|---|---|---|---|
| **`sqlite-vec`** | **0.1.9** | MIT | Mac arm64 ✅ / Mac x64 ✅ / Linux ✅ / **Windows: source-build** | C extension | ~500 KB ext + sqlite3 (stdlib) | sqlite-vec is the canonical embedded vector store. Native KNN search on `vec0(embedding float[1536])` virtual table. 7.6k★, v0.1.9 (2026-03-31). [VERIFIED at https://pypi.org/project/sqlite-vec/] **NO Windows wheel as of 2026-05-14** — see install rating caveat below. |
| **`pydub`** | **0.25.1** | MIT | pure Python | ✅ Yes (uses ffmpeg subprocess) | ~50 KB | MP3 transcoding for Gemini Embedding 2 (MP3/WAV only — must transcode user's AAC/M4A/FLAC). Bravoh's pipeline uses this verbatim. [VERIFIED at https://pypi.org/project/pydub/ as 0.25.1] |
| **`mutagen`** | **1.47.0** | GPL-2.0 | pure Python | ✅ Yes | ~250 KB | ID3/Vorbis/MP4 tag reader (BPM, key, energy, comments). Universal across DJ-tagged libraries. [VERIFIED at https://pypi.org/project/mutagen/ as 1.47.0] **License caveat:** GPL-2.0 — see §IV License Audit. |
| **`watchdog`** | **6.0.0** | Apache 2.0 | pure Python (with optional C accelerators per platform) | ✅ Yes (mostly) | ~150 KB | Cross-platform file watcher (FSEvents on Mac / ReadDirectoryChangesW on Windows). Bundled in PyInstaller cleanly per their docs. [VERIFIED at https://pypi.org/project/watchdog/ as 6.0.0] |

**System-level binary requirement — ffmpeg:**
- pydub uses `ffmpeg` (or `avconv`) under the hood for MP3 transcoding
- **macOS**: native `afconvert` is the fallback if ffmpeg is absent (Bravoh confirms this pattern works). Optional `brew install ffmpeg` for users who want it; vibemix bundles afconvert path as default.
- **Windows**: no system audio converter — **MUST bundle ffmpeg.exe** in the PyInstaller `--datas` block. Adds ~20 MB to Windows installer. Source: official ffmpeg static builds at https://www.gyan.dev/ffmpeg/builds/ (GPL/LGPL — License audit below).

**sqlite-vec Windows wheel — the YELLOW caveat:**
- Current PyPI build (0.1.9 as of 2026-03-31) ships wheels for `manylinux_2_17_x86_64`, `manylinux_2_17_aarch64`, `macosx_11_0_arm64`, `macosx_10_6_x86_64`. **No `win_amd64` wheel.** [VERIFIED via PyPI listing]
- Three workaround paths to evaluate during Phase planning:
  1. **Bundle the prebuilt `vec0.dll`** from sqlite-vec's GitHub Releases (https://github.com/asg017/sqlite-vec/releases) into the PyInstaller `--datas`, load via `sqlite_vec.load(conn)` with explicit path override
  2. **Build sqlite-vec from source on the Windows CI runner** (cmake + MSVC required — adds ~5 min to Windows build matrix; complex but reproducible)
  3. **Fallback to "store as bytes, rank in Python via `np.dot`"** — Bravoh's actual production pattern. At 30k × 1536 = ~6ms in numpy. Adds no deps. Recommend as the Windows fallback regardless of (1)/(2).

**Recommendation: ship the numpy fallback (3) for Windows in v2.0, document the (1) sidecar-bundled-DLL path as a v2.1 perf upgrade.** Keeps install GREEN on Mac, YELLOW-but-shippable on Windows.

**Gemini Embedding 2 specifics (already locked in memory `project_gemini_embedding_2.md`):**
- Model: `gemini-embedding-2-preview`
- Dim: **1536** (Bravoh's chosen sweet spot)
- L2-normalize client-side
- Audio cap: **80s** (Bravoh empirical, despite docs claim of 180s)
- Format: **MP3 or WAV only** (forces pydub transcoding for AAC/M4A/FLAC)
- Cost: $0.00016/sec paid, **free tier covers nearly all users**

**Bravoh pipeline lift (per memory `project_one_click_install_hard_req.md` and `F-library-intelligence.md`):**
- `_embed_text_sync`, `_embed_bytes_sync`, `embed_audio`, `embed_text` — verbatim from `/var/www/bravoh-backend/app/services/embedding/service.py`
- L2 normalization (`_l2_normalize`, 4 lines)
- SSL retry + 429 retry via tenacity
- pydub MP3 transcoding when >20MB

**Tenacity:** add `tenacity>=8.2` if not already transitive of livekit-agents. **Verify in plan-checker** — likely already pulled in transitively. Pure Python, MIT.

**Install rating: 🟡 YELLOW** — driven primarily by the sqlite-vec Windows wheel gap (workaroundable) and ffmpeg bundling on Windows (+20MB). All other deps GREEN. Recommendation: ship the numpy fallback for sqlite-vec on Windows, accept the ffmpeg bundle cost.

---

### F. Mascot 4-Layer Additive State Machine (Bucket D)

**Goal:** Mood baseline (continuous) + anticipation overlay (fires BEFORE Gemini round-trip — 400-1200ms perceived mask) + speak/react layer + effect layer, plus beat-coupled procedural hip-bob + inline emote-tag vocab.

**New npm packages: NONE.** Three.js already vendored in `tauri/ui/` at the version we need.

- **Required version:** `three@0.150+` for `AdditiveAnimationBlendMode` + `AnimationUtils.makeClipAdditive()`. Current vendored version per Phase 13 is well above this floor.
- **Verified API:** `AnimationAction.blendMode = THREE.AdditiveAnimationBlendMode` + `AnimationUtils.makeClipAdditive(clip)` preprocessing. [VERIFIED at https://threejs.org/examples/webgl_animation_skinning_additive_blending.html]

**Three.js version current:** 0.184.0 (npm `three`) — released 2026-04. Vendoring stays as-is unless we want WebGPU (out of scope for v2.0 mascot).

**Asset deltas (8 new GLB clips):**
- `prep_lean_in_neutral` / `prep_lean_in_hyped` / `prep_head_turn_left` / `prep_head_turn_right` / `prep_settle` (5 anticipation clips)
- `talk_loop_energetic_v2` / `react_celebrate_alt` / `dance_alt3` (3 reaction/talk variants)
- Authored with idle/zero lower-body delta for additive blending (per D §"bone-subset blending")
- Total disk: **~6 MB at compressed GLB** (DRACO compression already in our pipeline)
- Cost: $1500-2000 Meshy/Mixamo asset spend (memory `project_mascot_as_vtuber_personality_surface.md` covered the pipeline choice)

**Procedural hip-bob:** runs in `MascotRenderer.tick(deltaSeconds)` — direct `Hips` bone position modulation post-`mixer.update()`. Three.js skeletal manipulation, no new code paths. Driven by `bpm + downbeat_phase + recent_rms` already broadcast on the WS bus (Phase 13 added these per state.md decision).

**Inline emote tag spike (per D Risk + open question #1):** Bucket D recommends a 1-day spike to verify Gemini text-channel transcripts arrive BEFORE audio chunks via `livekit-plugins-google`. If verified, ship the 16-tag vocabulary. If not, fall back to event-detector-driven anticipation (cheaper, less precise).

**Install rating: 🟢 GREEN.** Zero new deps. ~6 MB asset growth.

---

### G. Post-Session Debrief (Bucket E)

**Goal:** Single Gemini call per session, chaptered review + 60-90s voiced TL;DR + 3 drills (hard cap) + clickable timeline. Long-term DJ profile = ~2KB structured JSON.

**New Python deps: NONE.**
- Single Gemini call uses existing `google-genai==2.0.1`
- Voiced TL;DR uses existing `livekit-plugins-google.beta.gemini_tts.TTS`
- Structured JSON DJ profile stored in the same SQLite local store as the library (Bucket E §IV — explicitly **NO mem0 / NO vector DB** per memory `project_v2_open_candidates.md` confirmed-list)
- Timeline UI is vanilla TS/Canvas in the existing Tauri shell

**SBI/STAR-AR framing:** prompt-side decision (no library), enforced by the citation linter (Bucket B above).

**Install rating: 🟢 GREEN.** Zero new deps.

---

### H. 10-SKU MIDI Controller Library (Bucket B-followup-1 §3)

**Goal:** Replace hardcoded `_CC_MAP` / `_NOTE_MAP` from `cohost_v4.py:586-602` with a JSON-per-SKU registry + `MidiMapLoader` Python class. 10 controllers covering ~70-85% of bedroom-DJ market.

**New Python deps: NONE.** Already-shipping `mido==1.3.3` + `python-rtmidi==1.5.8` decode wire messages. The new module is pure-Python schema + dispatch.

**Note: this overlaps with Phase 9's existing controller library work.** Phase 9 already shipped 10 controller JSONs (DDJ-FLX4 verified + 9 others by Mixxx-mapping basis). What v2.0 adds:
- Verified sniff data for the 9 currently-flagged-unverified SKUs (DDJ-400/FLX6/FLX10/SX3, XDJ-RX3, Numark Party Mix Live, Mixstream Pro+, Hercules Inpulse 300/500)
- 5-minute `mido` sniff to resolve the Sync note `0x60` (v4) vs `0x58` (Mixxx XML) disagreement (per B-followup-1 §7Q2)
- A formalized `MidiMapLoader` class replacing the in-line dict lookup

**Install rating: 🟢 GREEN.** Zero new deps. 10 JSON files ship as package-data (precedent: existing Phase 9 pattern). Sniff time = ~30 minutes of Kaan's hardware-on-the-bench time per SKU + Francesco's DJ network for loaner units.

---

## III. Per-Platform Constraints

### macOS-only paths (v2.0 additions)

| Capability | Implementation | Constraint |
|---|---|---|
| AX bridge for djay Pro overlay | Rust parent via `core-foundation` + `core-graphics` crates (already-transitive of `tauri` w/ `macos-private-api`) | TCC Accessibility prompt; sidecar inheritance broken (Tauri #8329); bundle ID `world.bravoh.vibemix` LOCKED |
| Window enumeration (highlight tracking) | `Quartz.CGWindowListCopyWindowInfo` (still supported on macOS 15+) | Already in use since Phase 3 |
| ffmpeg fallback (library transcoding) | macOS native `afconvert` binary at `/usr/bin/afconvert` | Pre-installed on all supported macOS versions (12.3+) — no install action |

### Windows-only paths (v2.0 additions)

| Capability | Implementation | Constraint |
|---|---|---|
| ffmpeg bundling (library transcoding) | Static ffmpeg.exe in PyInstaller `--datas` | +~20 MB installer size; license is LGPL build (see License audit) |
| sqlite-vec — numpy fallback | "Store float32 bytes in BLOB, rank in Python via `np.dot`" (Bravoh pattern) | 30k × 1536 = ~6ms in pure numpy — acceptable |
| Window enumeration (highlight tracking) | `EnumWindows` + `GetWindowRect` via `pywin32` (Phase 11 W4) | DPI virtualization caveat — mark process `PROCESS_PER_MONITOR_DPI_AWARE_V2` |
| djay Pro overlay | **Explicitly NOT shipped in v2.0** | Deferred to v2.1 per Bucket C scope discipline |

### Cross-platform additions (Mac + Windows both)

| Capability | Implementation |
|---|---|
| Latency stack (predictive firing, cancel-and-refire, ack bank, prompt cache) | Pure cascade-layer code; works on both OSes |
| Citation linter | Pure stdlib; works on both OSes |
| Pyrekordbox XML import | Pure Python; works on both OSes |
| Library intelligence (Gemini Embedding 2 + sqlite-vec/numpy fallback) | Works on both; sqlite-vec on Mac, numpy fallback on Windows |
| Mascot 4-layer additive | Three.js renders identically on both |
| Post-session debrief | Single Gemini call + local SQLite — both OSes |
| 10-SKU MIDI library | mido cross-platform — both OSes |
| File watcher (`watchdog`) | FSEvents on Mac, ReadDirectoryChangesW on Windows — single API |

---

## IV. License Audit (additions only)

| New dep | License | Linkable with vibemix's Apache 2.0 + DCO? | Notes |
|---|---|---|---|
| `pyrekordbox` 0.4.4 | MIT | ✅ Yes | Bundle freely. |
| `sqlite-vec` 0.1.9 | MIT (Apache-2.0 dual-licensed per repo) | ✅ Yes | Bundle freely. |
| `pydub` 0.25.1 | MIT | ✅ Yes | Bundle freely. |
| `mutagen` 1.47.0 | **GPL-2.0** | ⚠️ YELLOW — use-only at runtime, NOT linked statically | Python imports don't constitute GPL "linking" (RMS clarified this for Python years ago) — vibemix can run-time import mutagen as a separate dep without infecting Apache 2.0. PyInstaller bundle is a "mere aggregation" per GPL §0. **BUT**: distributing source bundled w/ mutagen needs careful README disclosure. If concerned, swap for `tinytag` (MIT, simpler but less complete tag support). Recommendation: ship mutagen, disclose in `LICENSE-3RD-PARTY.md`. |
| `watchdog` 6.0.0 | Apache 2.0 | ✅ Yes | Same license as vibemix. |
| `pyobjc-framework-ApplicationServices` | MIT-style (pyobjc license) | ✅ Yes | Same license family as existing pyobjc deps. |
| `tenacity` (transitive add-confirm) | Apache 2.0 | ✅ Yes | Likely already transitive of livekit-agents. |
| `three.js` 0.184.0 | MIT | ✅ Yes | Already vendored. |
| **ffmpeg static binary (Windows)** | **LGPL or GPL depending on build** | ⚠️ YELLOW | Use the **LGPL build** from gyan.dev (no GPL-licensed encoders). License obligation: ship source-availability notice + offer to provide modified source on request. Standard precedent — every Windows app that bundles ffmpeg follows this pattern (e.g. Audacity, OBS). |

**No new dep is RED.** Two YELLOW items (mutagen GPL, ffmpeg LGPL) require disclosure in `LICENSE-3RD-PARTY.md` and Settings → About surface. Both have well-precedented OSS distribution patterns.

---

## V. One-Click-Install Impact Table (the final summary)

Per memory `project_one_click_install_hard_req.md` — every new dep rated:

| New Item | Rating | Bundle Size Delta | Install-Time User Action | Why |
|---|---|---|---|---|
| Ack bank (40 WAVs) | 🟢 GREEN | +5-12 MB | None | Package-data inclusion |
| Citation linter | 🟢 GREEN | +0 | None | Stdlib only |
| AX bridge (Tauri Rust) | 🟢 GREEN | +0 | First-run TCC prompt (already onboarded via Phase 11 W4) | Existing pyobjc transitive |
| Highlight overlay (Tauri webview) | 🟢 GREEN | +50 KB (HTML/CSS/JS) | None | Same Tauri shell |
| `pyrekordbox` | 🟢 GREEN | +250 KB | User clicks Settings → "Import Rekordbox XML" (optional) | Pure Python MIT |
| `sqlite-vec` (Mac) | 🟢 GREEN | +500 KB | None | Bundled ext, prebuilt wheel |
| `sqlite-vec` (Windows) | 🟡 YELLOW | +0 (using numpy fallback) | None | Workaround documented; v2.1 perf upgrade ships actual Windows wheel |
| `pydub` | 🟢 GREEN | +50 KB | None | Pure Python |
| `mutagen` | 🟢 GREEN | +250 KB | None | Pure Python; GPL disclosed |
| `watchdog` | 🟢 GREEN | +150 KB | None | Pure Python core; optional C accelerators auto-bundle |
| ffmpeg (Mac) | 🟢 GREEN | +0 | None | macOS native `afconvert` fallback |
| **ffmpeg (Windows)** | 🟡 YELLOW | **+20 MB** | None | Static LGPL binary in `--datas`; license disclosed |
| Mascot 8 new GLBs | 🟢 GREEN | +6 MB | None | Asset spend $1500-2000 |
| 10-SKU MIDI verified JSONs | 🟢 GREEN | +50 KB total | None | Package-data, precedent from Phase 9 |

**Bundle size projection:**
- Phase 11 W1 baseline: 242 MB (Mac), ~250 MB (Win projected)
- v2.0 additions: +~12 MB (Mac), +~32 MB (Win, including ffmpeg)
- **v2.0 shipping size: ~254 MB (Mac), ~282 MB (Win)** — well under 350 MB hard cap

**Zero new user install actions.** TCC permissions for AX (Mac) are part of the existing first-run wizard. Library import is optional (Settings → "Import Rekordbox XML").

---

## VI. Installation Manifest (v2.0 delta)

```toml
# pyproject.toml — additions to [project.dependencies]
dependencies = [
  # ... v0.1.0 baseline (DO NOT change) ...

  # v2.0 additions
  "pyrekordbox==0.4.4",         # XML library import (XML path only; SQLCipher skipped)
  "sqlite-vec==0.1.9",           # Mac/Linux only; Windows uses numpy fallback (sys_platform marker below)
  "pydub==0.25.1",               # MP3 transcoding for Gemini Embedding 2
  "mutagen==1.47.0",             # ID3/Vorbis/MP4 tag reader
  "watchdog==6.0.0",             # Cross-platform file watcher
  # tenacity already transitive of livekit-agents — verify
]

# sqlite-vec only ships wheels for Mac/Linux as of 2026-05-14
# Plan-checker: confirm sys_platform marker syntax for the Windows fallback path
[project.optional-dependencies]
macos = [
  # ... v0.1.0 baseline (pyobjc-* etc.) ...
  # pyobjc-framework-ApplicationServices is transitive — no explicit add needed
]
windows = [
  # ... v0.1.0 baseline (PyAudioWPatch, pywin32, winsdk) ...
  # Windows sqlite-vec workaround: use numpy fallback. NO sqlite-vec on Windows.
]
```

```ts
// tauri/ui/package.json — NO CHANGES
// three.js@0.184.0 already vendored. New mascot clips ship as GLB assets in tauri/ui/public/mascot/clips/
```

```rust
// tauri/src-tauri/Cargo.toml — NO CHANGES
// AX bridge uses core-foundation + core-graphics already transitive via `tauri 2.x` with macos-private-api feature
// New highlight WebviewWindow uses existing tauri::webview::WebviewWindowBuilder
```

```bash
# PyInstaller spec deltas (vibemix-core.macos.spec / vibemix-core.windows.spec)
datas += [
  ('assets/ack_bank/*.wav', 'assets/ack_bank'),
  ('assets/element_maps/djay_pro_5.json', 'assets/element_maps'),
  ('assets/controller_library/*.json', 'assets/controller_library'),  # 10 SKU JSONs
]
# Windows-only: bundle ffmpeg.exe (LGPL build from gyan.dev)
if sys.platform == 'win32':
    datas += [('vendor/ffmpeg.exe', 'vendor')]
# Windows-only: bundle sqlite-vec vec0.dll workaround (v2.1)
# For v2.0, use numpy fallback — no bundling needed
```

---

## VII. Version Compatibility Matrix (v2.0 additions only)

| Package A | Compatible With | Notes |
|---|---|---|
| `pyrekordbox==0.4.4` | Python 3.8+, ours 3.12 ✅ | Apache 2.0 + DCO compatible (MIT lib) |
| `sqlite-vec==0.1.9` | Python 3.7+, sqlite3 stdlib | macOS arm64 + x64, Linux x64 + arm64 wheels. Windows: see workaround. |
| `pydub==0.25.1` | Python 3.6+ | Requires ffmpeg subprocess (system or bundled) |
| `mutagen==1.47.0` | Python 3.10+ (per docs; 3.7+ per setup.py) | Stdlib only — no native deps |
| `watchdog==6.0.0` | Python 3.9+ | Bundles platform-specific C accelerators (FSEvents/ReadDirectoryChanges) — auto-detect during install |
| `three.js@0.184.0` | Existing Vite build chain | AdditiveAnimationBlendMode shipped in r150+, no version bump needed |
| `pyobjc-framework-ApplicationServices` | Transitive of `pyobjc-core==12.1` | No explicit pin needed |
| `tenacity` | Transitive of livekit-agents (likely) | Verify in plan; if not transitive, pin `tenacity>=8.2.3` |

---

## VIII. Alternatives Considered (and rejected)

| Recommended | Alternative | Why Not |
|---|---|---|
| `sqlite-vec` | `vectorlite` (361★, Aug 2024) | Faster (15× at small N) but dormant — 8 months no release. Load-bearing dep for v2.0 should be active. |
| `sqlite-vec` | `chromadb` (18k★, active) | Heavyweight: ~50MB install (sqlite + hnswlib + duckdb deps). Overkill for our 1-table use case. |
| `sqlite-vec` | `faiss` (33k★) | Flaky Windows wheels — same install problem we're trying to solve. |
| `sqlite-vec` | `hnswlib` raw | Fastest but you build the metadata layer yourself. Not worth the effort for <30k vectors. |
| `sqlite-vec` | `Qdrant` embedded | Violates "no server" hard requirement. |
| `pyrekordbox` (XML path) | Roll our own ElementTree parser | pyrekordbox handles the format quirks (TEMPO + POSITION_MARK nesting, Rekordbox 5/6/7 schema variations). 250KB of pure Python saves us a week. |
| `pyrekordbox` (XML path) | Use pyrekordbox SQLCipher path instead | Broken post-Rekordbox 6.6.5 (Pioneer obfuscated `app.asar` key). 80%+ of users on current Rekordbox can't use SQLCipher. XML is the durable path. |
| `pydub` (subprocess ffmpeg) | `audiotools` / native PyAV bindings | pydub is Bravoh's verbatim pipeline — 80% portable code we already trust. PyAV adds a wheel-build complication on Windows (libav* DLLs). |
| `mutagen` (GPL) | `tinytag` (MIT) | tinytag is read-only and lighter but supports fewer formats (no Rekordbox-specific Vorbis comments, weaker MP4 atom handling). mutagen is the production standard. GPL infect-risk is minimal at "import as separate package" pattern. |
| `watchdog` | stdlib `os.path.getmtime` polling | Watchdog uses native FSEvents/ReadDirectoryChangesW — instant on-change vs polling lag. Worth the 150KB. |
| Three.js 4-layer additive | Spawning a new framework (React Three Fiber, Babylon.js) | Existing renderer + AnimationMixer covers the layered architecture. Adding R3F or Babylon = ~50KB + new mental model. Pure Three.js stays. |
| Bravoh-side proxy injection of `cached_content` | Client-side caching of system instruction | Cache lifecycle (1h default, 4-min refresh) is easier to manage server-side. Avoids client-side cache name leakage. |
| In-memory Evidence registry (citation) | SQLite-backed citation log | Citation evidence is per-session, ephemeral. No need for persistence; clears on session end. SQLite would be over-engineering. |
| Mascot bundled GLBs | Procedural mocap streaming | Mocap streaming + LiveKit rooms = whole new mascot pipeline. Bundled GLBs ship today (Phase 13 precedent). |
| ffmpeg static binary (Win) | Require user `winget install ffmpeg` | Violates one-click install. Bundling is the right answer. |
| Numpy fallback for sqlite-vec (Win) | Block Windows users from library intelligence | Hard rejection. Numpy fallback adds 0 deps and is fast enough. |

---

## IX. What NOT to Add (v2.0 anti-list)

Per memory `feedback_no_scope_creep_clean_utility.md` and `feedback_no_clap_use_gemini_embedding.md`:

| Avoid | Why |
|---|---|
| **CLAP / LAION-CLAP / MERT / OpenL3** | Memory locked: vibemix is Gemini-only. Gemini Embedding 2 is the embedding model. (Memory file: `feedback_no_clap_use_gemini_embedding.md`) |
| **mem0 / vector DB for DJ profile** | Memory locked: `project_v2_open_candidates.md` killed this. ~2KB structured JSON = local SQLite row. Vector DB is for library audio only. |
| **Multi-provider LLM abstraction** | Memory locked: `feedback_no_scope_creep_clean_utility.md`. Gemini-only. No OpenAI fallback, no Claude, no local LLMs. |
| **Stem separation (Demucs/Spleeter)** | Memory locked: deferred from v1 + v2. ~500MB model bundle violates one-click install. |
| **Pioneer ProDJ Link integration** | Memory locked: `project_v2_open_candidates.md` deferred. Wrong-market (CDJ hardware, not bedroom DJs). Requires Java + LAN config. |
| **Mixxx OSC as a v2.0 hard ship feature** | Bucket B-followup-1: PR #14388 unmerged into mainline Mixxx 2.5.6. Ship behind `--enable-mixxx-osc` flag for early adopters; promote to first-class when upstream merges. |
| **Serato session-file scraping** | Bucket B: `saga` archived, format undocumented. Build only if Serato users demand it. v2.1+. |
| **Rekordbox SQLCipher path** | Broken post-Rekordbox 6.6.5. XML path is the durable answer. |
| **Mascot ARKit blendshape lip-sync** | Memory locked + Bucket D: Mixamo killed blendshape export in 2020. Re-rigging = uncanny valley risk. Ship 3 amplitude-banded talk variants instead. |
| **Mixamo runtime SDK** | Memory locked: `project_mascot_as_vtuber_personality_surface.md` — Mixamo auto-rig is build-time only; runtime mascot is Three.js + GLB. |
| **Window picker auto-inference (aggressive mode)** | B-followup-1 §4: "observe, classify conservatively, never invent." Aggressive positional inference produces confidently-wrong audible-deck claims. |
| **Pydantic** | D-Area-4.4 / Phase 6 constraint: hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07. Pydantic stays banned across v2.0. |

---

## X. Plan-Checker Verification Checklist

Items the gsd-roadmapper / gsd-planner MUST verify when decomposing v2.0 phases:

- [ ] `pyrekordbox==0.4.4` install **does NOT pull `sqlcipher3-wheels`** as a hard dep — if it does, use `pip install pyrekordbox --no-deps` or evaluate `pyrekordbox-xml` shim
- [ ] `sqlite-vec==0.1.9` Windows wheel availability — re-check PyPI at planning time; if wheel ships, swap from numpy fallback to native
- [ ] `tenacity` is already transitive of livekit-agents 1.5.8 — if not, add `tenacity>=8.2.3` explicit dep
- [ ] `cached_content` field works on `gemini-3-flash-preview` (per A-followup-1 §VI open Q2 smoke test before locking caching design)
- [ ] `pyobjc-framework-ApplicationServices` is auto-resolved via `pyobjc-core==12.1` — verify with `uv pip list | grep ApplicationServices`
- [ ] PyInstaller spec includes new `datas` entries for: ack bank, element maps, controller library JSONs, ffmpeg.exe (Win)
- [ ] AIza leak gate (Phase 11 W1) extends scan to new bundle paths: `assets/ack_bank/`, `assets/element_maps/`, `assets/controller_library/`
- [ ] Bundle ID `world.bravoh.vibemix` stays locked across v2.0 (any change invalidates user TCC grants including the new AX permission)
- [ ] Three.js `AdditiveAnimationBlendMode` available at current vendored version (0.184.0 ✅ — feature shipped in r150)
- [ ] License audit: ffmpeg LGPL build chosen (not GPL build), source-availability notice in `LICENSE-3RD-PARTY.md`
- [ ] License audit: mutagen GPL-2.0 disclosed in `LICENSE-3RD-PARTY.md` with "imported as separate package" clarification
- [ ] Capability allowlist (`tauri/src-tauri/capabilities/default.json`): add `"highlight"` window label, do NOT add per-region invoke commands (overlay is draw-only, pure click-through)
- [ ] sqlite-vec import: lazy-load gated on `sys.platform != 'win32'` until Windows wheel ships
- [ ] Mascot anticipation layer 1-day spike (Bucket D open Q1): verify Gemini text-channel timing via `livekit-plugins-google` BEFORE committing to the inline-emote-tag design

---

## XI. Sources

### Primary (HIGH confidence — direct verification 2026-05-14)
- **pyrekordbox v0.4.4** — [PyPI](https://pypi.org/project/pyrekordbox/), [GitHub](https://github.com/dylanljones/pyrekordbox), 395★, MIT, Python 3.8+
- **sqlite-vec v0.1.9** — [PyPI](https://pypi.org/project/sqlite-vec/), [GitHub](https://github.com/asg017/sqlite-vec), 7.6k★, MIT/Apache 2.0, Mac+Linux wheels
- **python-osc v1.10.2** — [PyPI](https://pypi.org/project/python-osc/) (Public Domain, Python 3.10+) — for Mixxx OSC future-flag path
- **pydub v0.25.1** — [PyPI](https://pypi.org/project/pydub/), MIT
- **mutagen v1.47.0** — [PyPI](https://pypi.org/project/mutagen/), GPL-2.0, Python 3.10+
- **watchdog v6.0.0** — [PyPI](https://pypi.org/project/watchdog/), Apache 2.0, Python 3.9+
- **three.js@0.184.0** — [npm](https://www.npmjs.com/package/three), MIT
- **pyobjc-framework-AVFoundation v12.0** — [PyPI](https://pypi.org/project/pyobjc-framework-AVFoundation/)
- **pyobjc-framework-ApplicationServices** — [PyObjC docs](https://pyobjc.readthedocs.io/en/latest/apinotes/ApplicationServices.html) — AX bridge bundling
- **livekit-agents 1.5.8 source** — `.venv/.../livekit/agents/voice/speech_handle.py:141-154` (interrupt(force=True) verified empirically per A-followup-1)
- **google-genai 2.0.1 source** — `.venv/.../google/genai/caches.py:1053-1144` (caches.create() verified empirically)
- **Gemini context caching support matrix** — https://ai.google.dev/gemini-api/docs/caching — `gemini-3-flash-preview` listed (2026-05-14)
- **Tauri 2 WebviewWindowBuilder docs** — https://docs.rs/tauri/2.11.1/tauri/webview/struct.WebviewWindowBuilder.html

### Secondary (MEDIUM confidence — research artifacts)
- `.planning/research/v2-buckets/SYNTHESIS.md` — integration layer
- `.planning/research/v2-buckets/A-latency.md` + `A-followup-1-cancel-and-caching.md`
- `.planning/research/v2-buckets/B-industry-integrations.md` + `B-followup-1-v11-integration-spec.md`
- `.planning/research/v2-buckets/C-ui-overlay.md`
- `.planning/research/v2-buckets/D-mascot-emotion.md`
- `.planning/research/v2-buckets/F-library-intelligence.md`
- `.planning/research/v2-buckets/G-genre-taxonomy.md` + `G-followup-1-hard-tek-dsp.md`
- Bravoh `app/services/embedding/service.py` (private, `ssh altidus`) — 80%-portable embed pipeline

### Tertiary (LOW confidence — flag for plan-time validation)
- sqlite-vec Windows wheel availability at planning time (PyPI may have shipped one by Phase X kickoff — re-check)
- `pyrekordbox==0.4.4` SQLCipher dep tree — verify install-time whether `--no-deps` is needed to skip the broken SQLCipher chain
- ffmpeg LGPL static build for Windows — pin a specific gyan.dev build version + SHA-256 (precedent: Phase 11 W3 DSEG7 font pinning)

### Memory anchors (locked decisions — cite in plan-checker)
- `project_v2_open_candidates.md` — Mixxx OSC + map transpile + pyrekordbox + Gemini Embedding 2 + post-session debrief CONFIRMED; ProDJ Link + stems + CLAP DEFERRED
- `feedback_no_clap_use_gemini_embedding.md` — Gemini-only embedding stack
- `project_one_click_install_hard_req.md` — every new dep rated green/yellow/red
- `feedback_no_scope_creep_clean_utility.md` — Gemini-only, no multi-provider, no enterprise features
- `project_v4_canonical_baseline.md` — cohost_v4.py is the port baseline
- `project_phase_16_kaan_dj_testing.md` — Phase 16 = Kaan's DJ ear, NOT formal eval suite
- `project_v0_1_0_rc1_open_bugs.md` — outstanding v0.1.0 work being absorbed into v2.0

---

## XII. Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `pyrekordbox==0.4.4` doesn't hard-require `sqlcipher3-wheels` at import (only on `Rekordbox6Database()` instantiation) | §II.D, §X | Install footprint balloons by ~10MB if sqlcipher3-wheels gets pulled. Mitigation: `--no-deps` install path. |
| A2 | `sqlite-vec` Windows wheel will eventually ship via PyPI (v2.0 ships before that, v2.1 promotes to native) | §II.E, §III | If wheel never ships, the numpy fallback is permanent — acceptable per Bravoh's production pattern. |
| A3 | Ffmpeg LGPL static build is sufficient for pydub MP3 transcoding (no GPL-only encoders needed) | §II.E, §III | If LGPL build lacks an encoder we need (e.g. AAC decode for M4A → WAV → MP3 chain), fall back to GPL build and bear the license obligation. |
| A4 | `cached_content` field is forwarded through `livekit-plugins-google` LLM cascade via `extra_kwargs` mechanism | §II.A | Plan-checker smoke test required (per A-followup-1 open Q2). If broken, fall back to no-caching (~200-300ms TTFT regression — acceptable but loses 1000ms target). |
| A5 | AX permission TCC prompt on first-run does NOT regress the Phase 11 fresh-machine <90s wizard timing | §II.C | If AX prompt blocks for >10s, defer the prompt to user-triggered "Enable highlight" toggle (Bucket C open Q5 fallback). |
| A6 | Three.js `AdditiveAnimationBlendMode` works on stylised mascot rig without "skeleton overscaled" issues per [forum thread](https://discourse.threejs.org/t/changing-animationactions-blendmode-to-animationblendmode/46994) | §II.F | If overscale appears, the fix is `AnimationUtils.makeClipAdditive()` preprocessing — one-time per clip in asset-loader.ts. Standard recipe. |
| A7 | Bundle size growth ~270-290 MB (Mac), ~290-310 MB (Win) stays under 350 MB hard cap | §V | If bundle exceeds 350 MB, prime drop candidates: PyInstaller `--exclude-module` for `livekit.plugins.openai` (unused), trim mascot GLBs to 5 essential clips, audio ack bank → OPUS (saves ~7MB) |
| A8 | `mutagen` GPL-2.0 "import as separate package" pattern stands per RMS clarification on Python imports + GPL | §IV | If license counsel disagrees, swap to `tinytag` (MIT) — loses some Vorbis comment + MP4 atom support but covers 80% of DJ-tagged libraries |

---

*Stack research complete. v2.0 additions documented as a strict additive layer on top of the validated Phase 1-14 baseline. Every new dep rated for one-click-install impact. Plan-checker verification list in §X is the load-bearing handoff to gsd-roadmapper for phase decomposition.*

**Word count: ~4,500. Last updated: 2026-05-14.**
