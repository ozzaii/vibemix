# Codex Full-Product Sweep Map - 2026-05-26

Status: current handoff, not release closure.

Checkpoint: 2026-05-27 14:00 Europe/Istanbul.
Current HEAD: `e87ddcad docs(research): exhaustive live-channel verdict + rekordbox-independent awareness stack`.

Running processes at checkpoint:

- No Codex-owned `cargo tauri dev`, Vite dev server, source sidecar, Codex
  set-prep child, or Python listener on `127.0.0.1:8765` / `127.0.0.1:8766` /
  `127.0.0.1:1420` remained after the 10:01 runtime/package sweep.
- A pre-existing installed `/Applications/vibemix.app` process remains running
  outside the dev verification (`673`). It was left untouched because it was not
  started by this Codex dev loop.
- A separate `screen` session named `vibemix-ui` is serving Vite on
  `127.0.0.1:1420` and was left untouched because it was not started by this
  package rehearsal.
- Source-backed Tauri desktop verification via `cargo tauri dev` is complete
  for the dev path, and local package-prep verification now builds a real arm64
  frozen sidecar plus both no-bundle and unsigned `.app` macOS package outputs.
  Local unsigned DMG drag/install and packaged first-run CLAP setup are now
  verified. Signed/notarized DMG, signed updater rehearsal, and real Windows
  fresh-machine proof are still not release-closed.

## Evidence Read

- Root docs: `CLAUDE.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/MILESTONES.md`, `.planning/v8.2-MILESTONE-AUDIT.md`.
- Claude memory: `/Users/ozai/.claude/projects/-Users-ozai-projects-dj-set-ai/memory/`, especially frontend wiring, Viber agent, CLAP, auto-cue, Rekordbox ingest, and stale sidecar notes.
- Current source: `src/vibemix/`, `tauri/src-tauri/`, `tauri/ui/`, focused library DSP, CLAP, cue, prompt, status, and Viber surfaces.
- Version commands: `uv tree --depth 1 --group dev`, `npm ls --prefix tauri/ui --depth=0 --json`, `cargo tree --manifest-path tauri/src-tauri/Cargo.toml -e normal --depth 1`.
- External DSP/MIR sources checked/refreshed on 2026-05-27:
  - CUE-DETR: https://github.com/ETH-DISCO/cue-detr and https://arxiv.org/abs/2407.06823
  - CLAP model: https://huggingface.co/Xenova/larger_clap_music_and_speech and https://huggingface.co/laion/larger_clap_music_and_speech
  - librosa license: https://github.com/librosa/librosa/blob/main/LICENSE.md
  - Essentia licensing: https://essentia.upf.edu/licensing_information.html
  - aubio: https://github.com/aubio/aubio
  - madmom: https://github.com/CPJKU/madmom
  - all-in-one analyzer: https://github.com/mir-aidj/all-in-one
  - Runtime audio/DSP options: https://juce.com/,
    https://github.com/RustAudio/cpal, https://github.com/PortAudio/portaudio,
    https://essentia.upf.edu/, https://breakfastquay.com/rubberband/,
    https://faustdoc.grame.fr/, https://cmajor.dev/, and
    https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet.
  - Tauri updater: https://v2.tauri.app/plugin/updater/

DSP engine verdict at this checkpoint:

- For the current product/presentation path, do not replace the working Python
  analysis spine with a broad real-time engine. The app captures/analyzes audio,
  embeds libraries with local CLAP ONNX, and exports cues/sets; it is not yet a
  low-latency effects host. Current source already avoids scipy/librosa in the
  shipped CLAP/CUE path: PyAV/FFmpeg decodes/resamples files for local model
  input, and narrow numpy primitives own live feature extraction and cue
  fallback logic.
- If a true low-latency audio engine becomes a product feature, the clean
  architecture is layered: CPAL for Rust-side cross-platform audio I/O in the
  existing Tauri shell; a small native DSP core for deterministic filters/meters;
  Essentia as an optional offline MIR/reference analyzer; Rubber Band only for
  time-stretch/pitch-shift; and Faust/Cmajor/JUCE only if we intentionally build
  authored effects/plugins. JUCE is the industry C++ app/plugin heavyweight, but
  it is a licensing and integration decision, not a quick presentation fix.

## Cleanup / Archive Status

First cleanup pass is complete and intentionally non-destructive.

- Active sweep source stays at `.planning/research/CODEX-full-product-sweep-map.md`.
- Thirteen untracked scratch research/verification notes were moved out of the
  active research surface into `.planning/archive/2026-05-26-research-sweep/untracked-research/`.
- Archive manifest: `.planning/archive/2026-05-26-research-sweep/MANIFEST.md`.
- Local reversible bundle: `.planning/archive/2026-05-26-research-sweep.zip`.
- `.gitignore` now ignores `.planning/archive/*.zip` and `.planning/archive/*.tgz`
  so binary archive bundles do not accidentally enter a product commit.
- `AGENTS.md` now exists as the concise contributor guide for the repository and
  has been refreshed against the current `uv` / `npm --prefix` / Cargo-manifest
  workflow. Verification: `wc -w AGENTS.md` -> 399 words;
  `git diff --check -- AGENTS.md` -> pass.
- Contributor guide cleanup: `CONTRIBUTING.md` now uses the current
  `uv`/Ruff-format/`npm --prefix`/Cargo manifest commands, no longer repeats
  the closed-source proxy sentence, and runs controller sniffing through
  `uv run python scripts/sniff_controller.py`. Verification: targeted `rg`
  found no old venv/PYTHONPATH/black-defaults/duplicate-proxy hits;
  `uv run pytest -q tests/repo/test_readme_shape.py tests/repo/test_phase20_docs.py`
  -> 64 passed; `git diff --check` -> pass.
- Current docs and generated audit were cleaned of the stale "CLAP is banned /
  Gemini embeddings are default" guidance. Historical docs now mark that rule as
  superseded instead of leaving it as live advice.
- Package-root debloat: `vibemix.library` no longer exports the legacy Gemini
  `LibraryEmbedder`, `GEMINI_EMBEDDING_MODEL`, or
  `EXCERPT_STRATEGY_VERSION` from its public lazy export table. The legacy
  module is still directly importable for migration/cache tests, but the
  package-level API now advertises the CLAP-era `build_embedder` seam instead
  of the retired cloud embedder. Verification: targeted `rg` found no
  non-test/non-legacy-helper imports of the package-root legacy names;
  `uv run pytest -q tests/library/test_embed_clap.py
  tests/library/test_toolset.py::test_local_toolset_import_does_not_load_gemini_sdk`
  -> 13 passed; `uv run ruff check src/vibemix/library/__init__.py
  tests/library/test_embed_clap.py` -> pass; `git diff --check` -> pass.
- Canonical tracked docs now reflect the current CLAP embedding decision in the
  living surfaces: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, and
  `.planning/STATE.md` all say local CLAP ONNX owns embeddings, Gemini is the
  conversational/set-prep brain only, and fp32 is the default model precision.
  Historical milestone prose is left intact unless it is explicitly marked
  superseded.
- Second cleanup pass archived active-surface clutter:
  `.planning/HANDOFF-cdj-whisper-v5-ui-migration.md` and root
  `debrief-live.png` moved into
  `.planning/archive/2026-05-26-surface-clutter/`, with a manifest and local
  zip bundle. Current mocks stayed active because they are still referenced as
  visual/product contracts.
- Stale handoff/spec cleanup archived
  `docs/superpowers/specs/2026-05-26-auto-cue-engine-HANDOFF.md` into
  `.planning/archive/2026-05-26-stale-handoffs/` with a local zip bundle because
  it still said "mid-pivot" / "Nothing committed" while the current source/map
  describe CUE-DETR ONNX + local refinement as wired. The original auto-cue
  design spec was also archived because it described a not-yet-built pure-DSP
  engine; the active path now contains a concise current product spec for
  `cue_engine.detect_cues_auto()`.
- The original DJ-library ingest design was also archived from the active spec
  surface because it still described an aspirational multi-library watcher. The
  active path now documents the current Rekordbox-only MVP, local CLAP
  embedding, cue-anchored excerpts, and sqlite-vec store contract.
- Ignored generated output cleanup removed the root `build/` PyInstaller
  intermediate directory (`194M`). It was not zipped because it is reproducible
  generated output and already ignored by `.gitignore`; the action is recorded
  in `.planning/archive/2026-05-26-generated-output/MANIFEST.md`. The Rust
  `target/` cache and `tauri/ui/dist/` were intentionally kept for near-term
  verification/commit-splitting.
- Stale flat load-test JSONs were archived out of the active eval directory:
  215 ignored `.planning/eval-runs/loadtest_*.json` files moved into the local
  `.planning/archive/2026-05-26-eval-run-json.zip` bundle with a manifest.
  `.planning/eval-runs/.gitkeep` remains, so fresh load-test artifacts still
  have the expected default directory. This also avoids stale flat JSONs being
  confused with the release gate's nightly run directories.
- Stale planning notes/quick plans were archived out of active notes:
  `.planning/notes/{mem0-rejected-2026-05-18.md,v-next-memory-turn.md,vibe-mix-concept-brief.md}`
  plus quick folders `260525-fuv-token-and-cost-counter-for-live-sessions`,
  `260525-gz2-embed-real-music-library-dim-1536-folder`, and
  `260526-i3j-stage-clap-engine`. They contained old Gemini-only/no-CLAP,
  1536-dim Gemini embedding, stale €50 budget-gate, or "CLAP staged" guidance
  that conflicts with current CLAP/Codex truth. Manifest and ignored local zip:
  `.planning/archive/2026-05-26-stale-planning-notes/`.
- Expanded v2.1 phase-detail archive cleanup moved
  `.planning/milestones/v2.1-phases/` (143 tracked markdown files) into
  `.planning/archive/2026-05-27-v2.1-phase-detail/v2.1-phases/`, created the
  ignored local bundle `.planning/archive/2026-05-27-v2.1-phase-detail.zip`,
  and left a small pointer README at the original path. Reason: the detailed
  v2.1 implementation plans are historical and contain retired Gemini
  Embedding 2, Gemini-only/no-CLAP, budget, and installer guidance that kept
  polluting active sweeps. Current summary/audit docs remain under
  `.planning/milestones/v2.1-*`.
- Stale STACK research cleanup archived the old
  `.planning/research/STACK.md` body into
  `.planning/archive/2026-05-27-stale-stack-research/STACK.md` because it still
  presented Gemini Embedding 2 and Gemini-only/no-CLAP library embeddings as
  active guidance. The original path now contains only a current-source pointer
  to `.planning/codebase/STACK.md`, `CLAUDE.md`, `docs/clap-engine.md`,
  `docs/codex-agent.md`, and this sweep map. Active docs that referenced old
  Bucket sections now point at the archived file.
- Stale v6 memory research cleanup archived the old active
  `.planning/research/{SUMMARY,ARCHITECTURE,FEATURES,PITFALLS}.md` files into
  `.planning/archive/2026-05-27-stale-v6-memory-research/` because the GSD
  roadmapper reads `research/SUMMARY.md`, and those files still instructed
  agents to reuse Gemini Embedding 2 / `LibraryEmbedder` for retrieval and
  memory. The original paths now contain current CLAP/Codex pointers and risk
  notes; active docs with direct SignPath/installer references were redirected
  to the archived file when they needed the historical text. Local ignored zip:
  `.planning/archive/2026-05-27-stale-v6-memory-research.zip`.
- Stale CLAP deep-dive cleanup archived the old
  `.planning/research/clap-engine-deep-dive.md` body into
  `.planning/archive/2026-05-27-stale-clap-deep-dive/` because it still
  described server-side `laion_clap`, Gemini 1536-dim migration, and a staged
  CLAP swap. The original path now points at the current local CLAP ONNX/512
  truth in `docs/clap-engine.md`, `clap_engine.py`, `embed_clap.py`, and
  `model_assets.py`.
- Active planning-status cleanup reconciled v8.2/Phase 89 set-prep surfaces:
  `.planning/ROADMAP.md`, `.planning/PROJECT.md`, and `.planning/STATE.md`
  now mark v8.1/v8.2 shipped state accurately instead of in progress or not
  started; `.planning/phases/v8.2-STATUS.md`,
  `.planning/phases/87-agent/87-CONTEXT.md`, and
  `.planning/research/vibe-mix-ui-ipc-button-audit.md` no longer teach
  `ViberAgent.build_set`, future/staged Build-a-Set wiring, or a future
  1536-to-512 CLAP swap. `.planning/research/vibe-mix-agent-engine-synthesis.md`
  is now explicitly marked as historical pre-build synthesis and names the
  shipped local Codex + local CLAP path. Phase 89 ingest context and
  `library/ingest.py` now point at the product `ClapEmbedder` / local ONNX seam
  rather than the old staged `laion_clap` wording.
- Stale Viber direction research cleanup archived the old
  `.planning/research/viber-direction-2026-05-25/` report bodies into
  `.planning/archive/2026-05-27-stale-viber-direction-research/` and left a
  pointer README at the original path. The archived reports were pre-current
  and still mixed Gemini Embedding 2, Gemini-only/no-CLAP, staged CLAP, and
  early Codex/Viber assumptions into active-looking design docs. Live
  references now point to `docs/codex-agent.md`, current source comments, or the
  archived location explicitly.
- Root archived-research cleanup moved the lingering
  `.planning/research/*-archived.md` v3.1/v5.0 files into
  `.planning/archive/2026-05-27-root-archived-research/`. They were already
  named archived but still lived in the active research root and polluted broad
  stale-term searches.
- Stale v2/v3 research cleanup archived the historical
  `.planning/research/{v2-1,v2-buckets,v3-buckets,v3-shipped}/` directories
  into `.planning/archive/2026-05-27-stale-v2-v3-research/`. The original
  paths now contain pointer READMEs only. Current docs and tests now link to
  the archived paths when they need historical milestone context instead of
  treating old bucket research as live guidance.
- Setup/crash copy now states the product split precisely: the live co-host
  direct mode needs `GEMINI_API_KEY`, but Library search/ingest/chat/curate and
  build-set use local CLAP/Codex and do not require a Gemini key. The
  `api-key-missing` Tauri crash banner no longer claims all of vibemix needs
  Gemini to talk.
- Model-router docs/tests now label the `embedding` router path as legacy-only
  for Gemini cache/migration audits. Product library embeddings are documented
  as local CLAP ONNX/512 through `embed_factory`, so future work should not
  treat `resolve("embedding")` as the active library path.
- Runtime status-tick/fault seam is present in the working tree and verified:
  `ws_broadcast` emits `ipc.status.tick` at ~1Hz, screen-denied is badge-only
  rather than a deck fault, and the targeted backend/UI guards pass. This keeps
  the demo from blanking the deck when screen capture permission is denied.
- Stale dated-research cleanup archived the remaining active-looking
  `.planning/research/{clap-spike-2026-05-25,frontend-critique-2026-05-25,oss-launch-2026-05-25}/`
  folders into `.planning/archive/2026-05-27-stale-dated-research/`. The
  original paths now contain pointer READMEs only.
- UI-facing Library/Viber verification checkpoint: the current app seam is
  pinned to local Codex and local CLAP at the CLI, Rust bridge, and TypeScript
  UI contract layers. Verified on 2026-05-27 without restarting the frontend
  dev server: `npm --prefix tauri/ui run test --
  src/library/api.test.ts src/library/chat.test.ts src/library/build.test.ts
  src/library/curate.test.ts src/library/model-setup.test.ts
  src/library/state-machine.test.ts` -> 64 passed;
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds --
  --nocapture` -> 24 passed; `uv run pytest -q
  tests/library/test_setprep_tools.py tests/library/test_toolset.py
  tests/library/test_curate_unify.py tests/library/test_curator_persona_seam.py
  tests/library/test_next_suggestion.py tests/library/test_models_cli.py
  tests/capabilities/test_library_window_contract.py` -> 74 passed. Prior
  live CLI smokes also passed: `library stats --json` reported
  `embedding_backend=clap`, `embedding_dim=512`, `agent_backend=codex`,
  `agent_ready=true`; a real `chat_with_codex()` no-tool turn returned
  `READY` / `model_done`; and `library search "dark warehouse peak time" --k 3
  --json` returned CLAP-backed results.
- Generated-output cleanup continued: ignored
  `tauri/src-tauri/target/debug/binaries/` (`543M`) was removed because it was a
  stale expanded sidecar payload polluting searches with vendored dependency
  TODOs; `spikes/**/__pycache__/` bytecode caches were also removed. The rest of
  `tauri/src-tauri/target/` was kept to avoid slowing near-term Rust checks.
- Public/current copy cleanup removed stale Gemini-only / Gemini Embedding 2 /
  1536-d library claims from README/CONTRIBUTING, launch copy, anti-slop copy
  substitutions, the old library UI mock, deck-vision comments, dependency
  opportunity ratings, and historical spike notes. Remaining active hits are
  deliberately scoped to signed eval threshold docs, legacy migration code, or
  historical/superseded dependency notes.
- Generated-output cleanup removed another ignored `~948M` from the workspace:
  root `dist/` build/e2e/release artifacts (`vibemix-core`, old unsigned DMG,
  wheel, and dated e2e reports) plus the ignored local runtime recording
  `recordings/20260515-112139/`. The tracked `dist/launch-runs/.gitkeep` audit
  scaffold was preserved. Details are recorded in
  `.planning/archive/2026-05-26-generated-output/MANIFEST.md`.
- Cleanup drift fix: `dist/launch-runs/.gitkeep` is present again as the
  zero-byte tracked scaffold expected by `.gitignore` and the launch-trigger
  audit path. Verification: `test -f dist/launch-runs/.gitkeep` passed and
  `wc -c` reports 0 bytes.
- Generated-output cleanup also removed the active untracked expanded
  `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` sidecar payload
  (`543M`). Real sidecar bundles remain release/build artifacts produced by
  `scripts/build_sidecar.py`; tiny `.placeholder` files now keep both
  arch-specific Tauri resource globs valid for source checks.
- Repo-local bytecode/test/linter caches were cleared from source, tests,
  scripts, eval, installer, and proxy app/test trees. Virtualenvs,
  node_modules, Tauri target, frontend dist, and Claude worktrees were
  intentionally kept for now.
- Packaging cleanup added a dedicated local-model dependency split:
  `clap`, `cue`, and `ai-local`. The full app/installer path should now use
  `ai-local`; focused CI/dev jobs can still opt into `clap` or `cue` only.
  `uv.lock` was refreshed and `tests/library/test_models_cli.py` pins the
  extras contract.
- Model install target cleanup made `required` and `cue` first-class
  CLI/Rust/UI/API targets. `library models --install required --json` is the
  first-run app path and currently installs the required CLAP snapshot only.
  `library models --install all --json` remains strict and means both CLAP and
  optional CUE-DETR are ready; it no longer silently ignores CUE errors. The
  Library setup button now routes fresh CLAP-missing machines to `required`,
  and CUE-only gaps to `cue`, so a missing optional CUE artifact cannot fail the
  one-click required model install.
- Library model setup copy is now less scary for a first-run user: a successful
  required install reports `Required models ready` with downloaded/verified file
  counts, and a CUE-only setup miss is labeled `Optional CUE setup unavailable`
  instead of looking like required product setup failed. Verification:
  `env -u GEMINI_API_KEY uv run python -m vibemix library models --json` and
  `--install required --json` both returned CLAP/CUE installed on this machine;
  `env -u GEMINI_API_KEY uv run python -m vibemix library stats --json`
  returned stdout JSON with CLAP/512 and `agent_ready=true`; `npm --prefix
  tauri/ui test -- library` -> 65 passed; `npm --prefix tauri/ui run build`
  passed with existing Vite chunk warnings only; `git diff --check` passed for
  the touched UI/map slice.
- Model setup UI hardening split the required/optional decision into
  `deriveModelSetupView()` and normalized dataset targets through
  `modelInstallTargetFromDataset()`, including the backend-supported `clap`
  target instead of silently coercing it to `required`. New focused UI coverage
  pins all-ready, missing required CLAP, optional CUE check/repair, required
  retry, and optional CUE retry states. Verification:
  `npm --prefix tauri/ui run test -- src/library/model-setup.test.ts
  src/library/api.test.ts` -> 20 passed; broader
  `npm --prefix tauri/ui run test -- src/library` -> 65 passed;
  `uv run python -m vibemix library
  models --install required --json` -> `ok=true` with six CLAP files
  checksum-verified/skipped; `uv run python -m vibemix library models --install
  cue --json` -> `ok=true` with the CUE-DETR file checksum-verified/skipped;
  `uv run pytest -q tests/library/test_models_cli.py` -> 17 passed;
  `npm --prefix tauri/ui run build` passed with existing Vite chunk warnings
  only; `git diff --check -- tauri/ui/src/library/index.ts
  tauri/ui/src/library/model-setup.test.ts
  .planning/research/CODEX-full-product-sweep-map.md` -> pass.
- Library chat UI hardening added dedicated `mountLibrary -> runChat` coverage
  for the agentic surface: one successful grounded turn renders tool trace,
  playlist artifact, cleared input, and `iterations/stop_reason`; a second turn
  receives only completed prior user/Viber turns as history; and thrown backend
  errors no longer poison future API history with an uncompleted user turn. The
  visible thread still shows the error. Verification:
  `npm --prefix tauri/ui run test -- src/library/chat.test.ts` -> 3 passed;
  `npm --prefix tauri/ui run test -- src/library` -> 68 passed;
  `npm --prefix tauri/ui run build` passed with existing Vite chunk warnings
  only. Direct CLI stream split showed stdout remains valid JSON: without
  `VIBEMIX_CODEX_ALLOW_SHELL=1`, `library chat --backend codex --json` returns
  `stop_reason=codex_mcp_blocked`; with bridge-equivalent
  `VIBEMIX_CODEX_ALLOW_SHELL=1`, it returns one `search_vibe` tool and a real
  `SMOKED OUT` recommendation, while the human `-> viber chat ...` receipt stays
  on stderr.
- Tauri Library bridge hardening extracted the command arg shaping for
  `library_chat` and `library_models` into pure helpers. Rust coverage now pins
  that chat always invokes `library chat <message> --backend codex --json`,
  appends serialized `--history` only when present, trips the Codex shell gate
  via the backend flag, and that model status/install/force args use
  `library models --json [--install target] [--force]`. Verification:
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds::tests`
  -> 24 passed; `cargo check --manifest-path tauri/src-tauri/Cargo.toml` ->
  pass; `npm --prefix tauri/ui run test -- src/library/chat.test.ts
  src/library/model-setup.test.ts` -> 11 passed; bridge-equivalent CLI smoke
  verified `library models --install required --json` with CLAP files
  checksum-skipped and `VIBEMIX_CODEX_ALLOW_SHELL=1 library chat --backend
  codex --json` with one `search_vibe` tool and `stop_reason=model_done`.
- Library packaged-exposure contract now pins the Vibe Engine capability
  surface. `tests/capabilities/test_library_window_contract.py` asserts the
  `library` WebviewWindow label stays in `capabilities/default.json`, every
  Library bridge command remains registered in `main.rs`, the frontend invokes
  those registered command names, and the dev-source `vibemix-library-uv` /
  `vibemix-library-python` shell entries remain available. Verification:
  `uv run pytest -q tests/capabilities/test_library_window_contract.py
  tests/capabilities/test_debrief_arg_allowlist.py
  tests/security/test_capability_snapshot.py` -> 13 passed; `git diff --check`
  on the new capability test -> pass.
- Frozen local-audio packaging cleanup made PyAV a direct runtime dependency
  instead of relying on the current LiveKit Agents transitive dependency. This
  matters because local CLAP/CUE file decode and debrief MP3 encode import
  `av` directly, so a future LiveKit debloat must not break the one-click
  model/audio path. Both PyInstaller specs now explicitly collect PyAV
  submodules and native libs alongside onnxruntime/tokenizers; `uv.lock` was
  refreshed against the current dependency graph. Verification:
  `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py
  tests/library/test_models_cli.py tests/library/test_audio_decode.py
  tests/debrief/test_tldr_mp3_codec.py` -> 60 passed; runtime import smoke
  printed `av 17.0.1`, `onnxruntime 1.26.0`, `tokenizers 0.22.2`;
  `uv tree --depth 1` shows top-level `av` plus local-AI extras and no
  top-level `scipy` / `librosa` / `transformers`; `uv lock --locked` -> pass;
  `git diff --check` on dependency/spec/test files -> pass.
