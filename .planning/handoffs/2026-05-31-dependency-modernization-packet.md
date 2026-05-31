# Dependency Modernization Packet - 2026-05-31

Purpose: turn the "make it lighter, faster, more capable, latest libraries, no
conflicts" ask into safe modernization rings. This is planning/evidence only.
Do not change dependency manifests or lockfiles while the feature packages are
still dirty unless the user explicitly opens a dependency lane.

## Current Evidence

Fresh audit commands from this checkout:

- Refresh at 2026-05-31 14:11 +03 confirmed this evidence is still current.
  The refresh did not intentionally update manifests or lockfiles; after the
  Cargo dry-run, the only dependency-shaped dirty files were the already-assigned
  `tauri/ui/package.json` and `uv.lock` hunks from other lanes.
- `uv pip check`
  - 145 packages checked.
  - 1 incompatibility: `pyrekordbox` requires `sqlcipher3-wheels`, but it is not
    installed.
  - This is the known intentional XML-only Rekordbox decision documented in
    `pyproject.toml`; do not "fix" it by adding SQLCipher without reopening the
    bundle-size and SQLCipher-path decision.
- `uv pip list --outdated --format=json`
  - 50 outdated Python packages.
  - Highest-risk groups: `google-genai`, `openai`, LiveKit packages, `mcp`,
    OpenTelemetry packages, `numpy`, `tokenizers`, PyObjC, `protobuf`,
    `websockets`, `requests`, `ruff`, and `starlette`.
- `npm --prefix tauri/ui audit --omit=dev --json`
  - production vulnerabilities: 0 total.
  - Current install metadata reports 2 production packages and 510 total npm
    packages.
- `npm --prefix tauri/ui audit --json`
  - dev vulnerabilities: 6 total, 5 moderate and 1 high.
  - Main chain: `vitest` -> nested `vite` / `vite-node` / `@vitest/mocker` /
    `esbuild`.
  - High finding: `tmp <0.2.6`.
- `npm --prefix tauri/ui explain tmp`
  - `tmp@0.2.5` comes from `@gltf-transform/cli@4.3.0`.
- `npm --prefix tauri/ui ls --depth=0`
  - exits cleanly for the top-level tree. Current notable resolved versions:
    `@playwright/test` / `playwright` 1.60.0, Tauri JS API 2.11.0,
    `@tauri-apps/plugin-shell` 2.3.5, `@tauri-apps/plugin-store` 2.4.3,
    `vite` 6.4.2, `vitest` 2.1.9, and `typescript` 5.9.3.
- `npm --prefix tauri/ui outdated --json`
  - `vitest` 2.1.9 -> 4.1.7
  - `vite` 6.4.2 -> 8.0.14
  - `vite-plugin-static-copy` 2.3.2 -> 4.1.0
  - `typescript` 5.9.3 -> 6.0.3
  - `three` 0.170.0 -> 0.184.0
  - `@types/three` 0.170.0 -> 0.184.1
- `cargo update --manifest-path tauri/src-tauri/Cargo.toml --dry-run`
  - 47 compatible updates available.
  - Includes Tauri stack patch updates such as `tauri` 2.11.1 -> 2.11.2,
    `tauri-build` 2.6.1 -> 2.6.2, `tauri-utils` 2.9.1 -> 2.9.2,
    `tauri-plugin-global-shortcut` 2.3.1 -> 2.3.2, and
    `tauri-plugin-positioner` 2.3.1 -> 2.3.2.
  - Dry-run did not update the lockfile.
- `cargo tree --manifest-path tauri/src-tauri/Cargo.toml -d`
  - duplicate crate families exist, mostly from the Tauri/Wry ecosystem:
    `base64`, `bitflags`, `core-foundation`, `core-graphics`, `getrandom`,
    `hashbrown`, `indexmap`, `png`, `serde_json`, `thiserror`, `toml`,
    `uuid`, and `winnow`.
  - Treat these as dependency-graph facts, not immediate cleanup targets. Many
    are transitive and should be reduced only through Tauri/upstream updates.

## Ring 0 - Conflict And Lockfile Hygiene

