# Stack Research — v2.1 The Unified Cut

**Domain:** Desktop AI co-host (subsequent milestone — v2.0 already shipped at `tech_debt`)
**Researched:** 2026-05-14
**Confidence:** HIGH on existing-stack-covers verdicts (read directly from `pyproject.toml` + `Cargo.toml` + `package.json`); MEDIUM-HIGH on new pin recommendations (versions verified via WebSearch May 2026 — Context7 not available in this agent for these niche libs)
**Audience:** `gsd-research-synthesizer` → `gsd-roadmapper` → `gsd-planner`

---

## TL;DR — The v2.1 Stack Discipline

**Headline:** ~80% of v2.1 buckets need **zero new runtime dependencies**. The locked v2.0 stack already covers post-session debrief UI, library intelligence, mascot rewrite, GLB pipeline, screen capture, viral demo, token budgets, secret scanning hooks, and Apple/SignPath signing — what's missing is **wiring, dev-only deps, and CI surface**, not new shipped libs.

The new additions are concentrated in three places:
1. **Python sidecar** — `sqlite-vec==0.1.9` (was reserved-but-not-installed in v2.0; turn on for v2.1), and one optional dev-only `pytest-asyncio` if missing. That's it.
2. **CI yml** — `gitleaks`, `pip-audit`, `cargo-audit`, `cargo-deny`, `gh` CLI, `rcodesign` fallback, `SignPath CLI` invocation. All dev-tool surface, **zero bundle impact**.
3. **Off-machine helpers** — Meshy / Hunyuan3D API for one-time GLB authoring (Kaan/artist runs locally + commits resulting `.glb` files; nothing ships in the binary). Veo 3.1 for one-time demo film (output is the `.mp4`; SDK does not need to ship).

The "Bundle ≤350MB" cap is honored: net runtime bundle delta is **+0 MB to +0.6 MB** depending on whether the Apple-Silicon `sqlite-vec` extension lights up Windows numpy fallback (numpy already shipped, so Win = 0 MB; Mac = ~600 KB for the loadable `.dylib`).

**One-click install impact:** GREEN across the board for runtime. Dev-only deps land in `[dependency-groups] dev` so end-user `uv sync --no-dev` skips them entirely.

---

## Existing Stack (DO NOT modify)

Carried verbatim from `pyproject.toml` + `tauri/src-tauri/Cargo.toml` + `tauri/ui/package.json` as of v2.0 ship audit (`b777113`). Anything that v2.1 needs from this list is **already in the binary** — only call-site work required.

### Python sidecar runtime (locked by `pyproject.toml`)
- `google-genai>=2.0.1` — Gemini Embedding 2 + Veo 3.1 + Gemini 3 Flash multimodal + Gemini TTS streaming all use the same SDK; **no new package needed for embedding/judge/video**
- `livekit-agents>=1.5.8`, `livekit>=1.1.7`, `livekit-plugins-google>=1.5.8`, `livekit-plugins-openai>=1.5.8` (last is transitive only)
- `numpy>=2.4.4`, `scipy>=1.17.1`, `sounddevice>=0.5.5`, `mido>=1.3.3`, `python-rtmidi>=1.5.8`
- `pyrekordbox==0.4.4` + 5 manually-declared transitives + `sqlcipher3-wheels` permanently overridden out (saves 3.2 MB)
- `pillow>=12.2.0`, `pyjwt>=2.12.1`, `jsonschema>=4.23,<5`, `websockets>=13.0`, `python-dotenv>=1.2.2`, `keyring>=25.7.0`, `httpx>=0.28`
- **macOS-gated:** `pyobjc-core/Cocoa/Quartz/ScreenCaptureKit/AVFoundation>=12.1` (ScreenCaptureKit is the v2.0 macOS 12.3+ screen capture path; the v1 `mss` path is now win32-only)
- **Windows-gated:** `pyaudiowpatch>=0.2.12`, `pywin32>=308`, `winsdk>=1.0.0b10`, `mss>=10.2.0`

### Python dev-only (in `[dependency-groups] dev`)
- `ruff>=0.7`, `pytest>=8.0`, `pytest-mock>=3.15.1`, `pyinstaller==6.20.0`, `pyyaml>=6.0`

### Tauri Rust (locked by `Cargo.toml`)
- `tauri 2.11` with features `macos-private-api`, `config-json5`, `tray-icon`, `image-png`, `devtools`, `protocol-asset`
- 7 Tauri plugins: `shell`, `store`, `fs`, `positioner`, `updater`, `process`, `global-shortcut` (all on Tauri 2.x track)
- `tokio = "1"`, `tokio-tungstenite = "0.29"`, `futures-util = "0.3"` — async stack + WS conduit to Python ws_bus
- `serde / serde_json = "1"`, `tracing = "0.1"`, `file-rotate = "0.8"`, `dirs-next = "2"`
- **macOS-gated:** `core-graphics = "0.24"`, `core-foundation = "0.10"`, `accessibility-sys = "0.1"` (Phase 24 AX bridge for djay overlay)
- Release profile already tuned: `lto = true`, `panic = "abort"`, `strip = true`, `opt-level = "s"`

### Tauri webview (locked by `tauri/ui/package.json`)
- **Runtime:** `three ^0.170.0` only — that's the entire shipped JS runtime dep tree
- **Dev:** `@gltf-transform/cli ^4.0.0`, `@gltf-transform/core ^4.0.0`, `gltf-pipeline ^4.1.0`, `@tauri-apps/api ^2.11`, `@tauri-apps/plugin-shell ^2.3`, `@tauri-apps/plugin-store ^2.4`, `ajv ^8.20`, `ajv-formats ^3.0`, `vite ^6.0`, `vitest ^2.1`, `typescript ^5.7`, `json-schema-to-typescript ^15.0`, `jsdom ^29.1.1`, `vite-plugin-static-copy ^2.2.0`

### Locked decisions (do not relitigate)
- **Bundle ID `world.bravoh.vibemix`** — TCC permissions break on any change
- **Apache 2.0 + DCO** — every new dep MUST be Apache-2.0 / MIT / BSD / ISC compatible (no GPL / AGPL / LGPL-without-static-exception / SSPL)
- **macOS 12.3+ / Windows 10-11** — Linux explicitly excluded
- **Gemini-only AI**, no Anthropic / OpenAI / Ollama in the product (LiveKit plugin-openai is transitive-only and unused at call sites)
- **No CLAP / OpenL3 / MERT / LAION-CLAP** — even when research suggests them
- **No new external processes beyond Tauri parent + Python sidecar + FastAPI proxy** on api.altidus.world

---

## New Stack Additions — Per Bucket

### Bucket 1: Autonomous Proxy Hallucination Gate (Phase 27 candidate)

> Closes v2.0 carry-forward `VERIFY-07..10` autonomously via recorded-session replay + LLM-judge scorer + F1 validator. The autonomous-proxy gate substitutes for Phase 16 "Kaan's DJ ear" path per the v2.1 milestone memo.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Replay harness runtime** | **EXISTING v2.0 covers it.** `scripts/replay_linter.py` (shipped in Phase 20 Plan 03) is the harness skeleton; v2.1 extends with multi-session fixture loop. | — | — | 0 | GREEN |
| **LLM judge invocation** | **EXISTING `google-genai>=2.0.1` covers it.** Same SDK already used by Gemini 3 Flash live path; judge calls go to the same client. | — | — | 0 | GREEN |
| **Judge model selection** | **Gemini 3 Pro** for the judge, **Gemini 3 Flash** for the candidate. Pro's longer reasoning + deeper rubric-following make it the canonical judge per Vertex AI's eval-service guidance, and using a different model than the candidate is anti-correlation hygiene. Cost is a one-shot CI run (~50 sessions × ~5K tokens/session ≈ trivial); ongoing cost is zero (judge does not run in product). | model = `gemini-3-pro` via `client.models.generate_content` | — | 0 | GREEN |
| **F1 / precision / recall math** | **stdlib only.** Confusion-matrix counting is 20 lines; no `scikit-learn` needed (and `scikit-learn` would be ~30 MB; rejected for bundle violation even though dev-only because it pollutes the test env). | — | — | 0 | GREEN |
| **Threshold lock + CI gate** | New `scripts/hallucination_gate.py` in repo; runs in `release.yml` as a separate `verify-hallucination` job. PASS = ≥0.90 grounded-precision threshold (calibrated per ear-test session fixtures) gates the release artifact. | — | — | 0 | GREEN |
| **`pytest-asyncio` (if missing)** | Add to `[dependency-groups] dev` only if not already pulled transitively by `pytest-mock`. Replay harness awaits Gemini SDK coroutines under pytest. Confirm absence first before adding. | `>=0.24` | Apache-2.0 | 0 (dev-only) | GREEN |