- Local model-path cleanup centralized the runtime/install/cache contract in
  `vibemix.library.cache_paths`. CLAP installer, CLAP ONNX status/load,
  CUE-DETR status/load, and the CLAP ingest embedding cache now share one set
  of default paths and env override constants, avoiding first-run drift between
  setup UI, CLI status, and runtime inference. Verification:
  `uv run ruff check src/vibemix/library/cache_paths.py
  src/vibemix/library/model_assets.py src/vibemix/library/clap_engine.py
  src/vibemix/library/cue_detr.py src/vibemix/library/ingest.py
  tests/library/test_cache_paths.py` -> pass; `uv run pytest -q
  tests/library/test_cache_paths.py tests/library/test_models_cli.py` -> 20
  passed; `uv run pytest -q tests/library/test_cache_paths.py
  tests/library/test_models_cli.py tests/library/test_embed_clap.py
  tests/library/test_ingest.py tests/library/test_audio_decode.py
  tests/library/test_cue_engine.py` -> 56 passed; live
  `uv run python -m vibemix library models --json` reports CLAP and CUE ready;
  packaging-adjacent `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py
  tests/library/test_audio_decode.py tests/debrief/test_tldr_mp3_codec.py` -> 43
  passed; `npm --prefix tauri/ui run test -- src/library` -> 68 passed;
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds::tests`
  -> 24 passed; `uv run pytest -q tests/library/test_codex_curate.py
  tests/library/test_stats_cli.py tests/capabilities/test_library_window_contract.py`
  -> 32 passed; `npm --prefix tauri/ui run build` passed with existing Vite
  warnings only; `cargo check --manifest-path tauri/src-tauri/Cargo.toml` and
  `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` passed;
  `uv lock --locked` and touched-file `git diff --check` -> pass.
- Vibe Engine agent-mode runtime cleanup stopped mode switching from
  auto-starting Codex-backed `curate` / `build` runs. Opening those modes now
  renders an idle state (`No playlist curated yet.` / `No set built yet.`) and
  waits for the explicit run button or preset chip, while search/similar still
  auto-refresh because they are cheap library reads. This removes a demo-risky
  slow tool loop that could fire before the presenter edits the brief or energy
  curve. Verification: `npm --prefix tauri/ui run test --
  src/library/build.test.ts src/library/curate.test.ts` -> 27 passed;
  `npm --prefix tauri/ui run test -- src/library` -> 70 passed;
  `npm --prefix tauri/ui run build` passed with existing Vite warnings only;
  touched-file `git diff --check` -> pass.
- Vibe Engine indexed-count cleanup removed the mock-only `/ 1547` denominator
  from the live stats readout. The UI now renders the actual
  `library_stats.indexed` count only, so a fresh install or small demo corpus
  does not claim a stale library total. Verification: `npm --prefix tauri/ui
  run test -- src/library/chat.test.ts src/library/build.test.ts
  src/library/curate.test.ts` -> 31 passed; `npm --prefix tauri/ui run test --
  src/library` -> 71 passed; `npm --prefix tauri/ui run build` passed with
  existing Vite warnings only; touched-file `git diff --check` -> pass.
- Vibe Engine first-paint stats cleanup removed the same stale `/ 1547`
  denominator from `tauri/ui/library.html`, so the real entry document does not
  briefly render the mock corpus total before `libraryStats()` hydrates or if
  stats fails. Verification: `npm --prefix tauri/ui run test --
  src/library/api.test.ts src/library/chat.test.ts` -> 17 passed;
  `npm --prefix tauri/ui run test -- src/library` -> 72 passed;
  `npm --prefix tauri/ui run build` passed with existing Vite warnings only;
  targeted `rg` found `1547` only in negative regression assertions; touched-file
  `git diff --check` -> pass.
- Active contributor-doc drift cleanup removed the remaining `codex|gemini`
  Viber backend guidance from `CLAUDE.md` and the v8.2 state table. The
  contributor guide now describes Library/Viber as local Codex only, the
  Telegram bridge as running the Codex Viber path, and legacy Gemini harnesses
  as historical rather than exposed fallback. `tests/repo/test_phase20_docs.py`
  now guards `CLAUDE.md` and `.planning/STATE.md` against reintroducing
  `--backend codex|gemini`, "Gemini is fallback", "runs the Gemini agent", or
  similar stale Viber fallback copy. Verification: targeted `rg` across active
  contributor/docs/planning surfaces found no stale Viber Gemini-fallback hits;
  `uv run pytest -q tests/repo/test_phase20_docs.py` -> 25 passed; touched-file
  `git diff --check` -> pass.
- Runtime Codex app-path re-smoke tightened the desktop bridge contract. The
  current `STATE.md` head now records Phase 88 UI as wired into the Vibe Engine
  Library surface instead of deferred, `tests/capabilities/test_library_window_contract.py`
  pins the Rust Library bridge's Codex backend and `VIBEMIX_CODEX_ALLOW_SHELL`
  injection, and stale Gemini-fallback comments in the Codex/MCP source were
  rewritten as legacy-only context. Live source smokes verified the actual
  product commands: `library stats --json` reported 24 CLAP/sqlite-vec tracks
  and Codex ready, `library models --json` reported CLAP and CUE ready,
  `library search "dark hypnotic rolling" --k 3 --json` returned real local
  tracks, `VIBEMIX_CODEX_ALLOW_SHELL=1 library chat ... --backend codex --json`
  returned `stop_reason=model_done`, and `VIBEMIX_CODEX_ALLOW_SHELL=1 library
  build-set ... --export rekordbox --backend codex --json` exported
  `/Users/ozai/.cache/vibemix/sets/compact-dark-demo-opener.xml`. Verification:
  `uv run ruff check src/vibemix/library/mcp_server.py
  src/vibemix/library/codex_curate.py tests/capabilities/test_library_window_contract.py
  tests/repo/test_phase20_docs.py` passed; `uv run pytest -q
  tests/repo/test_phase20_docs.py tests/capabilities/test_library_window_contract.py
  tests/library/test_codex_curate.py` -> 51 passed; `npm --prefix tauri/ui run
  test -- src/library` -> 72 passed; `cargo test --manifest-path
  tauri/src-tauri/Cargo.toml library_cmds::tests` -> 24 passed;
  `npm --prefix tauri/ui run build` passed with existing Vite warnings only;
  touched-file `git diff --check` -> pass.
- Windows updater artifact wording cleanup removed the remaining release-runbook
  ambiguity that said Windows updater artifacts could be NSIS `*setup*.exe` or
  MSI. The current path is explicit: first install is the SignPath-signed Inno
  `vibemix-installer.exe`, updater payload is the Tauri NSIS `*setup*.exe`, and
  `latest.json` must not point at the DMG or Inno installer. Verification:
  `uv run pytest -q tests/install/test_windows_packaging_paths.py
  tests/repo/test_phase20_docs.py` -> 34 passed; `uv run pytest -q
  tests/install/test_windows_packaging_paths.py tests/install/test_macos_updater_artifact.py
  tests/install/test_macos_app_sidecar_symlink_repair.py
  tests/security/test_release_yml_signing_skips.py tests/repo/test_phase20_docs.py`
  -> 54 passed; `bash -n scripts/dist/create_macos_updater_artifact.sh
  scripts/dist/sign_manifest.sh scripts/dist/pretag_check.sh
  scripts/dist/sign_macos.sh scripts/release/check_bravoh_server_ready.sh
  scripts/launch/cut_release.sh` -> pass; touched-file `git diff --check` ->
  pass.
- Windows updater contract debloat removed MSI from the active updater path
  entirely. `release.yml` now uploads/finds/stages only Tauri NSIS
  `*setup*.exe` updater payloads, `sign_manifest.sh` rejects non-NSIS Windows
  updater artifacts, and updater/post-launch docs now name only NSIS for
  the current Windows updater. The remaining MSI helpers stay only for generic
  binary/signature inspection and historical telemetry fixtures. Verification:
  `uv run pytest -q tests/security/test_release_yml_signing_skips.py
  tests/install/test_windows_packaging_paths.py tests/repo/test_phase20_docs.py`
  -> 50 passed; `uv run ruff check tests/security/test_release_yml_signing_skips.py
  tests/install/test_windows_packaging_paths.py tests/repo/test_phase20_docs.py`
  passed; `bash -n scripts/dist/sign_manifest.sh
  scripts/dist/create_macos_updater_artifact.sh scripts/dist/pretag_check.sh
  scripts/dist/sign_macos.sh scripts/release/check_bravoh_server_ready.sh
  scripts/launch/cut_release.sh` passed; targeted `rg` found no active MSI
  updater artifact patterns in release.yml, sign_manifest, or updater docs.
- Broad source Ruff cleanup now makes `uv run ruff check src/vibemix` pass.
  The sweep was mechanical plus small lifecycle/test-contract fixes: import
  sorting, pyupgrade/Ruff nits, explicit unicode ignores for intentional
  docs/prompt glyphs, retained async task handles for wizard/evidence refresh,
  and stale debrief/router expected-model mirrors aligned to the current
  `gemini-3.5-flash` router truth. This is source hygiene, not full release
  closure.
- Debrief sidecar cleanup moved `open_debrief_window` off Tauri's stale named
  `externalBin` sidecar path. Debrief now uses the shared sidecar resolver
  (`bundle.resources` in packaged builds, `uv run python -m vibemix` in dev),
  appends `--debrief <validated_session_dir>`, and relays the same runtime auth
  / Viber backend setup env keys as the watchdog and library bridge. The stale
  `binaries/vibemix-core` sidecar capability entry was removed and the security
  snapshot regenerated.
- Viber set export cleanup fixed a product-contract mismatch: MCP/agent docs
  promised Rekordbox XML with order + key + BPM + cues, and
  `export_rekordbox.export_set()` already supports cues/beatgrid, but the
  `LibraryToolset.export_set` bridge was not forwarding Rekordbox cue marks or
  tempo nodes. It now threads DJ cue/loop/fade/load marks plus a first tempo
  node (or BPM-only constant grid) into the XML export payload. The Library UI
  skeleton comment and live centering docstring were also reconciled to the
  current local Codex and CLAP-store wording.
- Library setup cleanup made the offline agent preflight visible beside local
  model readiness: `renderStats()` now re-renders the model setup strip with
  `agent_hint`, so a user can see `CLAP ready / CUE ready` and also
  `Viber codex: Run codex login...` without first sending a failed chat turn.
- Pill next-suggestion cleanup now preserves existing Rekordbox cue metadata in
  the visible grounded `why` line. It adds only a first structural cue/loop hint
  already present on the resolved library entry, e.g. `cue drop @ 1:04`; it does
  not run cue detection in the realtime pill path and does not change the wire
  schema.
- Live prompt cleanup removed stale `phase=` / `phase=silent` references from
  the intermediate hype prompt. The prompt now names the evidence that actually
  exists (`hearing[...]`, `phase_age`, `phase_history`) and keeps phase changes
  subordinate to what Gemini hears in the attached audio.
- CUE-DETR installer cleanup added the missing hosted-artifact seam without
  pretending the public artifact exists yet. `library models --install cue
  --json` now downloads from operator-provided `VIBEMIX_CUE_ONNX_URL` only when
  `VIBEMIX_CUE_ONNX_SHA256` and `VIBEMIX_CUE_ONNX_SIZE` are also valid; missing
  or unverified CUE setup returns actionable JSON errors, and `model_status()`
  marks env-pinned size/SHA mismatches as not installed.
- CUE test isolation cleanup removed the module reload that could swap the
  `CueProducerUnavailable` class object under already-collected cue engine
  tests. The real env-pinned CUE status path is now covered via an explicit
  pytest marker instead of a global reload.
- Viber set-prep/curate setup cleanup fixed a bridge-level UI killer: Codex
  setup/no-playlist terminals from `library curate` / `library build-set`
  could exit nonzero with structured JSON plus a human hint on stderr, causing
  the Rust bridge to collapse them into a generic engine error. The bridge now
  preserves structured agent terminal payloads carrying `stop_reason`, while
  normal backend failures like "No library cache" still throw. Empty
  rationale now falls back to the agent `error` field so the Library UI can
  show the actionable Codex setup hint in the set-notes area.
- Sidecar packaging cleanup made the frozen sidecar local-AI-aware: the
  canonical `scripts/build_sidecar.py` PyInstaller call now runs through
  `uv run --extra ai-local`, and both macOS/Windows specs explicitly collect
  the lazy CLAP/CUE runtime packages (`onnxruntime`, `tokenizers`,
  PyAV/numpy audio decode/DSP, plus native libs) while excluding Transformers.
  This reduces the "works in source, missing model runtime in packaged app"
  risk without reintroducing the heavyweight model stack.
- Local-audio debloat removed the old `librosa` and `transformers.audio_utils`
  runtime paths from CLAP and CUE. `src/vibemix/library/audio_decode.py` now
  uses PyAV/FFmpeg for decode/resampling, and `audio_features.py` provides the
  narrow numpy Slaney mel/STFT/window helpers needed by the local ONNX models.
  The live/audio-buffer paths use a narrow numpy resampler, CUE peak picking is
  local, and phrase autocorrelation uses direct numpy FFTs. `uv sync --group
  dev --extra ai-local` removed the `scipy` plus
  `librosa`/`soundfile`/`soxr`/`numba`/`llvmlite`/`scikit-learn`/`transformers`
  families from the dev environment and the rebuilt frozen sidecar contains
  none of them.
- Detector tuning debloat fixed the remaining live SciPy import in
  `scripts/tune_detectors.py`. The harness now uses
  `vibemix.audio.resample.resample_audio`, script docs point at the local
  resampler, and `.planning/codebase/STACK.md` was replaced with the current
  Python 3.12/Tauri/local-CLAP stack map instead of the retired cohost.py /
  Python 3.14 / SciPy-era inventory.
- Viber/Codex documentation drift cleanup reconciled active tool-surface copy:
  `mcp_server.py`, `codex_curate.py`, and `docs/codex-agent.md` now describe
  the expanded grounded MCP surface (search/discover/features/energy/sequence/
  playlist/export plus media/knowledge/cue helpers) instead of the old "three
  tools" curation-only surface. `docs/AUDIT.md` was regenerated after adding
  ratings for `mcp`, optional `python-telegram-bot`, Playwright test packages,
  and `pixelmatch`; the stale Gemini-only and SciPy audit rows are gone.
- Live embedding-boundary cleanup removed the last misleading
  `__main__.py` signal that library grounding depended on Gemini
  `embedContent`. Startup grounding now describes and constructs local CLAP
  via `build_embedder()` without threading the live Gemini client into the
  embedding factory; legacy Gemini helper paths also avoid the product
  embedding factory.
- Product embedder isolation cleanup split the CLAP path away from the legacy
  Gemini embedding module. `embed_factory.py` now owns the product
  `build_embedder()` factory, `embed_config.py` / `embed_cache.py` own shared
  strategy constants and SQLite cache schema, and `cache_paths.py` owns the
  cache DB path. Search/similar/grounding/importer/agent now type against
  backend-neutral protocols in `embed_types.py`, so runtime library surfaces no
  longer import `LibraryEmbedder` just for annotations or constants. The
  `vibemix.library` lazy export for `build_embedder` also points at
  `embed_factory`, leaving `LibraryEmbedder` in `embed.py` for explicit legacy
  migration/probe/tests only.
- Eval embedding cleanup removed the active Gemini embedding dependency from
  `scripts/eval/cited_relevance.py`. The cited-relevance gate now keeps its
  async compatibility signature but computes a deterministic local token-cosine
  between stripped response prose and evidence payload. Cited relevance and
  substance tests are documented as local/no-cassette; `record_cassettes.py`
  now scopes Gemini cassette setup to judge tests. `clap_engine.py` copy also
  avoids comparing CLAP to the legacy cloud embedder.
- Legacy proxy-embed probe cleanup made `scripts/probe_proxy_embed.py` opt-in.
  Default invocation now returns `status="skipped"` with exit 0 because product
  embeddings are local CLAP ONNX; the old Bravoh `embedContent` route is only
  checked when explicitly running `--legacy-live-probe`.
- Active source/test/planning copy cleanup removed stale `LibraryEmbedder`,
  Gemini text-embedder, and 1536-d synthetic-corpus wording from CLAP, cue,
  folder-ingest, DJ knowledge, memory ingest, and genre-prototype test
  surfaces. Historical `.planning/PROJECT.md` milestone bullets now explicitly
  say Phase 28/41 Gemini embedding work is superseded for product library
  embeddings by Phase 90 local CLAP ONNX; `.planning/STATE.md` uses
  `EMBEDDING_DIM` for prototype-shape notes.
- Public launch-copy cleanup removed stale Gemini-Embedding-2 branding from
  `scripts/launch/changelog_template.md` and removed an unnecessary Gemini
  Embedding comparison from `docs/clap-engine.md`. Current launch-facing copy
  now says library intelligence is local CLAP ONNX; remaining Gemini-only hits
  in active docs are explicitly historical/superseded dependency-opportunity
  notes.
- Windows installer cleanup made the Inno app-payload source directory a real
  `/DSourceDir=...` macro instead of a hardcoded `dist\vibemix` path, and
  updated local build/docs to use `build_sidecar.py` rather than raw
  `pyinstaller`.
- Windows release-staging cleanup removed the old
  `dist/vibemix/vibemix.exe` signing/upload path. The workflow and local
  builder now stage `dist/windows-app/` from the Tauri app exe plus
  `binaries/vibemix-core-x86_64-pc-windows-msvc/`, and Inno consumes that
  staged app payload (or SignPath's returned signed copy) via `SourceDir`.
  Tauri resources now also include the Windows sidecar glob with a tiny
  placeholder so source checks do not depend on a built sidecar.
- Windows SignPath/Inno cleanup made full signing mode require every secret
  the Windows path actually consumes, including `SIGNPATH_SIGNTOOL_CMD`. The
  package step now fails fast if that command is missing and passes
  `/Ssignpath=$signTool` into ISCC so `SignTool=signpath` in the Inno script is
  registered instead of being a latent compile-time failure.
- Windows installer artifact cleanup corrected the active release surface from
  fake/stale `vibemix-installer.msi` naming to Inno Setup's real
  `vibemix-installer.exe` output. The release workflow, updater manifest URL,
  publish gate, public README, current Windows signing/install docs, and
  local SignPath rehearsal script now point at the signed EXE. The old MSI
  string remains only in historical planning/eval text and in a regression
  assertion that prevents the release workflow from reintroducing it.
- Windows Inno output-path cleanup made the CI output override real. The Inno
  script now uses `InstallerOutputDir` for `OutputDir` and
  `SignedUninstallerDir`; the release workflow passes
  `/DInstallerOutputDir=..\..\output`, so the later verify/upload steps that
  read `output/vibemix-installer.exe` now match the compiler output path.
- Windows Tauri build cleanup switched the Windows CI/local app build to
  `cargo tauri build --no-bundle`. Inno is the Windows package producer, so the
  Windows path now builds only `target/release/vibemix.exe` before staging
  `dist/windows-app/`, avoiding accidental use of the shared macOS
  `bundle.targets=["app","dmg"]` config on Windows.
- Updater secret-name cleanup aligned release prep on the canonical
  `TAURI_UPDATER_KEY_PASSWORD` name already used by `release.yml` and
  `sign_manifest.sh`. `pretag_check.sh` and `docs/ship-runbook.md` no longer
  require the stale `TAURI_UPDATER_PRIVATE_KEY_PASSWORD`; repo-shape tests now
  pin the canonical name and forbid the stale one in those active surfaces.
- Updater manifest signing cleanup fixed a release-publish ordering blocker:
  `sign_manifest.sh` no longer tries to sign GitHub Release URLs before the
  draft release/assets exist. The workflow now passes local downloaded
  artifact paths (`--macos-artifact`, `--windows-artifact`) for the signer and
  still writes the future public GitHub Release URLs into `latest.json`.
- Updater artifact-contract cleanup stopped `latest.json` from silently
  pointing at first-install artifacts that Tauri's updater should not consume.
  `release-publish` now searches for Tauri-style updater artifacts
  (`*.app.tar.gz` on macOS, Tauri NSIS `*setup*.exe` on Windows), and
  `sign_manifest.sh` rejects a macOS DMG or the Inno `vibemix-installer.exe`
  before any signing call. Release docs and the Bravoh upload contract now
  name signed manifest JSON plus updater artifacts rather than binary
  multipart upload of first-install media.
- `.planning/archive/README.md` now indexes the archive bundles and explains
  what was moved, deleted, or intentionally kept active.
- Mascot bundle cleanup archived the untracked extra character variants under
  `.planning/archive/2026-05-27-mascot-character-variants/` with a local zip.
  The active manifest is back to the single shipped `character.glb`, and the
  active mascot GLB bundle now checks at `22.64 MB / 25.00 MB` instead of the
  failing `41.79 MB` expanded variant set.
- Live verification cleanup removed the two source-sidecar recording sessions
  created during this pass from the app-data recordings directory
  (`20260527-011632`, `20260527-011917`) and removed the generated
  `peak-time-hardgroove-proof-set*` playlist/XML proof artifacts from
  `~/.cache/vibemix`.
- Tauri dev-loop cleanup fixed the desktop dev blocker: `beforeDevCommand`
  now runs `npm --prefix ui run dev`, matching the `cargo tauri dev` working
  directory (`tauri/`). Regression coverage lives in
  `tests/repo/test_tauri_dev_command.py`.
- Source desktop verification after that fix started Vite on `localhost:1420`,
  Rust `target/debug/vibemix`, and source sidecar
  `.venv/bin/python3 -m vibemix` on `127.0.0.1:8765`. Websocket smoke saw 56
  flat frames, 27 session snapshots, and 2 status ticks in 2 seconds; manual
  `ipc.settings.get` and `ipc.status.recheck` returned structured responses
  with `livekit=ok`, `gemini=ok`, and `screen=unavailable`.
- Live status recheck cleanup passed live runtime references into
  `SessionLoop`, so manual rechecks no longer report `livekit=connecting` /
  `gemini=down` while the live sidecar is actually attached. Screen status now
  reports `unavailable` when the screen stack is not installed rather than
  escalating to a deck fault.
- Renderer proof for the current source dev app showed the new Deck Speaks
  idle surface (`listening for the mix...`) and no false Gemini fault. A stale
  installed app was also discovered and identified as the source of earlier
  misleading screenshots/log tail noise.
- Runtime boot-IPC cleanup removed the blocking boot-time `ipc.settings.get`
  used only for the lighter-blur preference. The preference now applies from
  the normal `ipc.settings.state` bridge once the sidecar is connected, so a
  slow sidecar startup no longer logs a false 2s `ipc.settings.state` timeout.
  Source-backed hot reload showed clean `boot: start` -> profile/settings ->
  `live session mounted` with no `vmx:error`; a direct websocket probe still
  returned `ipc.settings.state` with `mode=hype` and `lighter_blur=false`.
- Focused gates after the desktop fixes:
  `uv run pytest -q tests/repo/test_tauri_dev_command.py tests/runtime/test_session_loop.py tests/runtime/test_ws_bus_status_tick.py tests/test_main_smoke.py`
  -> `54 passed`; focused `ruff check` -> pass; `cargo check
  --manifest-path tauri/src-tauri/Cargo.toml` -> pass.
- Dev verification cleanup removed inactive app-data recordings
  `20260527-012819/` and `20260527-013708/`, skipped live installed-app
  recording `20260527-012928/`, and cleared repo-local pytest/ruff/pycache
  artifacts while preserving `.venv`, `node_modules`, Tauri `target`, frontend
  `dist`, `.planning/archive`, and Claude worktrees.
- Fresh-install rehearsal doc cleanup now treats local CLAP model readiness and
  the Library/Viber surface as part of first-install success, not optional
  post-demo polish. `docs/install-rehearsal.md` requires `Required models
  ready` / `CLAP ready`, exact Viber setup actions, local Library search
  without Gemini keys, one Library chat turn, and a build-a-set smoke before the
  stopwatch can close. `docs/windows-setup.md` no longer claims the Windows
  installer is future work or a SignPath MSI; it points to the current
  SignPath-signed Inno `vibemix-installer.exe` release path. Verification:
  `uv run pytest -q tests/repo/test_phase20_docs.py
  tests/install/test_rehearsal_scaffold.py
  tests/install/test_windows_packaging_paths.py` -> 37 passed; `git diff
  --check -- docs/install-rehearsal.md docs/windows-setup.md
  tests/repo/test_phase20_docs.py` -> pass.
- Fresh-install rehearsal automation cleanup now matches that contract. The VM
  matrix tracks a 10-minute `install_ms` budget, expected steps include
  required CLAP setup, Viber setup, local Library search/chat, build-set,
  audio/MIDI, and first reaction, and CI now calls
  `install_vm_matrix.sh --simulate --check-install-budget` while keeping
  `--check-60s` as a compatibility alias. The latest-run lookup is Python-based
  instead of macOS-only `stat -f`, so the `ubuntu-latest` workflow path can
  actually find the simulated run it just wrote. Verification: `bash -n
  scripts/dist/install_vm_matrix.sh` -> pass; `uv run ruff check
  scripts/dist/check_60s_gate.py tests/install/test_install_vm_matrix.py
  tests/dist/test_60s_gate.py` -> pass; `uv run pytest -q
  tests/install/test_install_vm_matrix.py tests/dist/test_60s_gate.py
  tests/install/test_rehearsal_scaffold.py` -> 35 passed; simulated budget
  smoke wrote `run_id=codex-install-budget-smoke`, budget `600000`, 5 rows,
  max simulated `install_ms=450000`; touched-file `git diff --check` -> pass.
- Runtime source-app full smoke restarted the dev app from source after the
  install-gate pass: Vite on `127.0.0.1:1420`, Tauri source app, and Python
  sidecar on `127.0.0.1:8765`. Direct websocket probe returned
  `ipc.settings.state` (`mode=hype`, `mood=hype-man`, `lighter_blur=false`),
  `ipc.status.tick` (`gemini=ok`, `livekit=ok`, `screen=unavailable`), and an
  `ipc.session.snapshot` (`cohost_status=IDLE`). Library/Viber smokes from the
  same source tree verified `library stats --json` reports sqlite-vec,
  CLAP/512, and Codex ready; `library models --json` reports CLAP and CUE ready;
  `library search "dark hypnotic rolling" --k 3 --json` returns local track
  ids; and `library chat ... --backend codex --json` completed one tool turn.
  A slow build-set smoke exposed that CLI `--n-slots` was parsed but not
  forwarded into the Codex set prompt; it is now threaded through, export intent
  is explicit, default set-prep wall-clock is 90s instead of 300s, and bounded
  live smokes returned both no-export (`stop_reason=created`, 3 tracks) and
  export (`stop_reason=exported`, 3 tracks, Rekordbox XML path) results. The
  proof XML/M3U/JSON artifacts were removed afterward, and ports/processes were
  clean after shutdown. Verification: `uv run ruff check
  src/vibemix/library/codex_curate.py src/vibemix/__main__.py
  tests/library/test_codex_curate.py` -> pass; `uv run pytest -q
  tests/library/test_codex_curate.py tests/capabilities/test_library_window_contract.py`
  -> 26 passed.
- Package sidecar readiness gate now catches the local bundle footgun where a
  direct Tauri package can silently include only committed `.placeholder`
  directories. `scripts/dist/check_sidecar_bundle_ready.py` validates the exact
  Rust resource path (`binaries/vibemix-core-<triple>/vibemix-core-<triple>`),
  rejects placeholder-only/tiny/non-executable bundles, requires PyInstaller's
  `_internal/` tree, and is wired into `scripts/dist/pretag_check.sh` as step
  5/8. Current repo-local `tauri/src-tauri/binaries` intentionally fails this
  gate until `uv run python scripts/build_sidecar.py --spec
  vibemix-core.macos.spec` is run. Verification: `uv run pytest -q
  tests/install/test_sidecar_bundle_ready.py tests/repo/test_phase20_docs.py`
  -> 34 passed; broader package slice
  `tests/sidecar/test_build_sidecar_rename.py
  tests/runtime_closeouts/test_universal2_sidecar.py
  tests/install/test_macos_app_sidecar_symlink_repair.py
  tests/install/test_macos_updater_artifact.py
  tests/install/test_windows_packaging_paths.py
  tests/install/test_install_vm_matrix.py tests/dist/test_60s_gate.py` ->
  117 passed, 2 skipped because no real repo-local sidecar bundle is built.
- Runtime/browser UI sweep fixed a plain-Vite boot crash: `@tauri-apps/api`
  `listen()` is importable in Chromium but rejects outside a real Tauri
  webview while reading `window.__TAURI_INTERNALS__`, producing repeated
  `transformCallback` page errors on the main surface. `tauri-runtime.ts` now
  wraps Tauri `listen` as a no-op outside Tauri while preserving `invoke`
  rejection semantics; `main.ts`, `crash-banner.ts`, and `ipc/client.ts` use
  it. Browser smokes for `/`, `/library.html`, and `/pill.html` now report no
  console errors or page errors. Verification: `npm test -- --run
  tests/crash-banner.spec.ts tests/session/integration.spec.ts
  tests/session/tray-mood.spec.ts src/library/chat.test.ts
  src/library/build.test.ts src/library/model-setup.test.ts` -> 49 passed;
  `npm run build` passed with only existing Vite chunk-size/dynamic-import
  warnings.

## Product North Star

Vibemix is a local-first AI DJ co-host. Gemini and Codex are reasoning surfaces, not truth sources. Truth comes from local evidence: live audio DSP, DJ-app state, MIDI, Rekordbox/library metadata, vectors, citations, and explicit tool results.

Protect these invariants:

1. Only the refresh loop writes `MusicState`.
2. Track ids, citations, and export paths must resolve against real local evidence.
3. Live audio and DJ-app state beat prompt guesses.
4. One live UI socket: `127.0.0.1:8765`; debrief uses `8766`.
5. Idle, unavailable optional sensors, and denied screen capture must not blank
   the deck. Surface denied permissions as badges/setup work unless the missing
   permission truly prevents the current mode from operating.

## Current Version Map

Python:

- Package: `vibemix 0.1.0.dev0`.
- Python: `>=3.12,<3.13`.
- Runtime highlights: `google-genai 2.0.1`, `livekit 1.1.7`, `livekit-agents 1.5.8`, `livekit-plugins-google 1.5.8`, `livekit-plugins-openai 1.5.8`, `numpy 2.4.4`, `sounddevice 0.5.5`, `pyrekordbox 0.4.4`, `sqlite-vec 0.1.9`, `websockets 15.0.1`, `mcp 1.27.1`.
- Optional local-model extras now exist as `clap`, `cue`, and `ai-local`.
  `clap`/`ai-local` resolve to `onnxruntime` plus `tokenizers`; `cue` resolves
  to `onnxruntime` only. CLAP/CUE audio decode uses the app's existing PyAV
  and narrow numpy helpers instead of `librosa`, `scipy`, or Transformers.
- The app/installer path must include `ai-local` because product library
  embeddings default to local CLAP ONNX and cue-anchored ingest can use
  CUE-DETR ONNX; keeping narrow extras optional preserves lean import-only CI
  jobs.
- Dev highlights: `pytest 9.0.3`, `ruff 0.15.12`, `pyinstaller 6.20.0`, `vcrpy 8.1.1`.

Frontend:

- Package: `vibemix-ui 0.0.0`.
- Direct resolved highlights: `@tauri-apps/api 2.11.0`, `@tauri-apps/plugin-shell 2.3.5`, `@tauri-apps/plugin-store 2.4.3`, `three 0.170.0`, `typescript 5.9.3`, `vite 6.4.2`, `vitest 2.1.9`, `playwright 1.60.0`, `ajv 8.20.0`, `json-schema-to-typescript 15.0.4`.
- Scripts: `npm run dev`, `npm run build`, `npm run test`, `npm run check:ipc`, `npm run codegen:ipc`, `npm run build:mascot`.

Rust/Tauri:

- Crate: `vibemix 0.0.1`.
- Rust edition: 2021, minimum `1.77`.
- Direct resolved highlights: `tauri 2.11.1`, `tokio 1.52.3`, `tokio-tungstenite 0.29.0`, `serde 1.0.228`, `serde_json 1.0.149`, Tauri plugins for fs, global shortcut, macOS permissions, positioner, process, shell, store, updater.

Model routes in `src/vibemix/llm/_router_config.py`:

- `live_coach`: `gemini-3.5-flash`, STANDARD.
- `live_coach_tts`: `gemini-3.1-flash-tts-preview`, STANDARD.
- `live_coach_tts_fallback`: `gemini-2.5-flash-preview-tts`, STANDARD.
- `live_coach_tts_openrouter`: `google/gemini-3.1-flash-tts-preview`, OpenRouter sentinel.
- `debrief`: `gemini-3.5-flash`, FLEX.
- `debrief_tts`: `gemini-3-flash-tts-preview`, FLEX.
- `library_auto_tag`: `gemini-3.5-flash`, FLEX.
- `embedding`: legacy Gemini embedding route remains in router/tests, but the
  product library embedding factory now uses local CLAP ONNX instead.

## Current Architecture Map

Live co-host:

- Entrypoint: `uv run python -m vibemix`.
- Local UI event bus: `src/vibemix/runtime/ws_bus.py`.
- IPC schema/types: `src/vibemix/ui_bus/messages.py`, `tauri/ui/src/ipc/messages.*`.
- Gemini native TTS is primary and fallback. OpenRouter TTS is standby only when `VIBEMIX_TTS_OPENROUTER=1` and a key exists.
- Screen status is now tri-state: `ok`, `denied`, `unavailable`. UI treats unavailable as neutral/off.

Library and Viber:

- Search and ingest flow through local stores and embeddings under `src/vibemix/library/`.
- CLI surfaces: `library search`, `similar`, `curate`, `build-set`, `chat`, `embed-folder`, stats/export helpers.
- Rust/Tauri surfaces now expose `library_curate`, `library_build_set`,
  `library_chat`, and `library_models`.
- Library UI starts in chat mode and calls `library_chat(message, history)`.
- App-facing curate/build/chat are pinned to local Codex for the current
  demo/test phase. Stale `VIBEMIX_LIBRARY_AGENT_BACKEND=gemini` is overridden
  by the desktop bridge, and visible CLI Viber commands accept only
  `--backend codex`.
- Rust bridge sets `VIBEMIX_CODEX_ALLOW_SHELL=1` only for explicit
  `--backend codex` app calls; this covers chat/build/curate and avoids relying
  on the parent shell env inside the desktop app.
- Library stats now carries `embedding_backend`, `embedding_dim`, and
  `agent_backend`; the titlebar renders the active Viber reasoning backend plus
  embedding engine from stats instead of hardcoded engine copy.

Embeddings:

- Product backend is CLAP ONNX, 512-d.
- `VIBEMIX_EMBED_BACKEND` is no longer the product selector; the factory always
  returns `ClapEmbedder`.
- Stores are namespaced with the `-clap` suffix so old 1536-d Gemini stores are
  not clobbered during re-embed.
- `ClapEmbedder` and direct `ClapEngine()` default to ONNX.
- `build_embedder(embed_strategy="cue_anchored")` now threads the strategy
  into `ClapEmbedder`; local tracks route through cue-window embedding and the
  cue-anchored cache key is namespaced away from whole-track CLAP vectors.

Auto-cue:

- `src/vibemix/library/cue_engine.py` is the single public entry for product cue detection.
- `detect_cues_auto()` tries CUE-DETR ONNX first through `cue_detr.detect_cue_positions()`, refines anchors, then falls back to the heuristic engine.
- `excerpt.py`, `embed.py`, and `ingest.py` now call `detect_cues_auto()`.
- CUE-DETR model path is `VIBEMIX_CUE_ONNX_PATH` or `~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx`.

Prompting:

- Model ids are centralized in `_router_config.py`.
- Turkish psytrance prompt overlay is gated by `VIBEMIX_PROMPT_OVERLAY=psy_tripper_tr`.
- No genre/persona overlay should be global default.

## Done Up To Now

- v8.0/v8.1/v8.2 source state indicates the core GSD/library/Viber milestones
  are shipped enough for demo wiring. Living planning docs now match the
  CLAP/Codex/current-embedding truth; milestone-status bookkeeping can still be
  refined separately.
- v8.2 Set Builder is present in CLI, Rust command, and UI path. Audit docs say it passed.
- Codex set-prep CLI now treats `stop_reason="exported"` as a successful
  terminal, so a real Rekordbox XML export is emitted on stdout with exit 0
  instead of being mistaken for a failed command by the Tauri bridge.
- Phase 89 Rekordbox XML ingest/export path is present. SQLCipher database path remains intentionally unused.
- Phase 90 CLAP is now the product embedding path and is wired with backend namespacing.
- Auto-cue pivot exists: CUE-DETR ONNX producer plus refinement plus heuristic fallback.
- CUE-DETR preprocessing no longer calls
  `DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")` at runtime.
  The processor is built from explicit local DETR defaults, so a user with the
  installed model cache does not hit a hidden Hugging Face lookup on first cue run.