Goal: make sure dependency work starts from a truthful baseline.

Do:

- Preserve the intentional `pyrekordbox` / `sqlcipher3-wheels` mismatch unless
  the Rekordbox SQLCipher path is deliberately reopened.
- Keep the residual `uv.lock` local-MOSS diff in its hold lane until the local
  TTS package is accepted or removed.
- Before any dependency commit, prove no unrelated product files are staged.

Commands:

```bash
uv pip check
git diff -- pyproject.toml uv.lock
git diff --cached --name-only
```

Promotion gate:

- The dependency commit must explain whether `uv pip check` still reports the
  intentional SQLCipher omission or whether the design decision changed.

## Ring 1 - Python Patch Updates With Low Runtime Risk

Candidate packages:

- `aiohappyeyeballs`, `certifi`, `click`, `google-auth`, `huggingface-hub`,
  `idna`, `jaraco-functools`, `jiter`, `mcp`, `more-itertools`,
  `pydantic-core`, `pyjwt`, `requests`, `rpds-py`, `ruff`, `sqlalchemy`,
  `typer`, `types-protobuf`, `watchfiles`, `wrapt`, `yarl`, `zipp`.

Why first:

- Mostly patch or small minor updates.
- Less likely to alter audio, model inference, or Tauri behavior.

Checks:

```bash
uv sync --group dev --extra ai-local
uv pip check
uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py
uv run pytest -q tests/scripts/test_check_dirty_package_plan.py
uv run pytest -q tests/library tests/ipc tests/ui_bus
```

Stop if:

- `uv.lock` pulls in local-MOSS or model-runtime changes that are not part of the
  selected ring.

## Ring 2 - Live AI And Runtime SDKs

Candidate packages:

- `google-genai` 2.0.1 -> 2.7.0
- `openai` 2.36.0 -> 2.38.0
- `livekit` 1.1.8 -> 1.1.9
- `livekit-protocol` 1.1.8 -> 1.1.11
- `livekit-agents` 1.5.14 -> 1.5.15
- `livekit-plugins-cartesia` 1.5.14 -> 1.5.15
- `livekit-plugins-google` 1.5.14 -> 1.5.15
- `livekit-plugins-openai` 1.5.14 -> 1.5.15

Why separate:

- These can change streaming behavior, model API shapes, TTS behavior, and live
  co-host latency.

Checks:

```bash
uv sync --group dev --extra ai-local
uv pip check
bash scripts/release/check_no_hardcoded_model.sh
uv run pytest -q tests/llm tests/runtime tests/prompts
VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session
```

Live proof:

- Attach to `127.0.0.1:8765`.
- Send `ipc.status.recheck`.
- Inspect `ui.log` and session `events.jsonl`.
- Confirm no brain-mute signature caused by the package update.

## Ring 3 - Model, Binary, And Platform-Adjacent Updates

Candidate packages:

- `numpy` 2.4.4 -> 2.4.6
- `tokenizers` 0.22.2 -> 0.23.1
- PyObjC family 12.1 -> 12.2
- `protobuf` 6.33.6 -> 7.35.0
- `websockets` 15.0.1 -> 16.0
- `starlette` 1.1.0 -> 1.2.1
- OpenTelemetry family 1.39.1 -> 1.42.1

Why separate:

- `numpy` and `tokenizers` can affect CLAP/CUE preprocessing and embedding
  behavior.
- PyObjC affects macOS capture/screen/audio permission paths.
- `protobuf`, `websockets`, `starlette`, and OpenTelemetry can affect protocol,
  server, or telemetry integration.

Checks:

```bash
uv sync --group dev --extra ai-local
uv pip check
uv run python -m vibemix library models --json
uv run pytest -q tests/library/test_clap_retrieval_eval.py tests/library/test_clap_real_retrieval.py
uv run pytest -q tests/audio tests/state tests/runtime tests/memory
uv run pytest -q tests/test_audio_macos.py
```

Missing stronger proof:

- A real ONNX `InferenceSession` test still does not exist in CI. Do not claim
  full model-regression safety until that gate is added or explicitly deferred.

