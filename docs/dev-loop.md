<!-- SPDX-License-Identifier: Apache-2.0 -->
# Dev loop — what you edit is what you test

The Tauri shell normally runs a **pre-built PyInstaller binary** for the Python
sidecar (`vibemix-core`), resolved from `resource_dir()` and copied in by
`scripts/build_sidecar.py`. That means `cargo tauri dev` runs *whatever was last
built into* `tauri/src-tauri/binaries/` — so edits under `src/vibemix/` are
**invisible until you rebuild**.

This footgun bit us live: a sidecar fix (the Phase-52 BPM stabilizer `fd25337`)
was edited in `src/vibemix/` but the running app kept showing the old behavior,
because `cargo tauri dev` was still spawning the stale bundled binary. You can
burn a lot of time "fixing" something that the app you're testing never runs.

There are two dev loops. Use source-spawn for fast iteration; rebuild for
prod-fidelity verification.

## 1. Source-spawn (fast iteration — the default dev loop)

Set `VIBEMIX_DEV_SIDECAR=1` and `cargo tauri dev` spawns the sidecar **from
repo source** (`uv run python -m vibemix`) instead of the bundled binary. Your
`src/vibemix/` edits are reflected immediately — no PyInstaller round-trip.

```bash
VIBEMIX_DEV_SIDECAR=1 cargo tauri dev
```

Env contract (read by `tauri/src-tauri/src/sidecar.rs::resolve_sidecar_invocation`):

| Env var | Effect | Default |
|---|---|---|
| `VIBEMIX_DEV_SIDECAR=1` | spawn from source instead of the bundled binary | unset → bundled |
| `VIBEMIX_DEV_PYTHON` | interpreter to run `-m vibemix` (e.g. `/path/python3`) | `uv` → `uv run python -m vibemix` |
| `VIBEMIX_DEV_REPO` | cwd the sidecar runs in (the repo root) | `CARGO_MANIFEST_DIR`'s repo root |

The dev branch activates **only** when `VIBEMIX_DEV_SIDECAR=1`. When the flag is
absent the spawn path is byte-for-byte the shipped bundled-binary path (the same
binary, the same `--wizard` logic, the same exit-code sentinels 2/3 and
wizard→session handoff). A release build never reads dev env from any
IPC/config surface — env only — so the dev path can never leak into a shipped
binary. This is pinned by the `resolve_sidecar_*` unit tests in `sidecar.rs`.

**Standalone (no Tauri shell).** To live-drive / debug the sidecar by itself:

```bash
./scripts/dev/run_sidecar_from_source.sh            # real cohost
./scripts/dev/run_sidecar_from_source.sh --wizard   # wizard pass
```

That script exports the same `VIBEMIX_DEV_SIDECAR=1` / `VIBEMIX_DEV_REPO`
contract and execs `uv run python -m vibemix "$@"` from the repo root — so it
doubles as the documentation of the env names the Rust dev path reads.

Requirements: `uv` and the project venv must be present in your dev shell (the
standard `vibemix` dev setup — see `CONTRIBUTING.md`).

## 2. Rebuild (prod-fidelity verification)

Before you ship — or whenever you want to test the *actual* bundled binary
(PyInstaller packaging quirks, the `_internal/` tree, the no-`AIza` leak gate) —
rebuild the sidecar, then run `cargo tauri dev` **without** the flag so it spawns
the freshly-built binary:

```bash
uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec   # macOS
# uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec  # Windows
cargo tauri dev   # no VIBEMIX_DEV_SIDECAR -> runs the freshly-built bundle
```

`scripts/build_sidecar.py` is the canonical rebuild route: it runs PyInstaller
(`dist/vibemix-core/` onedir) and installs it into
`tauri/src-tauri/binaries/vibemix-core-<triple>/`. It is the slow path (full
PyInstaller build) — which is exactly why source-spawn exists for day-to-day
iteration.

## Rule of thumb

- Iterating on Python sidecar logic → **source-spawn** (`VIBEMIX_DEV_SIDECAR=1`).
- Verifying packaging / final release behavior → **rebuild**, then plain
  `cargo tauri dev`.