- Frontend dead controls had recent fixes: rocker/mood/gear/pill/status paths are no longer obviously inert in source.
- Pill demo "next suggestion" is gated by `VITE_VIBEMIX_DEMO_NEXT=1`.
- Viber has grounded capabilities expanded in source: search/discovery helpers,
  quote/moment tools, DJ knowledge RAG notes, cue export, set builder, and
  conversational chat.
- Library chat now renders Codex setup terminals (`codex_not_installed`,
  `codex_auth_required`, `codex_mcp_blocked`) as explicit setup cards in the
  Viber side panel instead of treating them like an empty tool turn.
- Library build/curate now render structured Codex setup terminals as no-set
  states with the backend setup hint instead of a generic engine error.
- TTS chain is now native Gemini first. OpenRouter is no longer silently preferred just because a key exists.
- Library header source no longer hardcodes Gemini/1536. `library stats --json`
  reports CLAP/512 plus offline Viber agent setup status (`agent_ready`,
  `agent_status`, `agent_hint`), and the UI titlebar renders from that plus the
  active agent backend.
- `docs/AUDIT.md`, `docs/byo-key.md`, `docs/launch-prep/LAUNCH-SEQUENCE.md`,
  `docs/dep-opportunities/2026-05-scan.md`, `pyproject.toml`, and
  `scripts/audit/dep_ratings.yaml` now reflect the current CLAP/Codex split.
- `library models --json` is now the offline local-model status seam for setup.
  `library models --install required --json` installs/verifies the required
  CLAP Hugging Face snapshot with atomic writes and SHA-256 checks; `--install
  clap` remains the explicit CLAP-only equivalent. The default manifest is
  quality-first/full-precision ONNX. A brief q8-default pass was rejected after
  Kaan called out quality preference; Hugging Face also exposes fp16 ONNX files,
  so fp16 is the next candidate only after parity testing. CUE-DETR is reported
  honestly and can be installed from an operator-provided HTTPS URL only when
  size and SHA-256 pins are present. There is still no baked-in public CUE
  artifact URL. On Kaan's Mac both currently report installed.
- The desktop Library window has a basic model setup block wired to
  `library_models`: it shows CLAP/CUE status, routes first-run required setup
  through `required`, and only exposes a CUE action when the CLI reports the
  optional CUE artifact as installable. Missing non-installable CUE is labeled
  optional/manual instead of presenting a dead setup button. Required-model
  installs now stream `library://model-progress` events into the setup row with
  file count and byte progress.
- Latest frontend mock/Impeccable status:
  - `mocks/vibemix-rebuild-session.html` is largely wired in
    `tauri/ui/src/session/SessionLayout.ts` + `render-loop.ts`: persona tap-cycle,
    deck mute, restart-cohost wording, quiet status row, amber-only master meter,
    signature receipt rule, silent/fault/live modes.
  - `mocks/vibemix-pill-notch.html` / `vibemix-pill-hover.html` are largely wired
    in `tauri/ui/src/pill/index.ts` + `pill.css`: grounded next suggestion,
    notch/lip, collapsed hover peek, resize-to-content, no demo next unless
    `VITE_VIBEMIX_DEMO_NEXT=1`.
  - `mocks/vibemix-viber-chat.html` is wired into the library chat mode:
    thread, tool trace, artifact card, chips, Enter-to-send, and real
    `library_chat` bridge. The app now surfaces Viber backend truth in the
    titlebar via `agent_backend`.

## Current Dirty State

The worktree is intentionally not clean. Do not commit the whole thing as one lump.

Modified surfaces include:

- Live runtime and prompt: `__main__.py`, agent TTS files, `prompts/matrix.py`, `runtime/ws_bus.py`, `ui_bus/messages.py`.
- Library DSP/agent: CLAP, cue detection, ingest, excerpt, Rekordbox, Codex/Viber tests.
- Tauri/Rust: `main.rs`, config, library commands.
- UI: library chat/build/curate, pill, session status, settings, mascot assets, IPC generated files.
- Tests across agent, runtime, prompts, library, UI.

Untracked surfaces include:

- This sweep map, the new `.planning/archive/2026-05-26-research-sweep/` and
  `.planning/archive/2026-05-26-surface-clutter/` manifests/archived files,
  `.planning/archive/2026-05-26-generated-output/MANIFEST.md`,
  `.planning/archive/2026-05-26-eval-run-json/MANIFEST.md`,
  `.planning/archive/2026-05-26-stale-handoffs/`, `AGENTS.md`,
  active auto-cue design spec, UI mocks,
  `cue_detr.py`, `cue_engine.py`, `cue_refine.py`, `cue_types.py`, new cue/runtime
  tests, and the mascot character-variant archive.

## Engine Verdict

There is no single "best DSP engine" for this product. The best path is a layered local engine:

1. Realtime core: keep the lean numpy/sounddevice stack for live beat, energy, RMS, latency-sensitive hints, resampling, and DJ-state fusion.
2. Offline cue points: keep CUE-DETR ONNX as the primary structural cue producer. It is specialized for DJ cue estimation and maps cleanly into local ONNX distribution.
3. Cue refinement: keep deterministic local refinement and confidence scoring around CUE-DETR. The model finds candidates; local DSP makes them useful for mixing.
4. Library similarity: keep CLAP ONNX for audio-to-audio similarity and coarse text/audio bridge. Treat text prompt matching as broad vibe, not fine-grained truth.
5. Fallback: keep heuristic cue detection as an honest fallback only, never as the premium engine.

Do not replace the product core with these today:

- Essentia: powerful, but AGPL/commercial-model licensing and model licensing are a product/legal decision, not a drop-in.
- aubio: useful low-level onset/tempo library, but GPL and older release cadence make it a bad bundled desktop default.
- madmom: historically strong MIR, but old release baseline and noncommercial model/data licensing make it risky for product bundling.
- all-in-one: attractive offline structure analyzer with beats/downbeats/segments/labels, but it brings PyTorch/NATTEN-style weight and install friction. Good research/reference path, not one-click default yet.
- Raw LLM audio reasoning: not a DSP engine. Use it for narration over grounded tool results only.

## Weak Points To Fix

- Source-spawn live sidecar has now been restarted against current source and
  verified over the renderer-facing websocket. Source-backed Tauri desktop
  verification via `cargo tauri dev` is complete. Local unsigned packaged
  fresh-install verification and packaged first-run CLAP install proof are also
  complete; signed/notarized public install remains externally blocked.
- Milestone-status bookkeeping still needs a separate owner if the team wants
  `.planning/MILESTONES.md` to describe v8.2/v8.3 closure state. The current
  CLAP/Gemini/q8 drift in the living planning docs is reconciled.
- Generated UI dist was refreshed by `npm --prefix tauri/ui run build` during
  this checkpoint. Decide during commit splitting whether dist output belongs
  in the same UI commit.
- Plain Rust/Tauri dev checks no longer need a `TAURI_CONFIG` resource override:
  the missing sidecar resource globs are satisfied by tiny `.placeholder` files
  while real release sidecars remain build-matrix artifacts. Direct local
  packaging must now pass `scripts/dist/check_sidecar_bundle_ready.py`; the
  current placeholder-only repo-local bundle tree is a caught blocker, not a
  shippable package state.
- Codex is again the app default for chat/build/curate during this test/demo
  phase; one-click OSS distribution still needs a later provider/proxy decision
  because local Codex depends on `codex login` and shell gate behavior. Setup
  terminals now render cleanly in chat and build/curate instead of crashing
  the Library window path.
- The old Gemini/proxy Viber fallback is no longer a visible product path;
  live Gemini/proxy verification still belongs to the live co-host path.
- CLAP model download is productized at the CLI and basic Library UI level.
  It now has a cheap status repair signal for wrong-sized cache files, so an
  accidental fp16/q8/fp32 mismatch no longer looks ready just because filenames
  exist. CUE setup is truthfully checked from the same app surface, and the CLI
  can download a pinned operator-hosted CUE artifact. A real public/default CUE
  artifact URL, friend-machine timing proof, and friendlier setup copy remain
  open.
- Frozen sidecar builds now request the `ai-local` extra and explicitly collect
  local model runtime modules plus sqlite-vec's `vec0.*` native extension.
  Release CI builds those bundles before Tauri packaging; the current local
  source tree has a real arm64 sidecar bundle plus placeholder-only Windows and
  x86_64 macOS sentinel trees, which the release/package gates intentionally
  reject until those platform bundles are built. Local unsigned `.app`/DMG
  drag-install verification is complete for arm64; signed/notarized public
  install is still open.
- Windows release workflow now stages the current Tauri app payload instead of
  the old PyInstaller app shape. A real Windows runner / SignPath returned
  payload / Inno compile, including the `/Ssignpath` hook, still needs to be
  run before claiming Windows release closure.
- Windows release artifact naming now matches the actual Inno Setup output
  (`vibemix-installer.exe`). A real Windows runner still needs to prove the
  signed EXE launches, installs, runs the companion chain, and passes the
  fresh-machine rehearsal.
- Windows Inno output path is now wired in source/tests, but still needs a real
  Windows ISCC run to prove the macro path works exactly as expected.
- Windows Tauri app build no longer asks Tauri to bundle on Windows, but a real
  Windows runner still needs to prove `cargo tauri build --no-bundle` emits the
  expected `tauri/src-tauri/target/release/vibemix.exe` for the staging script.
- Updater signing prep now has one password-secret name across the active
  release workflow, manifest signer, pretag gate, and ship runbook:
  `TAURI_UPDATER_KEY_PASSWORD`. The old alternate name remains only in the
  release workflow's drift detector and regression assertions.
- Updater manifest signing now signs local artifact bytes instead of
  pre-upload GitHub URLs. This removes one certain release-publish failure
  mode, but a real updater rehearsal still needs to prove the served artifact
  type/install flow for each platform.
- `latest.json` no longer accepts the DMG/Inno first-install pair as updater
  artifacts. This is intentionally stricter: release-publish now blocks until
  macOS `.app.tar.gz` and Windows Tauri NSIS updater artifacts exist.
- CUE-DETR runtime still depends on optional `onnxruntime`, PyAV/numpy audio
  decode, and the ONNX file, but no longer has a hidden
  `facebook/detr-resnet-50` preprocessor download path or a
  `scipy`/`librosa`/`numba`/`transformers` runtime dependency.
- Cue labels are still coarse. Candidate timing improved before label quality did.
- CLAP text-to-audio is reliable for genre/coarse mood, not fine tags like exact substyle, scene, or "feels like" nuance.

## Unnecessary Bloat / Overengineering

- Making Codex CLI the mandatory consumer path before fallback UX is finished.
- Shipping Telegram/mobile/public discovery/Composio/web-agent surfaces before the local desktop loop is verified end to end.
- Rebuilding UI appearance again before restart, smoke, and live interaction audit.
- Pulling broad MIR frameworks into runtime when one specialized ONNX model plus local refinement solves the current job.
- Tuning heuristic thresholds as if they are the flagship cue engine.
- Asking Gemini to infer structure where local DSP/model evidence exists.
- Adding more planning docs without reconciling the old milestone docs.

## Drop-In Replacements / Small Moves

- Dedicated local-AI dependency split now exists:
  - `clap`: CLAP ONNX similarity.
  - `cue`: CUE-DETR ONNX plus audio loading/preprocessing.
  - `ai-local`: combined app/installer local-model runtime target.
  `clap`/`ai-local` currently depend on `onnxruntime` and `tokenizers`; `cue`
  depends on `onnxruntime` only. Audio decode/DSP is supplied by PyAV/FFmpeg
  and narrow numpy helpers.
- Add model manager UX for CLAP and CUE-DETR:
  - cache directory, download/progress, checksum/version, disk size, "not installed" neutral state, retry.
- Current model-manager status seam exists as `library models --json`; CLAP
  download/checksum exists as `library models --install required --json`
  (`clap` remains explicit CLAP-only). The JSON now distinguishes `installable`
  from merely missing, so CUE does not look like a broken required setup when no
  hosted artifact is configured. CUE setup can still be checked with `library
  models --install cue --json`, and that target downloads an HTTPS artifact only
  when `VIBEMIX_CUE_ONNX_URL`, `VIBEMIX_CUE_ONNX_SHA256`, and
  `VIBEMIX_CUE_ONNX_SIZE` are valid. `--install all` requires both local model
  targets. CLAP default is full-precision. fp16/q8 should be added as explicit
  installer variants only after real-library retrieval parity. Publishing a
  default CUE-DETR artifact remains the next optional-model packaging task.
- App Viber backend is now explicit:
  - desktop product path: local Codex MCP.
  - stale `VIBEMIX_LIBRARY_AGENT_BACKEND=gemini` is ignored/overridden for
    app one-shot Library commands.
  - the Library chat surface now distinguishes Codex setup failures from normal
    empty tool turns.
  - `library stats --json` now carries an offline preflight setup signal for
    obvious Codex install/login gaps. The Library window now has a dedicated
    Viber setup row for Codex login/install, hidden when ready. A full
    settings-level affordance is still future polish.
  - The Tauri sidecar env relay now includes direct/proxy mode/auth and Codex
    home (`VIBEMIX_LLM_MODE`, `GEMINI_API_KEY`, `VIBEMIX_PROXY_JWT`,
    `VIBEMIX_PROXY_BASE_URL`, `VIBEMIX_CLIENT_VERSION`, `CODEX_HOME`).
    The old Library backend selector is intentionally excluded.
- Refresh generated UI dist only during an intentional build; source now renders embedding copy from live backend info.
- Add a small cue label classifier after timing is stable. Do not block cue timing on perfect semantic labels.
- Move old milestone docs to "historical" or update them in one pass after source verification.
- Keep `detect_cues_auto()` as the public product cue API. Direct `cue_detect` use should mean fallback/test only.

## Next Shipping Order

1. Freeze the worktree and separate commits by product surface: runtime/status/TTS, prompt overlay, cue engine, CLAP, Viber chat/build, UI polish, docs.
2. Restart Vite and the Python sidecar, then verify the running app reflects current source.
3. Run focused smoke:
   - `uv run pytest tests/agent/test_tts_chain.py tests/runtime/test_ws_bus_status_tick.py tests/prompts/test_matrix.py -q`
   - `uv run pytest tests/library/test_cue_engine.py tests/library/test_cue_refine.py tests/library/test_cue_detect.py -q`
   - `cd tauri/ui && npm run check:ipc`
   - `cd tauri/ui && npx vitest run src/pill/index.test.ts src/pill/next-suggestion.test.ts tests/session/grounding-failure.spec.ts --reporter=dot`
4. Run broader release checks after separating commits:
   - `uv run pytest -q`
   - `cd tauri/ui && npm run build && npm test`
   - `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
   These now pass in-source at the 01:13 checkpoint; repeat after commit
   splitting and before packaging.
5. Publish/version a pinned default CUE-DETR ONNX artifact before promising
   one-click local cue setup to users; CLAP install is already checksum-backed.
6. Finish app Viber setup UX: Codex setup errors are now visible in chat,
   stats carries agent readiness, and the Library window has a dedicated Viber
   setup row for Codex install/login gaps. A settings-level setup affordance
   is still future polish, not the only visible dependency signal.
7. Reconcile milestone-status bookkeeping from source truth if it matters for
   the presentation cut.
8. Do a live desktop pass: permissions, status lights, pill, chat, set builder, library search, export, crash banner, reload behavior.

## Verification Already Run By Codex

Focused checks passed after recent patches:

- `uv run pytest tests/agent/test_tts_chain.py tests/runtime/test_ws_bus_status_tick.py tests/prompts/test_matrix.py tests/test_main_smoke.py::test_smoke_03_full_wiring tests/test_main_smoke.py::test_smoke_04_no_openrouter_key -q` -> 119 passed.
- `cd tauri/ui && npm run check:ipc` -> passed.
- `cd tauri/ui && npx vitest run tests/session/grounding-failure.spec.ts src/pill/index.test.ts src/pill/next-suggestion.test.ts --reporter=dot` -> 48 passed.
- `uv run pytest tests/library/test_cue_engine.py tests/library/test_cue_refine.py tests/library/test_cue_detect.py -q` -> 30 passed.
- `uv run pytest tests/library/test_stats_cli.py -q` -> 5 passed.
- `uv run pytest tests/library/test_embed.py tests/library/test_embed_clap.py tests/library/test_stats_cli.py tests/library/test_search.py tests/library/test_similar.py -q` -> 37 passed.
- `cd tauri/ui && npx vitest run src/library/api.test.ts --reporter=dot` -> 9 passed.
- `cd tauri/ui && npx vitest run src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts --reporter=dot` -> 27 passed.
- `TAURI_CONFIG='{"bundle":{"resources":["binaries/vibemix-core-aarch64-apple-darwin/**/*"]}}' cargo test --manifest-path tauri/src-tauri/Cargo.toml app_agent_backend -- --nocapture` -> 4 passed.
- `TAURI_CONFIG='{"bundle":{"resources":["binaries/vibemix-core-aarch64-apple-darwin/**/*"]}}' cargo test --manifest-path tauri/src-tauri/Cargo.toml codex_shell_gate -- --nocapture` -> 1 passed.
- `TAURI_CONFIG='{"bundle":{"resources":["binaries/vibemix-core-aarch64-apple-darwin/**/*"]}}' cargo check --manifest-path tauri/src-tauri/Cargo.toml` -> passed.
- `env -u GEMINI_API_KEY uv run python -m vibemix library stats --json` -> CLAP/512, model installed, 24 indexed.
- `env -u GEMINI_API_KEY uv run python -m vibemix library models --json` ->
  CLAP and CUE-DETR both installed on this machine.
- `env -u GEMINI_API_KEY uv run python -m vibemix library models --install all --json` ->
  CLAP files verified/skipped with SHA-256, CUE-DETR already installed, `ok: true`.
- `env -u GEMINI_API_KEY uv run python -m vibemix library models --install clap --json` ->
  `install.ok=true`, 6 CLAP files verified/skipped.
- `uv run pytest tests/library/test_models_cli.py tests/library/test_stats_cli.py -q` -> 7 passed.
- `uv run pytest tests/library/test_models_cli.py tests/library/test_stats_cli.py tests/library/test_embed_clap.py -q` -> 18 passed.
- `uv run ruff check src/vibemix/library/model_assets.py tests/library/test_models_cli.py src/vibemix/library/cue_detr.py` -> passed.
- `uv run python -m vibemix library chat ... --backend codex --json` without
  `VIBEMIX_CODEX_ALLOW_SHELL=1` -> actionably returns `codex_mcp_blocked`.
- `VIBEMIX_CODEX_ALLOW_SHELL=1 env -u GEMINI_API_KEY uv run python -m vibemix library chat ... --backend codex --json` -> `stop_reason=model_done`.
- Redirected Codex chat run proved stdout is valid JSON and diagnostics stay on stderr.
- `uv run python scripts/audit/gen_audit_md.py --check` -> passed.
- `uv run python scripts/audit/scan_opportunities.py --quiet` -> passed.
- `git diff --check` -> passed.
- `uv run pytest -q tests/library/test_models_cli.py tests/library/test_cue_engine.py tests/library/test_cue_refine.py` -> 23 passed.
- `uv run pytest -q tests/library/test_cue_engine.py tests/library/test_cue_refine.py` -> 18 passed after removing the CUE-DETR `from_pretrained` runtime lookup.
- `uv run ruff check src/vibemix/library/cue_detr.py tests/library/test_cue_engine.py` -> passed.
- `jq empty tauri/src-tauri/capabilities/default.json` -> passed after updating the library command description.
- `TAURI_CONFIG='{"bundle":{"resources":["binaries/vibemix-core-aarch64-apple-darwin/**/*"]}}' cargo test --manifest-path tauri/src-tauri/Cargo.toml model_install_target -- --nocapture` -> 1 passed.
- `TAURI_CONFIG='{"bundle":{"resources":["binaries/vibemix-core-aarch64-apple-darwin/**/*"]}}' cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds -- --nocapture` -> 22 passed.
- `uv run python -m vibemix library models --json` -> CLAP and CUE-DETR both installed on this machine.
- `cd tauri/ui && npm run build` -> passed; only known dynamic-import/chunk-size warnings.
- `uv run pytest -q tests/library/test_models_cli.py tests/library/test_stats_cli.py` -> 13 passed after full-precision CLAP installer manifest/repair-status update.
- `uv run ruff check src/vibemix/library/model_assets.py src/vibemix/library/clap_engine.py tests/library/test_models_cli.py` -> passed.
- `env -u GEMINI_API_KEY uv run python -m vibemix library models --json` -> CLAP and CUE-DETR both installed; CLAP `mismatched: []` against the full-precision manifest.
- `env -u GEMINI_API_KEY uv run python -m vibemix library models --install clap --json` -> install ok, fp32 CLAP files skipped/verified.
- `cd tauri/ui && npx vitest run src/library/api.test.ts --reporter=dot` -> 9 passed after adding model `mismatched` to the UI contract.
- `cd tauri/ui && npm run build` -> passed; same known dynamic-import/chunk-size warnings.
- `git diff --check` -> passed after the CLAP manifest/repair-status update.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` -> passed without
  `TAURI_CONFIG` after the x86_64 sidecar placeholder fix.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds -- --nocapture` -> 22 passed without `TAURI_CONFIG`.
- `uv run pytest -q tests/runtime_closeouts/test_universal2_sidecar.py` -> 8 passed.
- `git diff --check` -> passed after the Tauri resource-placeholder fix.
- Targeted `rg` for stale q8/default-Gemini/staged-CLAP/concurrent-no-touch
  patterns in `.planning/{ROADMAP,STATE,PROJECT}.md` -> only historical
  v8.1/v7/v3 text remains; living CLAP docs are reconciled.
- `git diff --check -- .planning/ROADMAP.md .planning/STATE.md .planning/PROJECT.md` -> passed after planning-doc reconciliation.
- `rg -n 'HANDOFF-cdj-whisper-v5-ui-migration|debrief-live\.png' . --glob '!/.planning/archive/**' --glob '!/.planning/research/CODEX-full-product-sweep-map.md' --glob '!/.git/**'` -> no active references after archiving the old handoff and screenshot.
- `find .planning/archive/2026-05-26-surface-clutter -maxdepth 1 -type f -print` -> manifest, moved handoff, and moved screenshot present.
- `test ! -e build` -> root ignored PyInstaller `build/` output removed.
- `git diff --check -- .planning/archive/2026-05-26-generated-output/MANIFEST.md` -> passed.
- `find .planning/eval-runs -maxdepth 1 -type f -print` -> only `.gitkeep`
  remains after archiving ignored load-test JSONs.
- `find .planning/eval-runs -maxdepth 1 -name 'loadtest_*.json' -type f | wc -l` -> 0.
- `ls -lh .planning/archive/2026-05-26-eval-run-json.zip` -> local archive
  bundle present.
- Active `.planning/notes`/`.planning/quick` stale guidance cleanup:
  `find .planning/notes .planning/quick -maxdepth 3 -type f` -> only
  `.planning/quick/20260525-dead-controls-fix/SUMMARY.md` remains; targeted `rg`
  for old no-CLAP/Gemini-only/staged/1536/legacy-budget-gate phrases across
  those active dirs -> no matches.
- `test ! -e tauri/src-tauri/target/debug/binaries` -> stale ignored debug
  sidecar payload removed; `find spikes -type d -name __pycache__ | wc -l` -> 0.
- `test ! -e dist/vibemix-core && test ! -e dist/vibemix_0.1.0-rc1_aarch64-unsigned.dmg && test ! -e dist/e2e-macbook-runs && test ! -e recordings/20260515-112139 && test -f dist/launch-runs/.gitkeep`
  -> ignored root build/release/e2e/runtime-recording payload removed while the
  tracked launch-run scaffold remains; `du -sh dist .planning/archive` ->
  `4.0K dist`, `824K .planning/archive`.
- Repo-local cache cleanup check excluding virtualenvs, Claude worktrees,
  node_modules, Tauri target, frontend dist, and `.planning/archive`:
  `find ... (__pycache__|.pytest_cache|.ruff_cache|.mypy_cache|.vite) | wc -l`
  -> 0.
- Large-file scan excluding kept environments/build caches and archive:
  `find . -maxdepth 4 ... -type f -size +20M` -> no active matches.
- `git diff --check -- .planning/archive/2026-05-26-generated-output/MANIFEST.md .planning/research/CODEX-full-product-sweep-map.md`
  -> passed after generated-output cleanup map updates.
- `uv run pytest -q tests/repo/test_live_spike_scaffold.py tests/e2e/test_phase_41_latency_stack_integration.py::test_spike_scaffold_is_not_in_runtime_path`
  -> 10 passed, confirming the remaining `spikes/` tree stays scaffold-only and
  runtime code still has no `spikes.*` imports.
- Stale product-copy sweep: targeted `rg` over active README/CONTRIBUTING,
  launch copy, library mock, deck-vision comments, dependency docs, and spike
  notes no longer finds unsafe Gemini-only/default-Gemini/1536-d/CLAP-staged
  claims in those edited surfaces.
- `uv run pytest -q tests/state/test_deck_vision.py spikes/vibe_mix_slice1/tests/test_calibration.py spikes/vibe_mix_slice3/tests/test_detect.py`
  -> 25 passed.
- `uv run ruff check src/vibemix/state/deck_vision.py tests/state/test_deck_vision.py src/vibemix/library/embed.py spikes/vibe_mix_slice1/calibration.py spikes/vibe_mix_slice1/__init__.py spikes/vibe_mix_slice3/__init__.py`
  -> passed.
- `uv run python scripts/audit/gen_audit_md.py --check` -> `docs/AUDIT.md` in
  sync with generator + `dep_ratings.yaml`.
- `git diff --check -- README.md CONTRIBUTING.md docs/internal/copy-substitutions.md scripts/dayzero/launch_copy/linkedin.txt mocks/vibemix-library-ui.html src/vibemix/state/deck_vision.py tests/state/test_deck_vision.py scripts/audit/dep_ratings.yaml docs/dep-opportunities/2026-05-scan.md eval/corpus/hard_tek/README.md src/vibemix/library/embed.py spikes/vibe_mix_slice1/__init__.py spikes/vibe_mix_slice1/calibration.py spikes/vibe_mix_slice3/__init__.py spikes/vibe-mix-prep-flow-status.md .planning/research/CODEX-full-product-sweep-map.md`
  -> passed.
- Local-AI packaging split:
  `pyproject.toml` now declares optional extras `clap`, `cue`, and
  `ai-local`; `uv lock` refreshed `uv.lock`; a tomllib probe confirmed
  `ai-local == ["onnxruntime>=1.20", "tokenizers>=0.22"]`.
- `uv run pytest -q tests/library/test_models_cli.py` -> 9 passed after adding
  the optional-extra contract test.
- `uv run ruff check tests/library/test_models_cli.py` -> passed.
- `uv lock --check` -> passed.
- `uv run python scripts/audit/gen_audit_md.py --check` -> `docs/AUDIT.md` in
  sync after the optional-extra lock refresh.
- `git diff --check -- pyproject.toml uv.lock AGENTS.md docs/library.md docs/clap-engine.md CLAUDE.md tests/library/test_models_cli.py .planning/research/CODEX-full-product-sweep-map.md`
  -> passed.
- Model install target cleanup:
  `library models --install cue --json` returns a `cue-detr` install result;
  `library models --install all --json` returns CLAP file verification plus
  `cue-detr`. On this machine both report installed and `install.ok=true`.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml model_install_target -- --nocapture`
  -> 1 passed after allowing `cue` through the Rust bridge.