**Why over alternatives:**
- `deepeval` / `langchain-evals` / Vertex AI Eval Service — all rejected. Each pulls 50-200 MB of transitive deps (langchain alone ≈100 MB), violates the Gemini-only + lean-utility memory, and re-implements 20 lines of confusion-matrix math we'd write anyway. Direct `google-genai` calls + stdlib counting wins on every axis.
- Gemini 3 Pro vs Flash as judge — Pro chosen because v2.0 ear-test ground truth is sparse; deeper rubric-following at the judge layer offsets the small sample size. Flash would be ~5× cheaper but the run is one-shot.

**Integration point:** `scripts/hallucination_gate.py` (new) + `.github/workflows/release.yml` (extend) + extend `scripts/replay_linter.py` (existing). All Python-side, no Tauri/Rust touch.

**What NOT to add:**
- `scikit-learn` — 30 MB transitive bloat for 20 lines of confusion-matrix math
- `deepeval` / `langchain-evals` / `evidently` — multi-provider wrappers, scope-creep
- `mlflow` for run tracking — overkill; events.jsonl in `recordings/` already captures session-level state

---

### Bucket 2: Library Intelligence v1 — Gemini Embedding 2 + sqlite-vec

> Closes v2.0 `LIBRARY-03..06` carry-forward. Vibe search, "what's playing" grounding, transition critique queries.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Gemini Embedding 2 client** | **EXISTING `google-genai>=2.0.1` covers it.** Model ID `gemini-embedding-2-preview`, called via `client.models.embed_content(model="gemini-embedding-2-preview", contents=[...], config=...)`. 3072-dim default, MRL truncation to lower dims supported. Up to 180s audio per call (matches v2.0 audio buffer windows). | model = `gemini-embedding-2-preview` | — | 0 | GREEN |
| **sqlite-vec loadable extension** | **Architectural slot already reserved in v2.0** per `pyproject.toml` comment (LIBRARY-08); v2.1 lights it up. Add `sqlite-vec==0.1.9` to `dependencies`. macOS + Win wheels ship from PyPI; pure-stdlib `numpy` cosine fallback path is already partially scaffolded. | `sqlite-vec==0.1.9` (released 2026-03-31) | Apache-2.0 / MIT dual | +0.6 MB on Mac (loadable `.dylib`), +0.4 MB on Win | GREEN |
| **Cosine / dot-product math** | **EXISTING `numpy>=2.4.4` covers it.** `numpy.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))` is the fallback when sqlite-vec is unavailable; sqlite-vec handles vector indexes + KNN when present. | — | — | 0 | GREEN |
| **Vibe-search query interface** | New Python module `src/vibemix/library/embedding.py` (re-uses `RekordboxLibrary` from Phase 25). No new lib. | — | — | 0 | GREEN |
| **Drag-drop UI in Settings → Library tab** | **EXISTING Tauri 2 `dragDropEvent`** in `@tauri-apps/api ^2.11` covers it (web-standard HTML5 drag-drop fires inside Tauri webview). No plugin needed. | — | — | 0 | GREEN |
| **30-day staleness nudge** | Pure Python date arithmetic + existing IPC ws_bus surfaces the nudge to the Settings drawer. No lib. | — | — | 0 | GREEN |

**Why over alternatives:**
- **Gemini Embedding 2 vs CLAP/MERT/OpenL3:** locked by memory `feedback_no_clap_use_gemini_embedding` — Gemini Embedding 2 is the chosen path (natively multimodal: audio + image + text + video + docs into one 3072-dim space; perfectly fits cross-modal queries like "tracks that sound like this screenshot + this audio clip"). CLAP/MERT/OpenL3 also each ship 200-500 MB of model weights, violating the bundle cap.
- **sqlite-vec vs Faiss / Qdrant / Chroma:** locked by `pyproject.toml` v2.0 comment and `feedback_no_scope_creep_clean_utility`. Qdrant/Chroma are server-bound (violates "no new external processes"). Faiss adds 30-100 MB + requires Intel MKL on Win (red install impact). sqlite-vec ships as a single SQLite extension (~600 KB), uses the SQLite file already on every OS, and the numpy fallback handles Windows ARM64 where the wheel may not have an ARM64 binary yet (graceful degradation — small-corpus brute-force cosine is fast enough for personal libraries).
- **Output dimension:** default 3072-dim from Gemini Embedding 2, truncatable to 768 or 1536 via MRL if storage matters for 50k-track libraries. Phase plan decides per-corpus-size benchmark.

**Integration point:** `src/vibemix/library/embedding.py` (new) + `src/vibemix/library/__init__.py` extend `RekordboxLibrary` + `tauri/ui/src/settings/library/*` (drag-drop component) + new `ipc.library.embed_progress` schema in `src/vibemix/ui_bus/schemas/`.

**What NOT to add:**
- `chromadb` / `qdrant-client` / `weaviate-client` / `pymilvus` — all server-bound, violate one-click install + no-new-external-processes
- `faiss-cpu` / `faiss-gpu` — 30-100 MB + Intel MKL on Win → red install impact
- `sentence-transformers` / `transformers` — pulls torch (~800 MB), violates Gemini-only + bundle cap
- `langchain` / `llama-index` — multi-provider wrappers; we own our 100 lines of glue, no abstraction tax

---

### Bucket 3: Post-Session Debrief MVP UI