## Ring 4 - UI Dev Tooling And Audit Findings

Candidate packages:

- `vitest` 2.1.9 -> 4.1.7
- `vite` 6.4.2 -> 8.0.14
- `vite-plugin-static-copy` 2.3.2 -> 4.1.0
- `typescript` 5.9.3 -> 6.0.3

Why separate:

- This likely clears the nested Vite/esbuild audit chain but crosses major
  versions for Vitest, Vite, and TypeScript.
- It can break test configuration, module resolution, generated IPC checks, and
  Playwright/e2e setup.

Checks:

```bash
npm --prefix tauri/ui audit --json
npm --prefix tauri/ui run check:ipc
npm --prefix tauri/ui test
npm --prefix tauri/ui run build
npm --prefix tauri/ui run test:e2e:pill
```

Special note:

- `tmp@0.2.5` comes from `@gltf-transform/cli@4.3.0`. If `npm audit fix` wants
  to change GLTF tooling, isolate it from the Vitest/Vite upgrade and verify the
  asset pipeline separately.

## Ring 5 - Three.js And Visual/3D Stack

Candidate packages:

- `three` 0.170.0 -> 0.184.0
- `@types/three` 0.170.0 -> 0.184.1
- possibly `@gltf-transform/cli` / `@gltf-transform/core` if selected to address
  the `tmp` chain.

Why separate:

- Visual output, screenshots, and any 3D/canvas behavior can regress without
  failing unit tests.

Checks:

```bash
npm --prefix tauri/ui test
npm --prefix tauri/ui run build
npm --prefix tauri/ui run test:e2e:visual
npm --prefix tauri/ui run test:e2e:pill
```

Proof:

- Capture before/after screenshots for session shell, Settings, pill, Viber, and
  any GLTF/Three surface.

## Ring 6 - Rust Compatible Updates

Candidate package group:

- Compatible Cargo dry-run updates, especially the Tauri stack patch updates.

Why separate:

- Tauri, Wry, plugin, tray, updater, and platform crates are release-critical.
- Duplicate crates should be observed through `cargo tree -d`, but not manually
  forced unless upstream compatible updates remove them.

Checks:

```bash
cargo update --manifest-path tauri/src-tauri/Cargo.toml
cargo fmt --manifest-path tauri/src-tauri/Cargo.toml
cargo check --manifest-path tauri/src-tauri/Cargo.toml
cargo test --manifest-path tauri/src-tauri/Cargo.toml
cargo tree --manifest-path tauri/src-tauri/Cargo.toml -d
```

Release proof:

- Sidecar bundle freshness checks.
- Tauri dev-source launch proof.
- Full signed/notarized build belongs to release packaging, not the first Cargo
  compatibility update.

## Staging Rules

- Do not mix dependency modernization with feature packages.
- Do not stage `uv.lock`, `tauri/ui/package-lock.json`, or `Cargo.lock` unless
  the matching manifest/ring is intentionally part of the same commit.
- Do not use `git add -A`.
- After staging, run:

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
```

If the cached diff contains product source outside the chosen ring, unstage it.

## Recommended Order

1. Keep dependency work paused until Package 2 + 3 IPC and any selected product
   packages either land or are explicitly deferred.
2. Start with Ring 0 to normalize the baseline and explain the known SQLCipher
   omission.
3. Do Ring 1 Python low-risk patches.
4. Do Ring 4 UI dev-audit remediation if the team wants to remove the current
   npm dev-audit findings.
5. Do Ring 6 Rust compatible updates.
6. Do Ring 2 live SDK updates only with live co-host proof ready.
7. Do Ring 3 model/platform updates and Ring 5 visual/Three updates only with
   their stronger runtime/visual gates.

## Non-Goals

- No dependency update should claim the app is faster, smaller, safer, or more
  capable without measuring the relevant path.
- No model/runtime dependency update should claim CLAP/CUE regression safety
  until real-model proof is added or explicitly deferred.
- No broad repo-wide Ruff/autofix pass belongs in dependency modernization while
  the feature tree is dirty.