- `cd tauri/ui && npx vitest run src/library/api.test.ts --reporter=dot` -> 10
  passed after adding `cue` to `LibraryModelInstallTarget` and the dev fallback.
- `cd tauri/ui && npm run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- Required-model first-run setup fix:
  `library models --install required --json` now installs only required assets
  (currently CLAP), while `all` stays strict for CLAP + optional CUE-DETR.
  Fresh Library UI setup now calls `required` instead of failing on missing
  optional CUE.
- `uv run pytest -q tests/library/test_models_cli.py` -> 17 passed.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/build.test.ts`
  -> 28 passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml model_install_target_normalizes_and_rejects_unknown`
  -> 1 passed.
- `npm --prefix tauri/ui run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- `uv run ruff check src/vibemix/library/model_assets.py tests/library/test_models_cli.py`
  -> passed.
- `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` -> passed.
- `git diff --check` -> passed.
- Repo-local cache cleanup check excluding virtualenvs, node_modules, Rust
  target, frontend dist, `.planning/archive`, and Claude worktrees -> 0 cache
  directories remain.
- Focused smoke group from Next Shipping Order:
  `uv run pytest tests/agent/test_tts_chain.py tests/runtime/test_ws_bus_status_tick.py tests/prompts/test_matrix.py -q`
  -> 118 passed.
- `uv run pytest tests/library/test_cue_engine.py tests/library/test_cue_refine.py tests/library/test_cue_detect.py -q`
  -> 31 passed.
- `npm --prefix tauri/ui run check:ipc` -> passed.
- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts tests/session/grounding-failure.spec.ts`
  -> 45 passed.
- Library Viber setup UX: the model readiness strip now stays focused on
  CLAP/CUE, while a dedicated `vmx-lib-agent-setup` row surfaces Codex
  login/install gaps from `library stats --json`.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts`
  -> 38 passed.
- `npm --prefix tauri/ui run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- `git diff --check` -> passed after the Viber setup row patch.
- Plain ruff caveat cleanup:
  `uv run ruff check src/vibemix/__main__.py src/vibemix/prompts/matrix.py`
  -> passed after mechanical `__main__.py` cleanup and a file-level
  `RUF001/RUF003` exception for intentional Turkish prompt overlay text.
- `uv run python -m py_compile src/vibemix/__main__.py src/vibemix/prompts/matrix.py`
  -> passed.
- `uv run pytest -q tests/test_main_smoke.py tests/prompts/test_matrix.py tests/library/test_models_cli.py tests/library/test_codex_curate.py`
  -> 153 passed.
- Broad source hygiene checkpoint:
  `uv run ruff check src/vibemix` -> passed after the mechanical Ruff cleanup
  and the final manual fixes (`zip(..., strict=True)`, retained async task
  handles, Windows import ordering/ClassVar, tuple/yield simplifications).
- `uv run ruff check src/vibemix tests/e2e/test_phase_41_latency_stack_integration.py tests/debrief/test_tldr_model_dispatch.py tests/debrief/test_drills_model_dispatch.py`
  -> passed.
- `uv run python -m compileall -q src/vibemix tests/e2e/test_phase_41_latency_stack_integration.py tests/debrief/test_tldr_model_dispatch.py tests/debrief/test_drills_model_dispatch.py`
  -> passed.
- `uv run pytest -q tests/bench tests/library/test_cue_engine.py tests/library/test_cue_refine.py tests/library/test_cue_detect.py tests/library/test_codex_curate.py tests/library/test_toolset.py tests/library/test_setprep_tools.py tests/library/test_next_suggestion.py tests/state/detectors/test_phrase_dsp.py`
  -> 115 passed.
- `uv run pytest -q tests/wizard tests/runtime/test_ws_bus.py tests/runtime/test_ws_bus_status_tick.py tests/runtime/test_ws_bus_snapshot.py tests/agent/test_cache_mutation_refresh.py tests/e2e/test_phase_41_latency_stack_integration.py tests/integration/test_audio_backends.py tests/state/test_evidence_registry.py tests/state/test_evidence_registry_library.py tests/e2e/test_seam_p18__p20.py`
  -> 148 passed after stale debrief/router expected-model mirrors were aligned
  to the current `gemini-3.5-flash` router truth.
- `uv run pytest -q tests/llm tests/debrief/test_tldr_model_dispatch.py tests/debrief/test_drills_model_dispatch.py tests/e2e/test_phase_41_latency_stack_integration.py`
  -> 71 passed / 1 skipped (unrecorded live TTS VCR cassette).
- `uv run pytest -q tests/test_main_smoke.py tests/library/test_models_cli.py tests/library/test_codex_curate.py tests/agent/test_tts_chain.py tests/runtime/test_ws_bus_status_tick.py tests/prompts/test_matrix.py`
  -> 177 passed.
- `npm --prefix tauri/ui run check:ipc` -> passed after IPC codegen/typecheck.
- `git diff --check` -> passed.
- Repo-local cache cleanup excluding virtualenvs, node_modules, Rust target,
  frontend dist, `.planning/archive`, and Claude worktrees -> 0 cache
  directories remain.
- Agent setup status preflight:
  `library stats --json` now emits `agent_backend`, `agent_ready`,
  `agent_status`, and `agent_hint`; the Rust `library_stats` command preserves
  those fields, and the Library titlebar labels an unready backend as setup.
- `uv run pytest -q tests/library/test_stats_cli.py` -> 7 passed.
- `uv run ruff check tests/library/test_stats_cli.py` -> passed.
- `uv run python -m py_compile src/vibemix/__main__.py` -> passed.
- `cd tauri/ui && npx vitest run src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts --reporter=dot`
  -> 33 passed.
- `cd tauri/ui && npm run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml app_agent_backend -- --nocapture`
  -> 4 passed after the stats contract carried agent setup fields.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` -> passed.
- Redirected `env -u GEMINI_API_KEY uv run python -m vibemix library stats --json`
  proved stdout remains valid JSON while the store banner stays on stderr; on
  this machine it reports `agent_backend=codex`, `agent_ready=true`, and
  `agent_status=ready`.
- `git diff --check -- src/vibemix/__main__.py tests/library/test_stats_cli.py tauri/src-tauri/src/library_cmds.rs tauri/ui/src/library/api.ts tauri/ui/src/library/api.test.ts tauri/ui/src/library/index.ts`
  -> passed.
- Agent setup env relay fix:
  `FORWARDED_ENV_KEYS` now relays `VIBEMIX_PROXY_JWT`,
  `VIBEMIX_PROXY_BASE_URL`, `VIBEMIX_LIBRARY_AGENT_BACKEND`, and `CODEX_HOME`
  in addition to the direct Gemini/OpenRouter keys, so the Python one-shot
  stats probe sees the same backend/auth setup that Rust selected.
- `uv run pytest -q tests/library/test_stats_cli.py` -> 8 passed after adding
  Gemini proxy-readiness coverage.
- `uv run ruff check tests/library/test_stats_cli.py` -> passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml forwarded_env_keys -- --nocapture`
  -> 1 passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml app_agent_backend -- --nocapture`
  -> 4 passed.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` -> passed.
- `VIBEMIX_LIBRARY_AGENT_BACKEND=gemini VIBEMIX_PROXY_JWT=test-token env -u GEMINI_API_KEY uv run python -m vibemix library stats --json`
  redirected through `json.tool` -> stdout valid JSON with `agent_backend=gemini`,
  `agent_ready=true`, `agent_status=ready`; store banner remained on stderr.
- `git diff --check -- tauri/src-tauri/src/sidecar.rs tauri/src-tauri/src/library_cmds.rs tests/library/test_stats_cli.py`
  -> passed.
- Library chat setup UX:
  `cd tauri/ui && npx vitest run src/library/build.test.ts --reporter=dot` ->
  13 passed after pinning the real `mountLibrary()` chat flow for a
  `codex_not_installed` result.
- `cd tauri/ui && npx vitest run src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts --reporter=dot`
  -> 33 passed.
- `cd tauri/ui && npm run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- `git diff --check -- tauri/ui/src/library/index.ts tauri/ui/src/library/build.test.ts`
  -> passed after the chat setup-card patch.
- Library setup UI target routing:
  `cd tauri/ui && npx vitest run src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts --reporter=dot`
  -> 32 passed after adding CUE-only setup routing coverage through the real
  `mountLibrary()` button path.
- `cd tauri/ui && npm run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- `git diff --check -- tauri/ui/src/library/index.ts tauri/ui/src/library/api.test.ts tauri/ui/src/library/build.test.ts tauri/ui/library.html`
  -> passed after the Library setup UI routing patch.
- Generated sidecar payload cleanup:
  `du -sh tauri/src-tauri/binaries` -> `12K` after replacing the reappeared
  untracked expanded arm64 PyInstaller bundle with placeholders; `find
  tauri/src-tauri/binaries -maxdepth 3 -type f` now lists only the three
  `.placeholder` files.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` -> passed with only
  the placeholder resource directories present.
- Codex set-prep exported terminal fix:
  `uv run pytest -q tests/library/test_codex_curate.py` -> 21 passed after
  pinning that `_cmd_library_build_set_codex` returns 0 and writes stdout JSON
  for `stop_reason="exported"`.
- `uv run ruff check tests/library/test_codex_curate.py` -> passed.
- `uv run python -m py_compile src/vibemix/__main__.py` -> passed.
- `git diff --check -- src/vibemix/__main__.py tests/library/test_codex_curate.py`
  -> passed.
- `uv run python -m py_compile src/vibemix/__main__.py` -> passed after the CLI
  choices/help update.
- `uv run ruff check src/vibemix/library/model_assets.py tests/library/test_models_cli.py`
  -> passed.
- `git diff --check -- src/vibemix/library/model_assets.py src/vibemix/__main__.py tauri/src-tauri/src/library_cmds.rs tauri/ui/src/library/api.ts tauri/ui/src/library/api.test.ts tests/library/test_models_cli.py docs/library.md`
  -> passed.
- `rg -n 'auto-cue-engine-HANDOFF|Status: \*\*mid-pivot\*\*|Nothing committed' . --glob '!/.planning/archive/**' --glob '!/.git/**'` -> no active stale auto-cue handoff references.
- `test -f docs/superpowers/specs/2026-05-26-auto-cue-engine-design.md && test ! -e docs/superpowers/specs/2026-05-26-auto-cue-engine-HANDOFF.md` -> clean design spec remains active, stale handoff archived.
- `rg -n 'ready to build|Engine design \(v1, pure DSP\)|librosa are NOT installed|cue_detect.py.*working v0.5' docs/superpowers/specs src/vibemix/library --glob '!/.planning/archive/**'` -> no active stale auto-cue design claims.
- `uv run ruff check src/vibemix/library/cue_types.py` -> passed after the cue seam docstring was corrected to reference `cue_engine`.
- Targeted `rg` over the active planning/spec/sweep-map surface for obsolete
  staged-contract and old design-disclaimer phrases -> no active matches.
- `git diff --check -- .planning/ROADMAP.md .planning/STATE.md .planning/research/CODEX-full-product-sweep-map.md .planning/archive/README.md docs/superpowers/specs/2026-05-26-dj-library-ingest-design.md docs/superpowers/specs/2026-05-26-auto-cue-engine-design.md src/vibemix/library/cue_types.py` -> passed after the stale planning/spec cleanup.
- Codex backend contract cleanup: exported set-prep now reports
  `stop_reason="exported"` when a Rekordbox XML path exists, matching the
  Gemini agent and frontend contract; chat prompt history now labels Viber
  turns as `Viber:` instead of `You:`.
- `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_agent.py::test_build_set_export_is_terminal tests/library/test_models_cli.py` -> 29 passed after the Codex set-prep/chat contract cleanup.
- `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py` -> passed.
- Status-tick/live-badge lane verified coherent: `ws_broadcast` emits
  `ipc.status.tick` about once per second; screen denied/unavailable is a
  status-row badge state, not a deck fault.
- `uv run pytest -q tests/runtime/test_ws_bus_status_tick.py` -> 9 passed.
- `cd tauri/ui && npx vitest run tests/session/grounding-failure.spec.ts --reporter=dot` -> 12 passed.
- Model/package CLI probes: `library models --json` reports CLAP and CUE-DETR
  installed with `mismatched: []`; `library stats --json` reports
  `embedding_backend=clap`, `embedding_dim=512`, 24 indexed, and required CLAP
  ready; Codex chat without `VIBEMIX_CODEX_ALLOW_SHELL` fails closed as
  `codex_mcp_blocked`.
- `library budget --json` now labels its monthly projection as
  `legacy_gemini_embedding_what_if` and includes
  `active_embedding_backend="clap"`, so the old €897/mo Gemini-audio what-if is
  not confused with active CLAP runtime telemetry.
- `uv run pytest -q tests/library/test_budget.py tests/library/test_stats_cli.py` -> 16 passed / 1 expected xfail.
- `uv run ruff check tests/library/test_budget.py` -> passed.
- Library UI contract pass: `src/library/build.test.ts` and
  `src/library/curate.test.ts` jsdom skeletons now include the model-install
  controls and mocked `libraryModels()` shape that production `library.html` /
  `index.ts` require.
- `cd tauri/ui && npx vitest run src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts --reporter=dot` -> 29 passed.
- `cd tauri/ui && npm run build` -> passed; only known dynamic-import and chunk-size warnings.
- Prompt/brain prose sanity cleanup: the living stack baseline and live
  docstrings now describe local CLAP ONNX/512 as the library embedding path,
  Gemini as the conversational/live/TTS brain, and the genre auto-detector as a
  realtime DSP-only loop rather than an old no-CLAP policy surface.
- `uv run pytest -q tests/prompts/test_matrix.py tests/library/test_ingest.py tests/state/test_genre_autodetect.py` -> 121 passed.
- `uv run ruff check src/vibemix/state/genre/genre_autodetect.py src/vibemix/library/embed.py tests/library/test_ingest.py` -> passed.
- `git diff --check -- .planning/PROJECT.md src/vibemix/state/genre/genre_autodetect.py src/vibemix/library/embed.py tests/library/test_ingest.py .planning/research/CODEX-full-product-sweep-map.md` -> passed.
- Targeted stale-contract `rg` for old Gemini-embedding/default and
  `EMBEDDING_DIM=1536` wording in the patched surfaces -> no matches.
- Planning brain-contract cleanup: living `.planning/{PROJECT,ROADMAP,STATE}.md`
  now state the current split explicitly: Gemini = live/TTS brain and fallback;
  local Codex = current Viber set-prep/chat default for demo/test; CLAP ONNX =
  library/search/curator embeddings. Historical v8.1 Gemini-only/no-CLAP
  language is marked historical where it remains near current roadmap text.
- Source/test prose cleanup: `library.discovery` no longer describes current
  dimensions as "1536 Gemini or 512 CLAP"; the genre auto-detect tests now scope
  the no-heavy-model rule to the realtime DSP loop; MCP/client messages say
  Gemini-based media tools instead of implying the whole app is Gemini-only.
- `uv run pytest -q tests/state/test_genre_autodetect.py tests/library/test_discovery.py` -> 51 passed.
- `uv run ruff check src/vibemix/library/discovery.py src/vibemix/library/mcp_server.py tests/state/test_genre_autodetect.py` -> passed.
- `uv run python -m py_compile src/vibemix/__main__.py` -> passed.
- Targeted stale-contract `rg` for old set-prep/Gemini-only/no-CLAP/1536-dim
  wording across planning/source/docs/tests -> no active matches for the exact
  unsafe phrases.
- App-facing Viber copy cleanup: CLI `library curate` help, Library UI loading
  comments/dev fallback copy, `.planning` agent bullets, and
  `docs/codex-agent.md` now describe "Viber agent; local Codex" instead of
  "Gemini agent". Dev fallback text also avoids the forbidden "seamless" copy
  token.
- Gemini backend module/test docstrings now label `ViberAgent` as the legacy
  Gemini harness, not the default Viber brain.
- `cd tauri/ui && npx vitest run src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts --reporter=dot` -> 29 passed after the copy cleanup.
- `uv run python -m py_compile src/vibemix/__main__.py` -> passed after CLI help
  copy update.
- Shared Viber toolset cleanup: comments now state the optional Gemini client is
  only for media/reasoning capability tools, not embeddings; `toolset.py` is
  focused-ruff-clean after removing stale BLE `noqa`s/import debt.
- `uv run ruff check src/vibemix/library/toolset.py` -> passed.
- `uv run pytest -q tests/library/test_agent.py::test_build_set_export_is_terminal tests/library/test_codex_curate.py` -> 21 passed.
- Cheap CLI probes re-run: `library stats --json` reports `clap/512`, 24 indexed;
  `library models --json` reports CLAP and CUE-DETR installed; `library budget --json`
  reports `projection_kind=legacy_gemini_embedding_what_if` and active backend
  `clap`; Codex chat without shell opt-in still returns
  `stop_reason=codex_mcp_blocked`.
- Stream split check: `library stats --json` and Codex-blocked `library chat`
  keep stdout as pure JSON; status banners go to stderr, so the Rust bridge's
  JSON parser is not fed mixed output.
- Final focused presentation sweep at this checkpoint:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_agent.py::test_build_set_export_is_terminal tests/library/test_budget.py tests/library/test_stats_cli.py tests/runtime/test_ws_bus_status_tick.py tests/state/test_genre_autodetect.py tests/library/test_discovery.py`
  -> 97 passed / 1 expected xfail.
- `cd tauri/ui && npm run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml debrief -- --nocapture` -> 9 passed after debrief moved to the shared resource/dev resolver.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml resolve_sidecar -- --nocapture` -> 5 passed.
- `uv run pytest -q tests/capabilities/test_debrief_arg_allowlist.py tests/security/test_capability_snapshot.py tests/runtime_closeouts/test_universal2_sidecar.py` -> 15 passed / 2 skipped (no built sidecars present).
- `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py` -> 15 passed.
- `uv run ruff check tests/capabilities/test_debrief_arg_allowlist.py scripts/build_sidecar.py` -> passed.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` -> passed after the debrief resolver patch.
- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_export_rekordbox.py` -> 34 passed after forwarding Rekordbox cues/beatgrid through Viber `export_set`.
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/centering.py tests/library/test_setprep_tools.py` -> passed.
- `uv run python -m py_compile src/vibemix/library/toolset.py src/vibemix/library/centering.py` -> passed.
- `uv run pytest -q tests/library/test_agent.py::test_build_set_export_is_terminal tests/library/test_codex_curate.py` -> 22 passed.
- `uv run pytest -q tests/library/test_centering.py` -> 7 passed.
- `uv run pytest -q tests/library/test_toolset.py` -> 7 passed.
- `cd tauri/ui && npx vitest run src/library/build.test.ts src/library/api.test.ts --reporter=dot`
  -> 25 passed after surfacing agent setup hints beside model readiness.
- `cd tauri/ui && npm run build` -> passed; same known dynamic-import and
  chunk-size warnings.
- `uv run pytest -q tests/library/test_next_suggestion.py` -> 10 passed after
  adding first-cue hints to the grounded pill suggestion reason.
- `uv run ruff check src/vibemix/library/next_suggestion.py tests/library/test_next_suggestion.py`
  -> passed.
- `cd tauri/ui && npx vitest run src/pill/next-suggestion.test.ts --reporter=dot`
  -> 12 passed.
- `uv run python -m py_compile src/vibemix/library/next_suggestion.py` -> passed.
- `uv run pytest -q tests/library/test_next_suggestion.py tests/library/test_setprep_tools.py tests/library/test_export_rekordbox.py`
  -> 44 passed.
- `cd tauri/ui && npx vitest run src/library/build.test.ts src/library/api.test.ts src/pill/next-suggestion.test.ts --reporter=dot`
  -> 37 passed.
- Targeted stale-contract `rg` for unsafe `Gemini agent` / `Gemini-only` /
  `No CLAP` / `EMBEDDING_DIM=1536` patterns across living docs/source found
  only historical/superseded planning text and expected migration comments.
- `uv run pytest -q tests/prompts/test_matrix.py tests/agent/test_hype_prompt_grounding.py`
  -> 99 passed after the live prompt stopped referencing the removed raw
  `phase=` field.
- `uv run python -m py_compile src/vibemix/prompts/matrix.py` -> passed.
- `uv run ruff check src/vibemix/prompts/matrix.py tests/prompts/test_matrix.py --ignore RUF001,RUF002,RUF003`
  -> passed; the ignored RUF rules are the existing intentional Turkish prompt
  overlay / multiplication-sign docstring caveat.
- `rg -n "phase=|phase=silent" src/vibemix/prompts/matrix.py` -> no matches.
- `git diff --check -- src/vibemix/prompts/matrix.py tests/prompts/test_matrix.py`
  -> passed.
- CUE hosted-artifact installer seam:
  `uv run pytest -q tests/library/test_models_cli.py` -> 15 passed after adding
  env-hosted CUE install coverage, unverified-host rejection, and env-pinned
  mismatch detection.
- `uv run ruff check src/vibemix/library/model_assets.py src/vibemix/library/cue_detr.py tests/library/test_models_cli.py`
  -> passed.
- `uv run python -m py_compile src/vibemix/library/model_assets.py src/vibemix/library/cue_detr.py`
  -> passed.
- `env VIBEMIX_CUE_ONNX_PATH=/tmp/vibemix-missing-cuedetr.onnx VIBEMIX_CUE_ONNX_URL= uv run python -m vibemix library models --install cue --json`
  -> exited nonzero with pure JSON and an actionable `VIBEMIX_CUE_ONNX_URL` /
  manual-target error.
- `env VIBEMIX_CUE_ONNX_PATH=/tmp/vibemix-missing-cuedetr.onnx VIBEMIX_CUE_ONNX_URL=https://models.example/cuedetr.onnx VIBEMIX_CUE_ONNX_SHA256= VIBEMIX_CUE_ONNX_SIZE= uv run python -m vibemix library models --install cue --json`
  -> exited nonzero with pure JSON requiring valid SHA-256 and positive size
  pins before any hosted CUE download.
- `uv run pytest -q tests/library/test_models_cli.py tests/library/test_cue_engine.py tests/library/test_cue_refine.py`
  -> 33 passed after removing the CUE module reload from the model-status test.
- `uv run ruff check tests/library/test_models_cli.py pyproject.toml src/vibemix/library/model_assets.py src/vibemix/library/cue_detr.py`
  -> passed.
- `env -u VIBEMIX_CUE_ONNX_PATH -u VIBEMIX_CUE_ONNX_URL -u VIBEMIX_CUE_ONNX_SHA256 -u VIBEMIX_CUE_ONNX_SIZE uv run python -m vibemix library models --json`
  -> pure JSON; CLAP and CUE-DETR both installed on this machine with
  `mismatched: []`.
- `git diff --check` -> passed.
- Repo-local cache cleanup check excluding virtualenvs, `node_modules`, Tauri
  `target`, frontend `dist`, `.planning/archive`, and Claude worktrees:
  `find ... (__pycache__|.pytest_cache|.ruff_cache|.mypy_cache|.vite) | wc -l`
  -> 0.
- Viber build/curate setup-terminal bridge cleanup:
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml parse_cli_json -- --nocapture`
  -> 2 passed after preserving structured nonzero agent terminal payloads.
- `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` -> passed.
- `cd tauri/ui && npx vitest run src/library/build.test.ts --reporter=dot`
  -> 15 passed after adding a Codex setup/no-set rendering regression.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds -- --nocapture`
  -> 24 passed.
- `cd tauri/ui && npx vitest run src/library/api.test.ts src/library/build.test.ts src/library/curate.test.ts --reporter=dot`
  -> 35 passed.
- `git diff --check -- tauri/src-tauri/src/library_cmds.rs tauri/ui/src/library/build.test.ts`
  -> passed.