> Closes v2.0 `DEBRIEF-01..02` carry-forward — the sidecar `--debrief` flag + 3 IPC schemas + port 8766 already ship; v2.1 builds the UI consumer.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Audio player + waveform** | **Recommended: wavesurfer.js v7** — best-in-class waveform renderer with Regions + Timeline plugins; v7 is a TS rewrite with Shadow DOM CSS isolation. **NOT yet in `package.json`** (CLAUDE.md mentioned it; reality is the bundle currently has zero web audio lib). Add as new npm dep. | `wavesurfer.js ^7.10` + `@wavesurfer/react ^1.0` (React-19-compatible hook wrapper); or use vanilla wavesurfer directly since the rest of the codebase is vanilla TS — **vanilla is the choice** (no React in vibemix UI). | BSD-3-Clause | +180 KB minified (~60 KB gzipped) | GREEN |
| **Chaptered timeline** | wavesurfer.js **Regions plugin** (built-in, ships with main package) handles chapter markers. Chapter data structure: stdlib JSON in `events.jsonl` per session (already exists). | — | — | 0 (in the +180 KB above) | GREEN |
| **Drill cards (interactive)** | **EXISTING vanilla TS + tokens.css** covers it. Same pattern as Settings/Recording browser. No framer-motion, no React. | — | — | 0 | GREEN |
| **Voiced TL;DR audio generation** | **EXISTING `google-genai>=2.0.1` + Gemini TTS** covers it. Same path as live-mode TTS streams; only difference is the prompt template ("60-90s summary of session") and offline generation (sidecar's `--debrief` flag, no live constraint). | — | — | 0 | GREEN |
| **Chapter markers data structure** | New `src/vibemix/debrief/chapters.py` + new IPC schema `ipc.debrief.chapter` (extends the 3 reserved DEBRIEF schemas). | — | — | 0 | GREEN |

**Why over alternatives:**
- **CLAUDE.md note:** the doc says "WaveSurfer.js" is in the stack, but the actual `package.json` does not include it. Treating it as a **new add for v2.1**, not existing.
- **wavesurfer.js vs Howler.js vs Tone.js vs raw `<audio>`:** wavesurfer alone provides chaptered waveform UI out-of-box. Howler is pure playback (no waveform). Tone.js is a synthesis library (wrong tool). Raw `<audio>` + custom canvas waveform = +2 weeks of phase work. wavesurfer is the unambiguous fit.
- **React vs vanilla TS:** vibemix's `tauri/ui/src/` is vanilla TS — adding React 19 just for the debrief view (as CLAUDE.md project section suggests) would pull React 19 + react-dom + 200 KB of runtime, violate the lean-utility memory, and create a split UI architecture. Reject React; stay vanilla. The CLAUDE.md "React 19 + Vite + TS" line is **Bravoh's** stack, not vibemix's. Confirmed by reading `package.json`.

**Integration point:** `tauri/ui/src/session/debrief/*` (new directory) + `src/vibemix/debrief/*` (new Python module) + extend `tauri/ui/package.json` with `wavesurfer.js ^7.10`. Sidecar `--debrief` already wired in v2.0 Phase 25 Plan 03.

**What NOT to add:**
- React / Vue / Svelte — vanilla TS is the locked UI architecture
- Howler.js / Tone.js — wrong domain (playback / synthesis vs visualization)
- Framer Motion — also Bravoh-stack confusion in CLAUDE.md; vibemix has none of it
- Custom WebAudio + canvas waveform — +2 weeks; wavesurfer is the right "buy not build"

---

### Bucket 4: 4-Layer Mascot Full Additive State Machine

> Replaces v2.0 simplified anticipation subset with full base + emotion + anticipation + reaction additive layers.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Three.js single-mixer + additive blend** | **EXISTING `three ^0.170.0` covers it.** `THREE.AnimationMixer` + `THREE.AnimationUtils.makeClipAdditive()` + `action.blendMode = THREE.AdditiveAnimationBlendMode` + `action.crossFadeTo()` are all native APIs in r170. v2.0 Phase 22 already ships `additive-layer.ts` + `state-machine.ts` — v2.1 extends to 4 layers. | — | — | 0 | GREEN |
| **Priority stack + crossfade scheduler** | EXISTING `tauri/ui/src/mascot/state-machine.ts` covers the data structure; v2.1 expands the priority enum to 4 levels (base 10, emotion 30, anticipation 70, reaction 90). Pure TS. | — | — | 0 | GREEN |
| **Cancel-aware GLB layer system** | EXISTING ws_bus integration covers the cancel signal. The cancel-cooldown plumbing from `CancelGate` (v2.0 Phase 19) already publishes cancel events at 30Hz to mascot. No new lib. | — | — | 0 | GREEN |
| **Tween library** | **NOT NEEDED.** Three's `crossFadeTo(duration, warpFlag)` handles temporal blending natively. No `tween.js` / `gsap` / `@tweenjs/tween.js`. | — | — | 0 | GREEN |
| **Mixamo helper / IK solver** | **NOT NEEDED at runtime.** Mixamo rigs are baked at authoring time (off-machine) and the resulting `.glb` files are static at runtime. No `three-mixamo` / `three-ik` package. | — | — | 0 | GREEN |
| **Beat-coupled hip-bob** | EXISTING Phase 22 Plan 02 shipped this — v2.1 wires it into the 4-layer priority graph as a continuous procedural layer at priority 5 (under base). Pure TS math. | — | — | 0 | GREEN |

**Why over alternatives:**
- **Three.js native vs gsap/@tweenjs/tween.js:** `crossFadeTo` does exactly what we need (temporal weight ramp between two actions on the same mixer). gsap is a $$$ marketing-page tool; @tweenjs/tween.js is a 5 KB lib that mostly duplicates Three's animation API. Native wins.
- **Single mixer mandate:** locked by v2.0 Phase 22 Plan 02 (P19 Pitfall mitigation). Multi-mixer architectures cause phase drift between hip-bob and prep clips. v2.1 honors the single-mixer constraint.

**Integration point:** `tauri/ui/src/mascot/state-machine.ts` (extend), `tauri/ui/src/mascot/additive-layer.ts` (extend to 4 channels), `tauri/ui/src/mascot/types.ts` (extend MascotState union). All TS-side, no Python/Rust touch.

**What NOT to add:**
- `@tweenjs/tween.js` / `gsap` / `motion` — Three's native APIs cover crossfades
- `three-mixamo` / `three-ik` — rigging is baked off-machine; runtime IK not needed
- `cannon-es` / `rapier3d` — physics-based mascot was rejected in earlier mascot research; we use pre-authored anim, not physics

---

### Bucket 5: One-Click Install Hardening

> macOS DMG + Windows MSI fresh-VM tested end-to-end; TCC permissions wizard; auto-fetch deps; first-launch onboarding.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **TCC permissions wizard (macOS)** | **Recommended: `tauri-plugin-macos-permissions` v2.3.0** (2025-05-06) — community plugin, works with Tauri 2.x; provides check/request hooks for accessibility, screen-recording, microphone, full-disk-access, camera, input-monitoring. Pulls `macos-accessibility-client` + `FullDiskAccess` underneath. The wizard flow calls these from the Rust parent (NOT sidecar, per Tauri #8329 / Phase 24 lessons). Add as new Rust crate dep. | `tauri-plugin-macos-permissions = "2.3.0"` | MIT | +200 KB Mac binary (zero on Win — gated by `cfg(target_os = "macos")`) | GREEN (Tauri permission prompts are macOS-native, single OS dialog) |
| **Windows UAC / WASAPI loopback init test** | **EXISTING `pyaudiowpatch>=0.2.12`** covers WASAPI loopback enumeration. UAC elevation only needed for first-run if Defender SmartScreen blocks — handled by **EXISTING `signtool`-signed MSI** (Phase 21 SignPath path). No new Rust crate; the Tauri MSI bundler is the unblock. | — | — | 0 | GREEN once SignPath approval lands |
| **Defender SmartScreen handling** | **EXISTING SignPath OSS** (Phase 21 Kaan-action pending) is the actual fix — SmartScreen reputation builds after ~3000 downloads of a signed binary. No tooling addition; the docs need a "what to expect on first launch" callout in the install README. | — | — | 0 | YELLOW until reputation builds (~3000 first installs) — known OSS pain |
| **Dep auto-fetch verifier** | New `scripts/preflight.py` (Python) runs at first launch — checks BlackHole/VB-CABLE present, MIDI port accessible, mic perm granted, screen-recording perm granted. Pure stdlib (`subprocess`, `pathlib`, `shutil.which`). No new lib. | — | — | 0 | GREEN |
| **Fresh-VM test runner** | **Recommended: `tart` for macOS + GitHub Actions `windows-2022` runners for Windows.** Tart uses Apple's native Virtualization.framework, runs macOS 14+ images in CI, hands the binary into a clean userland in <60s. Windows side: GH Actions windows-2022 runner is already a clean VM per-job, so no separate provisioner needed. | tart latest (CLI install via Homebrew) | Fair Source 1.0 (free for OSS / non-commercial CI; we are OSS) | 0 (CI-only) | GREEN (CI-only) |
| **Fresh-VM rehearsal screencast** | EXISTING `ffmpeg` (via Veo 3.1 output pipeline anyway) handles screen capture if Kaan runs the rehearsal manually on a fresh VM. Day-Zero ops audit gate is `scripts/dayzero/healthz_check.sh` (shipped Phase 26). Kaan-action surface, but no new tooling. | — | — | 0 | GREEN |

**Why over alternatives:**
- **`tauri-plugin-macos-permissions` vs writing AX shims by hand:** Phase 24 already proves Rust-parent AX is the right pattern (Tauri #8329 lesson). The plugin abstracts the 6 TCC permission types we need, has been maintained through Tauri 2.0 → 2.3.0 with active updates, and is single-purpose (no other features creep in).
- **`tart` vs `multipass` vs `vagrant`:** macOS support is the limiting factor. Tart is Apple-Silicon-native via Virtualization.framework (sub-second cold-start); Multipass on macOS only runs Ubuntu VMs (wrong OS); Vagrant + VirtualBox on Apple Silicon is broken since 2022 (Oracle hasn't shipped ARM64 VirtualBox). Tart wins by default.
- **`tart` license:** Fair Source 1.0 is OSS-friendly (free for our use); license-clean for Apache-2.0 OSS CI runners. Verified license terms allow embedding the CLI invocation in our `release.yml`.
- **Windows: GH Actions runners vs dedicated VM:** GH `windows-2022` runners are already isolated per-job; using them avoids spinning up a separate Hyper-V / VirtualBox toolchain and lets the existing release.yml matrix double as the fresh-VM rehearsal.

**Integration point:** `tauri/src-tauri/Cargo.toml` (+tauri-plugin-macos-permissions), `tauri/src-tauri/src/main.rs` (register plugin), `tauri/src-tauri/capabilities/default.json` (allowlist), `tauri/ui/src/wizard/` (extend wizard step for permissions), `scripts/preflight.py` (new), `.github/workflows/freshvm-rehearsal.yml` (new).

**What NOT to add:**
- `osascript`-driven AppleScript automation for TCC — Apple deprecated programmatic `tccutil` reset path; doesn't survive between OS versions
- `winreg` / `WMI` for Defender SmartScreen workarounds — Microsoft explicitly blocks these; only signing builds reputation
- Multipass / Vagrant — see above; wrong fit for macOS rehearsal

---

### Bucket 6: Open-Source Security Pass

> API key gate audit · secret scanner CI · dependency CVE audit · signed-binary verification · permission least-scope · threat model + SECURITY.md.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Secret scanner (CI gate)** | **Recommended: `gitleaks` v8.x in CI + GitHub Push Protection enabled** | gitleaks 8.x (action `gitleaks/gitleaks-action@v2`) | MIT | 0 (CI-only) | GREEN (CI-only) |
| **Python dep CVE audit** | **Recommended: `pip-audit` v2.x in CI + OSV.dev backing.** Lower false-positive rate vs Safety, free for OSS+commercial (Safety CLI restricts commercial), PyPA-maintained. | pip-audit 2.7+ | Apache-2.0 | 0 (CI-only) | GREEN (CI-only) |
| **Rust dep CVE audit** | **Recommended: `cargo-audit` + `cargo-deny` (paired).** Audit catches RustSec advisories; deny enforces license policy (auto-reject GPL/AGPL transitives into our Apache-2.0 binary). | cargo-audit 0.21+, cargo-deny 0.16+ | Apache-2.0 / MIT each | 0 (CI-only) | GREEN (CI-only) |
| **npm dep CVE audit** | **Recommended: `npm audit` + `osv-scanner` second opinion.** `npm audit` is built-in (zero install cost); `osv-scanner` (Google's, 30+ ecosystem aggregator) catches the small slice that npm misses. | osv-scanner 1.9+ | Apache-2.0 | 0 (CI-only) | GREEN (CI-only) |
| **PyInstaller bundle scanner** | **Recommended: `pip-audit` already covers the resolved-dep graph at build time.** Avoid Trivy specifically — there was a March 2026 supply-chain compromise of Trivy's GitHub Actions tags; DB updates are still suspended per search results. **NOT picking Trivy** until upstream resolves. Grype is the contingency if pip-audit ever proves insufficient. | (Grype as fallback only) | — | 0 | GREEN |
| **Signed-binary verifier** | New `scripts/dist/verify_binary.py` (already shipped in v2.0 — extend it) + GH Actions step that re-verifies the signed artifact's notarization receipt + SignPath signature after download in the release matrix. Pure CI scripting. | — | — | 0 | GREEN |
| **Threat model docs** | **STRIDE-lite markdown in `SECURITY.md`** (already stubbed in v2.0 README). Mozilla Rapid Risk Assessment is overkill for a single-binary OSS desktop app. STRIDE-lite = ~1 page covering Spoofing (proxy auth via api.altidus.world JWT), Tampering (signed binaries + Tauri updater ed25519), Repudiation (local recordings, no upload), Information Disclosure (audio streamed to proxy only, never persisted server-side), DoS (proxy rate-limit), Elevation (TCC sandbox + no root install). | — | — | 0 | GREEN |
| **SBOM generation** | **`syft` in CI** for SBOM emission (optional, low-cost). Pairs with Grype if we ever pivot off pip-audit. | syft 1.x | Apache-2.0 | 0 (CI-only) | GREEN |

**Why over alternatives:**
- **gitleaks vs trufflehog vs detect-secrets:** gitleaks wins for **fast CI gates** (regex engine, milliseconds, SARIF for GitHub Code Scanning); trufflehog's secret-verification feature is overkill for a single-repo lean utility. detect-secrets is best for legacy codebases with existing leaks to baseline — we don't have that problem. Best-practice 2026 = gitleaks in pre-commit + trufflehog in scheduled scans; for an OSS utility, gitleaks-only is enough.
- **pip-audit vs Safety vs OSV-Scanner:** pip-audit + OSV is the lowest-false-positive combo per 2026 benchmarks (98% CVE recall in the OSV space). Safety CLI is not free for commercial — even though vibemix is OSS, Bravoh's internal use is not (per CONSTRAINT memory "must allow Bravoh to use the same code internally"). pip-audit clears that license restriction.
- **cargo-audit + cargo-deny:** standard Rust-secure-code-WG pairing. cargo-deny enforces the no-GPL transitive policy without a manual check.
- **Trivy SUPPLY CHAIN ALERT:** March 2026 compromise documented in WebSearch results — Trivy's release tags were hijacked and DB updates are suspended. **HARD NO on Trivy in v2.1 CI** until upstream resolves; revisit ≥ Q3 2026.

**Integration point:** `.github/workflows/security.yml` (new — runs gitleaks + pip-audit + cargo-audit + cargo-deny + npm audit + osv-scanner on every push), `SECURITY.md` (extend), `scripts/dist/verify_binary.py` (extend already-shipped script).

**What NOT to add:**
- Trivy — supply chain compromise active as of March 2026
- Safety CLI — commercial-use restriction blocks Bravoh's internal reuse
- Snyk / GitHub Advanced Security — closed-source / paid; we are OSS
- Veracode / Checkmarx — enterprise overkill

---

### Bucket 7: Long-Term DJ Profile

> ~2KB JSON regenerated each session, injected verbatim into the next live system prompt.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **JSON serialization** | **EXISTING stdlib `json`** covers it. ~2KB is trivial. | — | — | 0 | GREEN |
| **Storage location** | New `~/Library/Application Support/vibemix/profile_<user_hash>.json` (mac) + `%APPDATA%/vibemix/profile_<user_hash>.json` (win) — same pattern as v2.0 `library.pkl` cache. Stdlib `pathlib` + `os.environ`. | — | — | 0 | GREEN |
| **2KB token budget enforcement** | **`client.models.count_tokens(model="gemini-3-flash-preview", contents=...)` from EXISTING `google-genai>=2.0.1`.** Per WebSearch: tiktoken is **NOT useful for Gemini** (different tokenizer — SentencePiece, not BPE). The Gemini SDK's native count_tokens uses the right vocabulary. Local cached on first call (downloads vocab once, then offline). | — | — | 0 | GREEN |
| **Schema validation** | **EXISTING `jsonschema>=4.23,<5`** covers it. Same Draft-07 path already used by all `ipc.*` schemas. | — | — | 0 | GREEN |
| **Profile generation prompt** | New `src/vibemix/profile/regenerator.py` — calls Gemini 3 Flash with session events.jsonl as input, asks for ≤2KB JSON output. No new lib. | — | — | 0 | GREEN |

**Why over alternatives:**
- **tiktoken — REJECTED.** Per WebSearch: tiktoken is BPE-based (GPT vocab), Gemini uses SentencePiece. Adding tiktoken would give the wrong count by 10-30%. The SDK's native counter is the only correct path.
- **No DB needed:** ~2KB JSON × one user = trivial; stdlib `json.dump()` is the right answer. No SQLite, no `tinydb`, no mem0.

**Integration point:** `src/vibemix/profile/` (new module), `src/vibemix/runtime/coach.py` (inject profile into system instruction), `src/vibemix/__main__.py` (load profile at session start, regenerate at session end).

**What NOT to add:**
- `mem0` / `motorhead` / `langgraph-checkpoint` — wrong problem; we have a 2KB blob, not an agent-memory graph
- `tiktoken` — wrong tokenizer
- `tinydb` / sqlite — overkill for a single 2KB file

---

### Bucket 8: Real GLB Mascot Animations + Rigging Autonomously

> Replace 5 `prep_*` placeholder GLBs with real animations; close v2.0 `MASCOT-11`.

**Important framing:** This is **off-machine authoring**, not runtime. Nothing in this bucket ships in the binary — the output is committed `.glb` files in `tauri/ui/public/mascot/`.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Text-to-3D base mesh** | **Recommended: Meshy AI v6 API** (text-to-3D with Standard + Pose preset for animation-ready rigging). REST API, async tasks, exports GLB/FBX/USDZ. Costs ~$20-50 in credits for the 1 base mascot + alt mood meshes. **One-shot, off-machine** — invoked via `scripts/gen_mascot_assets.py` Kaan/artist runs locally. | Meshy REST API (no SDK to ship) | API ToS | 0 (output files only) | N/A (off-machine authoring) |
| **Hunyuan3D 2.0 fallback** | Tencent's Hunyuan3D 3.0 (open weights) is the no-API-cost alternative. Self-host via `huggingface_hub` + diffusers ad-hoc — but only as Plan B if Meshy quality disappoints. | (off-machine, ad-hoc) | Tencent OSS | 0 | N/A |
| **Auto-rigging** | **Mixamo** (free, manual upload) — Meshy v6 also has integrated auto-rig + 100+ preset clips, which removes the Mixamo step entirely. Pick Meshy integrated rig first; Mixamo is the fallback. | Adobe Mixamo (web UI) | Adobe ToS (free for use) | 0 | N/A |
| **GLB optimization (compression)** | **EXISTING `@gltf-transform/cli ^4.0.0` + `gltf-pipeline ^4.1.0`** — both already in `tauri/ui/devDependencies`. v2.0 build pipeline already runs these. v2.1 just extends the optimization recipe (Draco mesh compression + KTX2 textures + WebP). | — | — | -2 to -10 MB per GLB after optimization | GREEN |
| **Blender MCP tools** | **Optional dev-time helper.** If `mcp__blender__*` MCP tools are available in the spawning environment, use them for procedural cleanup (re-center pivot, scale to unit, fix material slots) — but this is dev-machine only. | (MCP server, no binary) | — | 0 | N/A |
| **GLB total budget** | EXISTING v2.0 CI gate: 15 MB total across all GLBs (Phase 22 MASCOT-19). v2.1 respects it. | — | — | — | — |

**Why over alternatives:**
- **Meshy vs Hunyuan3D vs Rodin Hyper3D vs Tripo3D:** Meshy v6 has the most complete pipeline (text → mesh → rig → animation library) in one API. Hunyuan3D requires self-hosting + manual rigging in Mixamo. Rodin is image-to-3D first; vibemix is text-prompt-first. Meshy wins for speed-to-result.
- **GLB optimization stack already complete:** Phase 22 + 11 build pipeline already runs `gltf-pipeline` (Draco compression) + `@gltf-transform/cli` (KTX2 textures). No new tooling.

**Integration point:** `scripts/gen_mascot_assets.py` (new — one-shot authoring script), `tauri/ui/public/mascot/prep_*.glb` (committed binary artifacts), `tauri/ui/scripts/build-mascot-bundle.mjs` (EXISTING — already runs optimization).

**What NOT to add:**
- `@huggingface/hub` / `diffusers` shipped as deps — these are auth-time only, off-machine
- `babylonjs` — single-runtime-3D-engine rule; we use Three.js

---

### Bucket 9: 30s Viral Demo Film Generation Autonomously

> Beat A overlay + Beat B mascot anticipation + Beat C silence; auto-edited; voiced.

**Important framing:** Again **off-machine authoring**. The output is one `.mp4`; the production binary doesn't need Veo SDK or ffmpeg shipped.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Screen capture pipeline** | **EXISTING `pyobjc-framework-ScreenCaptureKit` (Mac) + EXISTING `mss` (Win)** ship in v2.0 for the live `ScreenBuffer`. For viral demo, Kaan records his real DJ session via the same pipeline — outputs raw frames at 30fps to `recordings/<session>/screen.mp4` (new flag `--demo-capture` extending Phase 15 recording browser). | — | — | 0 | GREEN |
| **AI video edit** | **Recommended: Veo 3.1 in Gemini API via EXISTING `google-genai>=2.0.1`** for one-shot text-to-video stylization OR pure ffmpeg-driven montage for the deterministic 3-beat cut. **Final answer: ffmpeg montage** — Veo 3.1 at $0.75/sec for a 30s clip is $22.50/iteration and is non-deterministic (re-rolling iterations on rejection costs more). ffmpeg + scripted beat-aligned cuts is free, fast, repeatable. | (Veo 3.1 optional, ffmpeg primary) | ffmpeg LGPL-2.1+ | 0 (off-machine; ffmpeg is a CLI invoked from CI/Kaan-laptop, not bundled) | N/A (off-machine) |
| **ffmpeg** | Already on every dev laptop + GitHub Actions runner. No new bundled dep. | (system binary) | LGPL-2.1+ | 0 | N/A |
| **Narrative voiceover** | **EXISTING Gemini TTS via `google-genai>=2.0.1`** — same path as live mode's Achird voice. Generates 30s narration as one OPUS, ffmpeg laces it into the timeline. | — | — | 0 | GREEN |
| **Beat-aligned cut script** | New `scripts/viral/edit_demo.py` — ffmpeg subprocess driver. Pure stdlib + `subprocess`. | — | — | 0 | N/A |

**Why over alternatives:**
- **ffmpeg vs Veo 3.1:** ffmpeg is deterministic (every re-run produces identical cuts) — critical for the 3-beat structure (Beat A T+8s, Beat B T+14s, Beat C T+22-25s) we've committed to in `VIRAL-02/03/04`. Veo 3.1 is non-deterministic, costs ~$22 per re-roll, and adds zero value over an ffmpeg-driven cut of real session footage.
- **Veo 3.1 still has a role** — could generate the **outro frame** (15s "stars ticker" graphic per VIRAL-10) if the artist wants AI-generated motion graphics, but it's a `nice to have`, not the path.

**Integration point:** `scripts/viral/edit_demo.py` (new), `scripts/viral/render_voiceover.py` (new), Kaan-laptop produces final `.mp4` and commits to release-assets.

**What NOT to add:**
- DaVinci Resolve / ffmpeg-python wrapper / MoviePy — ffmpeg CLI is enough; wrappers add dep weight for zero gain
- Veo 3.1 as the primary editor — non-deterministic + $22/iteration
- Premiere Pro / Final Cut — manual editing path is the artist-fallback if AI flow fails

---

### Bucket 10: Day-Zero Ops Automation

> Discord auto-provision · pre-seeded stars · proxy load test · healthz live · launch trigger sequence.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Discord server automation** | **Recommended: `requests` + Discord webhook URLs** for server provision (channel-create + role-assign via Discord REST API). `discord.py` is overkill for one-shot setup. `dhooks` is a thin wrapper, not worth the dep. | EXISTING `httpx>=0.28` (already in deps) suffices — same async client we already ship. | — | 0 | GREEN |
| **GitHub release automation** | **Recommended: `gh` CLI in CI.** Already used in the v2.0 `release.yml` matrix scaffold. `gh release create` + `gh release upload` are 2-line CI steps. PyGithub adds Python dep for zero gain in a CI shell context. | `gh` 2.x (system binary; GitHub Actions runners ship it) | MIT | 0 | GREEN |
| **Proxy load test runner** | **Recommended: EXISTING `scripts/dayzero/proxy_load_test.py`** (Phase 26 Plan 04 — shipped with `--dry-run`). Pure Python + `httpx` async. v2.1 lights up the real 100 RPS × 5min run with p99 < 500ms + error_rate < 1% gate. **No new lib needed.** | — | — | 0 | GREEN |
| **Locust / k6 as alternative** | **REJECTED.** EXISTING script handles 100 RPS comfortably (single Python process + `httpx` concurrent requests). Locust would add ~10 MB dep weight + a runtime; overkill at 100 RPS. | — | — | — | — |
| **Healthz monitor** | **EXISTING `scripts/dayzero/healthz_check.sh`** (Phase 26 Plan 04) covers it — pure shell + `curl` foreground watchdog. | — | — | 0 | GREEN |
| **Launch trigger sequence** | New `scripts/dayzero/launch_trigger.sh` — orchestrates T-30/T+0/T+5/T+24h hooks; bash + curl + `gh`. No new lib. | — | — | 0 | GREEN |

**Why over alternatives:**
- **`httpx` (already shipped) vs `requests` vs `discord.py`:** we already have httpx for the Gemini SDK; reuse it. `discord.py` ships ~5 MB of state-machine + voice + intent abstractions for what is a one-time POST-to-create-channel script.
- **Locust vs custom httpx loop:** 100 RPS for 5 min × 5min is 30k requests. A single-process `asyncio.gather` over 100 concurrent httpx clients trivially saturates a 100 RPS rate-limited request budget. Locust shines at 1k+ RPS distributed; vibemix's proxy budget is two orders of magnitude under that. The custom script is more honest to the actual budget shape (per-anon-client rate-limit gating).

**Integration point:** `scripts/dayzero/launch_trigger.sh` (new), `scripts/dayzero/discord_provision.py` (new), `.github/workflows/release.yml` (extend with `gh release upload` step that already exists in v2.0 scaffold).

**What NOT to add:**
- `discord.py` — heavy state machine for what is a one-time POST
- Locust / k6 / vegeta — overkill at 100 RPS budget
- `PyGithub` — gh CLI is already in CI runners

---

### Bucket 11: Cross-Phase Integration Audit Gate

> integration-checker subagent (already exists) + E2E test harness.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **integration-checker subagent** | **EXISTING.** Already wrote the v2.0 audit (`v2.0-MILESTONE-AUDIT.md`). v2.1 runs it again at the milestone close. No new tool. | — | — | 0 | GREEN |
| **E2E test harness for Tauri** | **Recommended: `tauri-driver` + WebDriver on Windows; manual smoke tests on macOS.** Per WebSearch + Tauri's official docs: tauri-driver works on Windows + Linux; **macOS WKWebView has no WebDriver tool available**, so macOS E2E is necessarily manual or skipped in CI. Don't try to force pytest-playwright — WebKitGTK mismatch makes Playwright unreliable across the Tauri stack. | tauri-driver latest (cargo install) + WebdriverIO 8.x for the JS suite | MIT | 0 (CI-only) | YELLOW (macOS E2E gap is irreducible; documented limitation) |
| **Vitest for unit/JS surface** | **EXISTING `vitest ^2.1`** — already covers the 429 vitest assertions in Phase 22 mascot tests. v2.1 extends coverage to debrief + library UI. | — | — | 0 | GREEN |
| **pytest for Python surface** | **EXISTING `pytest>=8.0` + 1961 passing tests** — v2.1 extends. | — | — | 0 | GREEN |
| **BDD / cucumber** | **REJECTED.** Adds vocabulary tax with no test-output value over plain pytest/vitest naming. | — | — | — | — |

**Why over alternatives:**
- **pytest-playwright vs tauri-driver:** Per WebSearch, Playwright's WebKit binary is **NOT** the same WebKit that Tauri ships (WKWebView on Mac, WebKitGTK on Linux, WebView2 on Win). Playwright can run against the dev `vite` server but does not validate the packaged binary. tauri-driver is the right surface for "did the bundled binary actually launch."
- **macOS E2E gap:** Tauri's docs explicitly call out the macOS limitation. Document it in SECURITY.md / CONTRIBUTING.md as a known testing gap; don't try to plug it with brittle AppleScript-driven UI automation.

**Integration point:** `.github/workflows/e2e.yml` (new — tauri-driver on `windows-2022` only), `tests/e2e/` (new directory).

**What NOT to add:**
- `pytest-playwright` — WebKit engine mismatch with Tauri
- `selenium-webdriver` standalone — tauri-driver is the right wrapper
- `cucumber-rust` / `behave` — vocab tax with no real benefit

---

### Bucket 12: Signing Pipeline Autonomous Execution

> Apple notarytool + xcrun + SignPath CLI + signtool.

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **Apple macOS signing** | **Primary: `xcrun notarytool` + `codesign`** (Apple's official tools, pre-installed on Apple Silicon GH Actions runners). Already wired in v2.0 `release.yml` scaffold + `scripts/dist/sign_macos.sh`. **Fallback: `rcodesign` (apple-codesign Rust crate v0.29)** — pure Rust client to Apple's Notary API, runs on Linux/Win runners if we ever cross-compile from non-Mac CI. Not needed in v2.1 (mac runners ship notarytool), but documenting as the fallback path. | xcrun (system), rcodesign 0.29 (CI fallback) | Apple ToS / MPL-2.0 | 0 (CI-only) | GREEN once Apple Developer Agreement update lands (v2.0 carry-forward Kaan/Francesco-action) |
| **SignPath Windows signing** | **Primary: SignPath CLI + GH Actions integration** — SignPath provides a `signpath/signpath-codesigning-action@v1` GitHub Action that wraps `signtool.exe` against their HSM. Already documented in v2.0 `docs/signpath-application.md`. Activates on SignPath OSS approval (~1 week SLA, Kaan-action carry-forward). | SignPath CLI via `signpath/signpath-codesigning-action@v1` | SignPath ToS | 0 (CI-only) | GREEN once SignPath approval lands |
| **Autonomous execution** | "Autonomous" in v2.1 means **fully scripted in `release.yml`** — Apple secrets injected via GH Actions `secrets`, SignPath project ID + signing-policy slug also via `secrets`. The only human-actions are the **one-time approval handshakes** (Apple Agreement + SignPath OSS) — once those land, every release runs zero-human-touch. | — | — | 0 | GREEN once approvals land |

**Why over alternatives:**
- **`xcrun notarytool` vs `rcodesign`:** notarytool is the Apple-blessed path and runs on GH `macos-14` runners with no extra install. rcodesign is the cross-platform fallback if we ever sign from Linux/Win — keep as documented Plan B in `21-DEFERRED.md` but don't make it the primary.
- **SignPath vs DigiCert vs Sectigo vs self-signed:** SignPath OSS Foundation is free for OSS projects (verified) and integrates with GH Actions in 3 lines. DigiCert/Sectigo cost $300-700/year for the cert + HSM. Self-signed = SmartScreen red banner forever; bad UX.
- **Hardened runtime + entitlements:** EXISTING `entitlements.plist` (Phase 21 scaffold) already declares the minimum entitlements needed for screen-recording + accessibility. v2.1 verifies the entitlements file against Phase 24 + Phase 5 actual needs.

**Integration point:** `.github/workflows/release.yml` (EXISTING — v2.0 scaffold; v2.1 activates once approvals land), `scripts/dist/sign_macos.sh` (EXISTING), `scripts/dist/sign_manifest.sh` (EXISTING), `tauri/src-tauri/entitlements.plist` (EXISTING — verify per-Phase needs).

**What NOT to add:**
- `fastlane` — Ruby toolchain bloat for what is 3 lines of GH Actions YAML
- Self-signed / Ad-hoc — kills SmartScreen + Gatekeeper rep
- DigiCert / Sectigo — paid; SignPath OSS is free for our case

---

### Bucket 13: RC Cut + Ship Automation

> GitHub release publish + social post publish (Twitter / IG / Reddit / HN).

| Item | Decision | Version | License | Bundle Δ | Install impact |
|------|----------|---------|---------|----------|----------------|
| **GitHub release publish** | **EXISTING `gh` CLI** in `release.yml`. v2.0 already scaffolded `gh release create` step. | — | — | 0 | GREEN |
| **Twitter / X post** | **Manual publishing.** Twitter's API v2 free tier got nuked in 2023 + paid tiers start at $100/month for write access. **Not worth the cost for ~4 launch tweets**. Kaan posts manually from his account; v2.0 already shipped the draft. | (no automation) | — | 0 | GREEN |
| **Instagram Reels post** | **Manual publishing.** IG Graph API requires a Business/Creator account + Meta Business Verification + ~3 day approval; for one-shot launch posts, the Kaan-Francesco-manual flow is faster. v2.0 already shipped IT+EN drafts. | (no automation) | — | 0 | GREEN |
| **Reddit post (r/Beatmatch + r/DJs)** | **Manual publishing.** Reddit anti-spam policies make automated first-post-with-link extremely flag-prone. Drafts shipped Phase 26-03. Kaan posts manually. | (no automation) | — | 0 | GREEN |
| **HN Show HN submission** | **Manual publishing.** HN does not have a write API. Draft shipped Phase 26-03; Kaan submits. | (no automation) | — | 0 | GREEN |
| **Star ticker / launch dashboard** | **Optional**: `gh api repos/bravoh/vibemix --jq '.stargazers_count'` in a 60s polling loop for the launch-day dashboard. Pure shell. | — | — | 0 | GREEN |
| **"Autonomous" framing** | The autonomous-fully memo accepts "drafts shipped Claude-side; final publish-button is Kaan" as the **honest interpretation** of social-platform reality — every major social API restricts first-post automation. The autonomous discharge IS shipping the polished drafts + the dashboard tooling. | — | — | 0 | GREEN |

**Why over alternatives:**
- **Twitter API:** $100+/month write access for 4 launch tweets is wasteful. The draft is the value-add; the button-click is 30s.
- **IG Graph API:** Meta Business Verification + 3-day approval window doesn't fit a launch-week timeline.
- **Buffer / Hootsuite:** $15-50/month per channel; once-a-year usage doesn't justify.

**Integration point:** `scripts/dayzero/launch_dashboard.sh` (new — star-ticker), social posts manually published from drafts in `docs/launch-posts/`.

**What NOT to add:**
- Twitter API v2 paid tier — wasteful for one launch
- Buffer / Hootsuite — subscription overhead
- IFTTT / Zapier — vendor lock-in for a one-shot

---

## Stack Summary Table

| Bucket | New runtime deps | New dev/CI deps | Bundle Δ | Install impact | Existing-covers? |
|--------|------------------|------------------|----------|----------------|------------------|
| 1. Hallucination Gate | none | `pytest-asyncio` (if absent) | 0 | GREEN | mostly |
| 2. Library Intelligence | **`sqlite-vec==0.1.9`** | none | +0.4-0.6 MB | GREEN | partially |
| 3. Debrief UI | **`wavesurfer.js ^7.10`** (npm) | none | +180 KB (60 KB gz) | GREEN | partially |
| 4. 4-Layer Mascot | none | none | 0 | GREEN | fully |
| 5. Install Hardening | **`tauri-plugin-macos-permissions = "2.3.0"`** (Rust crate) | `tart` (CI helper) | +200 KB Mac, 0 Win | GREEN | partially |
| 6. Security Pass | none | gitleaks, pip-audit, cargo-audit, cargo-deny, osv-scanner, syft | 0 | GREEN (CI-only) | nothing |
| 7. DJ Profile | none | none | 0 | GREEN | fully |
| 8. Real GLB Animations | none | (Meshy API / Mixamo / Blender MCP — off-machine) | -2 to -10 MB after compression | GREEN | fully |
| 9. Viral Demo Film | none | ffmpeg (system) | 0 | N/A (off-machine) | fully |
| 10. Day-Zero Ops | none | none (everything stdlib or gh CLI) | 0 | GREEN | fully |
| 11. Integration Audit | none | tauri-driver + WebdriverIO (CI-only) | 0 | GREEN (CI-only) | partially |
| 12. Signing Pipeline | none | SignPath GH Action, rcodesign (CI fallback) | 0 | GREEN (waiting on approvals) | partially |
| 13. RC Cut + Ship | none | none (gh CLI already in CI) | 0 | GREEN | fully |
| **TOTAL** | **2 runtime adds** (sqlite-vec + wavesurfer + tauri-plugin-macos-permissions Rust crate) | **~10 CI-only / dev-only tools** | **+0.5 to +1.0 MB net runtime** (well within 350 MB cap) | **GREEN across the board** for one-click install | |

### Bundle math
- v2.0 PyInstaller bundle baseline ≈ ~200 MB (livekit + google-genai + numpy + scipy + pyobjc, per Phase 21 deferred audit)
- v2.1 adds:
  - `sqlite-vec==0.1.9` macOS dylib: ~600 KB
  - `sqlite-vec==0.1.9` Windows dll: ~400 KB
  - `tauri-plugin-macos-permissions` Rust crate compiled into the macOS binary: ~200 KB
  - `wavesurfer.js ^7.10` minified into the Tauri webview bundle: ~180 KB
- **Total v2.1 bundle ≤ ~201 MB** — comfortable below the 350 MB hard cap.

---

## Rejected Alternatives (Scope-Creep Guard)

Every entry here is something a less-disciplined research pass might recommend. Each is rejected with a one-line memo-anchored reason.

| Rejected | Why |
|----------|-----|
| `chromadb` / `qdrant-client` / `weaviate-client` / `pymilvus` / `pinecone-client` | Server-bound → violates "no new external processes" + one-click install (memory `project_one_click_install_hard_req`) |
| `faiss-cpu` / `faiss-gpu` | 30-100 MB + Intel MKL on Win — red install impact |
| `sentence-transformers` / `transformers` / `torch` / `tensorflow` | 800+ MB; violates Gemini-only memory + bundle cap (memory `feedback_no_clap_use_gemini_embedding`) |
| `langchain` / `langchain-core` / `langchain-google-genai` / `llama-index` | Multi-provider wrappers; violates lean-utility memory (memory `feedback_no_scope_creep_clean_utility`) |
| `deepeval` / `evidently` / `mlflow` / `wandb` | Stdlib counting + events.jsonl already cover what we need; multi-provider abstraction tax |
| `scikit-learn` for F1/precision/recall | 30 MB transitive bloat for 20 lines of confusion-matrix math |
| `tiktoken` | Wrong tokenizer family (BPE) for Gemini (SentencePiece) — would give 10-30% wrong counts |
| `Trivy` for CI CVE scanning | March 2026 supply-chain compromise; DB updates suspended (use pip-audit + osv-scanner instead) |
| `Safety CLI` for CVE scanning | Commercial-use restriction blocks Bravoh's internal reuse |
| `Snyk` / `Veracode` / `Checkmarx` | Closed-source / paid; we are OSS |
| `discord.py` for one-shot server provision | 5 MB state-machine + voice + intents for what's a single REST POST |
| `Locust` / `k6` / `vegeta` for 100 RPS budget | Overkill at 100 RPS; existing `scripts/dayzero/proxy_load_test.py` is enough |
| `PyGithub` for release upload | `gh` CLI is already in CI runners |
| `Twitter API v2 paid tier` for launch tweets | $100/month for 4 launch tweets is wasteful |
| `pytest-playwright` for Tauri E2E | WebKit engine mismatch with Tauri WKWebView; use tauri-driver (Windows only) |
| `cucumber-rust` / `behave` BDD | Vocab tax with no real test-output value |
| `@tweenjs/tween.js` / `gsap` / `motion` | Three's native `crossFadeTo` does what we need |
| `three-mixamo` / `three-ik` | Rigging is baked off-machine; runtime IK not needed |
| `cannon-es` / `rapier3d` for mascot physics | Physics-based mascot rejected in earlier research; pre-authored anim only |
| `React 19` / `Vue` / `Svelte` for debrief UI | Vanilla TS is the locked vibemix UI architecture |
| `Howler.js` / `Tone.js` | Wrong domain (playback / synthesis vs visualization) |
| `mem0` / `motorhead` / `langgraph-checkpoint` for DJ profile | Wrong problem; 2KB JSON blob, not an agent-memory graph |
| `Babylon.js` for any 3D | Single-runtime-3D-engine rule; we use Three.js |
| `Veo 3.1` as primary video editor | Non-deterministic + $22/iteration for a 3-beat cut ffmpeg handles deterministically |
| `Multipass` / `Vagrant` for fresh-VM macOS rehearsal | Multipass on macOS only runs Ubuntu; Vagrant + VirtualBox is broken on Apple Silicon |
| `fastlane` for signing automation | Ruby toolchain bloat for 3 lines of GH Actions YAML |
| `osascript` / `tccutil` programmatic TCC reset | Apple deprecated path; doesn't survive OS upgrades |

---

## Open Questions for Phase Planners

When phase plans land per-bucket, the planner should verify:

1. **Gemini Embedding 2 preview availability:** model ID `gemini-embedding-2-preview` is currently public preview (per March 2026 release). Verify the model ID + pricing + per-call audio cap (180s) are still live at phase-start. If Google promotes it to GA with a different model ID (`gemini-embedding-2` without `-preview`), update the phase plan.
2. **sqlite-vec wheel availability for Windows ARM64:** PyPI ships x64 wheel as of 0.1.9; ARM64 wheel status needs verification before phase start. If absent, scaffold the numpy fallback explicitly in the integration layer.
3. **`pytest-asyncio` presence check:** confirm whether `pytest-mock` pulls it transitively before adding to `[dependency-groups] dev`.
4. **`tauri-plugin-macos-permissions` 2.3.0 compatibility with Tauri 2.11:** versions match per latest release (2025-05-06); verify cargo build clean before sinking the plan.
5. **`tart` license & GH Actions integration:** Fair Source 1.0 is OSS-friendly for our use; confirm CI runner license-compliance check passes.
6. **SignPath OSS approval ETA:** v2.0 carry-forward; v2.1 unblocks Bucket 12 only when approval lands. Plan should sequence Bucket 12 AFTER the SignPath email confirms.
7. **Apple Developer Program Agreement update:** Francesco-action carry-forward; same gating as above for macOS signing.
8. **Veo 3.1 pricing fluctuation:** if Google drops Veo 3.1 cost by 5×, revisit "ffmpeg-only" decision in Bucket 9. Currently locked on ffmpeg.
9. **`wavesurfer.js` v7 + Tauri webview WebKit/WebView2 cross-platform render parity:** wavesurfer uses Shadow DOM + Canvas. Verify it renders identically in WKWebView (Mac) and WebView2 (Win) in the wizard / debrief view. Quick smoke test in Wave 0 of the debrief phase.
10. **Meshy v6 vs Hunyuan3D 3.0 quality A/B:** budget ~$50 in Meshy credits for the A/B before committing the GLB pipeline phase.

---

## Sources

### Verified via WebSearch (2026-05-14)

- [Gemini Embedding 2 (Google Developers Blog, March 2026)](https://developers.googleblog.com/building-with-gemini-embedding-2/) — multimodal embedding model, 3072-dim, 180s audio cap, model ID `gemini-embedding-2-preview`
- [sqlite-vec 0.1.9 PyPI](https://pypi.org/project/sqlite-vec/) — released 2026-03-31; Apache-2.0 / MIT dual; loadable extension
- [tauri-plugin-macos-permissions 2.3.0](https://docs.rs/crate/tauri-plugin-macos-permissions/latest) — released 2025-05-06; Tauri 2.x compatible; MIT
- [wavesurfer.js docs (v7)](https://wavesurfer.xyz/docs/) — TypeScript rewrite, Shadow DOM CSS isolation, Regions + Timeline plugins
- [Three.js AnimationMixer + AdditiveAnimationBlendMode](https://threejs.org/docs/pages/AnimationMixer.html) — native crossFadeTo / makeClipAdditive
- [Tauri 2 WebDriver](https://v2.tauri.app/develop/tests/webdriver/) — tauri-driver works on Win + Linux only; no macOS WKWebView driver
- [gitleaks vs trufflehog (AppSecSanta 2026)](https://appsecsanta.com/secret-scanning-tools/gitleaks-vs-trufflehog) — gitleaks is the right CI gate for OSS lean utility
- [pip-audit vs Safety vs OSV-Scanner (Inedo, 2026)](https://blog.inedo.com/python/pypi-package-vulnerabilities) — pip-audit + OSV = lowest false-positive
- [cargo-audit + cargo-deny (RustSec, 2026)](https://rustsec.org/) — Rust supply chain
- [Trivy March 2026 compromise (AppSecSanta)](https://appsecsanta.com/sca-tools/trivy-vs-grype) — DB updates suspended; avoid Trivy in v2.1
- [Apple notarytool + rcodesign (apple-codesign 0.29 docs)](https://gregoryszorc.com/docs/apple-codesign/stable/) — Rust fallback if non-Mac CI ever needed
- [SignPath OSS Foundation](https://signpath.io/solutions/open-source-community) — free for OSS, integrates with GH Actions
- [Tart Virtualization](https://tart.run/) — Apple Silicon native; Fair Source 1.0 license OSS-friendly
- [Meshy v6 Text-to-3D API](https://docs.meshy.ai/en/api/text-to-3d) — async REST API, GLB export, integrated rigging + 100+ animation library
- [Hunyuan3D 3.0 (Tencent)](https://hunyuan3dai.com/posts/hunyuan3d-vs-meshy/) — OSS weights; self-host fallback
- [Veo 3.1 in Gemini API](https://ai.google.dev/gemini-api/docs/video) — `client.models.generate_videos()` with `veo-3.1-generate-preview`; $0.75/sec
- [Locust vs k6 vs Vegeta (Vervali 2026)](https://www.vervali.com/blog/best-load-testing-tools-in-2026-definitive-guide-to-jmeter-gatling-k6-loadrunner-locust-blazemeter-neoload-artillery-and-more/) — all overkill at 100 RPS budget
- [tiktoken vs Gemini count_tokens (Propel)](https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025) — tiktoken is wrong tokenizer family for Gemini
- [PyGithub vs gh CLI](https://cli.github.com/manual/gh_release_upload) — gh CLI is the right CI tool

### Read directly from repo (HIGH confidence)

- `/Users/ozai/projects/dj-set-ai/pyproject.toml` — Python runtime + dev deps
- `/Users/ozai/projects/dj-set-ai/tauri/src-tauri/Cargo.toml` — Rust crate deps + features
- `/Users/ozai/projects/dj-set-ai/tauri/ui/package.json` — npm runtime + dev deps
- `/Users/ozai/projects/dj-set-ai/.planning/PROJECT.md` — v2.1 milestone scope
- `/Users/ozai/projects/dj-set-ai/.planning/milestones/v2.0-MILESTONE-AUDIT.md` — what shipped + carry-forward
- `/Users/ozai/projects/dj-set-ai/.planning/milestones/v2.0-REQUIREMENTS.md` — 94 v2.0 REQ-IDs
- `/Users/ozai/projects/dj-set-ai/.planning/milestones/v2.0-ROADMAP.md` — phase numbering reference (continues from Phase 27)
- `/Users/ozai/projects/dj-set-ai/README.md` — current public-facing surface (Phase 26 ship)
- `/Users/ozai/projects/dj-set-ai/.planning/codebase/STACK.md` — v0.1.0 baseline (now stale; pyproject.toml is the truth)

### Memory anchors

- `project_one_click_install_hard_req` — every dep choice rated green/yellow/red
- `feedback_no_clap_use_gemini_embedding` — no CLAP/OpenL3/MERT; Gemini Embedding 2 is the embedding model
- `project_gemini_embedding_2` — native multimodal, ~180s audio cap, 3072-dim with MRL truncation
- `project_anti_slop_grounded_gemini_thesis` — every feature evaluated by "what hallucination class does it close"
- `feedback_no_scope_creep_clean_utility` — OUT: stem separation, CLAP, multi-provider AI, enterprise features
- `project_phase_16_kaan_dj_testing` — v2.1 milestone memo overrides for the autonomous-proxy gate

---

*Stack research for v2.1 The Unified Cut. Researched 2026-05-14 by gsd-researcher subagent. Confidence: HIGH on existing-stack-covers; MEDIUM-HIGH on new pin recommendations.*