- Final cleanup for this slice: repo-local cache check (same exclusions as
  above) -> 0; full `git diff --check` -> passed.
- Sidecar local-AI packaging cleanup:
  `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py tests/install/test_iss_companion_run.py`
  -> 25 passed after pinning `uv run --extra ai-local`, PyInstaller spec
  local-AI runtime collection, and Inno `SourceDir` override behavior.
- `uv run ruff check scripts/build_sidecar.py tests/sidecar/test_build_sidecar_rename.py tests/install/test_iss_companion_run.py`
  -> passed.
- `uv run python -m py_compile scripts/build_sidecar.py` -> passed.
- `git diff --check -- scripts/build_sidecar.py vibemix-core.macos.spec vibemix-core.windows.spec tests/sidecar/test_build_sidecar_rename.py installer/windows/vibemix-installer.iss tests/install/test_iss_companion_run.py docs/dev-loop.md installer/windows/README.md docs/signing-windows.md scripts/win/build_local.ps1`
  -> passed.
- Targeted stale packaging grep after the sidecar packaging fix: raw
  `python -m PyInstaller vibemix-core.windows.spec` / docs-level
  `dist\vibemix\vibemix.exe` guidance was removed from docs/scripts. The
  remaining release-workflow `dist/vibemix/vibemix.exe` hits recorded at that
  moment were fixed by the later Windows release-staging cleanup below.
- Final cleanup after the sidecar packaging slice: repo-local cache check
  (excluding virtualenvs, `node_modules`, Tauri target, frontend dist, archive,
  and Claude worktrees) -> 0; full `git diff --check` -> passed.
- Windows release-staging cleanup:
  `uv run pytest -q tests/install/test_windows_packaging_paths.py tests/install/test_iss_companion_run.py tests/runtime_closeouts/test_universal2_sidecar.py`
  -> 18 passed / 2 skipped after adding the `dist/windows-app` staging
  contract, Windows sidecar resource glob, and stale `dist/vibemix/vibemix.exe`
  regression guard.
- `uv run ruff check tests/install/test_windows_packaging_paths.py tests/runtime_closeouts/test_universal2_sidecar.py`
  -> passed.
- `git diff --check -- .github/workflows/release.yml tauri/src-tauri/tauri.conf.json5 tauri/src-tauri/src/sidecar.rs scripts/win/stage_app_payload.ps1 scripts/win/build_local.ps1 installer/windows/vibemix-installer.iss installer/windows/README.md docs/signing-windows.md tests/install/test_windows_packaging_paths.py tests/runtime_closeouts/test_universal2_sidecar.py tauri/src-tauri/binaries/vibemix-core-x86_64-pc-windows-msvc/.placeholder`
  -> passed.
- Targeted stale Windows packaging grep after this fix: remaining
  `dist/vibemix-*` hits in the inspected release/install surfaces are macOS
  DMG patterns plus the regression assertion that forbids the old Windows
  `dist/vibemix/vibemix.exe` path.
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/release.yml")'`
  -> release workflow parsed.
- Final cleanup after the Windows release-staging slice: repo-local cache check
  (excluding virtualenvs, `node_modules`, Tauri target, frontend dist, archive,
  and Claude worktrees) -> 0; full `git diff --check` -> passed.
- Windows SignPath/Inno hook cleanup:
  `uv run pytest -q tests/install/test_windows_packaging_paths.py tests/security/test_release_yml_signing_skips.py`
  -> 14 passed after pinning the `/Ssignpath=$signTool` registration and
  `SIGNPATH_SIGNTOOL_CMD` signing-mode gate.
- `uv run ruff check tests/install/test_windows_packaging_paths.py tests/security/test_release_yml_signing_skips.py`
  -> passed.
- `bash -n scripts/dist/pretag_check.sh` -> passed after adding the missing
  SignPath policy/signtool required-secret names.
- A direct `bash -c` probe of the multi-line `detect-signing-mode` condition
  with all booleans set to true emitted `signing_available=true`.
- Windows installer EXE artifact cleanup:
  `uv run pytest -q tests/install/test_windows_packaging_paths.py tests/security/test_release_yml_signing_skips.py tests/repo/test_readme_shape.py tests/security/test_sign_windows_ps1.py tests/security/test_verify_signed.py tests/dist/test_verify_binary.py`
  -> 100 passed after aligning workflow/docs/tests with `vibemix-installer.exe`.
- `uv run ruff check tests/install/test_windows_packaging_paths.py tests/repo/test_readme_shape.py tests/security/test_sign_windows_ps1.py tests/security/test_verify_signed.py scripts/dist/verify_binary.py scripts/dist/verify_signed.py`
  -> passed after removing small local lint debt and modernizing
  `verify_binary.Pattern` to `StrEnum`.
- `uv run python -m py_compile scripts/dist/verify_binary.py scripts/dist/verify_signed.py`
  -> passed.
- `bash -n scripts/dist/sign_manifest.sh && bash -n scripts/dist/pretag_check.sh`
  -> passed.
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/release.yml")'`
  -> release workflow parsed.
- Targeted active-surface grep for stale `vibemix-installer.msi` / Windows MSI
  naming now returns only the regression assertion in
  `tests/install/test_windows_packaging_paths.py`; historical planning/eval
  mentions were intentionally left as history.
- Final cleanup after the Windows installer EXE artifact slice: repo-local
  cache check (excluding virtualenvs, `node_modules`, Tauri target, frontend
  dist, archive, and Claude worktrees) -> 0; full `git diff --check` -> passed.
- Windows Inno output-path cleanup:
  `uv run pytest -q tests/install/test_windows_packaging_paths.py tests/install/test_iss_companion_run.py tests/security/test_release_yml_signing_skips.py`
  -> 22 passed after pinning `InstallerOutputDir` and the root
  `output/vibemix-installer.exe` workflow path.
- `uv run ruff check tests/install/test_windows_packaging_paths.py tests/install/test_iss_companion_run.py tests/security/test_release_yml_signing_skips.py`
  -> passed.
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/release.yml")'`
  -> release workflow parsed after the `InstallerOutputDir` switch.
- Windows Tauri no-bundle cleanup:
  `uv run pytest -q tests/install/test_windows_packaging_paths.py tests/install/test_iss_companion_run.py tests/security/test_release_yml_signing_skips.py`
  -> 22 passed after pinning `cargo tauri build --no-bundle` in the Windows
  workflow and local build script.
- `uv run ruff check tests/install/test_windows_packaging_paths.py tests/install/test_iss_companion_run.py tests/security/test_release_yml_signing_skips.py`
  -> passed.
- Targeted grep with PCRE2 confirmed the remaining plain `cargo tauri build`
  hits are the macOS matrix build, generic comments, or the shared
  `bundle.targets=["app","dmg"]` config; Windows build commands now use
  `--no-bundle`.
- Updater password-secret cleanup:
  `uv run pytest -q tests/repo/test_phase20_docs.py tests/tauri/test_updater_key_rotated.py tests/security/test_release_yml_signing_skips.py`
  -> 35 passed / 1 skipped after aligning `pretag_check.sh` and
  `docs/ship-runbook.md` on `TAURI_UPDATER_KEY_PASSWORD`.
- `uv run ruff check tests/repo/test_phase20_docs.py` -> passed.
- `bash -n scripts/dist/pretag_check.sh` -> passed.
- Targeted active-surface grep for stale `TAURI_UPDATER_PRIVATE_KEY_PASSWORD`
  now returns only release-workflow drift-detector comments/checks and
  regression assertions; active scripts/docs no longer require it.
- Updater manifest local-artifact signing cleanup:
  `uv run pytest -q tests/security/test_release_yml_signing_skips.py tests/repo/test_phase20_docs.py tests/tauri/test_updater_key_rotated.py`
  -> 37 passed / 1 skipped after requiring `--macos-artifact` and
  `--windows-artifact` in the release workflow and signer script.
- `uv run ruff check tests/security/test_release_yml_signing_skips.py tests/repo/test_phase20_docs.py`
  -> passed.
- `bash -n scripts/dist/sign_manifest.sh scripts/dist/pretag_check.sh`
  -> passed.
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/release.yml")'`
  -> release workflow parsed after the manifest-signer local-artifact change.
- Targeted stale grep confirmed the old "sign a URL with Tauri signer" claim
  was removed from the active signer/workflow/updater surfaces.
- Updater artifact-contract guard:
  `uv run pytest -q tests/security/test_release_yml_signing_skips.py tests/install/test_windows_packaging_paths.py tests/repo/test_phase20_docs.py tests/tauri/test_updater_key_rotated.py tests/dayzero/test_bravoh_ops_endpoint_doc.py`
  -> 49 passed / 1 skipped after requiring Tauri updater artifact names in
  `release.yml` and rejecting DMG/Inno artifacts in `sign_manifest.sh`.
- `uv run ruff check tests/security/test_release_yml_signing_skips.py tests/repo/test_phase20_docs.py tests/install/test_windows_packaging_paths.py tests/dayzero/test_bravoh_ops_endpoint_doc.py`
  -> passed.
- `bash -n scripts/dist/sign_manifest.sh scripts/dist/pretag_check.sh` -> passed.
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/release.yml")'`
  -> release workflow parsed after the updater-artifact gate.
- Negative signer probe with temp `vibemix.dmg` + `vibemix-installer.exe`
  exited `2` before signing and reported the macOS `.app.tar.gz` requirement.
- Updater artifact production wiring:
  - Added `scripts/dist/create_macos_updater_artifact.sh`, which builds a
    Tauri-compatible `.app.tar.gz` from the signed macOS `.app`, verifies the
    archive top level, and optionally writes `<artifact>.sig`.
  - `release.yml` now uploads those macOS updater archives and builds a Windows
    Tauri NSIS updater bundle with `cargo tauri build --bundles nsis --no-sign`
    while keeping DMG/Inno as first-install artifacts. Follow-up cleanup wires a
    SignPath Authenticode step over the NSIS updater installer before
    `latest.json` is generated, so the Windows updater payload now has both OS
    reputation signing and Tauri update-integrity signing in the release path.
  - Release publish now searches downloaded Actions artifacts recursively and
    stages a flat `release-artifacts/upload/` directory before the GitHub
    Release upload. This avoids missing nested artifacts after
    `actions/download-artifact` and gives both macOS DMGs arch-specific names.
  - `sign_manifest.sh` and the macOS helper now accept an intentionally empty
    `TAURI_UPDATER_KEY_PASSWORD`; the env var must exist, but `--password ""`
    is valid.
  - The release/pretag docs were aligned on the current Apple App Store Connect
    API-key secret set and removed the stale Apple-ID/app-password and
    `APPLE_DEVELOPER_ID_P12_PASSWORD` names.
  - `scripts/dist/sign_macos.sh` now materializes CI signing inputs itself:
    imports the base64 `.p12` into a temporary keychain, decodes
    `APPLE_API_KEY_P8` to a temporary `.p8`, verifies the imported identity, and
    cleans up on exit. This fixes the previous workflow/script mismatch where
    the workflow passed secrets but the script still required
    `APPLE_API_KEY_PATH`.
  - `latest.json` generation now includes all shipped updater targets:
    `darwin-aarch64`, `darwin-x86_64`, and `windows-x86_64`. The previous
    arm64-only macOS manifest would have stranded Intel macOS installs even
    though the workflow built and uploaded their updater archive.
  - Bravoh readiness docs and `scripts/release/check_bravoh_server_ready.sh`
    now probe the runtime updater endpoint shape from `tauri.conf.json5`:
    `/vibemix/updates/{target}/{arch}/{current_version}` for macOS arm64,
    macOS x86_64, and Windows x86_64. The stale `/updates/latest.json`
    readiness path was removed from active docs/scripts/tests.
- Verification for the updater-production slice:
  - `bash -n scripts/dist/create_macos_updater_artifact.sh scripts/dist/sign_manifest.sh scripts/dist/pretag_check.sh scripts/dist/sign_macos.sh`
    -> passed.
  - `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/release.yml")'`
    -> release workflow parsed.
  - Fake `.app` probe created `vibemix-0.2.3-arm64.app.tar.gz` containing
    `vibemix.app/Contents/Info.plist`.
  - `uv run pytest -q tests/security/test_release_yml_signing_skips.py tests/install/test_macos_updater_artifact.py tests/install/test_windows_packaging_paths.py tests/repo/test_phase20_docs.py tests/tauri/test_updater_key_rotated.py tests/dayzero/test_bravoh_ops_endpoint_doc.py`
    -> 53 passed / 1 skipped after the CI signing-material patch.
  - `uv run ruff check tests/security/test_release_yml_signing_skips.py tests/install/test_macos_updater_artifact.py tests/repo/test_phase20_docs.py`
    -> passed.
  - `git diff --check` -> passed.
  - Windows updater Authenticode cleanup verification:
    `uv run pytest -q tests/install/test_windows_packaging_paths.py
    tests/install/test_macos_updater_artifact.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/repo/test_phase20_docs.py` -> 33 passed;
    `uv run pytest -q tests/security/test_release_yml_signing_skips.py
    tests/security/test_p46_audit.py
    tests/security/test_verify_signed.py::test_release_yml_has_verify_signed_publish_gate
    tests/runtime_closeouts/test_universal2_sidecar.py` -> 46 passed;
    `git diff --check` passed for the touched workflow/docs/tests/map.
  - Workflow-secret inventory cleanup: `.github/workflows/README.md` now matches
    the current 16 configured release secrets and includes the missing
    `SIGNPATH_SIGNTOOL_CMD` row. Verification:
    `uv run pytest -q tests/repo/test_phase20_docs.py
    tests/install/test_windows_packaging_paths.py` -> 29 passed; targeted `rg`
    found no remaining `14-secret inventory` wording; `git diff --check`
    passed for the README/test/map slice.
  - Legacy Gemini embedding cache-tool cleanup: `scripts/library/migrate_embeddings_2.py`
    and `scripts/library/__init__.py` no longer describe a default
    lazy-on-first-launch Gemini re-embed UX. They now state the current product
    path is local CLAP ONNX/512 and the helper only audits or clears historical
    Gemini cache rows. Verification: targeted `rg` found no remaining
    `lazy on first launch` / `pre-warm` / `trigger a re-embed` wording in the
    helper/tests; `uv run ruff check scripts/library/migrate_embeddings_2.py
    scripts/library/__init__.py tests/library/test_migrate_embeddings_2.py`
    -> pass; `uv run pytest -q tests/library/test_migrate_embeddings_2.py`
    -> 14 passed; `git diff --check` -> pass.
  - Re-ran the same focused pytest/ruff/YAML/shell gates after the recursive
    artifact-discovery + flat-upload staging patch and again after the macOS
    CI signing-material patch; they remained green.
  - Rechecked Tauri plugin source locally: static updater manifests search
    `{os}-{arch}-{installer}` then `{os}-{arch}`; macOS x86_64 therefore needs
    `darwin-x86_64`, not just `darwin-aarch64`.
  - `uv run pytest -q tests/security/test_release_yml_signing_skips.py tests/dayzero/test_bravoh_ops_endpoint_doc.py tests/install/test_macos_updater_artifact.py tests/install/test_windows_packaging_paths.py tests/repo/test_phase20_docs.py tests/tauri/test_updater_key_rotated.py`
    -> 54 passed / 1 skipped after adding a fake-`npx` execution test proving
    `sign_manifest.sh` writes all three platform entries.
  - `uv run ruff check tests/security/test_release_yml_signing_skips.py tests/dayzero/test_bravoh_ops_endpoint_doc.py tests/install/test_macos_updater_artifact.py tests/repo/test_phase20_docs.py`
    -> passed after the three-target manifest patch.
  - `uv run pytest -q tests/release/test_check_bravoh_server_ready.py tests/dayzero/test_bravoh_ops_endpoint_doc.py tests/security/test_release_yml_signing_skips.py tests/install/test_macos_updater_artifact.py tests/install/test_windows_packaging_paths.py tests/repo/test_phase20_docs.py tests/tauri/test_updater_key_rotated.py`
    -> 66 passed / 1 skipped after aligning Bravoh readiness probes with the
    runtime updater endpoint contract.
  - `uv run ruff check tests/release/test_check_bravoh_server_ready.py tests/dayzero/test_bravoh_ops_endpoint_doc.py tests/security/test_release_yml_signing_skips.py`
    -> passed.
  - `bash -n scripts/release/check_bravoh_server_ready.sh scripts/launch/cut_release.sh scripts/dist/sign_manifest.sh scripts/dist/sign_macos.sh scripts/dist/create_macos_updater_artifact.sh scripts/dist/pretag_check.sh`
    -> passed.
  - Targeted grep over docs/scripts/tests/workflow/Tauri config found no active
    `/vibemix/updates/latest.json`, stale "3/3 endpoints", or `latest_status`
    readiness-contract references.
  - Repo-local cache cleanup after the test run found and removed pytest/ruff
    and Python bytecode caches outside the excluded virtualenv, node_modules,
    Tauri target, frontend dist, archive, and Claude worktree paths; follow-up
    cache scan returned 0.
- Verification for the 01:13 full-suite repair slice:
  - Initial `uv run pytest -q` intentionally found the remaining blocker
    buckets: stale 1536-d parity fixtures against current 512-d CLAP, mascot
    GLB bundle over the size cap, `cut_release.sh --dry-run` requiring deleted
    release artifacts, a default-suite network README badge check, and one
    public orphan helper.
  - Fixed those buckets by regenerating 512-d parity fixtures, archiving
    untracked mascot character variants, making release dry-run artifact gaps
    nonfatal only under `--dry-run`, default-deselecting `network` tests, and
    privatizing the CLAP model-dir helper.
  - `uv run pytest -q tests/library/test_embeddings_parity.py tests/library/test_store_parity.py tests/mascot/test_bundle_size_cap.py tests/repo/test_mascot_glb_size_gate.py tests/scripts/test_glb_optimize.py tests/repo/test_cut_release_dry_run.py tests/repo/test_github_presence.py tests/scripts/test_orphan_inventory.py`
    -> 54 passed / 10 deselected.
  - `bash scripts/check_mascot_glb_size.sh` -> mascot active bundle `22.64 MB /
    25.00 MB`.
  - `uv run python scripts/glb_optimize.py --check tauri/ui/assets/mascot` ->
    49 files, total `22.64 MB / 25.00 MB`, largest animation `179.9 KB`.
  - `uv run pytest -q` -> 4904 passed / 27 skipped / 12 deselected / 1 xfailed
    / 4 xpassed / 13 warnings.
  - `npm --prefix tauri/ui run build` -> passed; known Vite dynamic-import and
    chunk-size warnings remain.
  - `npm --prefix tauri/ui test` -> 92 files passed / 901 tests passed after
    aligning the library state-machine test with the chat-first UI.
  - `npm --prefix tauri/ui run check:ipc` -> passed and regenerated the IPC
    TypeScript/validator outputs.
  - `cargo check --manifest-path tauri/src-tauri/Cargo.toml` -> passed.
  - `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` -> passed.
  - `uv run ruff check src/vibemix ...` plus touched test/script surfaces ->
    passed.
  - `bash -n scripts/launch/cut_release.sh scripts/check_mascot_glb_size.sh scripts/mascot/check_bundle_size.sh`
    -> passed.
  - `git diff --check` -> passed.
  - Repo-local cache cleanup excluding virtualenvs, `node_modules`, Tauri
    target, frontend dist, `.planning/archive`, and Claude worktrees -> 0 cache
    directories remain.
- Verification for the 01:25 live-source / Viber bridge slice:
  - Stopped the stale May 26 Python sidecar that owned `127.0.0.1:8765` after
    graceful `TERM`/`INT` did not exit it, then launched
    `./scripts/dev/run_sidecar_from_source.sh` from the current checkout.
  - Source sidecar booted from `.env`, registered 1547 library tracks for
    citations, opened the CLAP/sqlite-vec store, armed grounding and pill
    next-suggestion, and bound `ws://127.0.0.1:8765`.
  - Websocket receive smoke over 4 seconds saw 110 flat mascot frames,
    54 `ipc.session.snapshot` frames, and 4 `ipc.status.tick` frames.
  - Inbound websocket smoke covered `ipc.settings.get`, `ipc.session.mute`,
    and `ipc.status.recheck`. The first recheck exposed a live-path bug:
    manual recheck painted the app as `livekit=connecting` / `gemini=down`
    even while the periodic live tick was healthy.
  - Fixed that bug by wiring live refs (`levels`, `playback_queue`,
    `controller_state`, `screen_available`) into the live `SessionLoop`
    handler bag and making status recheck mirror attached-live status instead
    of standalone `--session` defaults.
  - Restarted the source sidecar after the patch. Periodic and manual recheck
    status now both returned `livekit=ok`, `gemini=ok`, `screen=unavailable`;
    settings and mute acknowledgements still returned over the same socket.
  - `uv run python -m vibemix library stats --json` -> CLAP/512,
    `agent_backend=codex`, `agent_ready=true`, sqlite-vec reachable.
  - `uv run python -m vibemix library models --json` -> CLAP and CUE-DETR both
    installed on this machine.
  - `VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat ... --backend codex --json`
    -> exit 0, valid JSON, `stop_reason=model_done`, one `search_vibe` tool
    trace.
  - `VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library build-set ... --backend codex --json`
    -> exit 0 and `stop_reason=exported`; separated stdout/stderr proof showed
    stdout is valid JSON and the human `-> set ... exported` trace stays on
    stderr for the Rust bridge.
  - `npm --prefix tauri/ui run dev -- --host 127.0.0.1 --port 1420` plus a
    Playwright Chromium smoke opened `library.html`, switched to Viber chat,
    rendered the dev-fallback reply/tool trace, showed
    `Viber codex / CLAP ready / 512d / sqlite-vec`, and reported no page errors.
  - `uv run pytest -q tests/test_main_smoke.py tests/runtime/test_session_loop.py tests/runtime/test_ws_bus_status_tick.py`
    -> 53 passed.
  - `uv run ruff check src/vibemix/__main__.py src/vibemix/runtime/session_loop.py tests/runtime/test_session_loop.py`
    -> passed.
  - `uv run python -m compileall -q src/vibemix/__main__.py src/vibemix/runtime/session_loop.py tests/runtime/test_session_loop.py`
    -> passed.
  - Vite and source-sidecar verification processes were stopped; no listener
    remained on `8765` or `1420`.
- Verification for the 01:47 Tauri desktop-dev slice:
  - Initial `cargo tauri dev` exposed a dev-command working-directory bug:
    Tauri executes `beforeDevCommand` from `tauri/`, so bare `npm run dev`
    failed.
  - `tauri/src-tauri/tauri.conf.json5` now uses
    `npm --prefix ui run dev`, and `tests/repo/test_tauri_dev_command.py`
    pins that contract.
  - `cargo tauri dev` then launched Vite on `localhost:1420`, the Rust desktop
    app, and a source sidecar on `127.0.0.1:8765`. Renderer-facing websocket
    smoke saw flat/snapshot/status frames, settings, and manual recheck.
  - Renderer screenshot by PID showed the current Deck Speaks surface and no
    false Gemini fault. The pre-existing installed `/Applications/vibemix.app`
    process was left untouched and is not proof of the current package.
  - Focused gates after the desktop patch:
    `uv run pytest -q tests/repo/test_tauri_dev_command.py tests/runtime/test_session_loop.py tests/runtime/test_ws_bus_status_tick.py tests/test_main_smoke.py`
    -> 54 passed; focused runtime/main ruff passed after removing a duplicate
    local `Path` import; `cargo check --manifest-path
    tauri/src-tauri/Cargo.toml` -> passed.
  - Codex-owned Tauri dev, Vite, source sidecar, and inactive verification
    recording dirs were stopped/cleaned; the installed app's active recording
    dir remained untouched.
- Verification for the 01:53 packaged sqlite-vec slice:
  - Pre-existing installed app logs showed bundled sidecar fallback from
    sqlite-vec to `NumpyStore` because `_internal/sqlite_vec/vec0.dylib` was
    missing. The current source package has `sqlite_vec/vec0.dylib` and
    `sqlite_vec.loadable_path()` loads that runtime extension by package path.
  - `vibemix-core.macos.spec` and `vibemix-core.windows.spec` now collect
    `sqlite_vec` submodules and `collect_dynamic_libs("sqlite_vec")`, with a
    `collect_data_files("sqlite_vec", includes=["vec0.*"])` fallback that
    dedupes sources already collected as binaries.
  - `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py`
    -> 20 passed.
  - `uv run ruff check tests/sidecar/test_build_sidecar_rename.py`
    -> passed.
  - `uv run python -m py_compile vibemix-core.macos.spec vibemix-core.windows.spec`
    -> passed.
  - Repo-local pytest/ruff/bytecode caches were removed again outside the
    excluded virtualenv, node_modules, Tauri target, frontend dist, archive,
    and Claude worktree paths; follow-up cache scan returned 0.
- Verification for the 01:58 CLAP-only recall embedding slice:
  - Found an active startup leak: live boot constructed
    `LibraryEmbedder(genai_client)` for `MemoryRecall` even when
    `VIBEMIX_RECALL_ENABLED` was default-off. That could run the legacy Gemini
    embedding probe during normal startup.
  - `src/vibemix/__main__.py` now keeps recall fully idle unless explicitly
    enabled; the enabled path builds its embedder through `build_embedder()`,
    so recall uses local CLAP like search/similarity/grounding.
  - `src/vibemix/memory/retrieval.py` and `src/vibemix/memory/store.py` no
    longer import/re-export the legacy `LibraryEmbedder`; they describe the
    injected local embedder contract instead.
  - `tests/test_main_smoke.py::test_smoke_03_full_wiring` now asserts
    default-off recall passes `recall=None`, `recall_enabled=False`, and makes
    zero `genai_client.models.embed_content` calls.
  - `rg -n "LibraryEmbedder\\(" src/vibemix --glob '!**/library/embed.py' --glob '!*.pyc'`
    -> no direct production construction outside the legacy module.
  - `uv run pytest -q tests/test_main_smoke.py::test_smoke_03_full_wiring tests/library/test_embed_clap.py tests/memory/test_retrieval.py tests/memory/test_store.py`
    -> 24 passed.
  - `uv run ruff check src/vibemix/__main__.py src/vibemix/memory/retrieval.py src/vibemix/memory/store.py tests/test_main_smoke.py`
    -> passed.
  - `uv run python -m compileall -q src/vibemix/__main__.py src/vibemix/memory/retrieval.py src/vibemix/memory/store.py tests/test_main_smoke.py`
    -> passed.
  - Repo-local pytest/ruff/bytecode caches were removed again outside the
    excluded virtualenv, node_modules, Tauri target, frontend dist, archive,
    and Claude worktree paths; follow-up cache scan returned 0.
- Verification for the 02:00 CLAP memory-drift safety slice:
  - `MemoryRecall.on_event()` now catches store query failures (including stale
    pre-CLAP vector dimensionality) and returns/latches `[]` for that dispatch
    instead of raising through a live reaction turn.
  - Memory docs/comments now describe active-dimension/local-CLAP behavior
    instead of stale 768-d/FLEX wording.
  - Added `tests/memory/test_retrieval.py::test_store_query_failure_latches_nothing`
    to pin "broken memory backend -> no recall this turn".
  - `uv run pytest -q tests/memory/test_retrieval.py tests/memory/test_store.py`
    -> 17 passed.
  - `uv run ruff check src/vibemix/memory/retrieval.py src/vibemix/memory/store.py tests/memory/test_retrieval.py tests/memory/test_store.py`
    -> passed.
  - `uv run python -m compileall -q src/vibemix/memory/retrieval.py src/vibemix/memory/store.py tests/memory/test_retrieval.py tests/memory/test_store.py`
    -> passed.
  - Repo-local pytest/ruff/bytecode caches were removed again outside the
    excluded virtualenv, node_modules, Tauri target, frontend dist, archive,
    and Claude worktree paths; follow-up cache scan returned 0.
- Verification for the 02:56 frozen macOS sidecar/local-AI packaging slice:
  - Built a real Apple Silicon PyInstaller sidecar with
    `uv run --extra ai-local python scripts/build_sidecar.py --spec vibemix-core.macos.spec`.
    The build installed
    `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin`
    and the AIza scan passed (`720` files scanned after the current debloat).
  - The bundle now contains `_internal/sqlite_vec/vec0.dylib`; frozen
    `library stats --json` reports `backend=sqlite-vec`,
    `embedding_backend=clap`, `embedding_dim=512`,
    `agent_backend=codex`, and `agent_ready=true`.
  - Frozen `library models --json` reports CLAP installed from
    `~/.cache/vibemix/clap-onnx` and CUE-DETR installed from
    `~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx`.
  - Frozen `library search "dark peak-time techno" --k 1` succeeded, proving
    the trimmed bundle still loads the local CLAP text path
    (`transformers.models.roberta.tokenization_roberta` + ONNX runtime).
  - Frozen `library embed-folder /tmp/vibemix-frozen-cue-smoke/audio --strategy cue_anchored --json`
    ran under isolated `HOME=/tmp/vibemix-frozen-cue-smoke/home` with explicit
    CLAP/CUE env paths and embedded one tiny WAV with `failed=0`, proving the
    cue-anchored CLAP ingest path survived packaging.
  - First frozen `--version` immediately after reinstall took `44.66s`, then
    warm single probes returned normally: `--version` in `1.85s`, CLAP text
    search in `2.32s`, and `library stats --json` in `1.81s`. Do not use the
    first post-install launch or parallel frozen probes as the steady-state
    startup baseline.
  - Bundle size before the transformer/hiddenimport trim was about `540M` in
    `tauri/src-tauri/binaries`; after the targeted Transformers trim it was
    `492M`, after removing the librosa/numba dependency family it was `354M`,
    after replacing scipy it was `308M`, after narrowing Pillow plus excluding
    Hugging Face Xet it was `288M`, after preserving PyInstaller's native
    library symlinks during install it was `247M`, and after excluding unused
    LiveKit demo `.ogg`/Jupyter resources it was `244M`. After replacing the
    remaining Transformers runtime helpers with local numpy preprocessing plus
    direct `tokenizers`, the sidecar is `231M`. Root PyInstaller outputs now
    measure `dist/vibemix-core=231M` and `build/vibemix-core.macos=86M` before
    cleanup.
  - The frozen bundle and refreshed `uv.lock` contain no `scipy`, `librosa`,
    `numba`, `llvmlite`, `sklearn`, `soundfile`, `soxr`, or `transformers`
    packages. The frozen bundle also excludes `hf_xet`; CLAP first-run install uses
    `model_assets.py` direct pinned HTTPS downloads rather than
    Hugging Face Hub/Xet APIs.
    Remaining top package mass is `onnxruntime=61M`, `av=44M`, `livekit=20M`,
    `grpc=18M`, `libpython3.12=17M`, `cryptography=11M`,
    `tokenizers=7.9M`, `numpy=6.6M`, and `PIL=4.8M`.
  - Pillow broad hidden-import collection was narrowed to the runtime image
    core plus JPEG/PNG plugins. Frozen `PIL` dropped from `11M` to `4.8M`;
    screen capture still has source-level JPEG coverage and frozen CUE ingest
    still exercises the DETR image processor path.
  - Focused source/spec gates:
    `uv run pytest -q tests/audio/test_resample.py tests/audio/test_mic_audio_buf.py::test_t2_callback_resamples_48k_to_16k tests/library/test_audio_decode.py tests/library/test_cue_engine.py::test_detr_preprocess_is_local_config tests/library/test_cue_engine.py::test_producer_unavailable_when_model_missing tests/library/test_cue_refine.py tests/state/detectors/test_phrase_dsp.py tests/test_audio_macos.py::test_open_voice_output_resamples_instead_of_raising tests/sidecar/test_build_sidecar_rename.py`
    -> 50 passed; focused ruff passed; spec/source `py_compile` passed.
  - Follow-up gates after lock/doc refresh:
    `uv lock --check` passed; `uv run python scripts/audit/gen_audit_md.py --check`
    passed; `uv run pytest -q tests/test_main_smoke.py::test_smoke_03_full_wiring tests/test_main_smoke.py::test_smoke_04_no_openrouter_key tests/audio/test_resample.py tests/library/test_audio_decode.py`
    -> 8 passed; source `library stats --json` still reports sqlite-vec,
    CLAP/512, and Codex ready.
  - Follow-up after the Pillow/Xet trim:
    `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py tests/test_screen_macos.py tests/test_screen_windows.py tests/library/test_cue_engine.py::test_detr_preprocess_is_local_config tests/library/test_audio_decode.py`
    -> 70 passed; focused spec ruff and `py_compile` passed. Frozen
    `library models --install required --json` verified the existing CLAP cache
    and returned `install.ok=true`.
  - Follow-up after the PyInstaller symlink install trim:
    `scripts/build_sidecar.py` now calls `shutil.copytree(..., symlinks=True)`
    so PyInstaller's top-level FFmpeg symlinks are not dereferenced into
    duplicate files under `tauri/src-tauri/binaries`. A failed spec-level prune
    attempt proved the nested `av/.dylibs` files are the real targets of those
    symlinks; the correct fix is preserving links, not deleting PyAV's wheel
    library directory.
  - Symlink-trim gates: `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py`
    -> 27 passed; focused ruff and `py_compile` passed. Rebuilt the frozen
    macOS sidecar with `uv run --extra ai-local python scripts/build_sidecar.py
    --spec vibemix-core.macos.spec`; AIza scan passed over 720 files. Frozen
    `--version`, `library stats --json`, and `library search "dark peak-time
    techno" --k 1` passed under isolated `HOME`. Frozen `library embed-folder`
    over `tests/audio/fixtures/test_lookahead_track.mp3` with
    `VIBEMIX_CLAP_ONNX_DIR=/Users/ozai/.cache/vibemix/clap-onnx` embedded one
    track with `failed=0`, then frozen `library search "test track" --k 1`
    returned that indexed track.
  - LiveKit demo-resource trim: the macOS PyInstaller spec still collects
    `collect_dynamic_libs("livekit")` and keeps `livekit/rtc/resources/
    liblivekit_ffi.dylib`, but excludes unused package `.ogg` background audio
    clips and the `jupyter-html` demo asset from `collect_data_files`. Focused
    `tests/sidecar/test_build_sidecar_rename.py` is now 28 passed; focused
    ruff and `py_compile` passed. Rebuilt the frozen sidecar again; AIza scan
    still passed over 720 files. Frozen `--version`, `library stats --json`,
    `library search "dark peak-time techno" --k 1`, frozen `library
    embed-folder` over `tests/audio/fixtures/test_lookahead_track.mp3`, and
    frozen `library search "test track" --k 1` all passed after this trim.
    Root `dist/`, root `build/`, and `/tmp` smoke dirs were removed after
    verification; the installed Tauri sidecar bundle remains at `244M`.
  - Packaging env relay fix: `tauri/src-tauri/src/sidecar.rs`
    `FORWARDED_ENV_KEYS` now includes `VIBEMIX_LLM_MODE` and
    `VIBEMIX_CLIENT_VERSION`, closing the packaged-app path where a parent
    launched for proxy mode could still spawn Python in default direct mode and
    hit exit code 4 (`GEMINI_API_KEY` missing). `library_cmds.rs` shares the
    same relay, so library stats/chat/build/model commands see the same
    mode/auth setup as the long-lived sidecar.
  - Env-relay gates: `cargo test --manifest-path tauri/src-tauri/Cargo.toml
    sidecar -- --nocapture` -> 16 passed; `cargo test --manifest-path
    tauri/src-tauri/Cargo.toml library_cmds -- --nocapture` -> 24 passed;
    `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` passed.
  - Packaged `.app` symlink repair: `cargo tauri build --bundles app --no-sign
    --ci` succeeded, but Tauri flattened the PyInstaller sidecar's top-level
    `av/.dylibs`/`PIL/.dylibs` symlinks inside
    `Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin`, inflating
    the packaged sidecar from `244M` source size to `286M` and the app to
    `315M`. `scripts/dist/repair_macos_app_sidecar_symlinks.py` now restores
    byte-identical flattened dylibs to relative symlinks, and both
    `.github/workflows/release.yml` and `scripts/dist/sign_macos.sh` run it
    before signing/updater packaging. Applied to the built app, it restored
    36 links with no mismatches; app size dropped to `274M` and packaged
    sidecar size returned to `244M`.
  - Packaged-app repair gates: `uv run pytest -q
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/security/test_release_yml_signing_skips.py` -> 18 passed; `uv run
    ruff check scripts/dist/repair_macos_app_sidecar_symlinks.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/security/test_release_yml_signing_skips.py` passed; `bash -n
    scripts/dist/sign_macos.sh`, `python3 -m py_compile
    scripts/dist/repair_macos_app_sidecar_symlinks.py`, and `git diff --check`
    on the touched files passed. The repaired packaged sidecar launched
    (`--version`), reported `library stats --json`, embedded the MP3 fixture
    with CLAP ONNX (`embedded=1`, `failed=0`), and returned it from
    `library search "test track" --k 1`.
  - Transformers-free local model path: `clap_engine.py` now uses the
    `tokenizers` Rust tokenizer directly and local `audio_features.py` Slaney
    mel/STFT helpers; `cue_detr.py` now uses local numpy DETR
    rescale/normalize/pad preprocessing. `pyproject.toml` `clap`/`ai-local`
    extras depend on `tokenizers>=0.22`, `cue` depends only on `onnxruntime`,
    and both PyInstaller specs exclude `transformers` outright. `uv.lock` no
    longer contains a `transformers` package entry.
  - Transformers-free gates: `uv run pytest -q
    tests/library/test_audio_decode.py tests/library/test_cue_engine.py
    tests/library/test_embed_clap.py tests/library/test_models_cli.py
    tests/sidecar/test_build_sidecar_rename.py` -> 72 passed; focused `ruff`,
    `uv lock --check`, `bash -n scripts/dist/sign_macos.sh`, `py_compile`, and
    `git diff --check` passed. Rebuilt the frozen sidecar with
    `uv run --extra ai-local python scripts/build_sidecar.py --spec
    vibemix-core.macos.spec`; AIza scan passed over 377 files. Frozen and
    packaged sidecars both passed `--version`, `library stats --json`, CLAP
    `embed-folder` on `tests/audio/fixtures/test_lookahead_track.mp3`
    (`embedded=1`, `failed=0`), and `library search "test track" --k 1`.
    Rebuilt `vibemix.app` with `cargo tauri build --bundles app --no-sign
    --ci`; before symlink repair it measured `303M` with a `273M` sidecar, and
    after `repair_macos_app_sidecar_symlinks.py` it measured `261M` with a
    `231M` sidecar and 36 restored symlinks. Both the installed sidecar and the
    packaged app sidecar have zero `transformers`/`torch`/`sentencepiece` paths.
  - Cohost-provider lazy-import cleanup: `vibemix.agent.__init__` now exposes
    cohost factories via lazy `__getattr__`, and `vibemix.__main__` resolves
    LiveKit session/LLM/TTS/proxy helpers only inside the live-session path.
    This keeps `vibemix library ...`, `vibemix --version`, and model setup
    imports from loading `livekit.plugins.*`, `google.cloud.*`, or `grpc`.
    It is a modularity/startup fix, not a bundle-size fix yet: the monolithic
    sidecar still intentionally bundles the cohost stack.
  - Lazy-import gates: subprocess import of `vibemix.__main__` reported no
    `livekit.plugins` / `google.cloud` / `grpc` modules in `sys.modules`.
    `uv run pytest -q tests/test_main_smoke.py tests/test_phase05_verification.py
    tests/agent/test_config.py tests/agent/test_tts_chain.py
    tests/agent/test_proxy_client.py` -> 55 passed, 1 skipped; focused
    `ruff` and `py_compile` passed. Source `python -m vibemix --version` and
    `python -m vibemix library stats --json` both returned in ~0.95s on this
    machine. Rebuilt the frozen sidecar again; AIza scan still passed over
    377 files. Frozen warm `--version` runs were ~1.0-1.1s after the first
    post-rebuild cold launch, and frozen/package sidecars both passed
    `--version`, `library stats --json`, CLAP `embed-folder` on the MP3
    fixture, and `library search "test track" --k 1`. Rebuilt unsigned
    `vibemix.app`; after symlink repair it remains `261M` with a `231M`
    sidecar and 36 restored symlinks.
  - Local library/Gemini SDK import cleanup: `vibemix.library.__init__` and
    `vibemix.llm.__init__` are now lazy export barrels, `model_router` stores
    route tiers as lightweight names until a real Gemini tier object is needed,
    and `library.embed` imports `google.genai.types` only inside the legacy
    Gemini embedder calls. `__main__` now lazy-loads `google.genai` and
    `GeminiContextCache` only on live/Gemini paths. Import smokes now show
    `vibemix.__main__`, `vibemix.library`, `vibemix.llm.model_router`,
    `vibemix.library.embed`, `vibemix.library.toolset`, and
    `vibemix.library.mcp_server` all load without `google.genai`,
    `livekit.plugins.*`, `google.cloud.*`, or `grpc`. Source `--version`,
    `library stats --json`, and CLAP `library search "test track" --k 1`
    still pass; focused gates were `tests/library/test_toolset.py`,
    `tests/llm/test_model_router.py`, `tests/agent/test_config.py`,
    `tests/library/test_embed_router_dispatch.py`, and
    `tests/library/test_grounding_router_dispatch.py`.
  - Slim LiveKit Google bundle cleanup: `vibemix.agent.llm_factory` and
    `tts_chain` now load only LiveKit's Gemini LLM and native Gemini TTS leaves
    through `vibemix.agent._livekit_google_slim`, avoiding the
    `livekit.plugins.google.__init__` import path that eagerly imports Google
    Cloud STT/TTS and grpc. Both PyInstaller specs now stop broad-collecting
    `livekit.plugins.google` / `google.cloud`, add exact Gemini leaf hidden
    imports, and exclude `livekit.plugins.google.{stt,tts,realtime}`,
    `google.cloud.*`, `grpc`, LiveKit dev CLI/Jupyter leaves, `jsonschema.cli`,
    and unusable OTLP-over-grpc exporter leaves.
  - Slim LiveKit Google gates: subprocess probes show `llm_factory`,
    `tts_chain`, `build_llm("dummy-key")`, and
    `build_tts_chain(gemini_api_key="dummy-key")` load without `google.cloud`
    or `grpc`. Focused tests passed:
    `uv run pytest -q tests/agent/test_livekit_google_slim.py
    tests/agent/test_llm_factory.py tests/agent/test_tts_chain.py
    tests/llm/test_thinking_gate.py::test_llm_factory_passes_with_default_config
    tests/llm/test_thinking_gate.py::test_llm_factory_raises_on_bad_thinking_override
    tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_use_slim_livekit_google_collection`
    -> 32 passed. Focused `ruff` and `py_compile` passed. A real frozen
    Apple Silicon sidecar build with `uv run --extra ai-local pyinstaller
    vibemix-core.macos.spec --clean --noconfirm` succeeded; the resulting
    `dist/vibemix-core` measured `212M`, launched `--version`, returned
    `library stats --json`, and passed `library search "test track" --k 1`.
    `find dist/vibemix-core/_internal` found no `google/cloud`,
    `livekit/plugins/google/{stt,tts,realtime}`, or grpc native-library paths,
    and `PYZ-00.toc` no longer contains `livekit.agents.cli`,
    `jsonschema.cli`, or OTLP grpc exporter modules.
    The generated `dist/vibemix-core` and `build/vibemix-core.macos` outputs
    were removed after verification.
  - Dev bench harness product-bundle trim: `vibemix bench` remains available
    in source/dev runs, but frozen sidecars now treat it as a source-only
    dev/eval command and return a clear exit code `2` message instead of
    bundling the harness. Both PyInstaller specs exclude `vibemix.bench.*` in
    the runtime-submodule filter and analysis excludes.
  - Bench trim gates: source bench tests still passed (`tests/bench/test_assemble.py`,
    `tests/bench/test_eval.py`, `tests/bench/test_review.py`,
    `tests/bench/test_run_fake.py`, `tests/bench/test_roundtrip.py` plus the
    frozen-bench guard/spec tests -> 25 passed). Focused `ruff`,
    `py_compile`, and `git diff --check` passed. A real macOS frozen sidecar
    build still measured `212M`, launched `--version`, returned
    `library stats --json`, passed `library search "test track" --k 1`, and
    `vibemix-core bench run --study no-audio` returned `rc=2` with the
    source-only message. `PYZ-00.toc` no longer contains `vibemix.bench`.
  - Optional Telegram dependency trim: `python-telegram-bot` moved out of
    default runtime dependencies into the `telegram` optional extra. The source
    `library telegram` command remains available via
    `uv run --extra telegram python -m vibemix library telegram`, and missing
    optional dependency now returns an actionable JSON error instead of a raw
    import traceback. Both PyInstaller specs explicitly exclude `telegram` /
    `telegram.ext`.
  - Telegram trim gates: `uv lock --check`, focused `ruff`, `py_compile`, and
    `tests/library/test_telegram_bridge.py
    tests/library/test_curate_unify.py::test_existing_surfaces_still_import
    tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_exclude_dev_cli_and_otlp_grpc`
    passed. A real macOS frozen sidecar build measured `211M`, launched
    `--version`, returned `library stats --json`, passed
    `library search "test track" --k 1`, and `library telegram` returned
    `rc=1` with the optional-extra JSON error. Bundle graph search found only
    expected exclusion warnings for `telegram` / `telegram.ext`, not bundled
    Telegram package paths.
  - ONNX Runtime helper trim: both PyInstaller specs now exclude unused
    ONNX Runtime backend/dataset/tool/conversion helper modules
    (`onnxruntime.backend`, `onnxruntime.datasets`,
    `onnxruntime.tools`, and
    `onnxruntime.capi.convert_npz_to_onnx_adapter`) at runtime-submodule
    collection and analysis-exclude time. These helpers are for ONNX model
    authoring/conversion, not CLAP/CUE inference, and previously caused a
    noisy missing-`onnx` collection probe.
  - ONNX helper trim gates: focused `ruff` passed for the sidecar spec guard
    plus both specs, and focused PyInstaller spec tests passed
    (`test_pyinstaller_specs_exclude_transformers`,
    `test_pyinstaller_specs_filter_test_submodules`,
    `test_pyinstaller_specs_collect_local_ai_runtime` -> 6 passed). A real
    macOS frozen sidecar build measured `211M`, launched `--version`, returned
    `library stats --json` with `sqlite-vec` + `clap` 512 + Codex ready,
    passed `library search "test track" --k 1`, and bundle graph search found
    no `onnxruntime.backend`, `onnxruntime.tools`, `onnxruntime.datasets`,
    `convert_npz_to_onnx_adapter`, or `No module named 'onnx'` hits in the
    warn file, `PYZ-00.toc`, or `dist/vibemix-core`.
  - CLAP precision/doc cleanup: code and tests already pinned the default
    CLAP installer manifest to full-precision fp32 ONNX
    (`onnx/audio_model.onnx` + `onnx/text_model.onnx`, size/SHA checked).
    `docs/clap-engine.md` now matches that quality-first default and no longer
    advertises the old 160-310 MB q8/fp16 footprint as the ship path.
  - Live prompt cleanup: the main intermediate hype prompt no longer
    contradicts itself by saying both "everything in past tense" and "don't
    make every reaction past-tense." The structural-variety rule now keeps
    latency-safe past-tense/timeless framing while still encouraging varied
    openings and fragment shapes.
  - CLAP/prompt gates: focused CLAP model-manifest tests passed
    (`test_clap_manifest_defaults_to_full_precision_runtime_models`,
    `test_onnx_model_status_marks_wrong_sized_cache_for_repair` -> 2 passed).
    Focused prompt tests and `ruff` passed for
    `src/vibemix/prompts/matrix.py` / `tests/prompts/test_matrix.py`
    (`test_hype_prompt_does_not_reference_removed_phase_field`,
    `test_hype_prompt_keeps_latency_safe_variety_rule`,
    `test_prompt_01_hype_intermediate_byte_identical_to_persona` -> 3 passed).
  - Local Codex/Viber verification: source `library stats --json` reports
    `embedding_backend="clap"`, `embedding_dim=512`,
    `agent_backend="codex"`, and `agent_ready=true`. With the same shell gate
    the desktop bridge applies (`VIBEMIX_CODEX_ALLOW_SHELL=1`), source
    `library chat ... --backend codex --json` returned `stop_reason=model_done`
    with parseable JSON on stdout and the human status line isolated on stderr.
    Source `library build-set "short hard techno test set" --curve peak_time
    --backend codex --json` completed through the agentic path with
    `stop_reason=exported`, selected six grounded `folder:` track IDs, wrote
    M3U/JSON playlist artifacts, and exported Rekordbox XML at
    `~/.cache/vibemix/sets/hard-techno-peak-time-test-set.xml`.
  - Local Codex setup fallback: running the same chat path without
    `VIBEMIX_CODEX_ALLOW_SHELL=1` returns the designed
    `codex_mcp_blocked` setup payload instead of hanging or crashing. This
    confirms the CLI layer is ready for the Library UI bridge's setup-card
    handling and that the UI must continue to set the gate only for explicit
    Codex backend invocations.
  - Detector tuning SciPy cleanup gates: `uv run python
    scripts/tune_detectors.py --help` now succeeds without SciPy installed;
    `uv run pytest -q tests/scripts/test_tune_detectors.py` -> 11 passed;
    `uv run ruff check scripts/tune_detectors.py
    tests/scripts/test_tune_detectors.py` -> passed; targeted `rg` found no
    live `from scipy` / `import scipy` references in `scripts`, `src`,
    `tests/scripts`, or `.planning/codebase/STACK.md`; and `git diff --check`
    passed for the edited harness/docs/stack files.
  - Viber tool/docs drift gates: focused `ruff` passed for
    `src/vibemix/library/mcp_server.py` and
    `src/vibemix/library/codex_curate.py`; `uv run python
    scripts/audit/gen_audit_md.py --check` passed; `uv run pytest -q
    tests/library/test_codex_curate.py
    tests/library/test_toolset.py::test_local_toolset_import_does_not_load_gemini_sdk`
    -> 22 passed; targeted `rg` found no active "three grounded tools",
    `NO RATING`, `MISSING`, stale Gemini-only audit, or SciPy audit rows in
    the patched surfaces; and `git diff --check` passed.
  - Live embedding-boundary gates: `uv run ruff check src/vibemix/__main__.py
    src/vibemix/library/mcp_server.py src/vibemix/library/codex_curate.py`
    passed; focused smoke/build-embedder/stats tests passed
    (`test_smoke_03_full_wiring`,
    `test_build_embedder_ignores_legacy_gemini_backend`,
    `test_empty_store_reports_zero` -> 3 passed); with `GEMINI_API_KEY` and
    `VIBEMIX_PROXY_JWT` unset, `build_toolset()` still constructed a
    `LibraryToolset` and `library stats --json` reported `clap` / `512` /
    Codex ready; targeted `rg` found no remaining `build_embedder(client)`,
    `_build_embedder(_embed_client)`, or `embedContent route` strings in the
    live/library/runtime surfaces.
  - Product embedder isolation gates: focused `ruff` passed for the new neutral
    cache/config/factory/type modules plus `embed.py`, `embed_clap.py`, search,
    similar, grounding, importer, agent, MCP, session loop, and `__main__.py`.
    Focused product tests passed
    (`test_embed_clap.py`, `test_search.py`, `test_similar.py`,
    `test_grounding.py`, `test_importer.py`, `test_toolset.py`,
    `test_agent.py`, `test_codex_curate.py`, `test_session_loop.py`,
    `test_main_smoke.py` -> 134 passed), and focused legacy/parity tests still
    passed (`test_embed.py`, `test_embed_router_dispatch.py`,
    `test_embedding_ga_probe.py`, `test_grounding_router_dispatch.py`,
    `test_embeddings_parity.py` -> 35 passed). With Gemini credentials unset,
    both `from vibemix.library.embed_factory import build_embedder` and
    `from vibemix.library import build_embedder` returned `ClapEmbedder` while
    leaving `vibemix.library.embed` unloaded; `build_toolset()` also returned a
    `LibraryToolset` with the legacy module unloaded. Source CLI smokes passed
    for `library stats --json`, `library search "acid techno" --k 2 --json`,
    and `library similar folder:2bbac1d2a917ca64 --k 2`; `git diff --check`
    passed.
  - Eval embedding cleanup gates: `uv run ruff check
    scripts/eval/cited_relevance.py tests/eval/test_cited_relevance.py
    scripts/eval/__init__.py scripts/eval/record_cassettes.py
    src/vibemix/library/clap_engine.py` passed; `uv run pytest -q
    tests/eval/test_cited_relevance.py tests/eval/test_substance_metric.py
    tests/eval/test_record_cassettes_invokable.py` -> 27 passed; a local
    `relevance_score(...)` smoke returned `0.7906` without a client; targeted
    `rg` found no `gemini-embedding-2-preview`, `SEMANTIC_SIMILARITY`,
    `Gemini Embedding 2`, or `embed_content` hits in the active eval relevance
    surface or CLAP engine copy; and `git diff --check` passed.
  - Legacy proxy-embed probe gates: `uv run ruff check
    scripts/probe_proxy_embed.py` passed; default `uv run python
    scripts/probe_proxy_embed.py` returned structured JSON with
    `status="skipped"` and exit 0; `--help` documents `--legacy-live-probe`;
    and `git diff --check` passed.
  - Active source/test/planning copy cleanup gates: `uv run ruff check
    src/vibemix/library/cue_detect.py src/vibemix/library/folder_ingest.py
    src/vibemix/library/embed_clap.py src/vibemix/memory/__init__.py
    src/vibemix/library/dj_knowledge.py src/vibemix/memory/ingest.py
    tests/state/conftest.py tests/library/test_genre_prototypes.py` passed;
    `uv run pytest -q tests/library/test_genre_prototypes.py
    tests/state/test_refresh_perceive.py tests/state/test_coach_perceive.py
    tests/memory/test_no_extraction.py tests/memory/test_retrieval.py
    tests/library/test_folder_ingest.py tests/library/test_embed_clap.py`
    -> 64 passed; targeted `rg` found no stale `LibraryEmbedder`,
    `existing Gemini text embedder`, `Gemini Embedding 2`,
    `gemini-embedding-`, or 1536-d synthetic-corpus wording in the edited
    active source/test surfaces; and `git diff --check` passed.
  - Launch-copy CLAP cleanup gates: `uv run pytest -q
    tests/scripts/test_populate_changelog.py
    tests/library/test_models_cli.py::test_clap_manifest_defaults_to_full_precision_runtime_models`
    -> 14 passed; targeted stale-copy `rg` across README, CONTRIBUTING, docs,
    launch scripts, dayzero copy, and mocks now finds only explicitly
    historical/superseded dependency-opportunity notes; `git diff --check`
    passed for the edited launch template and CLAP doc.
  - App-facing library bridge/UI gate: `tauri/ui/library.html` now first-paints
    in the actual chat/Viber state (`data-mode="chat"`, Viber tab selected,
    Ask Viber button, static intro turn) instead of briefly painting Search
    before `index.ts` applies `initialLibraryState.mode`. The webview API/header
    comments were corrected to the real Tauri one-shot CLI bridge contract.
    Verification: `npm --prefix tauri/ui test -- library` -> 65 passed;
    `npm --prefix tauri/ui run build` passed (existing Vite chunk/import
    warnings only, no `dist` churn); `cargo test --manifest-path
    tauri/src-tauri/Cargo.toml --bin vibemix library_cmds` -> 24 passed; and
    targeted `rg` found no stale first-paint `data-mode="search"`/1536d/Gemini
    embedding copy in the library UI surface.
  - Public README privacy wording now separates the live co-host's Bravoh
    Gemini proxy path from local CLAP library embeddings/search and optional
    local Codex CLI Viber chat/build. Verification: `uv run pytest -q
    tests/repo/test_readme_feature_matrix_sync.py
    tests/repo/test_no_recall_antifeatures.py` -> 11 passed; `git diff
    --check` passed for README + this map.
  - Active CLAP/Phase 89 doc-truth cleanup: `docs/clap-engine.md` now names
    `embed_factory.build_embedder()` as the product factory and describes
    `ClapEmbedder` through the product protocols instead of as a drop-in for
    legacy `LibraryEmbedder`; `.planning/STATE.md` now matches the Roadmap/spec
    that Phase 89 is a Rekordbox-only MVP, with Serato/Traktor adapters and the
    watcher/delta queue deferred. Verification: targeted `rg` found no stale
    `embed.py::build_embedder`, "drop-in for LibraryEmbedder", or overclaimed
    Phase 89 Rekordbox/Serato/Traktor/watch-for-changes wording in the active
    CLAP/Phase 89 surfaces; `uv run pytest -q tests/library/test_embed_clap.py
    tests/library/test_models_cli.py::test_clap_manifest_defaults_to_full_precision_runtime_models
    tests/repo/test_phase20_docs.py` -> 32 passed; and `git diff --check`
    passed for the touched docs.
  - Viber/Codex chat functionality gate: `CodexChatResult.to_dict()` now
    reports successful chat turns as at least one iteration instead of
    `iterations: 0`, so the Library UI no longer renders a successful local
    Codex reply as `0 iter · model_done`. Setup/error terminals remain
    `iterations: 0`. Verification: `uv run ruff check
    src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
    passed; `uv run pytest -q tests/library/test_codex_curate.py` -> 21
    passed after making playlist-persistence monkeypatches import the module
    explicitly instead of relying on test order; `VIBEMIX_CODEX_ALLOW_SHELL=0`
    CLI smokes proved `library chat --backend codex --json` emits valid stdout
    JSON setup payload and `library build-set ... --backend codex --json`
    emits parseable structured stderr JSON with exit 1 for the MCP-blocked
    setup terminal; `codex --version` returned `codex-cli 0.133.0`; and a live
    `VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat "No
    tools needed: reply with one short sentence saying Viber is wired."
    --backend codex --json` returned exit 0 with valid JSON
    (`reply='Viber is wired.'`, `iterations=1`, `stop_reason=model_done`).
  - Codex/Viber operator-doc cleanup: `docs/codex-agent.md` now documents all
    three Codex-backed surfaces (`curate`, `chat`, `build-set`), distinguishes
    direct CLI `VIBEMIX_CODEX_ALLOW_SHELL=1` from the desktop Rust bridge's
    trusted local env injection, and no longer claims Codex output is only
    M3U/JSON or "not Rekordbox XML". It now states the current contract:
    curate persists M3U/JSON, build-set can write a Rekordbox-importable
    collection XML via `export_set`, and neither path mutates the master DB.
    Verification: targeted `rg` confirmed the stale "not a Rekordbox XML" claim
    is gone and the current chat/build/doc terms are present; `uv run pytest -q
    tests/library/test_codex_curate.py
    tests/library/test_toolset.py::test_local_toolset_import_does_not_load_gemini_sdk
    tests/repo/test_phase20_docs.py` -> 42 passed; `git diff --check` passed
    for the doc.
  - Library/Viber Codex-only product-path cleanup removed the visible Gemini
    fallback from desktop and CLI surfaces. The Tauri Library bridge now pins
    `library_curate`, `library_build_set`, `library_chat`, and `library_stats`
    to `--backend codex`, explicitly overrides stale
    `VIBEMIX_LIBRARY_AGENT_BACKEND=gemini` for one-shot Library commands, and
    no longer forwards that old selector through the general sidecar env relay.
    The Python Library CLI now accepts only `--backend codex` for visible
    Viber chat/curate/build-set commands, `library stats --json` always reports
    Codex setup, and `library telegram` runs through `curate_with_codex()`
    instead of constructing a Gemini client. Public README, Codex-agent docs,
    BYO-key docs, install rehearsal, Library docs, UI comments/tests, and
    dependency audit copy now describe local CLAP embeddings plus local Codex
    Viber as the product path; the old Gemini Viber harness is labeled legacy.
    Verification: `uv run ruff check ...` passed for touched Python/tests;
    `uv run pytest -q tests/library/test_stats_cli.py
    tests/library/test_codex_curate.py tests/library/test_toolset.py
    tests/repo/test_phase20_docs.py` -> 59 passed; `npm --prefix tauri/ui test
    -- library` -> 64 passed; the two focused Rust tests
    `library_cmds::tests::app_agent_backend_is_pinned_to_codex` and
    `sidecar::tests::forwarded_env_keys_relay_runtime_auth_and_codex_home`
    passed; `env -u GEMINI_API_KEY VIBEMIX_LIBRARY_AGENT_BACKEND=gemini uv run
    python -m vibemix library stats --json` still reported
    `agent_backend="codex"`; and `uv run python -m vibemix library chat
    "hello" --backend gemini --json` exited with argparse's invalid-choice
    error for `gemini`.
  - Windows first-install naming cleanup removed remaining active
    MSI-era wording from the SmartScreen doc, threat model, install-VM runner
    comment, and dependency audit rationale. User-facing Windows docs now name
    the SignPath-signed Inno `vibemix-installer.exe`; the install VM runner
    says "DMG / Windows installer EXE"; and the dependency audit says
    `google-genai` is for the live co-host/TTS while Library/Viber is local
    Codex. Verification: `uv run pytest -q
    tests/install/test_install_vm_matrix.py
    tests/install/test_windows_smartscreen_doc.py
    tests/repo/test_phase20_docs.py` -> 45 passed; `git diff --check` passed
    for the touched docs/scripts/tests/map; targeted `rg` found no active
    `vibemix.msi`, `vibemix-setup.msi`, old DMG-vs-MSI wording, or "explicit Gemini fallback
    tools" hits outside the new forbidden-string tests.
  - Active planning docs now match the Codex-only Viber product path. The stale
    "Gemini fallback" wording was removed from `STACK.md`, `PROJECT.md`,
    `ROADMAP.md`, `REQUIREMENTS.md`, `v8.2-STATUS.md`, and the current
    `STATE.md` head/reference sections while preserving historical Gemini
    live-cohost notes. `tests/repo/test_phase20_docs.py` now guards these active
    surfaces against reintroducing Gemini fallback language for Viber/set-prep.
    Verification: `uv run pytest -q tests/repo/test_phase20_docs.py` -> 25
    passed; targeted `rg` found no stale Viber Gemini-fallback phrases in the
    active planning set; `git diff --check` passed.
  - Runtime app wiring pass: the main SessionLayout now has a visible
    `vibe engine` rail control wired to Tauri `open_library_window`, so
    Library/Viber chat/build is no longer tray-only. The rail controls now read
    callbacks from the latest rendered SessionState instead of the initial
    default mount state, fixing dead `mute`, mood-cycle, retry, and Vibe Engine
    clicks after the render loop hydrates real handlers. User-facing grounding
    failure text was normalized from Gemini-specific copy to `AI SERVICE
    OFFLINE` / `ai service unreachable` while retaining the internal `gemini`
    wire key for compatibility. `CLAUDE.md`, AGENTS.md, and Phase 74's ease
    summary were refreshed to keep Library/Viber pinned to local Codex and to
    avoid teaching future agents the old Viber/Gemini path. Verification:
    `npm --prefix tauri/ui run test -- tests/session/components.spec.ts
    tests/session/grounding-failure.spec.ts tests/session/render-loop.spec.ts`
    -> 69 passed; `npm --prefix tauri/ui run build` passed with only the
    existing Vite chunk-size/dynamic-import warnings; `uv run pytest -q
    tests/repo/test_phase20_docs.py` -> 25 passed; `git diff --check` passed
    for the touched files; and `AGENTS.md` is 399 words. Backend runtime
    evidence remains source-backed: the dev sidecar listened on
    `127.0.0.1:8765`, CLAP/CUE/Codex preflight passed without
    `GEMINI_API_KEY`, Library chat returned valid JSON via Codex, and
    build-set exported Rekordbox XML.
  - Runtime GUI activation blocker fixed: the default pill surface had been
    calling process-wide macOS Accessory activation, which made the dev app
    appear hidden/accessory to System Events and broke foregroundability of the
    full runtime window. `pill_window.rs` now keeps the `.focused(false)` floor
    but does not demote the whole app; `Cargo.toml` and `.planning/MILESTONES.md`
    were corrected, and `tests/repo/test_tauri_activation_policy.py` guards
    against reintroducing the Accessory policy. Source-backed verification via
    `VIBEMIX_DEV_SIDECAR=1 cargo tauri dev`: System Events saw the dev process
    as `visible=true frontmost=true`, main + pill windows were present, the
    main `vibe engine` button opened `vibemix · vibe engine` at 1180x760, and a
    real UI Viber prompt returned a Codex/library answer with a `search_vibe`
    tool trace and receipt `folder:2bbac1d2a917ca64` ("SMOKED OUT").
    Screenshots: `/tmp/vibemix-dev-regular-foreground.png`,
    `/tmp/vibemix-dev-vibe-engine-real-open.png`, and
    `/tmp/vibemix-dev-viber-ui-chat-smoke.png`. Verification:
    `uv run pytest -q tests/repo/test_tauri_activation_policy.py
    tests/repo/test_phase20_docs.py` -> 26 passed; `cargo check
    --manifest-path tauri/src-tauri/Cargo.toml` passed; focused Rust tests
    `pill_window::tests::defaults_pin_context_decisions` and
    `config::tests::primary_surface*` passed; `rustfmt --edition 2021 --check
    tauri/src-tauri/src/pill_window.rs` passed; `git diff --check` passed for
    the touched activation-policy/map files.
  - Rust formatting gate cleanup: the known broad `cargo fmt --check` failure
    in `tauri/src-tauri/src/library_cmds.rs` was narrowed to two argument-vector
    formatting sites and patched surgically, without broad-formatting unrelated
    dirty Rust. Verification: `cargo fmt --manifest-path
    tauri/src-tauri/Cargo.toml --check` now passes; `cargo check
    --manifest-path tauri/src-tauri/Cargo.toml` passes; `uv run pytest -q
  tests/repo/test_tauri_activation_policy.py tests/repo/test_phase20_docs.py
    tests/repo/test_tauri_dev_command.py` -> 27 passed; `git diff --check`
    passed for the touched Rust/map/test files.
  - Package prepare/build gate cleanup: `scripts/dist/prepare_tauri_build.py`
    is now the Tauri `beforeBuildCommand`. It builds the webview, verifies the
    exact Tauri sidecar resource path, builds the PyInstaller sidecar when the
    bundle is missing/bad, and rechecks before packaging continues.
    `scripts/dist/check_sidecar_bundle_ready.py` is also wired into
    `pretag_check.sh`, so placeholder-only sidecar trees fail before release.
    Verification: focused Ruff and pytest slices passed for the prepare script,
    sidecar readiness gate, Tauri dev-command test, and model-cache tests.
  - Real arm64 sidecar proof: `uv run python
    scripts/dist/prepare_tauri_build.py --skip-frontend --triple
    aarch64-apple-darwin` produced
    `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` with a real
    Mach-O arm64 executable and `_internal/` payload. The generated root
    PyInstaller intermediates `build/` (`78M`) and `dist/vibemix-core` (`211M`)
    were removed after proof; the Tauri resource bundle was kept for package
    checks.
  - CLAP first-run repair/proof: `vibemix.library.model_assets` now repairs a
    broken/non-directory CLAP cache path before install. The stale broken cache
    symlink on this machine no longer blocks setup; `library models --install
    required --json` downloaded/verified the six pinned full-precision CLAP
    files. Source and frozen sidecar `library stats --json` both report
    sqlite-vec, CLAP 512, installed models, and Codex readiness.
  - Local Tauri package-build proof: `cargo tauri build --no-bundle` from
    `tauri/src-tauri` invoked the prepare script, built the Vite webview, passed
    sidecar readiness, and produced
    `tauri/src-tauri/target/release/vibemix` under the release profile.
  - Local unsigned macOS `.app` proof: `cargo tauri build --bundles app
    --no-sign --ci` invoked the same prepare script and produced
    `tauri/src-tauri/target/release/bundle/macos/vibemix.app`. The raw Tauri
    resource copy flattened 36 PyInstaller duplicate dylib symlinks; running
    `scripts/dist/repair_macos_app_sidecar_symlinks.py` relinked them, and a
    second repair pass reported `already_linked=36`, `relinked=0`,
    `mismatches=[]`. The app-bundled arm64 sidecar then passed
    `library stats --json` with sqlite-vec, CLAP 512, installed CLAP cache, and
    Codex ready. `scripts/dist/create_macos_updater_artifact.sh --arch arm64`
    created `vibemix-0.0.1-arm64.app.tar.gz`; tar inspection showed the
    top-level `vibemix.app/Contents/` entry and preserved repaired dylib
    symlinks. No updater `.sig` was created because local signing secrets are
    absent.
  - macOS `.app` verifier gate added:
    `scripts/dist/check_macos_app_bundle_ready.py` now checks the emitted
    `vibemix.app` for `Contents/Info.plist`, executable main binary,
    executable target sidecar, `_internal/`, repaired PyInstaller dylib
    symlinks, and a sidecar smoke command. Release CI runs it after the symlink
    repair and before codesign/updater artifact creation, so a raw flattened
    `.app` can no longer slide into signing/upload. Verification:
    `python3 scripts/dist/check_macos_app_bundle_ready.py ... --smoke version
    --json` passed on the repaired local `.app` with `ok=true` and
    `smoke_stdout="vibemix 0.1.0-dev0"`; focused Ruff passed; and
    `uv run pytest -q tests/install/test_macos_app_bundle_ready.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/install/test_macos_updater_artifact.py
    tests/security/test_release_yml_signing_skips.py
    tests/repo/test_tauri_dev_command.py tests/repo/test_phase20_docs.py`
    -> 51 passed.
  - macOS updater artifact extraction gate added:
    `scripts/dist/check_macos_updater_artifact_ready.py` now safely extracts a
    `.app.tar.gz` into a clean install rehearsal directory, rejects traversal
    paths/unsafe links/non-empty install dirs, ignores AppleDouble metadata,
    and reuses the `.app` verifier on the extracted payload. The updater
    artifact creator now sets `COPYFILE_DISABLE=1` so new macOS tars do not
    contain `._*` metadata entries. Release CI runs the artifact verifier after
    `.app.tar.gz` creation and before upload/publish. Local proof recreated
    `vibemix-0.0.1-arm64.app.tar.gz`, confirmed no `._*` / `__MACOSX` members,
    extracted it into `/tmp/vibemix-updater-install-smoke`, preserved repaired
    dylib symlinks, and smoked the extracted sidecar with
    `smoke_stdout="vibemix 0.1.0-dev0"`. Verification: focused Ruff and
    `bash -n scripts/dist/create_macos_updater_artifact.sh` passed; `uv run
    pytest -q tests/install/test_macos_app_bundle_ready.py
    tests/install/test_macos_updater_artifact_ready.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/install/test_macos_updater_artifact.py
    tests/security/test_release_yml_signing_skips.py
    tests/repo/test_tauri_dev_command.py tests/repo/test_phase20_docs.py`
    -> 57 passed.
  - macOS first-install DMG drag-install gate added:
    `scripts/dist/check_macos_dmg_artifact_ready.py` now mounts a DMG read-only
    with `hdiutil`, finds `vibemix.app`, copies it to a clean rehearsal install
    directory with symlinks preserved, detaches the image, and runs the `.app`
    sidecar verifier on the copied install. Release CI runs it after
    `sign_macos.sh` creates the signed/notarized DMG and before updater
    artifact creation/upload. Local unsigned proof used `create-dmg` to create
    `/tmp/vibemix-local-first-install.dmg` from the repaired `.app`, copied it
    into `/tmp/vibemix-dmg-install-smoke`, preserved repaired dylib symlinks,
    detached cleanly, and smoked the copied sidecar with
    `smoke_stdout="vibemix 0.1.0-dev0"`. Verification: focused Ruff passed;
    real `check_macos_dmg_artifact_ready.py ... --smoke version --json` passed;
    and `uv run pytest -q tests/install/test_macos_app_bundle_ready.py
    tests/install/test_macos_updater_artifact_ready.py
    tests/install/test_macos_dmg_artifact_ready.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/install/test_macos_updater_artifact.py
    tests/security/test_release_yml_signing_skips.py
    tests/repo/test_tauri_dev_command.py tests/repo/test_phase20_docs.py`
    -> 60 passed.
  - Windows app payload readiness gate added at 2026-05-27 10:06 +03:
    `scripts/dist/check_windows_app_payload_ready.py` validates the staged
    `dist/windows-app` directory before SignPath/Inno consumes it. It checks
    that `vibemix.exe` and `binaries/vibemix-core-x86_64-pc-windows-msvc/`
    contain probable PE executables, rejects placeholder-only sidecar trees,
    requires PyInstaller `_internal/`, and can smoke the sidecar with
    `--version` or `library stats --json`. Release CI now runs this immediately
    after `scripts/win/stage_app_payload.ps1`, and `scripts/win/build_local.ps1`
    runs the same verifier for local Windows builds. Docs updated:
    `docs/dev-loop.md`, `docs/release-process.md`, and
    `docs/signing-windows.md`. Verification: `uv run ruff check
    scripts/dist/check_windows_app_payload_ready.py
    tests/install/test_windows_app_payload_ready.py
    tests/install/test_windows_packaging_paths.py`; `uv run pytest -q
    tests/install/test_windows_app_payload_ready.py
    tests/install/test_windows_packaging_paths.py
    tests/security/test_release_yml_signing_skips.py` -> 33 passed; and
    `git diff --check` on the touched slice passed.
  - Windows local-build rehearsal copy cleanup: `scripts/win/build_local.ps1`
    no longer tells operators to judge the full first-launch flow against the
    stale `<=60s per INSTALL-05` target. It now points at
    `docs/install-rehearsal.md`, the current under-10-minutes stopwatch
    contract that includes required CLAP setup, Library/Viber, and first AI
    reaction. Verification: `uv run pytest -q
    tests/install/test_windows_packaging_paths.py` pins the current wording.
  - Release-process stale route cleanup: `docs/release-process.md` no longer
    presents the historical v7 autonomous RC path as the current public release
    route or claims release work can ship without the external signature clock.
    The section now says automation may pre-stage only; a human publishes after
    signed/notarized macOS, signed Windows, updater artifacts, and
    fresh-machine install rehearsal pass. Verification: `uv run pytest -q
    tests/repo/test_phase20_docs.py` pins the current release-process wording.
  - Windows updater publish gate tightened in the same 10:06 slice:
    `verify-signed-publish-gate` now verifies the Tauri NSIS updater
    `*setup*.exe` separately from the Inno first-install
    `vibemix-installer.exe` before `release-publish` can sign `latest.json`.
    This prevents a signed first-install EXE from masking a missing or malformed
    updater artifact at publish time. Docs/tests updated in
    `docs/release-process.md`, `docs/updater.md`,
    `tests/security/test_release_yml_signing_skips.py`, and
    `tests/security/test_verify_signed.py`. Broader package gate verification:
    `uv run pytest -q tests/install/test_windows_app_payload_ready.py
    tests/install/test_windows_packaging_paths.py
    tests/install/test_macos_app_bundle_ready.py
    tests/install/test_macos_updater_artifact_ready.py
    tests/install/test_macos_dmg_artifact_ready.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/install/test_macos_updater_artifact.py
    tests/security/test_release_yml_signing_skips.py
    tests/security/test_verify_signed.py tests/repo/test_tauri_dev_command.py
    tests/repo/test_phase20_docs.py` -> 93 passed; focused Ruff and
    `git diff --check` on the touched slice passed.
  - Signed-artifact verifier hardening: `scripts/dist/verify_signed.py` no
    longer treats any Windows `MZ` header as signed. It now parses the PE
    optional header security directory and requires a bounded
    `WIN_CERTIFICATE` Authenticode table. The release publish gate now runs on
    `macos-14` so DMG/PKG checks can use `codesign --verify --strict`, while
    Windows EXE checks stay pure-Python/offline on the same runner. Verification:
    `uv run pytest -q tests/security/test_verify_signed.py
    tests/security/test_release_yml_signing_skips.py` -> 30 passed; focused
    Ruff and `git diff --check` passed.
  - Planning debloat archive verification: the expanded v2.1 phase-detail tree
    is now tracked under `.planning/archive/2026-05-27-v2.1-phase-detail/` and
    `.planning/milestones/v2.1-phases/` contains only the pointer README.
    `unzip -l .planning/archive/2026-05-27-v2.1-phase-detail.zip` confirms the
    bundle contains the moved tree; `rg` against the original active path now
    sees only the deprecation pointer, manifest, and map references rather than
    143 old phase files. Verification:
    `uv run pytest -q tests/scripts/test_grey_area_log.py
    tests/repo/test_v4_milestone_audit_present.py
    tests/repo/test_phase20_docs.py` -> 35 passed; `git diff --check` passed.
  - Local macOS first-install rehearsal fix: direct
    `cargo tauri build --bundles dmg --no-sign` produced an unsigned DMG, but
    `scripts/dist/check_macos_dmg_artifact_ready.py --smoke library-stats --json`
    failed because Tauri packaged the app before repairing PyInstaller's
    flattened `av/.dylibs` and `PIL/.dylibs` symlinks. Added
    `scripts/dist/build_macos_local_dmg.sh`, which builds the unsigned `.app`,
    forces a fresh PyInstaller sidecar rebuild through `VIBEMIX_FORCE_SIDECAR=1`,
    runs `repair_macos_app_sidecar_symlinks.py`, verifies the repaired app,
    creates the DMG with `create-dmg`/`hdiutil`, then mounts/copies/smokes the
    DMG. This prevents an old-but-ready frozen sidecar from slipping into a
    successful-looking local package after Python changes. Verification:
    `bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats` rebuilt
    the sidecar, repaired 36 links, and produced
    `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg`;
    `check_macos_dmg_artifact_ready.py ... --smoke library-stats --json`
    returned `ok=true` with `embedding_backend=clap`, `embedding_dim=512`,
    `clap_model_installed=true`, `agent_backend=codex`, and
    `agent_ready=true`; artifact size is 111M. Static/package coverage:
    `uv run pytest -q tests/install/test_macos_local_dmg_build.py
    tests/install/test_macos_app_bundle_ready.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/install/test_macos_dmg_artifact_ready.py
    tests/install/test_macos_updater_artifact_ready.py
    tests/install/test_prepare_tauri_build.py` -> 25 passed; focused
    `tests/install/test_prepare_tauri_build.py
    tests/install/test_macos_local_dmg_build.py` -> 10 passed after the forced
    sidecar freshness guard; `git diff --check` passed for the touched
    wrapper/docs/test slice.
  - Packaged first-run model setup proof: mounted the fixed local DMG into
    `/tmp/vibemix-dmg-fresh-install/vibemix.app`, pointed the embedded sidecar
    at an empty `VIBEMIX_CLAP_ONNX_DIR=/tmp/vibemix-empty-clap-cache`, and ran
    `library models --install required --json`. The packaged sidecar downloaded
    and checksum-reported all six CLAP files (`audio_model.onnx` 281,749,092
    bytes, `text_model.onnx` 501,513,769 bytes, plus tokenizer/config files),
    returned `required_ready=true`, `install.ok=true`, and `missing=[] /
    mismatched=[]`. A follow-up packaged `library search "fresh cache unique
    query 2026-05-27 1049" --k 1 --json` against that temp cache returned
    `cache_hit=false` and real results, proving the freshly installed CLAP text
    model loaded from the DMG-installed sidecar path.
  - First-run model setup progress seam: `library models --install required
    --json --progress` now keeps stdout as the final JSON contract while
    emitting `VIBEMIX_MODEL_PROGRESS {...}` frames on stderr. The Tauri bridge
    strips those frames from error text and relays them to
    `library://model-progress`; the Library setup row renders live file/count
    and byte progress instead of sitting on a generic spinner during the large
    CLAP download. Verification: `uv run pytest -q
    tests/library/test_models_cli.py` -> 20 passed; `npm --prefix tauri/ui run
    test -- src/library/model-setup.test.ts src/library/api.test.ts
    src/library/build.test.ts src/library/chat.test.ts
    src/library/curate.test.ts` -> 54 passed; `cargo test --manifest-path
    tauri/src-tauri/Cargo.toml library_cmds -- --nocapture` -> 25 passed; and
    a real `env -u GEMINI_API_KEY uv run python -m vibemix library models
    --install required --json --progress` smoke returned valid JSON with
    `required_ready=true` / `install.ok=true` plus six structured progress
    frames. After forcing a local sidecar rebuild, the DMG-installed packaged
    sidecar also accepted `library models --install required --json --progress`
    and emitted six `VIBEMIX_MODEL_PROGRESS` frames against the populated temp
    CLAP cache.
  - Viber chat artifact-contract cleanup: the Codex chat wrapper now uses a
    strict `{reply, tools_used, tool_trace, track_ids, playlist, export_path}`
    schema, tells Codex to copy the real `create_playlist` / `export_set` tool outputs, and
    re-validates playlist track ids plus saved artifact paths before surfacing
    them to the Library chat UI. `LibraryToolset.create_playlist` now returns
    the validated `track_ids` to the MCP caller, so a real chat-created
    playlist can render the existing playlist card instead of degrading to
    generic receipts. Verification: `uv run pytest -q
    tests/library/test_agent.py tests/library/test_codex_curate.py
    tests/library/test_toolset.py` -> 47 passed; `npm --prefix tauri/ui run test -- src/library/chat.test.ts
    src/library/api.test.ts` -> 17 passed; live no-tool
    `VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat "reply
    READY only" --backend codex --json` produced valid stdout JSON with
    `playlist=null`, `export_path=null`, and `stop_reason=model_done`; live
    tool-using chat smoke created a real one-track playlist via
    `search_vibe` + `create_playlist`, surfaced `stop_reason=created`,
    `playlist.name=Codex Chat Artifact Smoke`, and valid M3U/JSON paths in the
    chat DTO. The proof playlist files were removed from the local cache after
    verification.
  - Viber chat tool-trace honesty: the Codex chat schema now asks for
    UI-ready `tool_trace` rows (`name`, short visible `arg`, `ok`) instead of
    forcing the app to fake every real tool call as `{arg:"", ok:true}`. The
    wrapper keeps the old `tools_used` fallback for compatibility, derives
    names from rich rows when needed, and uses the rich row count for the
    visible iteration receipt. Verification: `uv run ruff check
    src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py` ->
    pass; `uv run pytest -q tests/library/test_codex_curate.py` -> 26 passed;
    `uv run pytest -q tests/library/test_agent.py
    tests/library/test_codex_curate.py tests/library/test_toolset.py` -> 48
    passed; `npm --prefix tauri/ui run test -- src/library/chat.test.ts
    src/library/api.test.ts` -> 17 passed; live no-tool Codex chat smoke
    returned valid JSON with `tool_trace=[]`; live tool-call Codex chat smoke
    returned `tool_trace=[{"name":"search_vibe","arg":"dark warehouse
    techno","ok":true}]` plus a grounded `seen_track_ids` row.
  - Library/Viber Gemini removal check: product stats and focused tests confirm
    the search/chat/set-prep path is CLAP/Codex, not Gemini embeddings.
    Verification: `uv run pytest -q tests/library/test_stats_cli.py
    tests/library/test_toolset.py tests/library/test_embed_clap.py` -> 27
    passed; `uv run python -m vibemix library stats --json` returned
    `embedding_backend="clap"`, `embedding_dim=512`, `agent_backend="codex"`,
    and `agent_ready=true`. The shipped Codex MCP product surface now avoids
    the Gemini-backed `ingest_youtube` tool entirely: `mcp_server.build_toolset`
    no longer resolves a Gemini/proxy client, `build_server` does not register
    `ingest_youtube`, and the Codex chat prompt no longer advertises YouTube
    grounding. Remaining Library Gemini references are legacy migration/eval
    tests or live co-host surfaces, not the local CLAP/Codex Viber path.
    Verification: `uv run ruff check
    src/vibemix/library/mcp_server.py src/vibemix/library/codex_curate.py
    tests/library/test_codex_curate.py tests/library/test_toolset.py` -> pass;
    `uv run pytest -q tests/library/test_codex_curate.py
    tests/library/test_toolset.py` -> 38 passed; targeted `rg` on the Codex
    MCP/prompt files found no registered `ingest_youtube` or active YouTube
    tool guidance; with `GEMINI_API_KEY` and `VIBEMIX_PROXY_JWT` unset, real
    `VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat "No
    tools needed: reply with exactly LOCAL VIBER OK." --backend codex --json`
    returned clean JSON (`reply="LOCAL VIBER OK"`, `tool_trace=[]`,
    `stop_reason=model_done`). The active Codex-agent doc and `library chat
    --help` copy now list the actual product tool surface
    (`search/discover/quote/web/knowledge/curate/build`) with no YouTube media
    claim. Verification: `uv run pytest -q tests/library/test_codex_curate.py
    tests/library/test_toolset.py tests/library/test_curate_unify.py` -> 46
    passed.
  - Follow-up debloat removed the Gemini/YouTube media tool from the shared
    Viber tool spine, not just the MCP wrapper: `LibraryToolset` no longer
    accepts a Gemini client or dispatches `ingest_youtube`, and the legacy
    `ViberAgent` no longer advertises that function declaration. The standalone
    `youtube_ingest.py` helper and its unit test were deleted as dead Library
    product code, and the Viber chat mock now demos `web_search` + `fetch_url`
    source reading instead of fake link-listening. Verification: `uv run ruff
    check src/vibemix/library/toolset.py src/vibemix/library/agent.py
    src/vibemix/library/mcp_server.py src/vibemix/library/codex_curate.py
    src/vibemix/__main__.py tests/library/test_toolset.py
    tests/library/test_codex_curate.py` -> pass; `uv run pytest -q
    tests/library/test_toolset.py tests/library/test_agent.py
    tests/library/test_codex_curate.py tests/library/test_curate_unify.py` ->
    61 passed; targeted product-surface `rg` finds `ingest_youtube` only in
    negative regression tests; a separated-stream real Codex chat smoke with
    Gemini/proxy env unset returned exit 0 and `json.tool` accepted stdout
    after the helper deletion (`reply="LOCAL VIBER OK"`, stderr held only the
    human receipt).
  - Sequencer cue-awareness fix: `PoolTrack` now carries cue metadata from the
    live library into the beam sequencer. Known weak structural anchors (missing
    plausible mix-out on the current track or mix-in on the next) are penalized
    and surfaced in `relaxed_transitions`; missing cues remain unknown/pass so
    sparse libraries do not collapse. This replaces the old "structural
    mixability placeholder" comment with actual cue-aware behavior while
    keeping set prep robust. Verification: `uv run ruff check
    src/vibemix/library/sequencer.py src/vibemix/library/toolset.py
    tests/library/test_sequencer.py` -> pass; `uv run pytest -q
    tests/library/test_sequencer.py tests/library/test_setprep_tools.py
    tests/library/test_toolset.py` -> 48 passed.
  - Presentation sanity pass after code fixes: `uv run pytest -q
    tests/library/test_agent.py tests/library/test_codex_curate.py
    tests/library/test_toolset.py tests/library/test_sequencer.py
    tests/library/test_setprep_tools.py tests/library/test_stats_cli.py
    tests/library/test_embed_clap.py` -> 107 passed;
    `npm --prefix tauri/ui run build` -> pass (only existing Vite chunk-size /
    dynamic-import warnings); `git diff --check --` on the touched code/tests/map
    files -> pass.
  - First-run optional CUE setup no longer looks like a broken required install:
    `library models --json` now marks each model with `installable`. CLAP is
    always installable; CUE-DETR is installable only when a hosted
    `VIBEMIX_CUE_ONNX_URL` is configured, so a fresh friend machine with CLAP
    ready and no CUE artifact source hides the optional CUE action instead of
    showing a dead "Check Optional CUE" button. The CLI still reports
    `required_ready=true` and `all_ready=false` honestly when optional CUE is
    missing. Verification: `uv run ruff check
    src/vibemix/library/model_assets.py src/vibemix/__main__.py
    tests/library/test_models_cli.py` -> pass; `uv run pytest -q
    tests/library/test_models_cli.py` -> 21 passed; `npm --prefix tauri/ui run
    test -- src/library/model-setup.test.ts src/library/build.test.ts
    src/library/api.test.ts` -> 42 passed; `uv run pytest -q
    tests/library/test_models_cli.py tests/library/test_stats_cli.py` -> 28
    passed; `npm --prefix tauri/ui run build` -> pass (existing chunk-size /
    dynamic-import warnings only); `cargo test --manifest-path
    tauri/src-tauri/Cargo.toml library_cmds -- --nocapture` -> 25 passed; real
    `env -u VIBEMIX_CUE_ONNX_URL VIBEMIX_CUE_ONNX_PATH=<missing> uv run python
    -m vibemix library models --json` returned CLAP installed/installable,
    CUE missing/non-installable, `required_ready=true`, and `all_ready=false`.
    Reverified after chat wiring: current `uv run python -m vibemix library
    models --json` reports CLAP installed/installable and CUE optional; `uv run
    pytest -q tests/library/test_models_cli.py tests/library/test_stats_cli.py`
    -> 28 passed; `PATH=/opt/homebrew/Cellar/node@22/22.22.3/bin:$PATH npm
    --prefix tauri/ui test -- src/library/model-setup.test.ts
    src/library/build.test.ts src/library/api.test.ts` -> 42 passed; targeted
    Rust model command tests -> 2 passed.
  - Library package-root debloat continued: `vibemix.library.__all__` no
    longer exports the legacy Gemini `ViberAgent` or its `CurateResult`. The
    deleted `vibemix.library.agent` harness is no longer a supported direct
    import; tests now pin the Codex-only curator seams. The package root
    advertises the current CLAP / Codex-era product seams rather than a retired
    backend. The stale `ViberAgent.build_set` wording in the active CLI
    docstring was also corrected to the local Codex/MCP set-prep surface.
    Verification:
    `uv run ruff check src/vibemix/library/__init__.py src/vibemix/__main__.py
    tests/library/test_embed_clap.py` -> pass; `uv run pytest -q
    tests/library/test_embed_clap.py tests/library/test_curate_unify.py
    tests/library/test_toolset.py` -> 28 passed; targeted `rg` found no
    package-root `ViberAgent` / `CurateResult` imports or active
    `ViberAgent.build_set` wording in source/tests/Tauri/map.
  - Legacy Library Gemini harness removal: `src/vibemix/library/agent.py` and
    `tests/library/test_agent.py` were deleted, the Gemini `library_agent`
    router path was removed, and the persona/taste seam tests now target the
    Codex product backend only. The shared `LibraryToolset`, MCP server, Rust
    bridge comments, bench comments, and CLAUDE context no longer teach future
    agents that a Gemini Viber backend exists. Verification: focused Ruff and
    Python/Rust router/curator checks passed after the deletion, and targeted
    `rg` shows no active `vibemix.library.agent`, `ViberAgent`, or
    `library_agent` model-route references outside historical map text and the
    Rust helper name for the Codex backend selector.
  - Local Codex subprocess launch is now app-path hardened: `codex_curate.py`
    prepends the resolved Codex directory plus discovered Node bin directories
    before spawning `codex exec`, and honors `VIBEMIX_CODEX_BIN`,
    `VIBEMIX_NODE_BIN`, and `NODE_BIN`. This fixes the real macOS failure where
    `/opt/homebrew/bin/codex` existed but its `#!/usr/bin/env node` shim failed
    from an app-like PATH with `env: node: No such file or directory`. The
    Tauri sidecar/library env relay now also forwards `VIBEMIX_NODE_BIN` and
    `NODE_BIN`, so custom Node installs have the same escape hatch as custom
    Codex installs.
    Verification: `uv run ruff check` on the touched Library/Viber slice ->
    pass; `uv run pytest -q tests/library/test_toolset.py
    tests/library/test_codex_curate.py tests/library/test_curate_unify.py
    tests/library/test_curator_persona_seam.py tests/llm/test_model_router.py
    tests/e2e/test_phase_41_latency_stack_integration.py
    tests/bench/test_run_fake.py` -> 89 passed; `cargo test --manifest-path
    tauri/src-tauri/Cargo.toml library_cmds -- --nocapture` -> 25 passed;
    `cargo test --manifest-path tauri/src-tauri/Cargo.toml sidecar
    -- --nocapture` -> 16 passed;
    `uv run python -m vibemix library stats --json` reported
    `embedding_backend=clap`, `embedding_dim=512`, `agent_backend=codex`,
    `agent_ready=true`; a real `library chat --backend codex --json` smoke with
    Gemini/proxy env unset returned valid JSON, `reply="LOCAL VIBER OK"`,
    `stop_reason="model_done"`, and no tools.
  - Frontend Library/Viber chat wiring is now verified against the current
    product path: the UI opens in chat mode, calls `libraryChat(message,
    history)`, sends only completed prior turns as history, renders grounded
    tool traces/artifacts/setup failures, and the Rust bridge pins
    `library chat <message> --backend codex --json` while enabling the Codex MCP
    shell gate only for Codex-backed commands. Verification:
    `PATH=/opt/homebrew/Cellar/node@22/22.22.3/bin:$PATH npm --prefix tauri/ui
    test -- src/library/chat.test.ts src/library/build.test.ts
    src/library/api.test.ts src/library/state-machine.test.ts` -> 46 passed;
    `PATH=/opt/homebrew/Cellar/node@22/22.22.3/bin:$PATH npm --prefix tauri/ui
    run build` -> pass (existing Vite chunk-size/dynamic-import warnings only);
    `uv run pytest -q tests/capabilities/test_library_window_contract.py` -> 5
    passed; `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` ->
    pass. Rendered sanity via Vite + Playwright captured
    `/tmp/vibemix-library-desktop.png` and `/tmp/vibemix-library-mobile.png`:
    no console/page errors, default `body[data-mode=chat]`, engine label
    `Viber codex / CLAP ready / 512d / sqlite-vec`, desktop no overflow, mobile
    no horizontal overflow.
  - Current-source macOS package rehearsal was refreshed after discovering the
    previous DMG/updater artifacts were stale (their bundled sidecar lacked the
    newer model `installable` field). Rebuilt the arm64 PyInstaller sidecar with
    `uv run --extra ai-local pyinstaller`, then rebuilt the unsigned `.app` and
    DMG through `bash scripts/dist/build_macos_local_dmg.sh --smoke
    library-stats`. The rebuild repaired 36 app-side PyInstaller dylib symlinks
    and re-ran the bundle AIza-pattern scan over 362 files. Verification:
    `uv run python scripts/dist/check_sidecar_bundle_ready.py` -> OK;
    `VIBEMIX_CLAP_ONNX_DIR=/tmp/vibemix-empty-clap-cache-current
    tauri/src-tauri/binaries/.../vibemix-core-aarch64-apple-darwin library
    models --json` showed missing CLAP with `installable=true` and optional CUE
    with `installable=false`; `uv run python
    scripts/dist/check_macos_dmg_artifact_ready.py
    tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg
    --install-dir /tmp/vibemix-dmg-current-check --smoke library-stats --json`
    -> OK; the copied DMG app's sidecar with an empty CLAP dir also reported
    the current `installable` fields; `bash
    scripts/dist/create_macos_updater_artifact.sh --arch arm64 --output-dir
    tauri/src-tauri/target/release/bundle/macos
    tauri/src-tauri/target/release/bundle/macos/vibemix.app` wrote a fresh
    unsigned updater `.app.tar.gz`; `uv run python
    scripts/dist/check_macos_updater_artifact_ready.py
    tauri/src-tauri/target/release/bundle/macos/vibemix-0.0.1-arm64.app.tar.gz
    --smoke library-stats --json` -> OK. Artifact sizes after rebuild:
    `.app` 241M, DMG 112M, sidecar binary 22M. This is local unsigned package
    proof only, not signed/notarized release proof.
  - Model-router cleanup closed another stale product-path crack: the optional
    OpenRouter live-coach brain default now resolves through
    `live_coach_openrouter` / `OPENROUTER_LLM_MODEL` instead of an inline model
    literal in `__main__.py` or `DJCoHostAgent`. Rust bridge and optional
    Telegram/create-playlist comments were also updated so they describe the
    current CLAP/Codex tool surface rather than teaching future agents a
    Gemini fallback path. Verification: `bash scripts/release/check_no_hardcoded_model.sh`
    -> clean; `uv run ruff check` on the touched Python/router/library files
    -> pass; `uv run pytest -q tests/llm/test_model_router.py
    tests/agent/test_config.py tests/agent/test_llm_factory.py
    tests/agent/test_dj_cohost_grounding.py` -> 39 passed;
    `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` -> pass;
    `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds
    -- --nocapture` -> 25 passed.
  - Release macOS signing/notarization remains externally blocked: a signed
    `cargo tauri build --bundles dmg` reached Apple notarization and failed
    with HTTP 403, "A required agreement is missing or has expired." This is an
    Apple Developer Program legal/account state blocker, not a local build or
    sidecar packaging failure. Do not claim a friend-ready signed/notarized DMG
    until that agreement is resolved and the signed DMG gate passes.
  - Pretag/release gate re-run on 2026-05-27: `bash
    scripts/dist/pretag_check.sh` originally returned `3 pass / 5 fail / 0
    warn`; the duplicate README pre-tag TODO marker was then removed while
    keeping the real Discord placeholder gate. Current result is `4 pass / 4
    fail / 0 warn`. Passing: README TODO-clean, updater pubkey real, bundled
    sidecar resource tree ready, and local Apple Developer ID cert present.
    Failing: Phase 16 ear-test signoff file is missing/not passed, Phase 17
    grading sheet is missing, GitHub Actions signing/upload secrets are
    incomplete, and the real Discord invite is not published.
    Focused release/package regression after the gate:
    `uv run pytest -q tests/repo/test_phase20_docs.py
    tests/tauri/test_updater_key_rotated.py
    tests/security/test_release_yml_signing_skips.py
    tests/security/test_verify_signed.py tests/install/test_windows_packaging_paths.py
    tests/install/test_macos_updater_artifact.py
    tests/install/test_macos_updater_artifact_ready.py` -> 82 passed, 1
    expected skip. The failing pretag status is therefore release-discharge
    debt, not a package smoke regression.
  - First-run required model setup was verified against the real upstream CLAP
    full-precision ONNX snapshot on 2026-05-27. Source CLI command:
    `VIBEMIX_CLAP_ONNX_DIR=/tmp/vibemix-clap-install-smoke-current uv run
    python -m vibemix library models --install required --json --progress`
    downloaded all six pinned files from
    `Xenova/larger_clap_music_and_speech`, emitted clean
    `VIBEMIX_MODEL_PROGRESS` frames, matched every pinned size/SHA, and returned
    `required_ready=true` / `install.ok=true`. Runtime ONNX smoke against that
    fresh cache loaded `ClapEngine(backend="onnx")` and produced finite,
    normalized 512d text and audio embeddings. The frozen PyInstaller sidecar
    then verified the same cache via `library models --install required --json
    --progress`, emitted six `verified` progress frames, and returned
    `install.ok=true`. The 757M temp cache and smoke WAV were deleted after the
    check.
  - Active planning prose cleanup: `.planning/PROJECT.md`,
    `.planning/ROADMAP.md`, and `.planning/STATE.md` no longer describe the
    v8.2 Library/Viber brain as Gemini or the current tech stack as a single
    Gemini conversational-brain path. The live/current statements now say local
    Codex owns Viber set-prep/chat, local CLAP ONNX owns library/search
    embeddings, and the live co-host brain is a separate config-resolved
    pipeline. Historical phase prose that discusses Gemini remains
    intentionally historical.
  - Stale active-note cleanup archived `.planning/REVIEW.md` and
    `.planning/seeds/copilot-memory-layer.md` into
    `.planning/archive/2026-05-27-stale-active-notes/` with a local ignored zip
    bundle. The review was tied to a May 25 GUI/stats/pill slice and referenced
    the removed Gemini `library/agent.py` path; the seed still proposed Gemini
    Embedding 002 as a future memory spine. Active replacement truth is the
    sweep map, current planning status docs, `docs/clap-engine.md`, and
    `docs/codex-agent.md`.
  - Current-day intelligence handoff notes were patched so they no longer
    point future agents at deleted Library Gemini/YouTube surfaces:
    `2026-05-27-intel-04-implementation-handoff.md` now targets
    `codex_curate.py`/Codex tests instead of `library/agent.py`, and
    `2026-05-27-intel-12-grounded-intelligence-tool-surface.md` now labels the
    Gemini harness removed and removes `ingest_youtube` from the chat tool
    group.
  - Historical phase-detail cleanup archived shipped v7.0/v8.0/v8.1 folders
    `.planning/phases/67-*` through `.planning/phases/82-*` into
    `.planning/archive/2026-05-27-v7-v8-1-phase-detail/phases/`, with a local
    ignored zip bundle and a small `.planning/phases/README.md` pointer. These
    detailed phase notes were the main active-surface source of stale
    no-CLAP/Gemini-only and removed `library/agent.py` hits. `docs/bench.md`
    now links to the archived Phase 81 validation record.
  - Current-state compression replaced the giant historical `.planning/STATE.md`
    with a concise product-state surface: v8.2 shipped, local CLAP ONNX owns
    library embeddings, local Codex owns Library/Viber set-prep/chat/build-set,
    live co-host brain remains separate/config-resolved, and release blockers
    are explicit. The pre-sweep state file was preserved at
    `.planning/archive/2026-05-27-state-snapshot/STATE-pre-product-sweep.md`
    with a local ignored zip bundle.
  - v8.2 detail cleanup moved the remaining active detailed phase folders
    `.planning/phases/{83-energy,87-agent,89-dj-library-ingest-auto-detect-dj-library-rekordbox-serato-tr,90-clap-swap-library-curator-embedding-engine-to-on-device-xeno}/`
    into `.planning/archive/2026-05-27-v8-2-active-phase-detail/phases/`, with
    a manifest and local ignored zip bundle. `.planning/phases/` now keeps only
    `README.md` and `v8.2-STATUS.md`, so future sessions start from compact
    current truth instead of stale in-flight Phase 89/90 prose.
  - Active research pointer cleanup reduced stale-term noise in
    `.planning/research/{SUMMARY,STACK,ARCHITECTURE,FEATURES,PITFALLS,questions,one-mind-charter,clap-engine-deep-dive,genre-from-embeddings}.md`,
    the Viber direction pointer README, and the 2026-05-27 intelligence notes.
    The long pre-build `vibe-mix-agent-engine-synthesis.md` body was archived
    at `.planning/archive/2026-05-27-stale-agent-engine-synthesis/` and replaced
    by a compact pointer to current v8.2/Codex/CLAP truth.
  - Pretag gate cleanup removed the duplicate README pre-tag TODO marker while
    keeping the real Discord placeholder gate intact. `scripts/dist/pretag_check.sh`
    now reports **4 pass / 4 fail / 0 warn**. Passing: README TODO-clean,
    updater pubkey real, bundled sidecar ready, local Apple Developer ID cert
    present. Remaining failures: Phase 16 signoff, Phase 17 grading CSV, GitHub
    release/signing/upload secrets, and real Discord invite.
  - Release-facing copy cleanup: README no longer claims the currently
    unpublished downloads are already signed/notarized. The Install section now
    says the v0.1.0 release gate requires Apple Developer ID signing +
    notarization on macOS and SignPath signing on Windows before downloads are
    published. The stale "What's shipped in v2.1" heading was replaced with
    "Current shipped surface"; the Discord runbook no longer tells Kaan to
    remove an already-removed TODO marker.
  - Package/release-shape verification after the copy cleanup:
    `uv run pytest -q tests/install/test_macos_local_dmg_build.py
    tests/install/test_macos_app_bundle_ready.py
    tests/install/test_macos_app_sidecar_symlink_repair.py
    tests/install/test_macos_dmg_artifact_ready.py
    tests/install/test_macos_updater_artifact.py
    tests/install/test_macos_updater_artifact_ready.py
    tests/install/test_prepare_tauri_build.py
    tests/install/test_sidecar_bundle_ready.py
    tests/install/test_windows_app_payload_ready.py
    tests/install/test_windows_packaging_paths.py
    tests/security/test_verify_signed.py
    tests/security/test_release_yml_signing_skips.py
    tests/repo/test_phase20_docs.py tests/repo/test_readme_shape.py` -> 155
    passed. `bash -n` over the dist signing/package scripts passed. Ruff found
    19 small import-order/unused-import issues in `scripts/dist` /
    `tests/install`; `uv run ruff check --fix ...` fixed them and the focused
    Ruff check is now clean.
  - Release-process guardrail cleanup: `docs/release-process.md` now makes
    `scripts/dist/pretag_check.sh` Step 0 before bump/tag and adds it to the
    release-day checklist, so the documented path cannot skip the current hard
    blockers. Verification: `uv run pytest -q tests/repo/test_phase20_docs.py
    tests/repo/test_readme_shape.py` -> 70 passed; `git diff --check` on the
    release-process/map files -> pass.
  - Active launch/ops doc refresh: `docs/launch-rotation.md` now labels the
    top hourly table as preserved v2.1 history and points current public-release
    execution at the `§SHIP-11` 4-shift section. `docs/bravoh-ops-endpoint.md`
    examples now use v0.1.0-style updater artifact URLs instead of old v2.1.0
    release URLs, and `docs/updater.md` replaced the proxy-side TODO wording
    with the current fallback contract. Verification:
    `uv run pytest -q tests/repo/test_launch_rotation_doc.py
    tests/launch/test_launch_rotation_ship_11.py
    tests/repo/test_kaan_action_ship_runbooks.py
    tests/dayzero/test_bravoh_ops_endpoint_doc.py
    tests/release/test_check_bravoh_server_ready.py
    tests/repo/test_phase20_docs.py tests/repo/test_readme_shape.py` -> 123
    passed; targeted stale-string `rg` -> no matches; `git diff --check` on the
    touched docs -> pass.
  - Active planning truth cleanup: `.planning/ROADMAP.md` now marks v8.2
    "Set Builder" as shipped on 2026-05-26 instead of in progress.
    `.planning/PROJECT.md` replaced the stale v3.0/v3.1 active blocker list
    and post-v3.1 current-state paragraph with the 2026-05-27 product-sweep
    truth: local Codex for Library/Viber set-prep/chat, local full-precision
    CLAP ONNX for embeddings, unsigned local macOS package smoke passed, and
    public/friend-ready release still blocked by the pretag failures,
    signed/notarized macOS release, signed updater rehearsal, Windows
    fresh-machine proof, and funded-key Build-a-Set ear-pass. Verification:
    `uv run pytest -q tests/repo/test_phase20_docs.py
    tests/repo/test_gate_42_hybrid_in_force.py` -> 36 passed;
    `git diff --check` on the touched planning files -> pass; targeted stale
    current-state `rg` -> no matches.
  - Memory/test/docs wording cleanup: the memory no-extraction tests now
    describe the injected local embedding protocol instead of `embed_content`
    via the retired `LibraryEmbedder`; `docs/clap-engine.md` now labels the
    matching legacy shim as test/migration-only; and the v8.1 roadmap line no
    longer points future agents at `ViberAgent`. Verification:
    `uv run pytest -q tests/memory/test_no_extraction.py
    tests/memory/test_ingest.py tests/memory/test_retrieval.py` -> 16 passed;
    repo planning guards -> 36 passed; targeted stale-string `rg` -> no
    matches; `git diff --check` on touched files -> pass.
  - Runtime wording cleanup removed stale "not yet wired" comments from the
    wizard smoke-test path, session bootstrap snapshot, and debrief feature
    probe. The wizard still intentionally uses the bundled offline greeting for
    first-run smoke so it can prove output playback without starting the full
    live co-host graph. Verification: `uv run pytest -q
    tests/wizard/test_smoke_test_exit.py tests/runtime/test_session_loop.py`
    -> 26 passed; targeted stale-string `rg` -> no matches; `git diff --check`
    on touched runtime/UI files -> pass. `npm` was not on this shell's PATH,
    but the running Vite server showed Homebrew `node@22`; running Vitest via
    `/opt/homebrew/opt/node@22/bin/node node_modules/vitest/vitest.mjs run
    --reporter=dot src/debrief` -> 54 passed.
  - `library budget` copy now advertises itself as a legacy Gemini-embedding
    what-if plus live token telemetry, not the current CLAP cost model. The
    active help output shows "Show legacy Gemini embedding what-if and live
    token telemetry." Verification: `uv run pytest -q tests/library/test_budget.py
    tests/scripts/test_cli_library_search.py` -> 17 passed, 1 expected xfail;
    `uv run python -m vibemix library --help` shows the corrected help line;
    `git diff --check` on the touched CLI/budget files -> pass.
  - Release/model status re-check after the cleanup: `scripts/dist/pretag_check.sh`
    remains the expected **4 pass / 4 fail / 0 warn** state (failures: Phase
    16 signoff, Phase 17 grading CSV, GitHub release/signing/upload secrets,
    real Discord invite). `uv run python -m vibemix library stats --json`
    reports `indexed=24`, `embedding_backend=clap`, `embedding_dim=512`,
    `agent_backend=codex`, `agent_ready=true`; `library models --json` reports
    required CLAP installed and all local model assets ready on this machine.
  - Package/CLI metadata cleanup: `tauri/ui/package.json` no longer says the
    webview is only a Phase 11 schema gate with wizard UI landing later;
    `vibemix --help` now describes `--wizard` as the first-run calibration
    wizard, `--session` as diagnostic/bootstrap IPC, and `--debrief` without
    old v2.0/v2.1 milestone copy; and the Tauri updater dependency comment no
    longer says the plugin is stubbed. Verification: `uv run python -m
    json.tool tauri/ui/package.json`, `uv run python -m vibemix --help`,
    targeted stale-string `rg`, `uv run pytest -q
    tests/test_main_smoke.py::test_smoke_01_version_exits_zero_without_devices_or_keys
    tests/main/test_debrief_short_circuits_audio_init.py` -> 4 passed,
    `git diff --check`, and `cargo check --manifest-path
    tauri/src-tauri/Cargo.toml` all passed.

Known caveat:

- Plain `cargo check --manifest-path tauri/src-tauri/Cargo.toml` and
  `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check` now pass;
  older `TAURI_CONFIG` override entries above are historical verification only.
- Full Python/UI/Rust source checks now pass, the source-spawn sidecar
  websocket/live-handler path has been restarted and verified, and source-backed
  Tauri desktop GUI verification (`cargo tauri dev`) has been completed. The
  repo-local arm64 sidecar bundle is now a real PyInstaller payload and direct
  `cargo tauri build --no-bundle` plus unsigned `--bundles app` pass locally;
  the local `.app` bundle requires the documented sidecar-symlink repair before
  execution/archive. A current-source local unsigned DMG drag-install rehearsal
  and unsigned macOS updater `.app.tar.gz` extraction smoke now pass. Signed /
  notarized DMG, signed updater rehearsal, and Windows fresh-machine proof are
  still not complete.
- The only remaining `LibraryEmbedder` construction path is the legacy
  implementation/tests themselves. Product recall/search/similarity/grounding
  paths route through `embed_factory.build_embedder()` and CLAP; import smokes
  confirm those product paths no longer load `vibemix.library.embed`.
- Auto-update remains unproven until a real macOS signed/notarized app archive
  and a Windows runner-produced NSIS updater artifact are published and used
  in a previous-version download/verify/install/restart rehearsal. The macOS
  helper and Windows workflow steps are now wired, including Windows NSIS
  Authenticode signing, but the live release runner and previous-version update
  rehearsal have not exercised them end to end.
- Remaining planning-history stale hits may still exist in older milestone and
  phase prose. Treat `.planning/codebase/STACK.md`, `CLAUDE.md`,
  `.planning/research/{SUMMARY,STACK,ARCHITECTURE,FEATURES,PITFALLS}.md`, and
  this sweep map as current product truth until those older references are
  either refreshed or archived.

## Do Not Do

- Do not commit all dirty files together.
- Do not claim the live running app includes current patches until restart/reload.
- Do not make heuristic cue detection the premium engine again.
- Do not present CLAP text prompts as exact semantic truth.
- Do not turn optional sensor denials into a blank deck. Show them as explicit
  badges/setup issues.
- Do not add another broad engine before backend setup UX is clean.
